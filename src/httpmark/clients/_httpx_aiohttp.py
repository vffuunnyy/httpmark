import ssl

import httpx

from httpx_aiohttp import HttpxAiohttpClient

from httpmark.clients.base import AsyncClient
from httpmark.config import BenchmarkConfig


class Client(AsyncClient):
    name = "httpx-aiohttp"
    http_versions = ("1.1",)

    async def setup(self, config: BenchmarkConfig, http_version: str = "1.1") -> None:
        ctx = ssl.create_default_context(cafile=config.ca_cert)
        pool_size = max(config.pool_size, config.concurrency)
        self._client = HttpxAiohttpClient(
            verify=ctx,
            limits=httpx.Limits(
                max_connections=pool_size,
                max_keepalive_connections=pool_size,
            ),
            timeout=httpx.Timeout(60.0, pool=120.0, write=None),
        )

    async def teardown(self) -> None:
        await self._client.aclose()

    async def get(self, url: str) -> int:
        resp = await self._client.get(url)
        return resp.status_code
