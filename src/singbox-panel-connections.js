/**
 * Active-connections list with filtering for the sing-box panel card.
 *
 * The list is fed by the integration's `singbox/connections` WebSocket
 * command. Everything here is presentation plus local filtering: the card
 * keeps a small history of snapshots so a connection that closes between two
 * polls does not blink out of the list immediately.
 *
 * Filtering is intentionally cheap and local (no round-trip to HA): a free
 * text query matched against host/process/outbound/rule, plus a set of quick
 * toggles (network, protocol, outbound).
 */

import { html } from "lit";

/** Normalize one connection coming from the WS command. */
export function normalizeConnection(raw) {
    if (!raw || typeof raw !== "object") return null;
    const id = String(raw.id ?? "");
    if (!id) return null;
    return {
        id,
        network: String(raw.network ?? ""),
        protocol: String(raw.protocol ?? ""),
        source: String(raw.source ?? ""),
        destination: String(raw.destination ?? ""),
        host: String(raw.host ?? raw.domain ?? ""),
        rule: String(raw.rule ?? ""),
        outbound: String(raw.outbound ?? ""),
        chain: Array.isArray(raw.chain) ? raw.chain.map(String) : [],
        process: String(raw.process ?? ""),
        upload: numberOrZero(raw.upload),
        download: numberOrZero(raw.download),
        uploadTotal: numberOrZero(raw.upload_total ?? raw.uploadTotal),
        downloadTotal: numberOrZero(raw.download_total ?? raw.downloadTotal),
        startedAt: numberOrZero(raw.created_at ?? raw.createdAt),
    };
}

function numberOrZero(value) {
    const n = Number(value);
    return Number.isFinite(n) ? n : 0;
}

/**
 * Apply the filter state to a connection list.
 *
 * @param {Array<object>} connections normalized connections
 * @param {object} filter
 * @param {string} [filter.query] free text
 * @param {string} [filter.network] exact network match ("" = all)
 * @param {string} [filter.protocol] exact protocol match ("" = all)
 * @param {string} [filter.outbound] exact outbound match ("" = all)
 * @param {string} [filter.onlyActive] "all" | "closed"
 * @returns {Array<object>} filtered connections
 */
export function filterConnections(connections, filter = {}) {
    const query = String(filter.query ?? "")
        .trim()
        .toLowerCase();
    const network = String(filter.network ?? "");
    const protocol = String(filter.protocol ?? "");
    const outbound = String(filter.outbound ?? "");
    return connections.filter((c) => {
        if (network && c.network !== network) return false;
        if (protocol && c.protocol !== protocol) return false;
        if (outbound && c.outbound !== outbound) return false;
        if (!query) return true;
        // One haystack per connection keeps the common case (a single typed
        // word) to a single includes() instead of five.
        const haystack = [
            c.host,
            c.process,
            c.outbound,
            c.rule,
            c.destination,
            c.source,
            c.protocol,
            c.network,
        ]
            .join(" ")
            .toLowerCase();
        return haystack.includes(query);
    });
}

/** Distinct non-empty values of one field, sorted, for the filter selects. */
export function distinctValues(connections, field) {
    const values = new Set();
    for (const c of connections) {
        const value = c[field];
        if (value) values.add(value);
    }
    return [...values].sort((a, b) => a.localeCompare(b));
}

/** Sort active connections: most recently started first, then by volume. */
export function sortConnections(connections) {
    return [...connections].sort((a, b) => {
        if (b.startedAt !== a.startedAt) return b.startedAt - a.startedAt;
        return b.downloadTotal + b.uploadTotal - (a.downloadTotal + a.uploadTotal);
    });
}

/**
 * Render the connections section.
 *
 * @param {object} options
 * @param {Array<object>} options.connections already filtered + sorted
 * @param {number} options.total number before filtering (for the counter)
 * @param {object} options.filter current filter state
 * @param {Array<string>} options.networks available networks
 * @param {Array<string>} options.protocols available protocols
 * @param {Array<string>} options.outbounds available outbounds
 * @param {(patch: object) => void} options.onFilter filter change handler
 * @param {(id: string) => void} options.onClose close-one handler
 * @param {() => void} options.onCloseAll close-all handler
 * @param {boolean} options.closingAll close-all request in flight
 * @param {(t: string, p?: object) => string} options.t translate
 * @param {(bytes: number) => string} options.formatBytes
 * @param {(ms: number) => string} options.formatAge
 * @returns {import("lit").TemplateResult}
 */
export function renderConnections({
    connections,
    total,
    filter,
    networks,
    protocols,
    outbounds,
    onFilter,
    onClose,
    onCloseAll,
    closingAll,
    t,
    formatBytes,
    formatAge,
}) {
    const hasFilters = Boolean(
        filter.query ||
            filter.network ||
            filter.protocol ||
            filter.outbound
    );
    return html`
        <div class="connections">
            <div class="conn-head">
                <span class="conn-title">${t("connections.title")}</span>
                <span class="conn-count">
                    ${hasFilters
                        ? t("connections.countFiltered", {
                              shown: connections.length,
                              total,
                          })
                        : t("connections.count", { total })}
                </span>
                ${total > 0
                    ? html`<button
                          class="conn-close-all"
                          ?disabled=${closingAll}
                          title=${t("connections.closeAll")}
                          @click=${() => onCloseAll()}
                      >
                          <ha-icon icon="mdi:close-circle-multiple-outline"></ha-icon>
                      </button>`
                    : ""}
            </div>

            ${total > 0
                ? html`
                      <div class="conn-filters">
                          <input
                              class="conn-search"
                              type="search"
                              .value=${filter.query || ""}
                              placeholder=${t("connections.search")}
                              aria-label=${t("connections.search")}
                              @input=${(e) =>
                                  onFilter({ query: e.target.value })}
                          />
                          <select
                              class="conn-select"
                              aria-label=${t("connections.network")}
                              .value=${filter.network || ""}
                              @change=${(e) =>
                                  onFilter({ network: e.target.value })}
                          >
                              <option value="">${t("connections.allNetworks")}</option>
                              ${networks.map(
                                  (n) => html`<option
                                      value=${n}
                                      ?selected=${filter.network === n}
                                  >
                                      ${n}
                                  </option>`
                              )}
                          </select>
                          <select
                              class="conn-select"
                              aria-label=${t("connections.protocol")}
                              .value=${filter.protocol || ""}
                              @change=${(e) =>
                                  onFilter({ protocol: e.target.value })}
                          >
                              <option value="">${t("connections.allProtocols")}</option>
                              ${protocols.map(
                                  (p) => html`<option
                                      value=${p}
                                      ?selected=${filter.protocol === p}
                                  >
                                      ${p}
                                  </option>`
                              )}
                          </select>
                          <select
                              class="conn-select"
                              aria-label=${t("connections.outbound")}
                              .value=${filter.outbound || ""}
                              @change=${(e) =>
                                  onFilter({ outbound: e.target.value })}
                          >
                              <option value="">${t("connections.allOutbounds")}</option>
                              ${outbounds.map(
                                  (o) => html`<option
                                      value=${o}
                                      ?selected=${filter.outbound === o}
                                  >
                                      ${o}
                                  </option>`
                              )}
                          </select>
                          ${hasFilters
                              ? html`<button
                                    class="conn-reset"
                                    @click=${() =>
                                        onFilter({
                                            query: "",
                                            network: "",
                                            protocol: "",
                                            outbound: "",
                                        })}
                                >
                                    ${t("connections.reset")}
                                </button>`
                              : ""}
                      </div>
                  `
                : ""}

            ${connections.length === 0
                ? html`<div class="conn-empty">
                      ${total === 0
                          ? t("connections.empty")
                          : t("connections.noMatch")}
                  </div>`
                : html`<div class="conn-list">
                      ${connections.map(
                          (c) => html`
                              <div class="conn-row">
                                  <div class="conn-main">
                                      <span class="conn-host">
                                          ${c.host || c.destination || c.source}
                                      </span>
                                      <span class="conn-sub">
                                          ${[
                                              c.protocol,
                                              c.network,
                                              c.outbound,
                                          ]
                                              .filter(Boolean)
                                              .join(" · ")}
                                      </span>
                                  </div>
                                  <div class="conn-stats">
                                      <span class="conn-stat up">
                                          <ha-icon icon="mdi:arrow-up"></ha-icon>
                                          ${formatBytes(c.uploadTotal)}
                                      </span>
                                      <span class="conn-stat down">
                                          <ha-icon icon="mdi:arrow-down"></ha-icon>
                                          ${formatBytes(c.downloadTotal)}
                                      </span>
                                      <span class="conn-age">
                                          ${formatAge(c.startedAt)}
                                      </span>
                                  </div>
                                  <button
                                      class="conn-close"
                                      title=${t("connections.close")}
                                      @click=${() => onClose(c.id)}
                                  >
                                      <ha-icon icon="mdi:close"></ha-icon>
                                  </button>
                              </div>
                          `
                      )}
                  </div>`}
        </div>
    `;
}
