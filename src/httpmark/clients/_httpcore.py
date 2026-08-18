import ssl

import httpcore

from httpmark.clients.base import AsyncClient
from httpmark.config import BenchmarkConfig


class Client(AsyncClient):
    name = "httpcore"
    http_versions = ["1.1", "2"]

    async def setup(self, config: BenchmarkConfig, http_version: str = "1.1") -> None:
        ssl_context = ssl.create_default_context(cafile=config.ca_cert)
        use_http2 = http_version == "2"
        pool_size = max(config.pool_size, config.concurrency)
        self._pool = httpcore.AsyncConnectionPool(
            ssl_context=ssl_context,
            max_connections=pool_size,
            max_keepalive_connections=pool_size,
            keepalive_expiry=30.0,
            http2=use_http2,
            http1=not use_http2,
        )

    async def teardown(self) -> None:
        await self._pool.aclose()

    async def get(self, url: str) -> int:
        resp = await self._pool.request("GET", url)
        return resp.status
