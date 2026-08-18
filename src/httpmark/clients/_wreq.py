from pathlib import Path

import wreq

from httpmark.clients.base import AsyncClient, SyncClient
from httpmark.config import BenchmarkConfig


def _client_kwargs(config: BenchmarkConfig, http_version: str) -> dict:
    kwargs: dict = {
        "tls_verify": Path(config.ca_cert),
        "pool_max_size": max(config.pool_size, config.concurrency),
    }
    if http_version == "1.1":
        kwargs["http1_only"] = True
    elif http_version == "2":
        kwargs["http2_only"] = True
    return kwargs


class Client(AsyncClient):
    name = "wreq"
    http_versions = ("1.1", "2")

    async def setup(self, config: BenchmarkConfig, http_version: str = "1.1") -> None:
        self._client = wreq.Client(**_client_kwargs(config, http_version))

    async def teardown(self) -> None:
        self._client.close()

    async def get(self, url: str) -> int:
        resp = await self._client.get(url)
        await resp.bytes()
        return resp.status.as_int()


class SyncHTTPClient(SyncClient):
    name = "wreq"
    http_versions = ("1.1",)

    def setup(self, config: BenchmarkConfig) -> None:
        self._client = wreq.blocking.Client(**_client_kwargs(config, "1.1"))

    def teardown(self) -> None:
        self._client.close()

    def get(self, url: str) -> int:
        resp = self._client.get(url)
        resp.bytes()
        return resp.status.as_int()
