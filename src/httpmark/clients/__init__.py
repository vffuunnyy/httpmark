from httpmark.clients.base import AsyncClient, SyncClient

ASYNC_HTTP1_CLIENTS: list[type[AsyncClient]] = []
ASYNC_HTTP2_CLIENTS: list[type[AsyncClient]] = []
SYNC_CLIENTS: list[type[SyncClient]] = []


def _register() -> None:
    from httpmark.clients import (
        _aiohttp,
        _aiosonic,
        _curl_cffi,
        _httpcore,
        _httpx,
        _impit,
        _niquests,
        _primp,
        _pycurl,
        _pyreqwest,
        _requests,
        _rnet,
        _urllib3f,
        _wreq,
    )

    async_modules = (
        _aiohttp,
        _aiosonic,
        _httpx,
        _httpcore,
        _niquests,
        _urllib3f,
        _impit,
        _primp,
        _rnet,
        _wreq,
        _curl_cffi,
        _pyreqwest,
    )
    for mod in async_modules:
        if hasattr(mod, "Client"):
            cls = mod.Client
            if "1.1" in cls.http_versions:
                ASYNC_HTTP1_CLIENTS.append(cls)
            if "2" in cls.http_versions:
                ASYNC_HTTP2_CLIENTS.append(cls)

    sync_modules = (_requests, _primp, _rnet, _wreq, _curl_cffi, _pyreqwest, _pycurl)
    for mod in sync_modules:
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
