import importlib

from httpmark.clients.base import AsyncClient, SyncClient


ASYNC_HTTP1_CLIENTS: list[type[AsyncClient]] = []
ASYNC_HTTP2_CLIENTS: list[type[AsyncClient]] = []
SYNC_CLIENTS: list[type[SyncClient]] = []
UNAVAILABLE: dict[str, str] = {}

_MODULES = [
    "_aiohttp",
    "_aiosonic",
    "_httpx",
    "_httpx_aiohttp",
    "_httpcore",
    "_niquests",
    "_urllib3f",
    "_impit",
    "_primp",
    "_rnet",
    "_wreq",
    "_curl_cffi",
    "_pyreqwest",
    "_zapros",
    "_zapros_rq",
    "_requests",
    "_pycurl",
]


def _register() -> None:
    for name in _MODULES:
        try:
            mod = importlib.import_module(f"httpmark.clients.{name}")
        except ImportError as e:
            UNAVAILABLE[name.lstrip("_")] = str(e)
            continue
        if hasattr(mod, "Client"):
            cls = mod.Client
            if "1.1" in cls.http_versions:
                ASYNC_HTTP1_CLIENTS.append(cls)
            if "2" in cls.http_versions:
                ASYNC_HTTP2_CLIENTS.append(cls)
        if hasattr(mod, "SyncHTTPClient"):
            SYNC_CLIENTS.append(mod.SyncHTTPClient)


_register()


def get_async_client(name: str) -> type[AsyncClient]:
    for cls in (*ASYNC_HTTP1_CLIENTS, *ASYNC_HTTP2_CLIENTS):
        if cls.name == name:
            return cls
    raise KeyError(f"unknown async client: {name}")


def get_sync_client(name: str) -> type[SyncClient]:
    for cls in SYNC_CLIENTS:
        if cls.name == name:
            return cls
    raise KeyError(f"unknown sync client: {name}")
