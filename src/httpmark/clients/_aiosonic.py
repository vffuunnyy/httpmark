import ssl

from aiosonic import HTTPClient
from aiosonic.connectors import TCPConnector
from aiosonic.pools import PoolConfig

from httpmark.clients.base import AsyncClient
from httpmark.config import BenchmarkConfig


class Client(AsyncClient):
    name = "aiosonic"
    http_versions = ("1.1",)

    async def setup(self, config: BenchmarkConfig, http_version: str = "1.1") -> None:
        self._ssl = ssl.create_default_context(cafile=config.ca_cert)
        pool_size = max(config.pool_size, config.concurrency)
        connector = TCPConnector(
            pool_configs={":default": PoolConfig(size=pool_size, max_conn_requests=None)},
        )
        self._client = HTTPClient(connector)

    async def teardown(self) -> None:
        await self._client.shutdown()

    async def get(self, url: str) -> int:
        resp = await self._client.get(url, ssl=self._ssl)
        await resp.content()
        return resp.status_code
