import { LitElement, html, css } from "lit";
import { resolveLanguage, translate } from "./singbox-panel-i18n.js";

/**
 * Visual editor for the sing-box panel card. Shown by the Lovelace card
 * editor when the card type is picked from the picker; edits the same config
 * keys that can be set in YAML.
 */

// update_interval selector values (seconds); 0 = live (render on every HA
// state change).
const INTERVAL_OPTIONS = [0, 1, 2, 3, 5, 10, 30, 60];

// unique_id markers of the ha-singbox entities (kept in sync with the card):
//   select: "{entry_id}_group_{group_tag}"
//   ping:   "{entry_id}_ping_{proxy_tag}"
//   mode:   "{entry_id}_clash_mode"
const GROUP_MARK = "_group_";
const PING_MARK = "_ping_";
const CLASH_MODE_SUFFIX = "_clash_mode";
const SYNTHETIC_GLOBAL = "GLOBAL";

// Card sections that can be shown/hidden from the editor. The order here is
// the order of the switches, which mirrors the card layout top to bottom.
const SECTIONS = [
    "show_test_all",
    "show_speeds",
    "show_chart",
    "show_totals",
    "show_groups",
    "show_connections",
];

class SingBoxPanelCardEditor extends LitElement {
    static properties = {
        hass: {},
        _config: { state: true },
        _candidates: { state: true },
    };

    static styles = css`
        .row {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 4px 0;
        }
        .row ha-switch {
            flex: none;
        }
        .row .label {
            flex: 1;
            font-size: 13px;
            overflow-wrap: anywhere;
        }
        ha-textfield,
        ha-select {
            width: 100%;
        }
        .block {
            margin-top: 12px;
        }
        .block-title {
            font-size: 13px;
            color: var(--secondary-text-color);
        }
        .hint {
            font-size: 11px;
            color: var(--secondary-text-color);
            margin: 2px 0 8px;
        }
        .exclude-tag {
            font-family: var(--paper-font-common-base-code-family, monospace);
        }
    `;

    setConfig(config) {
        this._config = { ...config };
        this._loadCandidates();
    }

    firstUpdated() {
        this._loadCandidates();
    }

    updated(changed) {
        // hass may arrive after firstUpdated (HA wires the editor after
        // creating it) — load the outbound list once it is available.
        if (changed.has("hass")) this._loadCandidates();
    }

    _lang() {
        return resolveLanguage(this._config, this.hass);
    }

    _t(key, params = {}) {
        return translate(this._lang(), key, params);
    }

    _update(key, value) {
        this._config = { ...this._config, [key]: value };
        this.dispatchEvent(
            new CustomEvent("config-changed", {
                detail: { config: this._config },
                bubbles: true,
                composed: true,
            })
        );
    }

    _onText(ev, key) {
        this._update(key, ev.target.value);
    }

    _onSwitch(ev, key) {
        this._update(key, ev.target.checked);
    }

    // ha-select changed its contract between HA releases: older builds are
    // mwc-select based (list-item children, fires `change` with target.value),
    // current builds take an `options` array and fire `selected` with
    // detail.value. Both events are bound and the shape that does not apply
    // is ignored, so a pick works on any HA.
    _onSelectChange(ev, key) {
        // current ha-select never fires `change`; a mwc `change` has no
        // detail.value payload
        if (ev.detail && "value" in ev.detail) return;
        this._applySelect(key, ev.target && ev.target.value);
    }

    _onSelectSelected(ev, key) {
        // mwc also fires `selected`, but only with detail.index — the value
        // comes later via `change`; current ha-select carries detail.value
        if (!ev.detail || !("value" in ev.detail)) return;
        this._applySelect(key, ev.detail.value);
    }

    _applySelect(key, value) {
        if (value === undefined || value === null || value === "") return;
        if (key === "update_interval") value = Number(value);
        this._update(key, value);
    }

    _toggleExclude(tag, checked) {
        const next = new Set(this._config.exclude_outbounds || []);
        if (checked) {
            next.add(tag);
        } else {
            next.delete(tag);
        }
        this._update("exclude_outbounds", [...next].sort());
    }

    // -- outbound discovery (drives the exclude check list) -----------------

    // Loads the outbound tags the card can display, mirroring the card's
    // entity model: ping sensors for standalone nodes, the options of every
    // group select for members. Falls back to the comma text field when the
    // registry cannot be read (or yields nothing).
    async _loadCandidates() {
        if (this._candidates !== undefined || this._loading) return;
        if (!this.hass || typeof this.hass.callWS !== "function") return;
        this._loading = true;
        try {
            const registry = await this.hass.callWS({
                type: "config/entity_registry/list",
            });
            this._candidates = this._candidateTags(registry || []);
        } catch (_) {
            this._candidates = [];
        } finally {
            this._loading = false;
        }
    }

    _candidateTags(registry) {
        const deviceId = this._config && this._config.device_id;
        const tags = new Set();
        for (const e of registry) {
            if (e.platform !== "singbox") continue;
            if (deviceId && e.device_id !== deviceId) continue;
            const uid = e.unique_id || "";
            const domain = (e.entity_id || "").split(".")[0];
            if (domain === "sensor" && uid.includes(PING_MARK)) {
                const tag = uid.slice(
                    uid.lastIndexOf(PING_MARK) + PING_MARK.length
                );
                if (tag !== SYNTHETIC_GLOBAL) tags.add(tag);
            } else if (
                domain === "select" &&
                uid.includes(GROUP_MARK) &&
                !uid.endsWith(CLASH_MODE_SUFFIX)
            ) {
                const state =
                    this.hass.states && this.hass.states[e.entity_id];
                const options =
                    state &&
                    state.attributes &&
                    Array.isArray(state.attributes.options)
                        ? state.attributes.options
                        : [];
                options.forEach((tag) => tags.add(tag));
            }
        }
        return [...tags].sort((a, b) => a.localeCompare(b));
    }

    // -- selector data ------------------------------------------------------

    _languageOptions() {
        return [
            { value: "auto", label: this._t("editor.languageAuto") },
            { value: "ru", label: "Русский" },
            { value: "en", label: "English" },
        ];
    }

    _intervalOptions() {
        return INTERVAL_OPTIONS.map((n) => ({
            value: String(n),
            label: this._intervalLabel(n),
        }));
    }

    _intervalLabel(n) {
        if (n === 0) return this._t("editor.intervalLive");
        return this._t("editor.intervalSec", { n });
    }

    render() {
        const cfg = this._config || {};
        const interval = Number(cfg.update_interval) || 0;
        const excluded = new Set(cfg.exclude_outbounds || []);
        const languageOptions = this._languageOptions();
        const intervalOptions = this._intervalOptions();
        const hasCandidates = (this._candidates || []).length > 0;
        return html`
            <ha-textfield
                label=${this._t("editor.title")}
                value=${cfg.title || "Sing-box"}
                @change=${(ev) => this._onText(ev, "title")}
            ></ha-textfield>

            <div class="block">
                <ha-select
                    label=${this._t("editor.language")}
                    .value=${cfg.language || "auto"}
                    .options=${languageOptions}
                    @change=${(ev) => this._onSelectChange(ev, "language")}
                    @selected=${(ev) => this._onSelectSelected(ev, "language")}
                >
                    ${languageOptions.map(
                        (o) => html`
                            <mwc-list-item value=${o.value}>
                                ${o.label}
                            </mwc-list-item>
                        `
                    )}
                </ha-select>
            </div>

            <div class="block">
                <ha-select
                    label=${this._t("editor.interval")}
                    .value=${String(interval)}
                    .options=${intervalOptions}
                    @change=${(ev) =>
                        this._onSelectChange(ev, "update_interval")}
                    @selected=${(ev) =>
                        this._onSelectSelected(ev, "update_interval")}
                >
                    ${intervalOptions.map(
                        (o) => html`
                            <mwc-list-item value=${o.value}>
                                ${o.label}
                            </mwc-list-item>
                        `
                    )}
                </ha-select>
                <div class="hint">${this._t("editor.intervalHint")}</div>
            </div>

            <div class="block">
                <div class="block-title">${this._t("editor.sections")}</div>
                <div class="hint">${this._t("editor.sectionsHint")}</div>
                ${SECTIONS.map(
                    (key) => html`
                        <div class="row">
                            <span class="label"
                                >${this._t(`editor.${key}`)}</span
                            >
                            <ha-switch
                                .checked=${cfg[key] !== false}
                                @change=${(ev) => this._onSwitch(ev, key)}
                            ></ha-switch>
                        </div>
                    `
                )}
            </div>

            ${hasCandidates
                ? html`
                      <div class="block">
                          <div class="block-title">
                              ${this._t("editor.exclude")}
                          </div>
                          <div class="hint">${this._t("editor.excludeHint")}</div>
                          ${this._candidates.map(
                              (tag) => html`
                                  <div class="row exclude-row">
                                      <span class="label exclude-tag"
                                          >${tag}</span
                                      >
                                      <ha-switch
                                          .checked=${excluded.has(tag)}
                                          @change=${(ev) =>
                                              this._toggleExclude(
                                                  tag,
                                                  ev.target.checked
                                              )}
                                      ></ha-switch>
                                  </div>
                              `
                          )}
                      </div>
                  `
                : html`
                      <ha-textfield
                          label=${this._t("editor.exclude")}
                          value=${(cfg.exclude_outbounds || []).join(", ")}
                          @change=${(ev) =>
                              this._update(
                                  "exclude_outbounds",
                                  ev.target.value
                                      .split(",")
                                      .map((t) => t.trim())
                                      .filter(Boolean)
                              )}
                      ></ha-textfield>
                      <div class="hint">${this._t("editor.excludeHint")}</div>
                  `}

            <ha-textfield
                label=${this._t("editor.device")}
                value=${cfg.device_id || ""}
                @change=${(ev) => this._onText(ev, "device_id")}
            ></ha-textfield>
            <div class="hint">${this._t("editor.deviceHint")}</div>

            <ha-textfield
                label=${this._t("editor.entity")}
                value=${cfg.entity || ""}
                @change=${(ev) => this._onText(ev, "entity")}
            ></ha-textfield>
            <div class="hint">${this._t("editor.entityHint")}</div>
        `;
    }
}

// The bundle can be evaluated in more than one module instance, so only
// register the element when it is not defined yet (see the card itself).
if (!customElements.get("singbox-panel-card-editor")) {
    customElements.define("singbox-panel-card-editor", SingBoxPanelCardEditor);
}