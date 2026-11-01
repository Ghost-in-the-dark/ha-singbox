import { LitElement, html } from "lit";
import { cardStyles } from "./singbox-panel-card-style.js";
import { resolveLanguage, translate } from "./singbox-panel-i18n.js";
import "./singbox-panel-card-editor.js";
import { niceCeiling, renderTrafficChart } from "./singbox-panel-graph.js";
import {
    distinctValues,
    filterConnections,
    normalizeConnection,
    renderConnections,
    sortConnections,
} from "./singbox-panel-connections.js";

const CARD_VERSION = "0.1.17";

// unique_id formats used by the ha-singbox integration:
//   select: "{entry_id}_group_{group_tag}"
//   ping:   "{entry_id}_ping_{proxy_tag}"
//   mode:   "{entry_id}_clash_mode"
const GROUP_MARK = "_group_";
const PING_MARK = "_ping_";
const CLASH_MODE_SUFFIX = "_clash_mode";
// Synthetic clash-API group present in /proxies but with no backing outbound
// (url-test on it always fails with 404) — never surfaced by the card.
const SYNTHETIC_GLOBAL = "GLOBAL";
// How long an optimistic outbound selection is shown before the card falls
// back to the entity state when the integration never confirms the change.
const PENDING_SELECT_TTL_MS = 10000;

const DEFAULT_TITLE = "Sing-box";

// Traffic chart: how many samples the ring buffer holds and how far back the
// window spans. One sample per hass push (the integration pushes about once a
// second), so 300 samples cover roughly five minutes at full rate and are
// thinned down to the window when renders are slower.
const CHART_MAX_SAMPLES = 300;
const CHART_WINDOW_MS = 5 * 60 * 1000;
// Minimum spacing between two chart samples (Home Assistant pushes faster).
const CHART_MIN_SAMPLE_MS = 900;

class SingBoxPanelCard extends LitElement {
    // _hass is intentionally NOT a reactive property: HA hands us a fresh
    // hass object on every state change and we decide when to re-render
    // ourselves (see _scheduleRender), so the configurable update interval
    // actually throttles the work. Lit would otherwise re-render on its own
    // whenever the hass object identity changes.
    static properties = {
        _state: { state: true }, // "loading" | "error" | "ready"
        _model: { state: true },
        _testing: { state: true }, // { [groupTag]: true }
        _testingAll: { state: true }, // batch url-test in progress
    };

    static styles = cardStyles;

    constructor() {
        super();
        this._hass = null;
        this._config = {};
        this._discovered = false;
        this._state = "loading";
        this._model = null;
        this._testing = {};
        this._testingAll = false;
        this._fallbackNote = null; // { key, params }
        this._error = null; // { key, params }
        // Rendering throttle state (update_interval > 0).
        this._lastRenderAt = 0;
        this._renderTimer = null;
        // Optimistic outbound selections: entity_id -> { tag, ts }.
        this._pendingSelections = {};
        // Traffic history for the chart (bounded ring buffer) and the value of
        // the last sample so a sample is only stored when traffic changed.
        this._chartSamples = [];
        // Connections: the list comes from the singbox/connections WS command,
        // polled on the card's own cadence (it is not part of the state push).
        this._connections = [];
        this._connectionsSupported = true;
        this._connectionsError = null;
        this._connFilter = {
            query: "",
            network: "",
            protocol: "",
            outbound: "",
        };
        this._closingAll = false;
        this._connPollTimer = null;
        this._connFetchInFlight = false;
        this._chartTimer = null;
    }

    static getStubConfig() {
        return {
            title: DEFAULT_TITLE,
            show_test_all: true,
            show_speeds: true,
            show_totals: true,
            show_chart: true,
            show_groups: true,
            show_connections: true,
            exclude_outbounds: [],
            update_interval: 0,
            language: "auto",
        };
    }

    static getConfigElement() {
        return document.createElement("singbox-panel-card-editor");
    }

    setConfig(config) {
        if (!config || typeof config !== "object") {
            throw new Error("Invalid configuration");
        }
        const prev = this._config || {};
        const next = {
            title: DEFAULT_TITLE,
            show_test_all: true,
            show_speeds: true,
            show_totals: true,
            show_chart: true,
            show_groups: true,
            show_connections: true,
            exclude_outbounds: [],
            update_interval: 0,
            language: "auto",
            ...config,
        };
        // Section switches: only an explicit false hides a block, so configs
        // written before these keys existed keep showing everything.
        for (const key of [
            "show_test_all",
            "show_speeds",
            "show_totals",
            "show_chart",
            "show_groups",
            "show_connections",
        ]) {
            next[key] = next[key] !== false;
        }
        // exclude_outbounds accepts a comma-separated string in YAML and an
        // array from the editor; normalize to a trimmed string array.
        next.exclude_outbounds = (Array.isArray(next.exclude_outbounds)
            ? next.exclude_outbounds
            : String(next.exclude_outbounds ?? "")
                  .split(",")
        )
            .map((t) => String(t).trim())
            .filter(Boolean);
        // update_interval: seconds; 0 = live (render on every HA push).
        const interval = Number(next.update_interval);
        next.update_interval =
            Number.isFinite(interval) && interval > 0
                ? Math.min(interval, 3600)
                : 0;
        this._config = next;

        // A pin (device/entity) or an exclusion-list change alters which
        // entities the card shows; the discovered model must be rebuilt.
        // Exclusions previously only applied on the very first discovery,
        // so editing the config did not hide the tags until a full reload.
        if (this._discovered && this._needsRediscovery(prev, next)) {
            this._discovered = false;
            if (this._hass) this._discover();
        }
        // Config edits (visual editor / YAML) render right away; a re-render
        // triggered by a later hass push would otherwise show stale values.
        this.requestUpdate();
    }

    _needsRediscovery(prev, next) {
        if (prev.device_id !== next.device_id || prev.entity !== next.entity) {
            return true;
        }
        const prevList = prev.exclude_outbounds || [];
        const nextList = next.exclude_outbounds || [];
        return (
            prevList.length !== nextList.length ||
            nextList.some((tag) => !prevList.includes(tag))
        );
    }

    getCardSize() {
        return 4;
    }

    get hass() {
        return this._hass;
    }

    set hass(hass) {
        this._hass = hass;
        if (hass && !this._discovered) {
            this._discovered = true;
            this._discover();
        }
        if (hass) {
            // Sample the speed sensors on every push so the chart has history
            // even when rendering itself is throttled.
            this._recordChartSample();
        }
        // Re-render on every hass push, gated by the configured interval.
        if (hass) this._scheduleRender();
    }

    connectedCallback() {
        super.connectedCallback();
        if (this._discovered) this._startConnectionPolling();
    }

    disconnectedCallback() {
        super.disconnectedCallback();
        this._stopConnectionPolling();
    }

    // -- localization --------------------------------------------------------

    _lang() {
        return resolveLanguage(this._config, this._hass);
    }

    _t(key, params = {}) {
        return translate(this._lang(), key, params);
    }

    // -- discovery ----------------------------------------------------------

    async _discover() {
        this._state = "loading";
        this._fallbackNote = null;
        try {
            const registry = await this._hass.callWS({
                type: "config/entity_registry/list",
            });
            if (!Array.isArray(registry)) {
                throw new Error("registry is unavailable");
            }
            const isMarkedGroup = (e) =>
                this._domain(e) === "select" &&
                e.unique_id &&
                e.unique_id.includes(GROUP_MARK) &&
                !e.unique_id.endsWith(CLASH_MODE_SUFFIX);
            const markedGroups = (list) => list.filter(isMarkedGroup);

            // Pin to a specific sing-box instance (device/entity). The pin is
            // a preference, not a hard filter: when the registry does not link
            // the sing-box entities to the device/entry (common with this
            // integration), the card falls back to marker search across the
            // whole registry so it still works.
            let entries = registry;
            if (this._config.device_id) {
                const byDevice = registry.filter(
                    (e) => e.device_id === this._config.device_id
                );
                if (markedGroups(byDevice).length > 0) {
                    entries = byDevice;
                } else {
                    this._fallbackNote = {
                        key: "fallback.device",
                        params: {
                            device: this._config.device_id,
                            count: byDevice.length,
                        },
                    };
                }
            } else if (this._config.entity) {
                const pinned = registry.find(
                    (e) => e.entity_id === this._config.entity
                );
                if (!pinned) {
                    this._fallbackNote = {
                        key: "fallback.entityNotFound",
                        params: { entity: this._config.entity },
                    };
                } else {
                    const byPinned = registry.filter(
                        (e) =>
                            (pinned.config_entry_id &&
                                e.config_entry_id === pinned.config_entry_id) ||
                            (pinned.device_id && e.device_id === pinned.device_id)
                    );
                    if (markedGroups(byPinned).length > 0) {
                        entries = byPinned;
                    } else {
                        this._fallbackNote = {
                            key: "fallback.entityNoGroups",
                            params: { entity: this._config.entity },
                        };
                    }
                }
            }
            // sing-box entities are recognized by their unique_id markers
            // ({entry_id}_group_<tag>, {entry_id}_ping_<tag>, ...) rather than
            // by the config entry, so the card works even when the registry
            // does not link them to an entry.
            this._model = this._buildModel(entries);
            if (this._model.groups.length === 0) {
                const allSelects = registry.filter(
                    (e) => this._domain(e) === "select"
                );
                const markedSelects = markedGroups(registry);
                const pingSensors = registry.filter(
                    (e) =>
                        this._domain(e) === "sensor" &&
                        e.unique_id &&
                        e.unique_id.includes(PING_MARK)
                );
                const deviceCount = this._config.device_id
                    ? registry.filter(
                          (e) => e.device_id === this._config.device_id
                      ).length
                    : null;
                const pinRecords = this._config.device_id
                    ? registry.filter(
                          (e) => e.device_id === this._config.device_id
                      )
                    : [];
                const pinSample = pinRecords
                    .slice(0, 5)
                    .map((e) => {
                        const uid = e.unique_id
                            ? e.unique_id.slice(0, 40)
                            : "—";
                        return `${e.entity_id} (${this._domain(e)}) [${uid}]`;
                    })
                    .join(", ");
                if (pinRecords.length) {
                    console.warn(
                        "singbox-panel: records matched by pin:",
                        pinRecords
                            .map(
                                (e) =>
                                    `${e.entity_id} ${this._domain(e)} ${e.unique_id ?? ""}`
                            )
                            .join("\n")
                    );
                }
                const sample = markedSelects
                    .slice(0, 5)
                    .map((e) => `${e.entity_id} [${e.unique_id}]`)
                    .join(", ");
                this._state = "error";
                if (markedSelects.length === 0 && deviceCount !== null) {
                    this._error = {
                        key: "errors.groupsDevice",
                        params: {
                            count: deviceCount,
                            selects: allSelects.length,
                            pings: pingSensors.length,
                            sample: pinSample,
                        },
                    };
                } else if (markedSelects.length === 0) {
                    this._error = {
                        key: "errors.groupsNone",
                        params: {
                            selects: allSelects.length,
                            pings: pingSensors.length,
                        },
                    };
                } else {
                    this._error = {
                        key: "errors.groupsBadUid",
                        params: { sample },
                    };
                }
                return;
            }
            if (this._fallbackNote) {
                console.warn(
                    `singbox-panel: ${this._t(
                        this._fallbackNote.key,
                        this._fallbackNote.params
                    )}`
                );
            }
            this._state = "ready";
            this._startConnectionPolling();
            this._fetchConnections();
        } catch (err) {
            this._state = "error";
            this._error = {
                key: "errors.loadFailed",
                params: {
                    msg: err && err.message ? err.message : String(err),
                },
            };
        }
    }

    _buildModel(registryEntries) {
        const excluded = new Set(this._config.exclude_outbounds || []);
        // Remember which config entry the discovered entities belong to: the
        // connections command is entry-scoped, and the registry is the only
        // place the card can learn the id from. Only sing-box-marked entities
        // count — an unpinned discovery walks the whole registry, and the first
        // foreign config_entry_id would point the command at another
        // integration.
        this._discoveredEntryId = null;
        for (const e of registryEntries) {
            if (!e || !e.config_entry_id || !e.unique_id) continue;
            const marked =
                e.unique_id.includes(GROUP_MARK) ||
                e.unique_id.includes(PING_MARK) ||
                e.unique_id.endsWith(CLASH_MODE_SUFFIX);
            if (marked) {
                this._discoveredEntryId = e.config_entry_id;
                break;
            }
        }
        const pings = {}; // proxy tag -> ping sensor entity_id
        for (const e of registryEntries) {
            if (
                this._domain(e) === "sensor" &&
                e.unique_id &&
                e.unique_id.includes(PING_MARK)
            ) {
                const tag = e.unique_id.slice(
                    e.unique_id.lastIndexOf(PING_MARK) + PING_MARK.length
                );
                if (tag === SYNTHETIC_GLOBAL) continue;
                pings[tag] = e.entity_id;
            }
        }

        const groups = [];
        const inGroups = new Set();
        for (const e of registryEntries) {
            if (
                this._domain(e) !== "select" ||
                !e.unique_id ||
                !e.unique_id.includes(GROUP_MARK) ||
                e.unique_id.endsWith(CLASH_MODE_SUFFIX)
            ) {
                continue;
            }
            const groupTag = e.unique_id.slice(
                e.unique_id.lastIndexOf(GROUP_MARK) + GROUP_MARK.length
            );
            const state = this._hass.states[e.entity_id];
            const options =
                state && state.attributes && Array.isArray(state.attributes.options)
                    ? state.attributes.options
                    : [];
            options.forEach((tag) => inGroups.add(tag));
            const visible = options
                .filter((tag) => !excluded.has(tag))
                .map((tag) => ({
                    tag,
                    pingEntity: pings[tag] || null,
                }));
            // A group whose every outbound is excluded is hidden entirely.
            if (visible.length === 0) continue;
            groups.push({
                tag: groupTag,
                entityId: e.entity_id,
                options: visible,
            });
        }

        // Standalone outbounds (VPN interfaces, direct links, ...) are proxies
        // with a ping sensor that belong to no group.
        const standalone = Object.keys(pings)
            .filter((tag) => !inGroups.has(tag) && !excluded.has(tag))
            .sort()
            .map((tag) => ({ tag, pingEntity: pings[tag] }));

        const sensorBySuffix = (suffix) => {
            const e = registryEntries.find(
                (ent) =>
                    this._domain(ent) === "sensor" &&
                    ent.unique_id &&
                    ent.unique_id.endsWith(suffix)
            );
            return e ? e.entity_id : null;
        };
        const clashMode = registryEntries.find(
            (e) =>
                this._domain(e) === "select" &&
                e.unique_id &&
                e.unique_id.endsWith(CLASH_MODE_SUFFIX)
        );

        return {
            version: sensorBySuffix("_version"),
            uplink: sensorBySuffix("_uplink"),
            downlink: sensorBySuffix("_downlink"),
            uplinkTotal: sensorBySuffix("_uplink_total"),
            downlinkTotal: sensorBySuffix("_downlink_total"),
            memory: sensorBySuffix("_memory"),
            connectionsIn: sensorBySuffix("_connections_in"),
            clashMode: clashMode ? clashMode.entity_id : null,
            groups,
            standalone,
        };
    }

    // -- helpers ------------------------------------------------------------

    _entity(id) {
        return id ? this._hass.states[id] : undefined;
    }

    // Real HA registry entries from config/entity_registry/list have no
    // `domain` field (only `platform` + the entity_id) — the domain is the
    // entity_id prefix.
    _domain(e) {
        if (e.entity_id) return e.entity_id.split(".")[0];
        return e.domain || "";
    }

    _stateValue(id) {
        const state = this._entity(id);
        if (!state) return null;
        return state.state === "unavailable" ? null : state.state;
    }

    _formatSpeed(id) {
        const state = this._entity(id);
        if (!state || state.state === "unavailable" || state.state === "unknown") {
            return { value: "—", unit: "" };
        }
        const value = Number(state.state);
        if (!Number.isFinite(value)) {
            return { value: "—", unit: "" };
        }
        return {
            value: value.toLocaleString(undefined, { maximumFractionDigits: 1 }),
            unit: state.attributes && state.attributes.unit_of_measurement
                ? state.attributes.unit_of_measurement
                : "",
        };
    }

    _formatBytes(id) {
        const state = this._entity(id);
        if (!state || state.state === "unavailable" || state.state === "unknown") {
            return "—";
        }
        const value = Number(state.state);
        if (!Number.isFinite(value)) {
            return "—";
        }
        // HA converts DATA_SIZE sensors (memory, totals) to their suggested
        // unit, so the state may arrive in KiB/MiB/GiB (or kB/MB/GB) — never
        // treat it as raw bytes.
        const unit = (state.attributes && state.attributes.unit_of_measurement) || "B";
        const toBytes = {
            B: 1,
            kB: 1e3,
            MB: 1e6,
            GB: 1e9,
            TB: 1e12,
            KiB: 1024,
            MiB: 1024 ** 2,
            GiB: 1024 ** 3,
            TiB: 1024 ** 4,
        };
        const bytes = value * (toBytes[unit] || 1);
        const units = ["B", "KiB", "MiB", "GiB", "TiB"];
        let scaled = bytes;
        let idx = 0;
        while (scaled >= 1024 && idx < units.length - 1) {
            scaled /= 1024;
            idx += 1;
        }
        const digits = idx ? 1 : 0;
        return `${scaled.toLocaleString(undefined, { maximumFractionDigits: digits })} ${units[idx]}`;
    }

    _ping(option) {
        const state = this._entity(option.pingEntity);
        if (!state || state.state === "unavailable" || state.state === "unknown") {
            return null;
        }
        const ms = Number(state.state);
        return Number.isFinite(ms) ? ms : null;
    }

    _pingClass(ms) {
        if (ms === null) return "none";
        if (ms <= 100) return "good";
        if (ms <= 300) return "warn";
        return "bad";
    }

    _pingText(ms) {
        return ms === null ? "—" : `${ms} ms`;
    }

    // -- traffic chart -------------------------------------------------------

    // Called on every hass push: reads the current up/down speed sensors and
    // appends a sample to the bounded history. Sampling here (rather than on a
    // timer) keeps the chart in step with the card's own refresh interval.
    _recordChartSample(force = false) {
        if (!this._model) return;
        const up = this._speedValue(this._model.uplink);
        const down = this._speedValue(this._model.downlink);
        // Nothing to plot yet (sensors missing or unavailable).
        if (up === null && down === null) return;
        const now = Date.now();
        const last = this._chartSamples[this._chartSamples.length - 1];
        // `hass` arrives as often as Home Assistant likes, but the chart only
        // needs one point per second: coalesce anything faster than that into
        // the previous sample instead of blowing through the buffer.
        if (!force && last && now - last.t < CHART_MIN_SAMPLE_MS) {
            last.up = up || 0;
            last.down = down || 0;
            return;
        }
        this._chartSamples = [
            ...this._chartSamples,
            { t: now, up: up || 0, down: down || 0 },
        ];
        this._pruneChartSamples(now);
    }

    _pruneChartSamples(now) {
        const cutoff = now - CHART_WINDOW_MS;
        let samples = this._chartSamples.filter((s) => s.t >= cutoff);
        // Hard cap even if pushes arrive faster than expected.
        if (samples.length > CHART_MAX_SAMPLES) {
            samples = samples.slice(samples.length - CHART_MAX_SAMPLES);
        }
        this._chartSamples = samples;
    }

    // Numeric value of a speed sensor in its own unit, or null.
    _speedValue(id) {
        const state = this._entity(id);
        if (!state || state.state === "unavailable" || state.state === "unknown") {
            return null;
        }
        const value = Number(state.state);
        return Number.isFinite(value) ? value : null;
    }

    _chartCaption() {
        const m = this._model;
        const peak = this._chartSamples.reduce(
            (acc, s) => Math.max(acc, s.up || 0, s.down || 0),
            0
        );
        const unit =
            (this._entity(m && m.downlink) &&
                this._entity(m.downlink).attributes &&
                this._entity(m.downlink).attributes.unit_of_measurement) ||
            "";
        const fmt = (v) =>
            v.toLocaleString(undefined, { maximumFractionDigits: 1 });
        return this._t("chart.peak", {
            value: `${fmt(peak)} ${unit}`.trim(),
        });
    }

    // Top-of-scale label ("0 — 5 kB/s") so the chart is readable without
    // hovering: the ceiling is the rounded peak the chart draws against.
    _chartScaleText() {
        const peak = niceCeiling(
            this._chartSamples.reduce(
                (acc, s) => Math.max(acc, s.up || 0, s.down || 0),
                0
            )
        );
        const unit =
            (this._entity(this._model && this._model.downlink) &&
                this._entity(this._model.downlink).attributes &&
                this._entity(this._model.downlink).attributes.unit_of_measurement) ||
            "";
        const fmt = (v) =>
            v.toLocaleString(undefined, { maximumFractionDigits: 1 });
        return `0 – ${fmt(peak)} ${unit}`.trim();
    }

    _renderChart() {
        const now = Date.now();
        const first = this._chartSamples[0];
        // A fixed window would squeeze the first seconds of history into a
        // spike at the right edge. Start at the oldest sample while the
        // buffer is still shorter than the window, and slide to the full
        // window once it fills up.
        const start = first
            ? Math.max(first.t, now - CHART_WINDOW_MS)
            : now - CHART_WINDOW_MS;
        return renderTrafficChart({
            samples: this._chartSamples,
            startMs: start,
            endMs: now,
            emptyText: this._t("chart.empty"),
            peakText: this._chartSamples.length > 1 ? this._chartCaption() : "",
            scaleText:
                this._chartSamples.length > 1 ? this._chartScaleText() : "",
        });
    }

    // -- connections ---------------------------------------------------------

    // Polls the integration's WS command. Deliberately independent of the hass
    // state push: the connection list is not a set of entities, so nothing
    // would trigger a refresh otherwise.
    _startConnectionPolling() {
        if (this._connPollTimer) return;
        const interval = this._refreshMs() > 0 ? this._refreshMs() : 2000;
        const tick = () => {
            this._connPollTimer = setTimeout(() => {
                this._fetchConnections();
                tick();
            }, Math.max(interval, 1000));
        };
        tick();
        // The chart cannot rely on hass pushes: Home Assistant only hands the
        // card a new hass object when a state actually changes, so a quiet
        // link (or a stalled sensor) would leave the chart empty forever.
        // Sample on the same timer instead.
        this._startChartTimer();
    }

    _startChartTimer() {
        if (this._chartTimer) return;
        const tick = () => {
            this._chartTimer = setTimeout(() => {
                this._recordChartSample();
                this._scheduleRender();
                tick();
            }, 1000);
        };
        tick();
    }

    _stopChartTimer() {
        if (this._chartTimer) {
            clearTimeout(this._chartTimer);
            this._chartTimer = null;
        }
    }

    _stopConnectionPolling() {
        if (this._connPollTimer) {
            clearTimeout(this._connPollTimer);
            this._connPollTimer = null;
        }
        this._stopChartTimer();
    }

    async _fetchConnections() {
        if (!this._hass || this._connFetchInFlight) return;
        // The list is an optional feature: older integrations simply do not
        // have the command, and that must not break the rest of the card.
        if (this._config.show_connections === false) return;
        this._connFetchInFlight = true;
        try {
            // The command validates entry_id with cv.string, which rejects
            // null — omit the key entirely when nothing is pinned.
            const message = { type: "singbox/connections" };
            const entryId = this._entryId();
            if (entryId) message.entry_id = entryId;
            let res;
            try {
                res = await this._hass.callWS(message);
            } catch (err) {
                // The registry can name an entry that is no longer loaded (a
                // re-added instance, a disabled entry). The id is only a hint,
                // so retry entry-less before treating it as a failure.
                if (!entryId) throw err;
                res = await this._hass.callWS({ type: "singbox/connections" });
            }
            const supported = res && res.supported !== false;
            const list = Array.isArray(res && res.connections)
                ? res.connections.map(normalizeConnection).filter(Boolean)
                : [];
            const changed =
                supported !== this._connectionsSupported ||
                (supported && list.length !== this._connections.length);
            this._connectionsSupported = supported;
            this._connections = supported ? sortConnections(list) : [];
            this._connectionsError = null;
            // Not reactive on purpose: a poll must respect the render throttle
            // instead of forcing a paint every second.
            if (changed) this._scheduleRender();
        } catch (err) {
            const msg = String(err && err.message ? err.message : err);
            // "Unknown command" / "not found" means an integration without the
            // feature — show the calm "unsupported" note, not an error.
            if (/unknown command|not_found|not found/i.test(msg)) {
                this._connectionsSupported = false;
                this._connections = [];
                this._connectionsError = null;
            } else {
                this._connectionsError = { msg };
            }
        } finally {
            this._connFetchInFlight = false;
        }
    }

    // The WS command accepts an entry_id to target one sing-box instance. It
    // is derived from the discovered entities when the user pinned nothing.
    _entryId() {
        return this._config.entry_id || this._discoveredEntryId || null;
    }

    _setConnFilter(patch) {
        this._connFilter = { ...this._connFilter, ...patch };
        // A filter edit is a direct user action: render immediately.
        this._requestRender();
    }

    async _closeConnection(id) {
        if (!this._hass || !id) return;
        try {
            await this._callService("singbox", "close_connection", {
                connection_id: id,
            });
            // Drop it locally right away; the next poll confirms.
            this._connections = this._connections.filter((c) => c.id !== id);
            this._requestRender();
        } catch (err) {
            console.error("singbox-panel: close_connection failed", err);
        }
    }

    async _closeAllConnections() {
        if (!this._hass || this._closingAll) return;
        this._closingAll = true;
        try {
            await this._callService("singbox", "close_all_connections", {});
            this._connections = [];
            this._requestRender();
        } catch (err) {
            console.error("singbox-panel: close_all_connections failed", err);
        } finally {
            setTimeout(() => {
                this._closingAll = false;
            }, 2000);
        }
    }

    _formatConnBytes(bytes) {
        const units = ["B", "KiB", "MiB", "GiB", "TiB"];
        let scaled = Number(bytes) || 0;
        let idx = 0;
        while (scaled >= 1024 && idx < units.length - 1) {
            scaled /= 1024;
            idx += 1;
        }
        const digits = idx ? 1 : 0;
        return `${scaled.toLocaleString(undefined, {
            maximumFractionDigits: digits,
        })} ${units[idx]}`;
    }

    _formatConnAge(startedAt) {
        if (!startedAt) return "";
        const sec = Math.max(0, Math.round((Date.now() - startedAt) / 1000));
        if (sec < 60) return `${sec}s`;
        const min = Math.floor(sec / 60);
        if (min < 60) return `${min}m`;
        const hours = Math.floor(min / 60);
        if (hours < 24) return `${hours}h`;
        return `${Math.floor(hours / 24)}d`;
    }

    _renderConnections() {
        if (this._config.show_connections === false) return "";
        if (!this._connectionsSupported) {
            return html`
                <div class="connections">
                    <div class="conn-head">
                        <span class="conn-title">${this._t("connections.title")}</span>
                    </div>
                    <div class="conn-empty">${this._t("connections.unsupported")}</div>
                </div>
            `;
        }
        const all = this._connections;
        return renderConnections({
            connections: filterConnections(all, this._connFilter),
            total: all.length,
            filter: this._connFilter,
            networks: distinctValues(all, "network"),
            protocols: distinctValues(all, "protocol"),
            outbounds: distinctValues(all, "outbound"),
            onFilter: (patch) => this._setConnFilter(patch),
            onClose: (id) => this._closeConnection(id),
            onCloseAll: () => this._closeAllConnections(),
            closingAll: this._closingAll,
            t: (key, params) => this._t(key, params),
            formatBytes: (bytes) => this._formatConnBytes(bytes),
            formatAge: (ms) => this._formatConnAge(ms),
        });
    }

    // -- render throttle -----------------------------------------------------

    // Seconds between value re-renders; 0 disables the throttle (live).
    _refreshMs() {
        const sec = Number(this._config.update_interval) || 0;
        return Math.min(Math.max(sec, 0), 3600) * 1000;
    }

    // Called on every hass push. With update_interval = 0 the card renders on
    // each push (previous behaviour). With an interval set, renders happen at
    // most every N seconds; `force` (user interaction) bypasses the throttle.
    _scheduleRender(force = false) {
        if (!this._hass) return;
        const interval = this._refreshMs();
        if (interval <= 0 || force) {
            this._requestRender();
            return;
        }
        const now = Date.now();
        const deadline = this._lastRenderAt + interval;
        if (now >= deadline) {
            this._requestRender();
            return;
        }
        if (this._renderTimer) return; // a render is already pending
        this._renderTimer = setTimeout(() => {
            this._renderTimer = null;
            this._requestRender();
        }, deadline - now);
    }

    _requestRender() {
        if (this._renderTimer) {
            clearTimeout(this._renderTimer);
            this._renderTimer = null;
        }
        this.requestUpdate();
    }

    // Selected outbound shown in the group header. Renders the optimistic
    // selection (the tag the user tapped) until the real entity state catches
    // up or the intent expires, so a switch is visible immediately even when
    // the render throttle would otherwise delay the next refresh.
    _groupCurrent(group) {
        const state = this._entity(group.entityId);
        const live =
            state && state.state !== "unavailable" ? state.state : null;
        const pending = this._pendingSelections[group.entityId];
        if (!pending) return live;
        if (pending.tag === live || Date.now() - pending.ts > PENDING_SELECT_TTL_MS) {
            delete this._pendingSelections[group.entityId];
            return live;
        }
        return pending.tag;
    }

    // -- actions ------------------------------------------------------------

    // The integration went through three service schemas: entity services
    // (v0.3.7, target required), a strict schema (v0.3.8, extra keys banned)
    // and ALLOW_EXTRA (v0.3.9). Send the target entity and retry without it
    // when the schema rejects the extra key — works with every version.
    async _callService(domain, service, data, target) {
        try {
            await this._hass.callService(
                domain,
                service,
                target ? { ...data, entity_id: target } : data
            );
        } catch (err) {
            const msg = String(err && err.message ? err.message : err);
            if (target && /extra keys not allowed/.test(msg)) {
                await this._hass.callService(domain, service, data);
                return;
            }
            throw err;
        }
    }

    async _selectNode(groupTag, nodeTag, target) {
        if (!this._hass || !target) return;
        // Show the switch right away; the header uses this until the select
        // entity state confirms the new outbound (see _groupCurrent).
        this._pendingSelections[target] = { tag: nodeTag, ts: Date.now() };
        this._scheduleRender(true);
        try {
            await this._callService(
                "singbox",
                "select_outbound",
                { group_tag: groupTag, outbound_tag: nodeTag },
                target
            );
        } catch (err) {
            console.error("singbox-panel: select_outbound failed", err);
            delete this._pendingSelections[target];
        }
        // Flush again once the service round-trip finished — by then HA has
        // usually pushed the new select state already.
        this._scheduleRender(true);
    }

    // Re-runs the url-test of every visible outbound of one group. A single
    // url_test on the group *tag* is not enough: sing-box only tests the
    // currently selected outbound of a Selector group, so when the urltest
    // auto-entry is selected (the common case) none of the node pings would
    // refresh. Testing each node individually works on both backends and
    // updates every chip. Errors on individual outbounds don't abort.
    async _testGroup(group) {
        const options = group.options || [];
        if (!this._hass || this._testing[group.tag] || options.length === 0) {
            return;
        }
        const nodeFlags = Object.fromEntries(
            options.map((o) => [o.tag, true])
        );
        this._testing = { ...this._testing, [group.tag]: true, ...nodeFlags };
        try {
            await Promise.all(
                options.map((o) =>
                    this._callService(
                        "singbox",
                        "url_test",
                        { outbound_tag: o.tag },
                        o.pingEntity || group.entityId
                    ).catch((err) => {
                        console.error(
                            `singbox-panel: url_test failed for ${o.tag}`,
                            err
                        );
                    })
                )
            );
        } finally {
            setTimeout(() => {
                const next = { ...this._testing };
                delete next[group.tag];
                for (const o of options) delete next[o.tag];
                this._testing = next;
            }, 4000);
        }
    }

    async _pingNode(nodeTag, target) {
        if (!this._hass || this._testing[nodeTag]) return;
        this._testing = { ...this._testing, [nodeTag]: true };
        try {
            await this._callService(
                "singbox",
                "url_test",
                { outbound_tag: nodeTag },
                target
            );
        } catch (err) {
            console.error("singbox-panel: url_test failed", err);
        } finally {
            setTimeout(() => {
                this._testing = { ...this._testing, [nodeTag]: false };
            }, 4000);
        }
    }

    // One tap re-runs the url-test of every visible outbound (each node of
    // every group plus every standalone) — the per-node form works on both
    // backends, unlike testing group tags (see _testGroup). Errors on
    // individual outbounds don't abort the batch.
    async _testAll() {
        if (!this._hass || !this._model || this._testingAll) return;
        this._testingAll = true;
        const seen = new Set();
        const targets = [];
        for (const g of this._model.groups) {
            for (const o of g.options) {
                if (seen.has(o.tag)) continue;
                seen.add(o.tag);
                targets.push({ tag: o.tag, target: o.pingEntity || g.entityId });
            }
        }
        for (const p of this._model.standalone) {
            if (seen.has(p.tag)) continue;
            seen.add(p.tag);
            targets.push({ tag: p.tag, target: p.pingEntity });
        }
        try {
            await Promise.all(
                targets.map((t) =>
                    this._callService(
                        "singbox",
                        "url_test",
                        { outbound_tag: t.tag },
                        t.target
                    ).catch((err) => {
                        console.error(
                            `singbox-panel: url_test failed for ${t.tag}`,
                            err
                        );
                    })
                )
            );
        } finally {
            setTimeout(() => {
                this._testingAll = false;
            }, 4000);
        }
    }

    // -- render -------------------------------------------------------------

    render() {
        // A render is the moment the throttle measures against: every actual
        // paint (loading/error/data) resets the next-refresh deadline.
        this._lastRenderAt = Date.now();

        if (this._state === "error") {
            const err = this._error || { key: "errors.loadFailed", params: {} };
            return html`
                <div class="card">
                    <div class="state-msg">
                        ${this._t(err.key, err.params)}
                    </div>
                </div>
            `;
        }
        if (this._state === "loading" || !this._model) {
            return html`
                <div class="card">
                    <div class="state-msg">
                        <div class="spinner"></div>
                        <span>${this._t("loading")}</span>
                    </div>
                </div>
            `;
        }

        const m = this._model;
        const version = this._stateValue(m.version);
        const mode = this._stateValue(m.clashMode);
        const showTestAll =
            this._config.show_test_all !== false &&
            (m.groups.length > 0 || m.standalone.length > 0);
        return html`
            <div class="card">
                <div class="header">
                    <h2>${this._config.title}</h2>
                    <div class="meta">
                        ${version ? html`<span>${version}</span>` : ""}
                        ${mode ? html`<span> · ${mode}</span>` : ""}
                    </div>
                    ${showTestAll
                        ? html`
                              <button
                                  class="test-all-btn"
                                  ?disabled=${this._testingAll}
                                  @click=${() => this._testAll()}
                              >
                                  <ha-icon icon="mdi:flash-outline"></ha-icon>
                                  ${this._testingAll
                                      ? this._t("testing")
                                      : this._t("testAll")}
                              </button>
                          `
                        : ""}
                </div>

                ${this._config.show_speeds !== false
                    ? html`<div class="speeds">
                          ${this._speedTile(
                              "up",
                              "mdi:arrow-up-bold",
                              this._t("speedUp"),
                              m.uplink
                          )}
                          ${this._speedTile(
                              "down",
                              "mdi:arrow-down-bold",
                              this._t("speedDown"),
                              m.downlink
                          )}
                      </div>`
                    : ""}

                ${this._config.show_chart !== false
                    ? this._renderChart()
                    : ""}

                ${this._config.show_totals !== false
                    ? html`<div class="totals">
                          ${this._totalChip(
                              "mdi:arrow-up",
                              this._formatBytes(m.uplinkTotal)
                          )}
                          ${this._totalChip(
                              "mdi:arrow-down",
                              this._formatBytes(m.downlinkTotal)
                          )}
                          ${this._totalChip(
                              "mdi:memory",
                              this._formatBytes(m.memory)
                          )}
                          ${this._totalChip(
                              "mdi:lan-connect",
                              this._stateValue(m.connectionsIn)
                          )}
                      </div>`
                    : ""}

                ${this._config.show_groups !== false
                    ? html`
                          ${m.groups.map((g) => this._renderGroup(g))}
                          ${m.standalone.length
                              ? this._renderStandalone(m.standalone)
                              : ""}
                      `
                    : ""}

                ${this._renderConnections()}

                ${this._fallbackNote
                    ? html`<div class="fallback-note">${this._t(
                          this._fallbackNote.key,
                          this._fallbackNote.params
                      )}</div>`
                    : ""}
                <div class="footer">sing-box panel · v${CARD_VERSION}</div>
            </div>
        `;
    }

    _renderStandalone(proxies) {
        return html`
            <div class="group">
                <div class="group-head">
                    <span class="group-name">Outbound</span>
                </div>
                <div class="nodes">
                    ${proxies.map((p) => this._renderStandaloneNode(p))}
                </div>
            </div>
        `;
    }

    _renderStandaloneNode(proxy) {
        const ms = this._ping(proxy);
        const pinging = Boolean(this._testing[proxy.tag]);
        return html`
            <div class="node">
                <span class="node-name standalone">${proxy.tag}</span>
                ${ms !== null
                    ? html`<span class="ping ${this._pingClass(ms)}">${this._pingText(ms)}</span>`
                    : ""}
                <button
                    class="node-ping"
                    title=${this._t("pingTitle", { tag: proxy.tag })}
                    ?disabled=${pinging}
                    @click=${() => this._pingNode(proxy.tag, proxy.pingEntity)}
                >
                    <ha-icon icon="mdi:radar"></ha-icon>
                </button>
            </div>
        `;
    }

    _speedTile(kind, icon, label, entityId) {
        const { value, unit } = this._formatSpeed(entityId);
        return html`
            <div class="tile ${kind}">
                <ha-icon icon=${icon}></ha-icon>
                <div class="tile-body">
                    <div class="tile-label">${label}</div>
                    <div class="tile-value">${value}<span class="unit">${unit}</span></div>
                </div>
            </div>
        `;
    }

    _totalChip(icon, text) {
        return html`
            <span class="chip-stat">
                <ha-icon icon=${icon}></ha-icon>
                <b>${text}</b>
            </span>
        `;
    }

    _renderGroup(group) {
        const current = this._groupCurrent(group);
        const testing = Boolean(this._testing[group.tag]);
        return html`
            <div class="group">
                <div class="group-head">
                    <span class="group-name">${group.tag}</span>
                    <span class="group-current">
                        ${current ? html`→ <b>${current}</b>` : ""}
                    </span>
                    <button
                        class="test-btn"
                        ?disabled=${testing}
                        @click=${() => this._testGroup(group)}
                    >
                        <ha-icon icon="mdi:flash-outline"></ha-icon>
                        ${testing ? this._t("testing") : this._t("test")}
                    </button>
                </div>
                <div class="nodes">
                    ${group.options.map(
                        (option) => this._renderNode(group, option, current)
                    )}
                </div>
            </div>
        `;
    }

    _renderNode(group, option, current) {
        const ms = this._ping(option);
        const active = option.tag === current;
        const pinging = Boolean(this._testing[option.tag]);
        return html`
            <div class="node ${active ? "active" : ""}">
                <button
                    class="node-select"
                    title=${this._t("selectTitle", { tag: option.tag })}
                    @click=${() => this._selectNode(group.tag, option.tag, group.entityId)}
                >
                    <span class="node-name">${option.tag}</span>
                    ${ms !== null
                        ? html`<span class="ping ${this._pingClass(ms)}">${this._pingText(ms)}</span>`
                        : ""}
                </button>
                <button
                    class="node-ping"
                    title=${this._t("pingTitle", { tag: option.tag })}
                    ?disabled=${pinging}
                    @click=${() => this._pingNode(option.tag, option.pingEntity || group.entityId)}
                >
                    <ha-icon icon="mdi:radar"></ha-icon>
                </button>
            </div>
        `;
    }
}

// The card can be loaded twice: once as an extra frontend module injected
// into index.html and once as a Lovelace resource. Both resolve to the same
// URL, but the two import paths may use different credentials (the bootstrap
// script sets crossorigin="use-credentials"), so the browser can evaluate the
// module in two separate instances. Guard both registrations: on the modern
// path the second instance would otherwise throw NotSupportedError from
// define(), and the element would stop rendering after the page settles.
if (!customElements.get("singbox-panel-card")) {
    customElements.define("singbox-panel-card", SingBoxPanelCard);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "singbox-panel-card")) {
    window.customCards.push({
        type: "singbox-panel-card",
        name: "Sing-box Panel",
        description: "Панель мониторинга и управления прокси sing-box",
        preview: false,
    });
}