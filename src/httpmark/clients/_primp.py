import primp

from httpmark.clients.base import AsyncClient, SyncClient
from httpmark.config import BenchmarkConfig


class Client(AsyncClient):
    name = "primp"
    http_versions = ["1.1", "2"]

    async def setup(self, config: BenchmarkConfig, http_version: str = "1.1") -> None:
        self._client = primp.AsyncClient(
            ca_cert_file=config.ca_cert,
            http2_only=(http_version == "2"),
            verify=True,
            follow_redirects=False,
        )

    async def teardown(self) -> None:
        pass

    async def get(self, url: str) -> int:
        resp = await self._client.get(url)
        resp.content
        return resp.status_code


class SyncHTTPClient(SyncClient):
    name = "primp"
    http_versions = ["1.1"]

    def setup(self, config: BenchmarkConfig) -> None:
        self._client = primp.Client(
            ca_cert_file=config.ca_cert,
            verify=True,
            follow_redirects=False,
        )

    def teardown(self) -> None:
        pass

    def get(self, url: str) -> int:
        resp = self._client.get(url)
        resp.content
        return resp.status_code
