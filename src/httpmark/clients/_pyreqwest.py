from pathlib import Path

from pyreqwest.client import ClientBuilder, SyncClientBuilder

from httpmark.clients.base import AsyncClient, SyncClient
from httpmark.config import BenchmarkConfig


class Client(AsyncClient):
    name = "pyreqwest"
    http_versions = ["1.1", "2"]

    async def setup(self, config: BenchmarkConfig, http_version: str = "1.1") -> None:
        pem = Path(config.ca_cert).read_bytes()
        pool_size = max(config.pool_size, config.concurrency)
        builder = (
            ClientBuilder()
            .add_root_certificate_pem(pem)
            .max_connections(pool_size)
            .pool_max_idle_per_host(pool_size)
        )
        if http_version == "2":
            builder = builder.http2(True)
        else:
            builder = builder.http1_only()
        self._client = builder.build()

    async def teardown(self) -> None:
        await self._client.close()

    async def get(self, url: str) -> int:
        resp = await self._client.get(url).build().send()
        await resp.bytes()
        return resp.status


class SyncHTTPClient(SyncClient):
    name = "pyreqwest"
    http_versions = ["1.1"]

    def setup(self, config: BenchmarkConfig) -> None:
        pem = Path(config.ca_cert).read_bytes()
        self._client = (
            SyncClientBuilder()
            .add_root_certificate_pem(pem)
            .max_connections(config.pool_size)
            .pool_max_idle_per_host(config.pool_size)
            .http1_only()
            .build()
        )

    def teardown(self) -> None:
        self._client.close()

    def get(self, url: str) -> int:
        resp = self._client.get(url).build().send()
        resp.bytes()
        return resp.status
