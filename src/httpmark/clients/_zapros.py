import ssl

from zapros import (
    AsyncClient as ZaprosAsyncClient,
    AsyncIOTransport,
    AsyncStdNetworkHandler,
    Client as ZaprosClient,
    StdNetworkHandler,
    SyncTransport,
)

from httpmark.clients.base import AsyncClient, SyncClient
from httpmark.config import BenchmarkConfig


class Client(AsyncClient):
    name = "zapros"
    http_versions = ("1.1",)

    async def setup(self, config: BenchmarkConfig, http_version: str = "1.1") -> None:
        ctx = ssl.create_default_context(cafile=config.ca_cert)
        pool_size = max(config.pool_size, config.concurrency)
        self._client = ZaprosAsyncClient(
            handler=AsyncStdNetworkHandler(
                transport=AsyncIOTransport(ssl_context=ctx),
                http1={"max_connections_per_host": pool_size},
            )
        )
        await self._client.__aenter__()

    async def teardown(self) -> None:
        await self._client.__aexit__(None, None, None)

    async def get(self, url: str) -> int:
        resp = await self._client.get(url)
        await resp.aread()
        return resp.status


class SyncHTTPClient(SyncClient):
    name = "zapros"
    http_versions = ("1.1",)

    def setup(self, config: BenchmarkConfig) -> None:
        ctx = ssl.create_default_context(cafile=config.ca_cert)
        self._client = ZaprosClient(
            handler=StdNetworkHandler(
                transport=SyncTransport(ssl_context=ctx),
                http1={"max_connections_per_host": config.pool_size},
            )
        )
        self._client.__enter__()

    def teardown(self) -> None:
        self._client.__exit__(None, None, None)

    def get(self, url: str) -> int:
        resp = self._client.get(url)
        resp.read()
        return resp.status
