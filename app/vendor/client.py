"""Shared HTTP client for the GPS TrackTech open API (API_EN.pdf, "Preface").

* Base URL and api version come from dbo.vendor_accounts; the secret key from the environment.
* Common headers: `key`, `version`, `Accept-Language`.
* Every response carries `code` / `data` / `msg` / `total` / `extend`. HTTP 200 alone is NOT success:
  the vendor `code` must be 200. Documented codes: 500 server failed, 504 missing/invalid key,
  401 no permission, 400 parameter error, 503 too frequent, 505 response timeout.
* Retries happen only for read-only calls (retry=True) on transient failures. Commands are never retried.
"""
import logging
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import Settings
from app.core.exceptions import (
    VendorAuthError,
    VendorBadRequestError,
    VendorError,
    VendorInvalidResponseError,
    VendorPermissionError,
    VendorRateLimitError,
    VendorTimeoutError,
    VendorUnavailableError,
)

logger = logging.getLogger(__name__)

_TRANSIENT_HTTP = {502, 503, 504}
_TRANSIENT_VENDOR_CODES = {503, 505}

@dataclass(frozen=True)
class VendorAccount:
    account_id: int
    tenant_id: int
    base_url: str
    api_version: str
    api_key: str = field(repr=False)
    vendor_user_id: int | None = None


@dataclass
class VendorResponse:
    code: int
    data: Any
    msg: str | None = None
    total: int | None = None
    extend: Any = None


class VendorClient:
    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None, sleep=time.sleep):
        self._settings = settings
        self._sleep = sleep
        self._http = httpx.Client(
            timeout=None,
            transport=transport,
            headers={"Accept": "application/json"},
            follow_redirects=False,
        )

    def close(self) -> None:
        self._http.close()

    def request(self, account: VendorAccount, method: str, path: str, *, params: dict | None = None,
                json: Any = None, data: dict | None = None, files: dict | None = None,
                retry: bool = False, language: str | None = None) -> VendorResponse:
        url = account.base_url.rstrip("/") + path
        headers = {
            "key": account.api_key,
            "version": account.api_version or "1.0",
            "Accept-Language": language or self._settings.gpstracktech_language,
        }
        attempts = 1 + (max(self._settings.gpstracktech_max_retries, 0) if retry else 0)
        last_error: VendorError | None = None
        for attempt in range(1, attempts + 1):
            started = time.perf_counter()
            try:
                response = self._http.request(method, url, params=params, json=json, data=data, files=files,
                                              headers=headers)
                result = self._parse(response)
                logger.info("vendor %s %s -> http=%s code=%s %.0fms", method, path, response.status_code,
                            result.code, (time.perf_counter() - started) * 1000)
                return result
            except httpx.TimeoutException:
                last_error = VendorTimeoutError()
            except httpx.TransportError as exc:
                last_error = VendorUnavailableError(f"Could not reach the vendor service ({type(exc).__name__})")
            except VendorError as exc:
                last_error = exc
            transient = isinstance(last_error, VendorTimeoutError | VendorUnavailableError | VendorRateLimitError)
            logger.warning("vendor %s %s failed (attempt %s/%s): %s", method, path, attempt, attempts, last_error.code)
            if not transient or attempt >= attempts:
                break
            self._sleep(self._settings.gpstracktech_retry_backoff * (2 ** (attempt - 1)))
        raise last_error

    @staticmethod
    def _parse(response: httpx.Response) -> VendorResponse:
        status = response.status_code
        try:
            body = response.json()
        except ValueError:
            body = None
        if not isinstance(body, dict) or "code" not in body:
            if status in _TRANSIENT_HTTP:
                raise VendorUnavailableError(http_status=status)
            if status in (401, 403):
                raise VendorAuthError(http_status=status)
            if status >= 400:
                raise VendorError(f"Vendor HTTP error {status}", http_status=status)
            raise VendorInvalidResponseError("The vendor returned a non-JSON or malformed response",
                                             http_status=status)
        try:
            code = int(body.get("code"))
        except (TypeError, ValueError):
            raise VendorInvalidResponseError("The vendor response code is missing or invalid",
                                             http_status=status) from None
        msg = body.get("msg")
        logger.warning(
    "GPS TRACKTECH RESPONSE: http_status=%s, vendor_code=%s, message=%s",
    status,
    code,
    str(msg)[:200] if msg else None
)

        if code == 200:
            if status >= 400:
                raise VendorError(f"Vendor HTTP error {status}", http_status=status, vendor_code=code)
            total = body.get("total")
            try:
                total = int(total) if total is not None else None
            except (TypeError, ValueError):
                total = None
            return VendorResponse(code=code, data=body.get("data"), msg=msg, total=total, extend=body.get("extend"))
        safe_msg = str(msg)[:200] if msg else None
        error_map = {
            504: VendorAuthError, 401: VendorPermissionError, 503: VendorRateLimitError,
            505: VendorTimeoutError, 500: VendorUnavailableError,
        }
        if code == 400:
            raise VendorBadRequestError(safe_msg, vendor_code=code, http_status=status,
                                        details={"vendorMessage": safe_msg} if safe_msg else None)
        error_cls = error_map.get(code)
        if error_cls:
            raise error_cls(vendor_code=code, http_status=status)
        raise VendorError(f"Vendor returned code {code}", vendor_code=code, http_status=status,
                          details={"vendorMessage": safe_msg} if safe_msg else None)
