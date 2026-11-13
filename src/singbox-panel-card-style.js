import { css } from "lit";

export const cardStyles = css`
    :host {
        display: block;
        font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif);
    }
    .card {
        background: var(--ha-card-background, var(--card-background-color));
        border-radius: var(--ha-card-border-radius, 12px);
        box-shadow: var(--ha-card-box-shadow, none);
        padding: 16px;
        color: var(--primary-text-color);
    }

    /* ---------- header ---------- */
    .header {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 8px;
        margin-bottom: 12px;
    }
    .header h2 {
        margin: 0;
        font-size: 18px;
        font-weight: 600;
        color: var(--primary-text-color);
    }
    .header .meta {
        font-size: 12px;
        color: var(--secondary-text-color);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        flex: 1;
        min-width: 0;
    }
    .header .test-all-btn {
        flex: none;
        display: inline-flex;
        align-items: center;
        gap: 4px;
        border: none;
        border-radius: 8px;
        padding: 5px 10px;
        font-size: 12px;
        font-weight: 500;
        cursor: pointer;
        color: var(--primary-text-color);
        background: var(--secondary-background-color, rgba(0, 0, 0, 0.05));
        transition: background 0.15s ease, opacity 0.15s ease;
    }
    .header .test-all-btn:hover {
        background: var(--primary-color);
        color: var(--text-primary-color, #fff);
    }
    .header .test-all-btn[disabled] {
        opacity: 0.5;
        cursor: default;
        pointer-events: none;
    }
    .header .test-all-btn ha-icon {
        --mdc-icon-size: 14px;
    }

    /* ---------- speed tiles ---------- */
    .speeds {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
        margin-bottom: 14px;
    }
    .tile {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px 12px;
        border-radius: 12px;
        background: var(--secondary-background-color, rgba(0, 0, 0, 0.04));
        min-width: 0;
    }
    .tile ha-icon {
        --mdc-icon-size: 22px;
        flex: none;
    }
    .tile .tile-body {
        min-width: 0;
    }
    .tile .tile-label {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: var(--secondary-text-color);
    }
    .tile .tile-value {
        font-size: 24px;
        font-weight: 600;
        line-height: 1.15;
        font-variant-numeric: tabular-nums;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .tile .tile-value .unit {
        font-size: 13px;
        font-weight: 500;
        color: var(--secondary-text-color);
        margin-left: 3px;
    }
    .tile.up ha-icon { color: #ff7043; }
    .tile.down ha-icon { color: var(--success-color, #2e7d32); }

    /* ---------- totals strip ---------- */
    .totals {
        display: flex;
        flex-wrap: wrap;
        gap: 4px 16px;
        margin-bottom: 14px;
        font-size: 12px;
        color: var(--secondary-text-color);
    }
    .totals .chip-stat {
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .totals .chip-stat b {
        color: var(--primary-text-color);
        font-weight: 600;
        font-variant-numeric: tabular-nums;
    }

    /* ---------- groups ---------- */
    .group {
        margin-top: 14px;
        border-top: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
        padding-top: 12px;
    }
    .group-head {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 10px;
    }
    .group-head .group-name {
        font-size: 14px;
        font-weight: 600;
        color: var(--primary-text-color);
    }
    .group-head .group-current {
        font-size: 12px;
        color: var(--secondary-text-color);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .group-head .group-current b {
        color: var(--primary-color);
        font-weight: 600;
    }
    .group-head .test-btn {
        margin-left: auto;
        flex: none;
        display: inline-flex;
        align-items: center;
        gap: 4px;
        border: none;
        border-radius: 8px;
        padding: 5px 10px;
        font-size: 12px;
        font-weight: 500;
        cursor: pointer;
        color: var(--primary-text-color);
        background: var(--secondary-background-color, rgba(0, 0, 0, 0.05));
        transition: background 0.15s ease, opacity 0.15s ease;
    }
    .group-head .test-btn:hover {
        background: var(--primary-color);
        color: var(--text-primary-color, #fff);
    }
    .group-head .test-btn[disabled] {
        opacity: 0.5;
        cursor: default;
        pointer-events: none;
    }
    .group-head .test-btn ha-icon {
        --mdc-icon-size: 14px;
    }

    .nodes {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
    }
    .node {
        display: inline-flex;
        align-items: stretch;
        border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
        border-radius: 10px;
        overflow: hidden;
        background: transparent;
        transition: border-color 0.15s ease, background 0.15s ease;
    }
    .node:hover {
        border-color: var(--primary-color);
        background: var(--secondary-background-color, rgba(0, 0, 0, 0.05));
    }
    .node.active {
        border-color: var(--primary-color);
        background: color-mix(in srgb, var(--primary-color) 14%, transparent);
    }
    .node.active .node-name {
        font-weight: 600;
        color: var(--primary-color);
    }
    .node-select {
        display: inline-flex;
        align-items: center;
        gap: 7px;
        border: none;
        background: transparent;
        padding: 6px 6px 6px 11px;
        font-size: 13px;
        cursor: pointer;
        color: var(--primary-text-color);
        font-family: inherit;
    }
    .node-name {
        max-width: 180px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .node-name.standalone {
        padding: 6px 0 6px 11px;
    }
    .node-ping {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border: none;
        border-left: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
        background: transparent;
        padding: 0 8px;
        cursor: pointer;
        color: var(--secondary-text-color);
        transition: color 0.15s ease, background 0.15s ease;
    }
    .node-ping:hover {
        color: var(--primary-color);
        background: color-mix(in srgb, var(--primary-color) 10%, transparent);
    }
    .node-ping[disabled] {
        opacity: 0.5;
        cursor: default;
        pointer-events: none;
    }
    .node-ping ha-icon {
        --mdc-icon-size: 15px;
    }
    .ping {
        font-size: 12px;
        font-weight: 600;
        font-variant-numeric: tabular-nums;
        border-radius: 6px;
        padding: 1px 6px;
        background: var(--secondary-background-color, rgba(0, 0, 0, 0.06));
    }
    .ping.good { color: var(--success-color, #2e7d32); }
    .ping.warn { color: #f9a825; }
    .ping.bad { color: var(--error-color, #c62828); }
    .ping.none { color: var(--disabled-text-color); }
    /* A failed url-test is not "slow", it is broken: same red as .bad but on
       a tinted background, so the ✕ cannot be mistaken for a high delay. */
    .ping.fail {
        color: var(--error-color, #c62828);
        background: color-mix(in srgb, var(--error-color, #c62828) 14%, transparent);
    }

    /* ---------- states ---------- */
    .state-msg {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 10px;
        padding: 28px 12px;
        color: var(--secondary-text-color);
        font-size: 14px;
        text-align: center;
    }
    .spinner {
        width: 26px;
        height: 26px;
        border: 3px solid var(--divider-color, rgba(0, 0, 0, 0.2));
        border-top-color: var(--primary-color);
        border-radius: 50%;
        animation: singbox-spin 0.9s linear infinite;
    }
    @keyframes singbox-spin {
        to { transform: rotate(360deg); }
    }
    .footer {
        margin-top: 12px;
        font-size: 11px;
        color: var(--disabled-text-color);
        text-align: right;
    }
    .fallback-note {
        margin-top: 12px;
        padding: 8px 10px;
        border-radius: 8px;
        font-size: 12px;
        line-height: 1.4;
        color: #f9a825;
        background: color-mix(in srgb, #f9a825 12%, transparent);
    }

    /* ---------- traffic chart ---------- */
    .chart {
        margin-top: 4px;
        margin-bottom: 14px;
    }
    .chart-head {
        display: flex;
        align-items: baseline;
        gap: 10px;
        margin-bottom: 6px;
        font-size: 12px;
        color: var(--secondary-text-color);
    }
    .chart-peak {
        font-variant-numeric: tabular-nums;
    }
    .chart-scale {
        margin-left: auto;
        font-variant-numeric: tabular-nums;
        font-size: 11px;
        opacity: 0.75;
    }
    .chart-legend {
        margin-left: auto;
        display: inline-flex;
        gap: 12px;
        font-size: 11px;
        color: var(--secondary-text-color);
    }
    .chart-legend .legend-item {
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .chart-legend .legend-item i {
        width: 8px;
        height: 8px;
        border-radius: 2px;
        display: inline-block;
    }
    .chart-legend .legend-item.up i { background: #ff7043; }
    .chart-legend .legend-item.down i { background: var(--success-color, #2e7d32); }
    .chart-svg {
        display: block;
        width: 100%;
        height: 96px;
        overflow: visible;
    }
    .chart-grid {
        stroke: var(--divider-color, rgba(0, 0, 0, 0.12));
        stroke-width: 1;
    }
    .chart-line {
        fill: none;
        stroke-width: 1.6;
        stroke-linejoin: round;
        stroke-linecap: round;
    }
    .chart-line.up { stroke: #ff7043; }
    .chart-line.down { stroke: var(--success-color, #2e7d32); }
    .chart-fill { stroke: none; }
    /* The two series overlap, so keep the areas translucent and let the
       stroked lines carry the shape. */
    .chart-fill.up { fill: color-mix(in srgb, #ff7043 14%, transparent); }
    .chart-fill.down {
        fill: color-mix(in srgb, var(--success-color, #2e7d32) 14%, transparent);
    }
    .chart-empty {
        margin-top: -58px;
        text-align: center;
        font-size: 12px;
        color: var(--disabled-text-color);
        pointer-events: none;
    }

    /* ---------- connections ---------- */
    .connections {
        margin-top: 14px;
        border-top: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
        padding-top: 12px;
    }
    .conn-head {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 10px;
    }
    .conn-title {
        font-size: 14px;
        font-weight: 600;
        color: var(--primary-text-color);
    }
    .conn-count {
        font-size: 12px;
        color: var(--secondary-text-color);
        font-variant-numeric: tabular-nums;
    }
    .conn-close-all {
        margin-left: auto;
        flex: none;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border: none;
        border-radius: 8px;
        padding: 5px 8px;
        cursor: pointer;
        color: var(--secondary-text-color);
        background: var(--secondary-background-color, rgba(0, 0, 0, 0.05));
        transition: background 0.15s ease, color 0.15s ease;
    }
    .conn-close-all:hover {
        background: var(--error-color, #c62828);
        color: var(--text-primary-color, #fff);
    }
    .conn-close-all[disabled] {
        opacity: 0.5;
        cursor: default;
        pointer-events: none;
    }
    .conn-close-all ha-icon { --mdc-icon-size: 16px; }
    .conn-filters {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-bottom: 10px;
    }
    .conn-search {
        flex: 1 1 160px;
        min-width: 0;
        border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
        border-radius: 8px;
        padding: 6px 9px;
        font-size: 12px;
        font-family: inherit;
        color: var(--primary-text-color);
        background: var(--card-background-color, transparent);
    }
    .conn-search:focus {
        outline: none;
        border-color: var(--primary-color);
    }
    .conn-select {
        flex: 0 1 110px;
        min-width: 0;
        border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
        border-radius: 8px;
        padding: 6px 6px;
        font-size: 12px;
        font-family: inherit;
        color: var(--primary-text-color);
        background: var(--card-background-color, transparent);
    }
    .conn-reset {
        border: none;
        border-radius: 8px;
        padding: 6px 10px;
        font-size: 12px;
        font-family: inherit;
        cursor: pointer;
        color: var(--primary-color);
        background: var(--secondary-background-color, rgba(0, 0, 0, 0.05));
    }
    .conn-list {
        display: flex;
        flex-direction: column;
        gap: 2px;
        max-height: 260px;
        overflow-y: auto;
    }
    .conn-row {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 5px 2px;
        border-bottom: 1px solid var(--divider-color, rgba(0, 0, 0, 0.06));
    }
    .conn-row:last-child { border-bottom: none; }
    .conn-main {
        display: flex;
        flex-direction: column;
        min-width: 0;
        flex: 1 1 auto;
    }
    .conn-host {
        font-size: 12px;
        color: var(--primary-text-color);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .conn-sub {
        font-size: 11px;
        color: var(--secondary-text-color);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .conn-stats {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        flex: none;
        font-size: 11px;
        font-variant-numeric: tabular-nums;
        color: var(--secondary-text-color);
    }
    .conn-stat {
        display: inline-flex;
        align-items: center;
        gap: 2px;
    }
    .conn-stat.up ha-icon { color: #ff7043; --mdc-icon-size: 12px; }
    .conn-stat.down ha-icon { color: var(--success-color, #2e7d32); --mdc-icon-size: 12px; }
    .conn-age {
        color: var(--disabled-text-color);
        min-width: 34px;
        text-align: right;
    }
    .conn-close {
        flex: none;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border: none;
        border-radius: 6px;
        padding: 3px;
        cursor: pointer;
        color: var(--secondary-text-color);
        background: transparent;
        transition: background 0.15s ease, color 0.15s ease;
    }
    .conn-close:hover {
        color: var(--error-color, #c62828);
        background: color-mix(in srgb, var(--error-color, #c62828) 12%, transparent);
    }
    .conn-close ha-icon { --mdc-icon-size: 14px; }
    .conn-empty {
        padding: 14px 8px;
        text-align: center;
        font-size: 12px;
        color: var(--secondary-text-color);
    }
`;