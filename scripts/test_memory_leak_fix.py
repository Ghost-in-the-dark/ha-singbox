"""Regression tests for the sing-box traffic_stream() busy loop.

The bug (shipped in v0.3.12): when the WebSocket transport is aborted without
a close frame (sing-box dies during HA shutdown), aiohttp answers
WSMsgType.CLOSED. The old loop did "continue", receive() returned from the dead
socket immediately, so the loop spun at ~170k iterations/s and every iteration
allocated a TimerHandle + Context through asyncio.wait_for(), until the kernel
OOM-killed Home Assistant.

Run:  python3 scripts/test_memory_leak_fix.py
Exits non-zero on failure.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import time
import types
from pathlib import Path

from aiohttp import web

ROOT = Path(__file__).resolve().parents[1]
PKG_DIR = ROOT / "custom_components" / "singbox"


def _load_package(name: str, pkg_dir: Path) -> None:
    pkg = types.ModuleType(name)
    pkg.__path__ = [str(pkg_dir)]
    sys.modules[name] = pkg


_load_package("singbox", PKG_DIR)


def _stub_homeassistant() -> None:
    """Minimal fake homeassistant so coordinator.py can be imported."""
    ha = types.ModuleType("homeassistant")
    ha.__path__ = []
    sys.modules["homeassistant"] = ha

    ce = types.ModuleType("homeassistant.config_entries")
    ce.ConfigEntry = object
    sys.modules["homeassistant.config_entries"] = ce

    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = object
    sys.modules["homeassistant.core"] = core

    helpers = types.ModuleType("homeassistant.helpers")
    helpers.__path__ = []
    sys.modules["homeassistant.helpers"] = helpers

    uc = types.ModuleType("homeassistant.helpers.update_coordinator")

    class DataUpdateCoordinator:
        def __class_getitem__(cls, item):
            return cls

        def __init__(self, hass, logger, *, name, update_interval, config_entry=None):
            self.hass = hass
            self.logger = logger
            self.name = name
            self.config_entry = config_entry
            self.last_update_success = True
            self.data = None

        def async_set_updated_data(self, data):
            self.data = data

        def async_update_listeners(self):
            pass

    uc.DataUpdateCoordinator = DataUpdateCoordinator
    sys.modules["homeassistant.helpers.update_coordinator"] = uc

    const = types.ModuleType("homeassistant.const")

    class Platform:
        SENSOR = "sensor"
        SELECT = "select"

    const.Platform = Platform
    sys.modules["homeassistant.const"] = const


_stub_homeassistant()

from singbox.clash import ClashClient  # noqa: E402
from singbox.coordinator import SingBoxCoordinator  # noqa: E402


# ---------------------------------------------------------------------------
# a server that dies the way sing-box dies: TCP abort, no close frame
# ---------------------------------------------------------------------------

async def _start(routes) -> tuple[web.AppRunner, int]:
    app = web.Application()
    for path, handler in routes:
        app.router.add_get(path, handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = runner.addresses[0][1]
    return runner, port


async def _aborting_traffic(request: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    await asyncio.sleep(0.05)
    # No WebSocket close handshake: the transport just disappears.
    request.transport.abort()
    return ws


async def _closing_traffic(request: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    await ws.send_json({"up": 10, "down": 20})
    await asyncio.sleep(0.02)
    await ws.send_json({"up": 20, "down": 40})
    await ws.close()
    return ws


async def test_patched_stream_terminates_on_abort() -> None:
    runner, port = await _start([("/traffic", _aborting_traffic)])
    client = ClashClient("127.0.0.1", port)
    started = time.monotonic()
    try:
        async for _up, _down in client.traffic_stream():
            pass
        raise AssertionError("the stream ended without raising")
    except ConnectionError as err:
        elapsed = time.monotonic() - started
        assert elapsed < 5, f"stream needed {elapsed:.2f}s to notice the abort"
        assert "traffic stream ended" in str(err), str(err)
    finally:
        await client.close()
        await runner.cleanup()
    print("  ok: traffic_stream raises ConnectionError on transport abort")


async def test_patched_stream_yields_frames() -> None:
    runner, port = await _start([("/traffic", _closing_traffic)])
    client = ClashClient("127.0.0.1", port)
    frames = []
    try:
        async for up, down in client.traffic_stream():
            frames.append((up, down))
    except ConnectionError:
        pass
    finally:
        await client.close()
        await runner.cleanup()
    assert frames == [(10, 20), (20, 40)], frames
    print("  ok: traffic_stream still delivers live frames")


# ---------------------------------------------------------------------------
# the original loop, for comparison: it must busy-spin (regression evidence)
# ---------------------------------------------------------------------------

BUSY_LOOP_PROBE = textwrap.dedent('''
    import asyncio, json, signal, sys, types
    import aiohttp
    from aiohttp import web

    pkg_dir, mode, cap = sys.argv[1], sys.argv[2], float(sys.argv[3])
    pkg = types.ModuleType("probe_pkg")
    pkg.__path__ = [pkg_dir]
    sys.modules["probe_pkg"] = pkg

    from probe_pkg.clash import ClashClient

    calls = 0
    _orig = aiohttp.ClientWebSocketResponse.receive

    async def _counting(self, *args, **kwargs):
        global calls
        calls += 1
        return await _orig(self, *args, **kwargs)

    aiohttp.ClientWebSocketResponse.receive = _counting

    class _Cap(Exception):
        pass

    def _alarm(signum, frame):
        raise _Cap()

    async def traffic(request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await asyncio.sleep(0.05)
        request.transport.abort()
        return ws

    async def main():
        app = web.Application()
        app.router.add_get("/traffic", traffic)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        port = runner.addresses[0][1]
        client = ClashClient("127.0.0.1", port)
        outcome = "busy-loop"
        try:
            async for _ in client.traffic_stream():
                pass
            outcome = "stream-ended-silently"
        except ConnectionError:
            outcome = "raised"
        except _Cap:
            outcome = "busy-loop"
        finally:
            await client.close()
            await runner.cleanup()
        return outcome

    signal.signal(signal.SIGALRM, _alarm)
    signal.setitimer(signal.ITIMER_REAL, cap)
    started = __import__("time").monotonic()
    try:
        outcome = asyncio.run(main())
    except _Cap:
        outcome = "busy-loop"
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    print(json.dumps({"outcome": outcome, "receives": calls,
                      "elapsed": round(__import__("time").monotonic() - started, 2)}))
''')


def _make_old_package(tmp: Path) -> Path:
    """Write the pre-fix clash.py (plus its grpc dependency) to a temp package."""
    src = (PKG_DIR / "clash.py").read_text(encoding="utf-8")
    new_block = """                if msg.type is not aiohttp.WSMsgType.TEXT:
                    # CLOSE / CLOSING / CLOSED / ERROR / BINARY: all terminal.
                    raise ConnectionError(
                        f"traffic stream ended: {getattr(msg.type, 'name', msg.type)}"
                    )"""
    old_block = """                if msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.ERROR):
                    raise ConnectionError(f"traffic stream closed: {msg.type}")
                if msg.type != aiohttp.WSMsgType.TEXT:
                    continue"""
    if new_block not in src:
        raise AssertionError("fixed traffic_stream block not found in clash.py")
    old_src = src.replace(new_block, old_block, 1)

    pkg = tmp / "probe_pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "clash.py").write_text(old_src, encoding="utf-8")
    (pkg / "grpc.py").write_text(
        (PKG_DIR / "grpc.py").read_text(encoding="utf-8"), encoding="utf-8"
    )
    return pkg


def test_old_code_busy_spins() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        pkg_dir = _make_old_package(tmp)
        probe = tmp / "probe.py"
        probe.write_text(BUSY_LOOP_PROBE, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(probe), str(pkg_dir), "old", "3"],
            capture_output=True,
            text=True,
            timeout=120,
        )
    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr, file=sys.stderr)
        raise AssertionError("busy-loop probe failed")
    report = json.loads(proc.stdout.strip().splitlines()[-1])
    assert report["outcome"] == "busy-loop", report
    assert report["receives"] > 1000, report
    print(
        "  ok: pre-fix loop spins without ever ending "
        f"({report['receives']} receive() calls in {report['elapsed']}s)"
    )


async def test_old_code_probe_matches(monkeypatch=None) -> None:
    """Sanity: the probe reports 'raised' once the fixed code is in place."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        probe = tmp / "probe.py"
        probe.write_text(BUSY_LOOP_PROBE, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(probe), str(PKG_DIR), "fixed", "5"],
            capture_output=True,
            text=True,
            timeout=120,
        )
    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr, file=sys.stderr)
        raise AssertionError("fixed-code probe failed")
    report = json.loads(proc.stdout.strip().splitlines()[-1])
    assert report["outcome"] == "raised", report
    assert report["receives"] <= 5, report
    print(f"  ok: fixed loop exits immediately ({report['receives']} receive() calls)")


# ---------------------------------------------------------------------------
# coordinator: shutdown must not be held hostage by the reconnect backoff
# ---------------------------------------------------------------------------

class _BrokenClient:
    def __init__(self) -> None:
        self.closed = False

    async def traffic_stream(self):
        raise ConnectionError("backend gone")
        yield  # pragma: no cover - makes this an async generator

    async def close(self) -> None:
        self.closed = True


async def test_coordinator_shutdown_is_quick() -> None:
    client = _BrokenClient()
    coordinator = SingBoxCoordinator(
        None, types.SimpleNamespace(entry_id="t"), client, "clash", update_interval_seconds=1
    )
    coordinator._stream_tasks = [
        asyncio.create_task(coordinator._run_clash_traffic_stream())
    ]
    await asyncio.sleep(0.2)  # let it fail once and enter the backoff
    started = time.monotonic()
    await coordinator.async_shutdown()
    elapsed = time.monotonic() - started
    assert elapsed < 2.5, f"shutdown took {elapsed:.2f}s"
    assert client.closed, "client session was not closed"
    assert not coordinator._stream_tasks
    print(f"  ok: coordinator shutdown stops a backoff-waiting stream in {elapsed:.2f}s")


async def _main() -> int:
    print("sing-box traffic_stream regression tests")
    await test_patched_stream_terminates_on_abort()
    await test_patched_stream_yields_frames()
    test_old_code_busy_spins()
    await test_old_code_probe_matches()
    await test_coordinator_shutdown_is_quick()
    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    os.chdir(ROOT)
    try:
        raise SystemExit(asyncio.run(_main()))
    except AssertionError as err:
        print(f"FAILED: {err}")
        raise SystemExit(1)
