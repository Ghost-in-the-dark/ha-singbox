"""Backend auto-detection for the sing-box integration.

sing-box exposes two management APIs:

* the gRPC ``api`` service (sing-box >= 1.14.0) over gRPC-Web;
* the ``clash_api`` Clash REST/WebSocket controller (sing-box 1.11+).

The integration prefers the gRPC service and falls back to the clash API
when the server does not route gRPC-Web paths (HTTP 404). Both the config
flow (connection validation) and entry setup use :func:`detect_backend`.
"""

from __future__ import annotations

import logging

from .clash import ClashClient
from .grpc import GRPC_STATUS_UNAUTHENTICATED, GrpcError, SingBoxClient

_LOGGER = logging.getLogger(__package__)

BACKEND_GRPC = "grpc"
BACKEND_CLASH = "clash"


async def detect_backend(
    host: str,
    port: int,
    secret: str,
    use_tls: bool,
    session,
) -> tuple[SingBoxClient | ClashClient, str]:
    """Create a client for the first working backend.

    Raises GrpcError(16) / ClashApiError(401) on authentication failure and
    ConnectionError when the server is unreachable.
    """
    grpc_client = SingBoxClient(
        host=host, port=port, secret=secret, use_tls=use_tls, session=session
    )
    try:
        await grpc_client.get_version()
    except GrpcError as err:
        if err.status == GRPC_STATUS_UNAUTHENTICATED:
            raise
        _LOGGER.info("gRPC API not available (%s), falling back to clash API", err)
    except (OSError, ConnectionError):
        _LOGGER.info("gRPC API unreachable, falling back to clash API")
    else:
        return grpc_client, BACKEND_GRPC
    await grpc_client.close()

    clash_client = ClashClient(
        host=host, port=port, secret=secret, use_tls=use_tls, session=session
    )
    version = await clash_client.get_version()
    _LOGGER.info("using clash API backend (sing-box %s)", version)
    return clash_client, BACKEND_CLASH
