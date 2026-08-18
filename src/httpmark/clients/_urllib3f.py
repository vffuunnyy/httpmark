from urllib3_future import AsyncPoolManager

from httpmark.clients.base import AsyncClient
from httpmark.config import BenchmarkConfig


class Client(AsyncClient):
    name = "urllib3-future"
    http_versions = ("1.1", "2")

    async def setup(self, config: BenchmarkConfig, http_version: str = "1.1") -> None:
        self._multiplexed = http_version == "2"
        pool_size = max(config.pool_size, config.concurrency)
        self._pool = AsyncPoolManager(
            maxsize=pool_size,
            ca_certs=config.ca_cert,
        )

    async def teardown(self) -> None:
        await self._pool.clear()

    async def get(self, url: str) -> int:
        if self._multiplexed:
            promise = await self._pool.urlopen("GET", url, multiplexed=True)
            resp = await self._pool.get_response(promise=promise)
        else:
            resp = await self._pool.urlopen("GET", url)
        return resp.status
