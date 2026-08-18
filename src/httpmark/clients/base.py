from abc import ABC, abstractmethod
from typing import Any, ClassVar

from httpmark.config import BenchmarkConfig


class AsyncClient(ABC):
    name: ClassVar[str]
    http_versions: ClassVar[list[str]]

    @abstractmethod
    async def setup(self, config: BenchmarkConfig, http_version: str = "1.1") -> None: ...

    @abstractmethod
    async def teardown(self) -> None: ...

    @abstractmethod
    async def get(self, url: str) -> Any: ...


class SyncClient(ABC):
    name: ClassVar[str]
    http_versions: ClassVar[list[str]] = ["1.1"]

    @abstractmethod
    def setup(self, config: BenchmarkConfig) -> None: ...

    @abstractmethod
    def teardown(self) -> None: ...

    @abstractmethod
    def get(self, url: str) -> Any: ...
