"""Probe the integration ClashClient against a running sing-box clash_api.

Replicates the coordinator's clash-mode sequence. Usage:
    python3 probe_clash_client.py [--port PORT] [--secret SECRET]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import types
from pathlib import Path

_PKG_DIR = Path(__file__).resolve().parents[1] / "custom_components" / "singbox"
_pkg = types.ModuleType("singbox")
_pkg.__path__ = [str(_PKG_DIR)]
sys.modules["singbox"] = _pkg

from singbox.clash import ClashClient  # noqa: E402


async def main(args: argparse.Namespace) -> None:
    client = ClashClient(args.host, args.port, secret=args.secret)
    print(f"== ClashClient against {args.host}:{args.port} (secret={args.secret!r})")

    print("get_version:", await client.get_version())
    print("get_configs:", await client.get_configs())
    groups, proxies = await client.get_proxies()
    print("get_proxies (groups):", [(g.tag, g.selectable, g.selected, [i.tag for i in g.items]) for g in groups])
    print(
        "get_proxies (pings):",
        [(p.tag, p.type, p.url_test_delay) for p in proxies if p.url_test_delay > 0]
        or "no delays yet",
    )
    print("get_connections:", await client.get_connections())

    async def drain(name: str, n: int = 2, timeout: float = 10.0) -> None:
        try:
            stream = client.traffic_stream()
            got = []
            async for item in stream:
                got.append(item)
                if len(got) >= n:
                    break
            print(f"{name}: {got}")
        except asyncio.TimeoutError:
            print(f"{name}: TIMEOUT (no frames)")
        except Exception as err:  # noqa: BLE001
            print(f"{name}: ERROR {type(err).__name__}: {err}")
        finally:
            await client.close()

    await drain("traffic_stream", n=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9091)
    parser.add_argument("--secret", default="")
    args = parser.parse_args()
    asyncio.run(main(args))
