import ssl

import aiohttp

from httpmark.clients.base import AsyncClient
from httpmark.config import BenchmarkConfig


class Client(AsyncClient):
    name = "aiohttp"
    http_versions = ("1.1",)

    async def setup(self, config: BenchmarkConfig, http_version: str = "1.1") -> None:
        ssl_context = ssl.create_default_context(cafile=config.ca_cert)
        pool_size = max(config.pool_size, config.concurrency)
        connector = aiohttp.TCPConnector(
            limit=pool_size,
            limit_per_host=pool_size,
            ssl=ssl_context,
            ttl_dns_cache=None,
        )
        self._session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=None),
        )

    async def teardown(self) -> None:
        await self._session.close()

    async def get(self, url: str) -> int:
        async with self._session.get(url) as resp:
            await resp.read()
            return resp.status
