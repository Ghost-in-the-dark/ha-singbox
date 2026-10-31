# sing-box for Home Assistant

![sing-box](custom_components/singbox/brand/icon.png)

Home Assistant integration that **monitors and controls** a running
[sing-box](https://sing-box.sagernet.org/) instance. Distributed via
[HACS](https://hacs.xyz/).

The integration supports **two backends**, auto-detected at setup:

1. the [`api` service](https://sing-box.sagernet.org/configuration/service/api/)
   (sing-box >= 1.14.0) over **gRPC-Web** — plain HTTP, no external
   dependencies;
2. the [`clash_api`](https://sing-box.sagernet.org/configuration/experimental/clash-api/)
   (Clash REST/WebSocket, any sing-box 1.11+) — used automatically when the
   gRPC `api` service is not available (e.g. OpenWrt builds that are still on
   1.13.x).

Either way, no Python packages need to be installed.

## Features

- **Live monitoring**:
  - memory usage, goroutines, active connections
  - uplink / downlink speed (averaged over the push interval)
  - uplink / downlink totals (session counters)
  - version, API version, start time
- **Control**:
  - a **select entity per outbound group** (selector, url-test and fallback
    groups) — switch proxies from the UI, automations or dashboards
  - a **clash mode select** when the [clash API](https://sing-box.sagernet.org/configuration/experimental/clash-api/)
    is enabled in sing-box
  - services: `select_outbound`, `url_test`, `set_group_expand`,
    `close_connection`, `close_all_connections`, `set_clash_mode`
- Automatic reconnection with exponential backoff if the connection drops;
  a stream that dies is restarted, and a rejected secret starts a reauth
  flow instead of failing silently.
- **Diagnostics** download (Settings → Devices & Services → sing-box → ⋮ →
  Download diagnostics) for issue reports.

## Requirements

- Home Assistant 2024.11 or newer
- sing-box with either the `api` service (>= 1.14.0) or the `clash_api`
  controller enabled

## sing-box configuration

Add an `api` service to your sing-box configuration (>= 1.14.0):

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

On older sing-box builds (1.11 – 1.13.x, e.g. some OpenWrt packages) enable
the `clash_api` controller instead — the integration detects it automatically:

```json
{
  "experimental": {
    "clash_api": {
      "external_controller": "127.0.0.1:9090",
      "secret": "your-secret"
    }
  }
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
  (memory, connections, traffic). Use a larger interval to reduce load on
  busy instances.
- **Speed unit** (B/s, KiB/s, kB/s, MiB/s, MB/s) — display unit for the
  uplink/downlink speed sensors. The raw value is always B/s; the sensor
  scales it to the chosen unit.

The integration reloads automatically when options are saved.

## Entities

| Entity | Type | Notes |
|---|---|---|
| sing-box Version / API version / Started at | sensor | diagnostics; API version & started at are gRPC-only |
| sing-box Memory | sensor | data size (B) |
| sing-box Goroutines | sensor | diagnostics; gRPC-only |
| sing-box Connections in / out | sensor | active connections; on the clash backend "out" is unavailable |
| sing-box Uplink / Downlink | sensor | data rate (B/s); pick the display unit in the entity settings (KiB/s, kB/s, MiB/s, MB/s) |
| sing-box Uplink total / Downlink total | sensor | session totals |
| sing-box \<proxy tag\> Ping | sensor | last url-test delay (ms) of each proxy; diagnostic entity, one per outbound |
| sing-box \<group tag\> | select | one per selector outbound group (url-test / fallback groups are automatic and cannot be switched) |
| sing-box Clash mode | select | only when the clash API is enabled |

On the clash API backend the entities that cannot be provided (goroutines,
connections out, started at, API version) simply stay unavailable.

Ping sensors report the last delay sing-box itself measured during a url-test
(group auto-tests on their configured interval, or via the `singbox.url_test`
service) — the integration never probes the network on its own.

## Panel card (bundled)

The integration ships a Lovelace card showing live speeds, traffic totals,
per-proxy pings and one-click proxy switching. It is served from the
integration itself and loaded automatically, so no manual resource entry is
needed — just add a card:

```yaml
type: custom:singbox-panel-card
```

The card source lives in the separate
[ha-singbox-panel](https://github.com/Ghost-in-the-dark/ha-singbox-panel)
repository, but it is **not** published to the HACS default store — the
bundled copy is the supported way to get the card. The standalone repository
is only for following the card's own development, or for installing it through
HACS as a custom repository.

## Services

All services take an optional `entry_id` field; it is only required when
multiple sing-box instances are configured.

| Service | Fields | Description |
|---|---|---|
| `singbox.select_outbound` | `group_tag`, `outbound_tag` | Select an outbound inside a group |
| `singbox.url_test` | `outbound_tag`, `url` | Trigger a URL test for a group (`url` is used by the clash backend only) |
| `singbox.set_group_expand` | `group_tag`, `is_expand` | Expand/collapse a group (gRPC backend only) |
| `singbox.close_connection` | `connection_id` | Close one connection |
| `singbox.close_all_connections` | – | Close all connections |
| `singbox.set_clash_mode` | `mode` | Switch clash mode |

## Development

Run the test suite (Home Assistant test harness, no sing-box needed):

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements_test.txt
.venv/bin/python -m pytest tests
```

Run the end-to-end smoke test against a local sing-box with both backends:

```bash
sing-box run -c /path/to/config.json &   # gRPC api service
python3 scripts/smoke_test.py --host 127.0.0.1 --port 9090 \
    --clash-port 9091 --secret your-secret
```

Run the offline regression suites (need only `aiohttp`, no sing-box):

```bash
python3 scripts/test_memory_leak_fix.py   # WebSocket shutdown OOM (0.3.13)
python3 scripts/test_regressions.py       # cyclic now-chain, protobuf decoding
```

It reproduces the shutdown OOM fixed in 0.3.13: a WebSocket abort without a
close frame sends `traffic_stream()` into a busy loop that allocates millions
of timers, so the pre-fix code is spun up in a subprocess and must fail to
exit, while the shipped code must raise `ConnectionError` immediately.

## Recorder

The integration creates one ping sensor per outbound. With many proxies that
is a lot of state to write on every url-test; exclude them from the recorder
to keep the database small:

```yaml
recorder:
  exclude:
    entity_globs:
      - sensor.sing_box_ping_*
```

## Disclaimer

Not affiliated with the sing-box project. This is a community integration.
