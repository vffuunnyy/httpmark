import requests

from httpmark.clients.base import SyncClient
from httpmark.config import BenchmarkConfig


class SyncHTTPClient(SyncClient):
    name = "requests"
    http_versions = ("1.1",)

    def setup(self, config: BenchmarkConfig) -> None:
        self._session = requests.Session()
        self._session.verify = config.ca_cert
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=config.pool_size,
            pool_maxsize=config.pool_size,
        )
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

    def teardown(self) -> None:
        self._session.close()

    def get(self, url: str) -> int:
        resp = self._session.get(url)
        return resp.status_code
