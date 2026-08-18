from pathlib import Path

from pyreqwest.client import ClientBuilder
from zapros import AsyncClient as ZaprosAsyncClient, AsyncPyreqwestHandler

from httpmark.clients.base import AsyncClient
from httpmark.config import BenchmarkConfig


class Client(AsyncClient):
    name = "zapros-rq"
    http_versions = ("1.1", "2")

    async def setup(self, config: BenchmarkConfig, http_version: str = "1.1") -> None:
        pem = Path(config.ca_cert).read_bytes()
        pool_size = max(config.pool_size, config.concurrency)
        builder = (
            ClientBuilder()
            .add_root_certificate_pem(pem)
            .max_connections(pool_size)
            .pool_max_idle_per_host(pool_size)
        )
        builder = builder.http2(True) if http_version == "2" else builder.http1_only()
        self._client = ZaprosAsyncClient(handler=AsyncPyreqwestHandler(client=builder))
        await self._client.__aenter__()

    async def teardown(self) -> None:
        await self._client.__aexit__(None, None, None)

    async def get(self, url: str) -> int:
        resp = await self._client.get(url)
        await resp.aread()
        return resp.status
