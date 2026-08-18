from pathlib import Path

import rnet

from httpmark.clients.base import AsyncClient, SyncClient
from httpmark.config import BenchmarkConfig


class Client(AsyncClient):
    name = "rnet"
    http_versions = ("1.1", "2")

    async def setup(self, config: BenchmarkConfig, http_version: str = "1.1") -> None:
        pool_size = max(config.pool_size, config.concurrency)
        kwargs: dict = {
            "verify": Path(config.ca_cert),
            "pool_max_size": pool_size,
        }
        if http_version == "1.1":
            kwargs["http1_only"] = True
        elif http_version == "2":
            kwargs["http2_only"] = True
        self._client = rnet.Client(**kwargs)

    async def teardown(self) -> None:
        pass

    async def get(self, url: str) -> int:
        resp = await self._client.get(url)
        await resp.bytes()
        return resp.status.as_int()


class SyncHTTPClient(SyncClient):
    name = "rnet"
    http_versions = ("1.1",)

    def setup(self, config: BenchmarkConfig) -> None:
        self._client = rnet.blocking.Client(
            verify=Path(config.ca_cert),
            pool_max_size=config.pool_size,
            http1_only=True,
        )

    def teardown(self) -> None:
        pass

    def get(self, url: str) -> int:
        resp = self._client.get(url)
        resp.bytes()
        return resp.status.as_int()
