"""Shared stdlib HTTP + provenance helpers for public providers.

Public providers use only the Python standard library (``urllib``) so the data
layer carries no heavy third-party dependency. A pluggable transport keeps the
providers testable offline.
"""

from __future__ import annotations

import hashlib
import json
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any

# transport(method, url, *, data, headers, timeout) -> (status, body_text)
Transport = Callable[..., tuple[int, str]]

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
}


def stdlib_transport(
    method: str,
    url: str,
    *,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 15.0,
) -> tuple[int, str]:
    request = urllib.request.Request(  # noqa: S310 - public market data endpoints
        url,
        data=data,
        headers={**DEFAULT_HEADERS, **(headers or {})},
        method=method,
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return response.status, response.read().decode("utf-8")


def get_json(
    url: str,
    *,
    transport: Transport,
    headers: dict[str, str] | None = None,
    timeout: float = 15.0,
) -> tuple[dict[str, Any], str]:
    """GET a URL and parse JSON, returning ``(payload, raw_text)``."""
    status, body = transport("GET", url, headers=headers, timeout=timeout)
    if status != 200:
        raise RuntimeError(f"GET {url} failed: status={status}")
    return json.loads(body), body


def post_form_json(
    url: str,
    form: dict[str, str],
    *,
    transport: Transport,
    headers: dict[str, str] | None = None,
    timeout: float = 15.0,
) -> tuple[Any, str]:
    """POST a urlencoded form and parse JSON, returning ``(payload, raw_text)``."""
    data = urllib.parse.urlencode(form).encode("utf-8")
    merged = {"Content-Type": "application/x-www-form-urlencoded", **(headers or {})}
    status, body = transport("POST", url, data=data, headers=merged, timeout=timeout)
    if status != 200:
        raise RuntimeError(f"POST {url} failed: status={status}")
    return json.loads(body), body


def content_hash(raw: str) -> str:
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def secid_for(ts_code: str) -> str:
    """EastMoney secid: ``1.<code>`` for SSE, ``0.<code>`` for SZSE/BSE."""
    code, _, suffix = ts_code.partition(".")
    market = "1" if suffix.upper() == "SH" else "0"
    return f"{market}.{code}"
