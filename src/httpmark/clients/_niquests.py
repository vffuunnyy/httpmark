import niquests

from httpmark.clients.base import AsyncClient
from httpmark.config import BenchmarkConfig


class Client(AsyncClient):
    name = "niquests"
    http_versions = ["1.1", "2"]

    async def setup(self, config: BenchmarkConfig, http_version: str = "1.1") -> None:
        use_multiplexed = http_version == "2"
        pool_size = max(config.pool_size, config.concurrency)
        self._session = niquests.AsyncSession(
            multiplexed=use_multiplexed,
            pool_connections=pool_size,
            pool_maxsize=pool_size,
        )
        self._session.verify = config.ca_cert
        self._multiplexed = use_multiplexed

    async def teardown(self) -> None:
        await self._session.close()

    async def get(self, url: str) -> int:
        resp = await self._session.get(url)
        if self._multiplexed:
            await self._session.gather(resp)
        return resp.status_code
