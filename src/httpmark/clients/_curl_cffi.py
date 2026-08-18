from curl_cffi import CurlHttpVersion
from curl_cffi.requests import AsyncSession, Session

from httpmark.clients.base import AsyncClient, SyncClient
from httpmark.config import BenchmarkConfig


def _curl_http_version(http_version: str) -> CurlHttpVersion:
    return CurlHttpVersion.V2TLS if http_version == "2" else CurlHttpVersion.V1_1


class Client(AsyncClient):
    name = "curl_cffi"
    http_versions = ("1.1", "2")

    async def setup(self, config: BenchmarkConfig, http_version: str = "1.1") -> None:
        self._session = AsyncSession(
            verify=config.ca_cert,
            http_version=_curl_http_version(http_version),
            max_clients=max(config.pool_size, config.concurrency),
        )

    async def teardown(self) -> None:
        await self._session.close()

    async def get(self, url: str) -> int:
        resp = await self._session.get(url)
        return resp.status_code


class SyncHTTPClient(SyncClient):
    name = "curl_cffi"
    http_versions = ("1.1",)

    def setup(self, config: BenchmarkConfig) -> None:
        self._session = Session(
            verify=config.ca_cert,
            http_version=CurlHttpVersion.V1_1,
        )

    def teardown(self) -> None:
        self._session.close()

    def get(self, url: str) -> int:
        resp = self._session.get(url)
        return resp.status_code
