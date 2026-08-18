from impit import AsyncClient as ImpitAsyncClient

from httpmark.clients.base import AsyncClient
from httpmark.config import BenchmarkConfig


class Client(AsyncClient):
    name = "impit"
    http_versions = ("1.1",)

    async def setup(self, config: BenchmarkConfig, http_version: str = "1.1") -> None:
        self._client = ImpitAsyncClient(verify=False)

    async def teardown(self) -> None:
        await self._client.__aexit__(None, None, None)

    async def get(self, url: str) -> int:
        resp = await self._client.get(url)
        return resp.status_code
