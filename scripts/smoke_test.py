"""End-to-end smoke test for the sing-box clients.

Usage:
    python3 scripts/smoke_test.py [--host HOST] [--port PORT] [--secret SECRET]
                                  [--clash-port PORT] [--tls]

Requires a running sing-box with the ``api`` service (gRPC, >= 1.14.0) on
--port and, when --clash-port is given, the ``clash_api`` controller on that
port. Exits non-zero on any failure.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import types
from pathlib import Path

# Load the integration package without homeassistant: register a fake
# "singbox" package whose __path__ points at custom_components, so relative
# imports inside grpc.py / clash.py / backend.py resolve normally.
_PKG_DIR = Path(__file__).resolve().parents[1] / "custom_components" / "singbox"
_pkg = types.ModuleType("singbox")
_pkg.__path__ = [str(_PKG_DIR)]
sys.modules["singbox"] = _pkg


def _stub_homeassistant() -> None:
    """Register a minimal fake homeassistant so coordinator.py can be imported."""
    ha = types.ModuleType("homeassistant")
    ha.__path__ = []
    sys.modules["homeassistant"] = ha

    config_entries = types.ModuleType("homeassistant.config_entries")
    config_entries.ConfigEntry = object
    sys.modules["homeassistant.config_entries"] = config_entries

    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = object
    sys.modules["homeassistant.core"] = core

    const = types.ModuleType("homeassistant.const")

    class Platform:
        SENSOR = "sensor"
        SELECT = "select"

    const.Platform = Platform
    sys.modules["homeassistant.const"] = const

    helpers = types.ModuleType("homeassistant.helpers")
    helpers.__path__ = []
    sys.modules["homeassistant.helpers"] = helpers

    update_coordinator = types.ModuleType("homeassistant.helpers.update_coordinator")

    class DataUpdateCoordinator:
        def __class_getitem__(cls, item):  # support DataUpdateCoordinator[T]
            return cls

        def __init__(
            self, hass, logger, *, name, update_interval, config_entry=None
        ) -> None:
            self.hass = hass
            self.logger = logger
            self.name = name
            self.config_entry = config_entry
            self.last_update_success = True
            self.data = None

        def async_set_updated_data(self, data) -> None:
            self.data = data

        def async_update_listeners(self) -> None:
            pass

    update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
    sys.modules["homeassistant.helpers.update_coordinator"] = update_coordinator


_stub_homeassistant()

from singbox.backend import BACKEND_CLASH, BACKEND_GRPC, detect_backend  # noqa: E402
from singbox.clash import ClashApiError, ClashClient  # noqa: E402
from singbox.grpc import (  # noqa: E402
    GRPC_STATUS_NOT_FOUND,
    GRPC_STATUS_UNIMPLEMENTED,
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
    # -- backend auto-detection ---------------------------------------------
    grpc_client, backend = await detect_backend(
        args.host, args.port, args.secret, args.tls, None
    )
    await check("detect_backend -> grpc", backend == BACKEND_GRPC, backend)
    await grpc_client.close()

    clash_client, backend = await detect_backend(
        args.host, args.clash_port, args.secret, args.tls, None
    )
    await check("detect_backend -> clash", backend == BACKEND_CLASH, backend)
    await clash_client.close()

    client = SingBoxClient(args.host, args.port, args.secret, args.tls)
    try:
        await _run_checks(args, client)
    finally:
        await client.close()
    if args.clash_port:
        await _run_clash_checks(args)
        await _run_coordinator_clash_checks(args)


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


async def _run_clash_checks(args: argparse.Namespace) -> None:
    print("\n-- clash API backend -----------------------------------------")

    # -- gRPC probe against a clash-only port must report UNIMPLEMENTED ----
    grpc_probe = SingBoxClient(args.host, args.clash_port, args.secret, args.tls)
    try:
        await grpc_probe.get_version()
        raise AssertionError("gRPC GetVersion succeeded on a clash-only port")
    except GrpcError as err:
        await check(
            "grpc->clash fallback detection",
            err.status == GRPC_STATUS_UNIMPLEMENTED,
            f"grpc {err.status}",
        )
    finally:
        await grpc_probe.close()

    client = ClashClient(args.host, args.clash_port, args.secret, args.tls)
    try:
        # -- static info -----------------------------------------------------
        version = await client.get_version()
        await check("clash get_version", version.startswith("1."), version)

        mode_list, current = await client.get_configs()
        await check(
            "clash get_configs",
            mode_list and current in mode_list,
            f"modes={mode_list}, current={current}",
        )

        # -- groups ----------------------------------------------------------
        groups = await client.get_proxies()
        await check("clash get_proxies", groups, f"{len(groups)} selectable groups")
        group = groups[0]
        await check(
            "clash group items",
            len(group.items) > 0,
            f"{group.tag}: [{', '.join(i.tag for i in group.items)}]",
        )

        # -- select outbound -------------------------------------------------
        target = group.items[0].tag
        await client.select_outbound(group.tag, target)
        refreshed = await client.get_proxies()
        now = next(g.selected for g in refreshed if g.tag == group.tag)
        await check("clash select_outbound", now == target, f"{group.tag} -> {now}")

        # -- url test (allowed to fail without internet) ----------------------
        try:
            await client.url_test(group.tag)
            print("  ok: clash url_test")
        except ClashApiError as err:
            print(f"  info: clash url_test failed: {err}")

        # -- connections snapshot --------------------------------------------
        n, memory, upload_total, download_total = await client.get_connections()
        await check(
            "clash get_connections",
            memory > 0,
            f"n={n}, memory={memory}, up={upload_total}, down={download_total}",
        )

        # -- traffic stream ---------------------------------------------------
        frames = []
        async for up, down in client.traffic_stream():
            frames.append((up, down))
            if len(frames) == 2:
                break
        await check(
            "clash traffic_stream",
            len(frames) == 2 and all(
                isinstance(up, int) and isinstance(down, int) for up, down in frames
            ),
            f"{len(frames)} frames",
        )

        # -- close all --------------------------------------------------------
        await client.close_all_connections()
        print("  ok: clash close_all_connections")

        # -- clash mode -------------------------------------------------------
        await client.set_clash_mode(mode_list[0])
        print("  ok: clash set_clash_mode")

        # -- auth -------------------------------------------------------------
        bad = ClashClient(args.host, args.clash_port, "definitely-wrong")
        try:
            await bad.get_version()
            raise AssertionError("wrong secret was accepted by clash API")
        except ClashApiError as err:
            await check("clash auth", err.status == 401, f"http {err.status}")
        finally:
            await bad.close()
    finally:
        await client.close()
    print("\nAll clash backend checks passed.")


async def _run_coordinator_clash_checks(args: argparse.Namespace) -> None:
    """Exercise the coordinator's clash poll loop against the live API.

    Regression guard: _apply_clash_mode/_apply_clash_connections were once
    called without await inside the poll loop, leaving every counter sensor
    permanently unavailable while the rest of the integration looked healthy.
    """
    from singbox.coordinator import SingBoxCoordinator  # noqa: E402

    client = ClashClient(args.host, args.clash_port, args.secret, args.tls)
    entry = types.SimpleNamespace(entry_id="test-entry")
    coordinator = SingBoxCoordinator(
        None, entry, client, BACKEND_CLASH, update_interval_seconds=1
    )
    task = asyncio.create_task(coordinator._run_clash_poll_loop())
    try:
        await asyncio.wait_for(coordinator._groups_ready.wait(), timeout=10)
        # The poll loop applies the clash mode and the connections snapshot
        # right after publishing the groups; give it a moment.
        for _ in range(50):
            if coordinator.data.memory is not None:
                break
            await asyncio.sleep(0.1)
        await check(
            "coordinator clash poll loop sets counters",
            coordinator.data.memory is not None
            and coordinator.data.connections_in is not None
            and coordinator.data.uplink_total is not None
            and coordinator.data.downlink_total is not None,
            f"memory={coordinator.data.memory}, conns={coordinator.data.connections_in}, "
            f"up={coordinator.data.uplink_total}, down={coordinator.data.downlink_total}",
        )
        await check(
            "coordinator clash mode",
            coordinator.clash_mode_available,
            f"mode={coordinator.data.clash_mode}",
        )
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        await client.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9090)
    parser.add_argument("--clash-port", type=int, default=9091, help="clash_api port (0 to skip)")
    parser.add_argument("--secret", default="test-secret")
    parser.add_argument("--tls", action="store_true")
    args = parser.parse_args()
    try:
        asyncio.run(run(args))
    except AssertionError as err:
        print(f"FAILED: {err}")
        return 1
    except (ConnectionError, GrpcError, ClashApiError) as err:
        print(f"FAILED: {err}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
