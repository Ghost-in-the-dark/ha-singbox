"""End-to-end smoke test for the sing-box gRPC-Web client.

Usage:
    python3 scripts/smoke_test.py [--host HOST] [--port PORT] [--secret SECRET]
                                  [--tls]

Requires a running sing-box (>= 1.14.0) with the ``api`` service enabled and
at least one selector outbound group. Exits non-zero on any failure.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Import grpc.py directly: the package __init__ requires homeassistant.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "singbox"))

from grpc import (  # noqa: E402
    GRPC_STATUS_NOT_FOUND,
    GRPC_STATUS_UNAUTHENTICATED,
    GrpcError,
    SingBoxClient,
    decode_fields,
)


async def check(step: str, condition: bool, detail: str = "") -> None:
    if not condition:
        raise AssertionError(f"{step}: {detail}")
    print(f"  ok: {step}" + (f" ({detail})" if detail else ""))


async def run(args: argparse.Namespace) -> None:
    client = SingBoxClient(args.host, args.port, args.secret, args.tls)
    try:
        await _run_checks(args, client)
    finally:
        await client.close()


async def _run_checks(args: argparse.Namespace, client: SingBoxClient) -> None:

    # -- static info ---------------------------------------------------------
    version, api_version = await client.get_version()
    await check("get_version", version and api_version >= 1, f"{version} (api {api_version})")

    started_at = await client.get_started_at()
    await check("get_started_at", started_at > 0, f"ts={started_at}")

    clash_available = True
    try:
        mode_list, current = await client.get_clash_mode_status()
        print(f"  ok: get_clash_mode_status (modes={mode_list}, current={current})")
    except GrpcError as err:
        clash_available = err.status != GRPC_STATUS_NOT_FOUND
        if err.status == GRPC_STATUS_NOT_FOUND:
            print("  ok: get_clash_mode_status -> NOT_FOUND (clash api disabled, expected)")
        else:
            raise

    # -- status stream -------------------------------------------------------
    frames = []
    async for fields in client.subscribe_status(1_000_000_000):
        frames.append(fields)
        if len(frames) == 3:
            break
    await check("subscribe_status", len(frames) == 3, f"{len(frames)} frames")
    last = frames[-1]
    await check("status fields", last.get(1), f"memory={last.get(1, [0])[0]}")

    # -- groups stream -------------------------------------------------------
    groups = None
    async for batch in client.subscribe_groups():
        groups = batch
        break
    await check("subscribe_groups", groups, f"{len(groups)} groups")
    selectable = [g for g in groups if g.selectable]
    await check("selectable groups", selectable, ", ".join(g.tag for g in selectable))
    group = selectable[0]
    await check("group items", len(group.items) > 0, f"{group.tag}: [{', '.join(i.tag for i in group.items)}]")

    # -- control: select an outbound and verify it sticks --------------------
    target = group.items[0].tag
    await client.select_outbound(group.tag, target)
    async for batch in client.subscribe_groups():
        refreshed = next((g for g in batch if g.tag == group.tag), None)
        if refreshed and refreshed.selected == target:
            print(f"  ok: select_outbound -> {group.tag}/{target}")
            break

    # -- URL test (allowed to fail on networks without internet) -------------
    try:
        await client.url_test(group.tag)
        print("  ok: url_test")
    except GrpcError as err:
        print(f"  info: url_test failed: {err}")

    # -- close connections ---------------------------------------------------
    await client.close_all_connections()
    print("  ok: close_all_connections")

    # -- clash mode (when available) -----------------------------------------
    if clash_available:
        await client.set_clash_mode(mode_list[0])
        print("  ok: set_clash_mode")

    # -- auth ----------------------------------------------------------------
    bad = SingBoxClient(args.host, args.port, "definitely-wrong")
    try:
        await bad.get_version()
        raise AssertionError("wrong secret was accepted")
    except GrpcError as err:
        await check("auth", err.status == GRPC_STATUS_UNAUTHENTICATED, f"grpc {err.status}")
    finally:
        await bad.close()

    # -- stream idle/close handling ------------------------------------------
    async for fields in client.subscribe_status(0):  # 0 -> server default 1s
        await check("subscribe_status(0)", fields.get(1), "interval 0 uses server default")
        break

    await client.close()
    print("\nAll smoke checks passed.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9090)
    parser.add_argument("--secret", default="test-secret")
    parser.add_argument("--tls", action="store_true")
    args = parser.parse_args()
    try:
        asyncio.run(run(args))
    except AssertionError as err:
        print(f"FAILED: {err}")
        return 1
    except (ConnectionError, GrpcError) as err:
        print(f"FAILED: {err}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
