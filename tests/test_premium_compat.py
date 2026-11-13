"""Tests for the premium/PDK clash-API compatibility layer.

Covers the three behaviours that came out of comparing an upstream
sing-box 1.14.4 with the "1.14.4-pdk" build:

* a failed url-test is data, not an exception (the full-screen red banner);
* the optional endpoints (/group batch tests, /rules, cache flushes) are
  probed once and simply disappear on a build that does not have them;
* a premium build and an upstream build produce the same coordinator
  snapshot, so nothing downstream has to know which one it talks to.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

_PKG_DIR = Path(__file__).resolve().parents[1] / "custom_components" / "singbox"
if "singbox" not in sys.modules:
    _pkg = types.ModuleType("singbox")
    _pkg.__path__ = [str(_PKG_DIR)]
    sys.modules["singbox"] = _pkg

from custom_components.singbox.clash import (  # noqa: E402
    ClashApiError,
    ClashClient,
    PingResult,
    _best_delay,
    is_testable_proxy,
    parse_group_delay,
)
from custom_components.singbox.errors import SingBoxNotSupported  # noqa: E402
from custom_components.singbox.grpc import SingBoxGroupItem  # noqa: E402


class FakeClash(ClashClient):
    """ClashClient with the HTTP layer replaced by a dict of canned replies."""

    def __init__(self, replies: dict[str, object]) -> None:
        super().__init__("127.0.0.1", 9090, secret="x")
        self.replies = replies
        self.calls: list[tuple[str, str, dict | None]] = []

    async def _json(self, method: str, path: str, **kwargs: object):
        self.calls.append((method, path, kwargs.get("params")))
        key = f"{method} {path}"
        reply = self.replies.get(key, ClashApiError(404, "Resource not found"))
        if isinstance(reply, Exception):
            raise reply
        return reply


# -- failed tests are data -------------------------------------------------


async def test_failed_url_test_returns_result_instead_of_raising() -> None:
    """A 503 (the reject outbound) must not become an exception.

    This is what produced the full-screen "Failed to perform the action
    singbox/url_test" banner for the block outbound.
    """
    client = FakeClash({"GET /proxies/block/delay": ClashApiError(503, "delay failed")})
    result = await client.url_test("block")
    assert result.failed is True
    assert result.delay == 0
    assert client.last_pings["block"].failed is True


async def test_missing_proxy_is_a_failed_ping_not_an_error() -> None:
    """GLOBAL (and a tag that vanished between polls) answers 404."""
    client = FakeClash({"GET /proxies/GLOBAL/delay": ClashApiError(404, "not found")})
    result = await client.url_test("GLOBAL")
    assert result.failed is True


async def test_zero_delay_is_a_failure_not_a_success() -> None:
    client = FakeClash({"GET /proxies/awg/delay": {"delay": 0}})
    result = await client.url_test("awg")
    assert result.failed is True


async def test_successful_test_records_delay_and_time() -> None:
    client = FakeClash({"GET /proxies/awg/delay": {"delay": 152}})
    result = await client.url_test("awg")
    assert result.failed is False
    assert result.delay == 152
    assert result.test_time > 0


async def test_auth_errors_still_propagate() -> None:
    """A rejected secret is not an outbound problem and must surface."""
    client = FakeClash({"GET /proxies/awg/delay": ClashApiError(401, "Unauthorized")})
    with pytest.raises(ClashApiError) as err:
        await client.url_test("awg")
    assert err.value.status == 401


# -- untestable outbounds ---------------------------------------------------


@pytest.mark.parametrize("tag", ["GLOBAL", "REJECT", "REJECT-DROP", "PASS"])
def test_synthetic_tags_are_never_tested(tag: str) -> None:
    assert is_testable_proxy(tag, None) is False


@pytest.mark.parametrize("outbound_type", ["Reject", "RejectDrop", "Block"])
def test_reject_outbounds_are_never_tested(outbound_type: str) -> None:
    assert is_testable_proxy("block", {"type": outbound_type}) is False


def test_real_outbounds_are_testable() -> None:
    assert is_testable_proxy("awg_EU", {"type": "Direct"}) is True
    assert is_testable_proxy("My servers: EU2", {"type": "VLESS"}) is True


# -- group batch results ----------------------------------------------------


def test_parse_group_delay_keeps_usable_delays() -> None:
    payload = {"eu: EU2": 152, "eu: EU-openwrt": 0, "ru: Game_ru": "x", "bad": True}
    assert parse_group_delay(payload) == {"eu: EU2": 152, "eu: EU-openwrt": 0}


def test_parse_group_delay_tolerates_junk() -> None:
    assert parse_group_delay(None) == {}
    assert parse_group_delay([1, 2]) == {}


async def test_group_delay_response_is_a_group_ping() -> None:
    """A group answers with {member: ms}; the *best* member is the group delay.

    max() used to be taken here, which reported the slowest node of the group
    as the group's own ping (the card showed a 176 ms group as "820 ms").
    """
    client = FakeClash({"GET /proxies/telaga-out/delay": {"eu: EU2": 130, "eu: X": 152}})
    result = await client.url_test("telaga-out")
    assert result.delay == 130
    assert result.failed is False


def test_best_delay_ignores_failed_members() -> None:
    """Failed members are reported as 0 and must not look like the best node."""
    assert _best_delay([0, 0]) == 0
    assert _best_delay([0, 127, 188]) == 127
    assert _best_delay([135, 129]) == 129
    assert _best_delay([]) == 0


async def test_group_delay_with_only_failures_is_a_failure() -> None:
    client = FakeClash({"GET /proxies/g/delay": {"m1": 0, "m2": 0}})
    result = await client.url_test("g")
    assert result.failed is True
    assert result.delay == 0


# -- capability detection ---------------------------------------------------


async def test_premium_build_enables_batch_and_rules() -> None:
    client = FakeClash(
        {
            "GET /group": {"proxies": [{"name": "g", "type": "Selector"}]},
            "GET /rules": {"rules": [{"type": "default", "payload": "x", "proxy": "y"}]},
        }
    )
    await client.detect_capabilities()
    assert client.group_delay_available is True
    assert client.rules_available is True


async def test_upstream_build_keeps_features_off() -> None:
    """Upstream 1.14.4 has /group but answers {"rules": null}."""
    client = FakeClash(
        {
            "GET /group": {"proxies": [{"name": "g", "type": "Selector"}]},
            "GET /rules": {"rules": None},
        }
    )
    await client.detect_capabilities()
    assert client.group_delay_available is True
    assert client.rules_available is False


async def test_build_without_optional_endpoints_still_detects() -> None:
    """A build that 404s everything optional must not raise."""
    client = FakeClash({})
    await client.detect_capabilities()
    assert client.group_delay_available is False
    assert client.rules_available is False


# -- batch url test falls back per proxy -----------------------------------


async def test_url_test_many_uses_group_endpoint_then_falls_back() -> None:
    client = FakeClash(
        {
            "GET /group/g1/delay": {"m1": 100, "m2": 120},
            "GET /proxies/leaf/delay": {"delay": 55},
        }
    )
    client.group_delay_available = True
    results = await client.url_test_many(["g1", "leaf"])
    assert results["g1"].delay == 100
    assert results["m1"].delay == 100
    assert results["leaf"].delay == 55
    # The batch call happened for the group, not one call per member.
    paths = [path for method, path, _ in client.calls]
    assert "/group/g1/delay" in paths


async def test_url_test_many_skips_untestable_tags() -> None:
    client = FakeClash({"GET /proxies/awg/delay": {"delay": 10}})
    results = await client.url_test_many(["GLOBAL", "REJECT", "awg"])
    assert set(results) == {"awg"}


# -- optional services on an upstream build --------------------------------


async def test_dns_query_raises_not_supported_on_upstream() -> None:
    client = FakeClash({})
    with pytest.raises(SingBoxNotSupported):
        await client.dns_query("example.com")


async def test_flush_cache_raises_not_supported_on_upstream() -> None:
    client = FakeClash({})
    with pytest.raises(SingBoxNotSupported):
        await client.flush_fakeip_cache()


async def test_reload_config_raises_not_supported_on_upstream() -> None:
    client = FakeClash({})
    with pytest.raises(SingBoxNotSupported):
        await client.reload_config()


async def test_get_rules_returns_empty_list_on_upstream() -> None:
    """{"rules": null} is a normal upstream answer, not a failure."""
    client = FakeClash({"GET /rules": {"rules": None}})
    assert await client.get_rules() == []


async def test_get_rules_returns_rules_on_premium() -> None:
    client = FakeClash(
        {"GET /rules": {"rules": [{"type": "default", "payload": "p", "proxy": "q"}]}}
    )
    assert await client.get_rules() == [{"type": "default", "payload": "p", "proxy": "q"}]


# -- proxy list merges test failures ---------------------------------------


async def test_get_proxies_marks_failed_outbounds() -> None:
    """A failure wins over the stale history entry sing-box keeps."""
    client = FakeClash(
        {
            "GET /proxies": {
                "proxies": {
                    "awg": {
                        "type": "Direct",
                        "history": [{"delay": 90, "time": 111}],
                    },
                }
            }
        }
    )
    client.last_pings["awg"] = PingResult(tag="awg", delay=0, failed=True, test_time=222)
    _, proxies = await client.get_proxies()
    assert proxies[0].url_test_failed is True
    assert proxies[0].url_test_delay == 0


async def test_get_proxies_keeps_history_when_test_succeeded() -> None:
    client = FakeClash(
        {
            "GET /proxies": {
                "proxies": {
                    "awg": {"type": "Direct", "history": [{"delay": 90, "time": 111}]},
                }
            }
        }
    )
    _, proxies = await client.get_proxies()
    assert proxies[0].url_test_failed is False
    assert proxies[0].url_test_delay == 90


def test_group_item_defaults_have_no_failure() -> None:
    item = SingBoxGroupItem(tag="a", type="Direct", url_test_time=0, url_test_delay=0)
    assert item.url_test_failed is False


# -- route and tag correctness ---------------------------------------------


async def test_reload_config_uses_put_not_post() -> None:
    """sing-box mounts PUT/PATCH on /configs only; POST is 405 on every build.

    The old code posted to /configs, so it reported "not supported" even on a
    server that answers the route.
    """
    client = FakeClash({"PUT /configs": None})
    await client.reload_config()
    methods = [(method, path) for method, path, _ in client.calls]
    assert ("PUT", "/configs") in methods
    assert not any(method == "POST" and path == "/configs" for method, path in methods)


async def test_reload_config_passes_force() -> None:
    client = FakeClash({"PUT /configs": None})
    await client.reload_config(force=True)
    assert client.calls[0][2] == {"force": "true"}


async def test_reload_config_maps_rejection_to_not_supported() -> None:
    client = FakeClash({"PUT /configs": ClashApiError(405, "Method Not Allowed")})
    with pytest.raises(SingBoxNotSupported):
        await client.reload_config()


async def test_reload_config_keeps_auth_errors() -> None:
    client = FakeClash({"PUT /configs": ClashApiError(401, "Unauthorized")})
    with pytest.raises(ClashApiError) as err:
        await client.reload_config()
    assert err.value.status == 401


async def test_select_outbound_percent_encodes_the_tags() -> None:
    """Real tags contain spaces, colons and emoji; a raw tag breaks the path."""
    client = FakeClash({"PUT /proxies/my%20group%3A%20EU/": None})
    await client.select_outbound("my group: EU", "eu: node one")
    method, path, _ = client.calls[0]
    assert method == "PUT"
    # quote(safe="") percent-encodes the space *and* the colon; sing-box
    # answers 204 for both forms, so either is accepted, but the encoded one
    # is the only one that survives a tag containing "/".
    assert path == "/proxies/my%20group%3A%20EU/"
    assert " " not in path


async def test_select_outbound_encodes_slashes_in_a_tag() -> None:
    """An unencoded slash would route the request to another endpoint."""
    client = FakeClash({"PUT /proxies/a%2Fb/": None})
    await client.select_outbound("a/b", "x")
    assert client.calls[0][1].count("/") == 3


async def test_group_delay_works_without_an_explicit_url() -> None:
    """It used to be a required positional argument, so calling it raised."""
    client = FakeClash({"GET /group/g/delay": {"m": 42}})
    assert await client._group_delay("g") == {"m": 42}


# -- authentication must never be masked as "unsupported" -------------------


async def test_rules_propagate_auth_errors() -> None:
    """A 401 is a reauth problem, not "this build has no rules endpoint"."""
    client = FakeClash({"GET /rules": ClashApiError(401, "Unauthorized")})
    with pytest.raises(ClashApiError) as err:
        await client.get_rules()
    assert err.value.status == 401


async def test_dns_query_propagates_auth_errors() -> None:
    client = FakeClash({"GET /dns/query": ClashApiError(401, "Unauthorized")})
    with pytest.raises(ClashApiError) as err:
        await client.dns_query("example.com")
    assert err.value.status == 401


async def test_flush_cache_propagates_auth_errors() -> None:
    client = FakeClash({"POST /cache/fakeip/flush": ClashApiError(401, "Unauthorized")})
    with pytest.raises(ClashApiError) as err:
        await client.flush_fakeip_cache()
    assert err.value.status == 401


async def test_dns_query_keeps_bad_request_visible() -> None:
    """A rejected record type is the caller's mistake, not a missing feature."""
    client = FakeClash({"GET /dns/query": ClashApiError(400, "invalid query type")})
    with pytest.raises(ClashApiError) as err:
        await client.dns_query("example.com", "NOPE")
    assert err.value.status == 400


async def test_close_connection_encodes_the_id() -> None:
    client = FakeClash({"DELETE /connections/a%2Fb": None})
    await client.close_connection("a/b")
    assert client.calls[0] == ("DELETE", "/connections/a%2Fb", None)
