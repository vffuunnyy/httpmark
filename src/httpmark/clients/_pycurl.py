import pycurl

from httpmark.clients.base import SyncClient
from httpmark.config import BenchmarkConfig


class SyncHTTPClient(SyncClient):
    name = "pycurl"
    http_versions = ("1.1",)

    def setup(self, config: BenchmarkConfig) -> None:
        self._curl = pycurl.Curl()
        self._curl.setopt(pycurl.CAINFO, config.ca_cert)
        self._curl.setopt(pycurl.HTTP_VERSION, pycurl.CURL_HTTP_VERSION_1_1)
        self._curl.setopt(pycurl.WRITEFUNCTION, len)
        self._curl.setopt(pycurl.FOLLOWLOCATION, 0)

    def teardown(self) -> None:
        self._curl.close()

    def get(self, url: str) -> int:
        self._curl.setopt(pycurl.URL, url)
        self._curl.perform()
        return self._curl.getinfo(pycurl.RESPONSE_CODE)
