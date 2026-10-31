"""Tests for the pure transport-level helpers (no Home Assistant)."""

from __future__ import annotations

import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG_DIR = ROOT / "custom_components" / "singbox"

_pkg = types.ModuleType("singbox")
_pkg.__path__ = [str(PKG_DIR)]
sys.modules.setdefault("singbox", _pkg)

from singbox.clash import _last_url_test_delay  # noqa: E402
from singbox.grpc import _parse_trailer, decode_fields  # noqa: E402


def test_cyclic_now_chain_does_not_recurse() -> None:
    proxies = {
        "A": {"type": "URLTest", "now": "B"},
        "B": {"type": "Fallback", "now": "A"},
    }
    assert _last_url_test_delay(proxies["A"], proxies) == (0, 0)


def test_self_reference_and_dangling_now() -> None:
    assert _last_url_test_delay({"now": "A"}, {"A": {"now": "A"}}) == (0, 0)
    assert _last_url_test_delay({"now": "missing"}, {}) == (0, 0)


def test_own_history_wins_over_selected_proxy() -> None:
    proxies = {
        "A": {"now": "B", "history": [{"delay": 0}, {"delay": 42, "time": 17}]},
        "B": {"history": [{"delay": 99, "time": 18}]},
    }
    assert _last_url_test_delay(proxies["A"], proxies) == (42, 17)


def test_long_chain_resolves_and_absurd_chain_is_bounded() -> None:
    proxies = {f"G{i}": {"now": f"G{i + 1}"} for i in range(20)}
    proxies["G20"] = {"history": [{"delay": 7, "time": 1}]}
    assert _last_url_test_delay(proxies["G0"], proxies) == (7, 1)

    deep = {f"G{i}": {"now": f"G{i + 1}"} for i in range(5000)}
    deep["G5000"] = {"history": [{"delay": 7, "time": 1}]}
    assert _last_url_test_delay(deep["G0"], deep) == (0, 0)


def test_decode_fields_rejects_truncated_frames() -> None:
    for payload in (b"\x0b", b"\x10", b"\x0a", b"\x0a\x05ab"):
        try:
            decode_fields(payload)
        except ValueError:
            continue
        raise AssertionError(f"{payload!r} decoded instead of raising ValueError")


def test_decode_fields_round_trip() -> None:
    # field 1 varint 300, field 2 bytes "hi"
    assert decode_fields(b"\x08\xac\x02\x12\x02hi") == {1: [300], 2: [b"hi"]}


def test_parse_trailer_tolerates_garbage() -> None:
    status, message = _parse_trailer(b"grpc-status: nope\r\n")
    assert status != 0
    assert message is not None
    assert _parse_trailer(b"grpc-status: 0\r\n") == (0, None)
