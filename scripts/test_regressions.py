"""Offline regression tests for the pure (Home Assistant free) helpers.

Covers the bugs fixed in 0.3.14:

* cyclic / self-referencing "now" chains used to recurse until Python raised
  RecursionError (clash /proxies parsing then failed on every poll);
* a stale "now" pointing at an unknown proxy crashed the same walk;
* decode_fields indexed past the end of a truncated frame (IndexError) and
  _parse_trailer raised ValueError on a malformed grpc-status.

Run:  python3 scripts/test_regressions.py
Exits non-zero on failure.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG_DIR = ROOT / "custom_components" / "singbox"

_pkg = types.ModuleType("singbox")
_pkg.__path__ = [str(PKG_DIR)]
sys.modules["singbox"] = _pkg

from singbox.clash import _last_url_test_delay  # noqa: E402
from singbox.grpc import _parse_trailer, decode_fields  # noqa: E402

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"ok   {name}")
    else:
        FAILURES.append(name)
        print(f"FAIL {name}{': ' + detail if detail else ''}")


def test_cyclic_now_chain() -> None:
    proxies = {
        "A": {"type": "URLTest", "now": "B"},
        "B": {"type": "Fallback", "now": "A"},
    }
    try:
        delay, tested_at = _last_url_test_delay(proxies["A"], proxies)
    except RecursionError:
        check("cyclic now chain does not recurse", False, "RecursionError")
        return
    check("cyclic now chain does not recurse", (delay, tested_at) == (0, 0))


def test_self_reference() -> None:
    proxies = {"A": {"type": "Selector", "now": "A"}}
    check(
        "self referencing now yields no delay",
        _last_url_test_delay(proxies["A"], proxies) == (0, 0),
    )


def test_dangling_now() -> None:
    proxies = {"A": {"type": "Selector", "now": "missing"}}
    check(
        "dangling now yields no delay",
        _last_url_test_delay(proxies["A"], proxies) == (0, 0),
    )


def test_own_history_wins() -> None:
    proxies = {
        "A": {
            "type": "URLTest",
            "now": "B",
            "history": [{"delay": 0}, {"delay": 42, "time": 1700000000000}],
        },
        "B": {"history": [{"delay": 99, "time": 1800000000000}]},
    }
    check(
        "own history wins over the selected proxy",
        _last_url_test_delay(proxies["A"], proxies) == (42, 1700000000000),
    )


def test_long_chain_still_resolves() -> None:
    # Selector -> Selector -> ... -> real proxy, well inside the walk bound.
    proxies = {f"G{i}": {"type": "Selector", "now": f"G{i + 1}"} for i in range(20)}
    proxies["G20"] = {"history": [{"delay": 7, "time": 1}]}
    result = _last_url_test_delay(proxies["G0"], proxies)
    check("long (non-cyclic) now chain resolves", result == (7, 1), str(result))


def test_absurd_chain_is_bounded() -> None:
    # Far beyond any real config: must stop instead of recursing forever.
    proxies = {f"G{i}": {"type": "Selector", "now": f"G{i + 1}"} for i in range(5000)}
    proxies["G5000"] = {"history": [{"delay": 7, "time": 1}]}
    try:
        result = _last_url_test_delay(proxies["G0"], proxies)
    except RecursionError:
        check("absurd now chain is bounded", False, "RecursionError")
        return
    check("absurd now chain is bounded", result == (0, 0), str(result))


def test_decode_fields_truncated() -> None:
    for payload in (b"\x0b", b"\x10", b"\x0a\x05ab", b"\x0a"):
        try:
            decode_fields(payload)
        except (ValueError, IndexError) as err:
            check(f"truncated frame {payload!r} raises ValueError", isinstance(err, ValueError), type(err).__name__)
        else:
            check(f"truncated frame {payload!r} raises ValueError", True)


def test_parse_trailer_garbage() -> None:
    try:
        status, message = _parse_trailer(b"grpc-status: not-a-number\r\n")
    except ValueError:
        check("malformed grpc-status does not raise", False)
        return
    check(
        "malformed grpc-status does not raise",
        status != 0 and message is not None,
        f"{status} {message}",
    )


def main() -> int:
    for test in (
        test_cyclic_now_chain,
        test_self_reference,
        test_dangling_now,
        test_own_history_wins,
        test_long_chain_still_resolves,
        test_absurd_chain_is_bounded,
        test_decode_fields_truncated,
        test_parse_trailer_garbage,
    ):
        test()
    if FAILURES:
        print(f"\n{len(FAILURES)} check(s) failed: {', '.join(FAILURES)}")
        return 1
    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
