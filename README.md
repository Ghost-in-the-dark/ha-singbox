# sing-box for Home Assistant

Home Assistant integration that **monitors and controls** a running
[sing-box](https://sing-box.sagernet.org/) instance through its built-in
[`api` service](https://sing-box.sagernet.org/configuration/service/api/)
(sing-box >= 1.14.0). Distributed via [HACS](https://hacs.xyz/).

The integration talks to sing-box over **gRPC-Web** (plain HTTP, no external
dependencies), so it works out of the box — no Python packages to install.

## Features

- **Live monitoring** — sing-box pushes status every second:
  - memory usage, goroutines, active connections
  - uplink / downlink speed
  - uplink / downlink totals (session counters)
  - version, API version, start time
- **Control**:
  - a **select entity per outbound group** (selector) — switch proxies from
    the UI, automations or dashboards
  - a **clash mode select** when the [clash API](https://sing-box.sagernet.org/configuration/experimental/clash-api/)
    is enabled in sing-box
  - services: `select_outbound`, `url_test`, `set_group_expand`,
    `close_connection`, `close_all_connections`, `set_clash_mode`
- Automatic reconnection with exponential backoff if the connection drops.

## Requirements

- Home Assistant 2024.6 or newer
- sing-box 1.14.0 or newer with the `api` service enabled

## sing-box configuration

Add an `api` service to your sing-box configuration:

```json
{
  "services": [
    {
      "type": "api",
      "tag": "api",
      "listen": "127.0.0.1",
      "listen_port": 9090,
      "secret": "your-secret"
    }
  ]
}
```

Notes:

- `secret` is optional but strongly recommended. Leave it empty only if the
  API is not reachable from other hosts.
- If sing-box runs on the same host as Home Assistant, `127.0.0.1` is fine.
  Otherwise bind a reachable address (e.g. `0.0.0.0`) and make sure your
  firewall allows the port — the `access_control_allow_private_network`
  option may also be needed.
- If you configured `tls` for the api service, enable **Use TLS** in the
  integration.

## Installation

1. In HACS, add this repository as a **Custom repository**
   (Settings → Devices & Services → HACS → ⋮ → Custom repositories), type
   `https://github.com/Ghost-in-the-dark/ha-singbox` and category
   **Integration**.
2. Install **sing-box** from the HACS "Integrations" tab.
3. Restart Home Assistant.
4. Add the integration via **Settings → Devices & Services → Add Integration
   → sing-box** and enter host, port and API secret.

## Configuration

After installation, all settings can be changed anytime from
**Settings → Devices & Services → sing-box → Configure**:

- **Host / Port / API secret / Use TLS** — connection settings. The
  integration reconnects automatically after saving.
- **Status update interval** (1–60 s) — how often sing-box pushes status
  (memory, connections, traffic). Speed sensors always report B/s regardless
  of the interval. Use a larger interval to reduce load on busy instances.

The integration reloads automatically when options are saved.

## Entities

| Entity | Type | Notes |
|---|---|---|
| sing-box Version / API version / Started at | sensor | diagnostics |
| sing-box Memory | sensor | data size (B) |
| sing-box Goroutines | sensor | diagnostics |
| sing-box Connections in / out | sensor | active connections |
| sing-box Uplink / Downlink | sensor | speed, B/s |
| sing-box Uplink total / Downlink total | sensor | session totals |
| sing-box \<group tag\> | select | one per selector outbound group |
| sing-box Clash mode | select | only when the clash API is enabled |

## Services

All services take an optional `entry_id` field; it is only required when
multiple sing-box instances are configured.

| Service | Fields | Description |
|---|---|---|
| `singbox.select_outbound` | `group_tag`, `outbound_tag` | Select an outbound inside a group |
| `singbox.url_test` | `outbound_tag` | Trigger a URL test for a group |
| `singbox.set_group_expand` | `group_tag`, `is_expand` | Expand/collapse a group |
| `singbox.close_connection` | `connection_id` | Close one connection |
| `singbox.close_all_connections` | – | Close all connections |
| `singbox.set_clash_mode` | `mode` | Switch clash mode |

## Development

Run the end-to-end smoke test against a local sing-box:

```bash
sing-box run -c /path/to/config.json &
python3 scripts/smoke_test.py --host 127.0.0.1 --port 9090 --secret your-secret
```

## Disclaimer

Not affiliated with the sing-box project. This is a community integration.
