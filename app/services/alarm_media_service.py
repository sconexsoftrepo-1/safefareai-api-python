"""Alarm media migration: GPS TrackTech vendor server -> our AWS S3 bucket.

For every dbo.alarm_media record with s3_key IS NULL:
    vendor URL  = ALARM_MEDIA_VENDOR_BASE_URL + vendor_url                      (leading slash optional)
    S3 key      = <prefix>/<yyyy-mm-dd of alarm_time>/img|video/<original file name>
    S3 URL      = https://<bucket>.s3.<region>.amazonaws.com/<S3 key>          (stored in alarm_media.s3_key)
The file is STREAMED from the vendor to S3 (never fully in memory) and s3_key is written only after the upload worked.
A failed record keeps s3_key = NULL and is retried later with an increasing delay (kept in memory, no schema change).
"""
from __future__ import annotations

import logging
import mimetypes
import socket
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, BinaryIO, Callable, Dict, List, Optional, Set, Tuple
from urllib.parse import quote, unquote, urlsplit

from app.config.alarm_media_config import AlarmMediaConfig

logger = logging.getLogger(__name__)

MEDIA_FOLDERS = {"IMAGE": "img", "VIDEO": "video"}


class InvalidMediaRecord(Exception):
    """The record itself is unusable (empty / foreign vendor_url, unknown media_type, no alarm_time)."""


class VendorError(Exception):
    """The vendor server could not deliver the file (HTTP error, timeout, connection problem)."""

    def __init__(self, message: str, status: Optional[int] = None):
        super().__init__(message)
        self.status = status


class DuplicateMediaError(Exception):
    """Another alarm_media record already owns this S3 URL (unique index on s3_key), so this record cannot get it."""

    def __init__(self, s3_url: str, owner_id: Optional[int] = None):
        super().__init__(f"S3 URL already stored for alarm_media id={owner_id}")
        self.s3_url, self.owner_id = s3_url, owner_id


class MigrationAborted(Exception):
    """The backend is shutting down; the record stays NULL and is picked up again after the next start."""


# ----------------------------------------------------------------------------------------------- pure helpers
def build_vendor_url(base_url: str, vendor_url: Any) -> str:
    """base + relative path. Handles paths with or without a leading slash. An absolute URL is accepted only when it
    already points at the vendor base URL (so a bad row can never make the server fetch an arbitrary host)."""
    path = str(vendor_url or "").strip()
    if not path:
        raise InvalidMediaRecord("vendor_url is empty")
    base = base_url.rstrip("/")
    if "://" in path:
        if not path.lower().startswith(base.lower() + "/"):
            raise InvalidMediaRecord(f"vendor_url is an absolute URL of another host: {path[:80]}")
        path = path[len(base):]
    path = path.split("#", 1)[0].split("?", 1)[0].strip().lstrip("/")
    segments = path.split("/")
    if not path or ".." in segments or "" in segments or not segments[-1]:
        raise InvalidMediaRecord(f"vendor_url is not a valid file path: {path[:80]!r}")
    return base + "/" + quote(path, safe="/%")


def media_file_name(vendor_url: Any) -> str:
    """Original file name = last path segment of vendor_url (query string ignored)."""
    path = urlsplit(str(vendor_url or "").strip()).path
    name = path.rstrip("/").rsplit("/", 1)[-1]
    if not name or name in (".", ".."):
        raise InvalidMediaRecord(f"no file name in vendor_url {str(vendor_url)[:80]!r}")
    return name


def alarm_date(alarm_time: Any) -> str:
    """yyyy-mm-dd taken from the alarm_time column (never from the vendor path)."""
    if isinstance(alarm_time, datetime):
        return alarm_time.strftime("%Y-%m-%d")
    if isinstance(alarm_time, date):
        return alarm_time.isoformat()
    if isinstance(alarm_time, str) and alarm_time.strip():
        text = alarm_time.strip().replace("T", " ")
        try:
            return datetime.fromisoformat(text[:19]).strftime("%Y-%m-%d")
        except ValueError:
            pass
    raise InvalidMediaRecord(f"alarm_time is missing or not a date: {alarm_time!r}")


def build_s3_key(prefix: str, alarm_time: Any, media_type: Any, vendor_url: Any) -> str:
    folder = MEDIA_FOLDERS.get(str(media_type or "").strip().upper())
    if folder is None:
        raise InvalidMediaRecord(f"media_type must be IMAGE or VIDEO, got {media_type!r}")
    return f"{prefix.strip('/')}/{alarm_date(alarm_time)}/{folder}/{media_file_name(vendor_url)}"


def build_s3_url(bucket: str, region: str, key: str) -> str:
    return f"https://{bucket}.s3.{region}.amazonaws.com/{quote(key, safe='/')}"


def key_from_s3_url(s3_url: Any, prefix: str) -> str:
    """Object key from the full URL stored in s3_key. Only keys inside the alarm media folder are accepted, so a
    signed link can never be made for any other file of the bucket."""
    path = unquote(urlsplit(str(s3_url or "").strip()).path).lstrip("/")
    folder = prefix.strip("/") + "/"
    if not path.startswith(folder) or ".." in path.split("/") or path.endswith("/"):
        raise InvalidMediaRecord("s3_key is not inside the alarm media folder")
    return path


def guess_content_type(file_name: str, vendor_type: Optional[str]) -> str:
    guessed = mimetypes.guess_type(file_name)[0]
    if guessed:
        return guessed
    if vendor_type and vendor_type.lower() not in ("application/octet-stream", "binary/octet-stream"):
        return vendor_type.split(";")[0].strip()
    return "application/octet-stream"


# ----------------------------------------------------------------------------------------------- retry bookkeeping
class RetryTracker:
    """Failures per record id (in memory). Delay = base * 2^(failures-1), at most backoff_max; after max_attempts
    failures in a row the record is parked for park_seconds and the counting starts again."""

    def __init__(self, cfg: AlarmMediaConfig):
        self._cfg = cfg
        self._lock = threading.Lock()
        self._state: Dict[int, Tuple[int, float]] = {}        # id -> (failures, retry_not_before)

    def blocked(self, record_id: int, now: float) -> bool:
        with self._lock:
            entry = self._state.get(record_id)
            return entry is not None and entry[1] > now

    def failure(self, record_id: int, now: float, permanent: bool = False, park: bool = False) -> float:
        """Register a failure; returns the delay (seconds) before the record is tried again.
        park=True (a duplicate that can never be saved) waits the full park_seconds at once."""
        cfg = self._cfg
        with self._lock:
            failures = self._state.get(record_id, (0, 0.0))[0] + 1
            if park:
                delay, failures = float(cfg.park_seconds), 0
            elif failures >= cfg.max_attempts:
                delay, failures = float(cfg.park_seconds), 0
            else:
                delay = float(min(cfg.backoff_base_seconds * (2 ** (failures - 1)), cfg.backoff_max_seconds))
            if permanent:                                      # bad data will not fix itself in a few seconds
                delay = max(delay, float(cfg.backoff_max_seconds))
            self._state[record_id] = (failures, now + delay)
            return delay

    def success(self, record_id: int) -> None:
        with self._lock:
            self._state.pop(record_id, None)


# ----------------------------------------------------------------------------------------------- vendor download
@dataclass
class VendorResponse:
    stream: BinaryIO
    content_length: Optional[int]
    content_type: Optional[str]
    _close: Callable[[], None]

    def close(self) -> None:
        self._close()


class UrllibDownloader:
    """Opens the vendor file for streaming (standard library only, same as vendor_location_service)."""

    def __init__(self, timeout_seconds: int):
        self.timeout = timeout_seconds

    def open(self, url: str) -> VendorResponse:
        request = urllib.request.Request(url, headers={"User-Agent": "SafeFare-AlarmMedia/1.0"})
        try:
            response = urllib.request.urlopen(request, timeout=self.timeout)       # noqa: S310 (http/https URL built above)
        except urllib.error.HTTPError as error:
            raise VendorError(f"vendor server answered HTTP {error.code}", status=error.code) from None
        except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, OSError) as error:
            raise VendorError(f"vendor server not reachable / timed out: {error}") from None
        length = response.headers.get("Content-Length")
        return VendorResponse(
            stream=response,
            content_length=int(length) if length and length.isdigit() else None,
            content_type=response.headers.get("Content-Type"),
            _close=response.close,
        )


# ----------------------------------------------------------------------------------------------- S3
class S3MediaStorage:
    """Our S3 bucket, through the existing app.services.s3_service client (same bucket, region and credentials)."""

    def __init__(self, s3_service=None):
        if s3_service is None:
            from app.services.s3_service import s3_service as shared
            s3_service = shared
        from app.config.settings import settings
        self._client = s3_service.s3_client
        self._settings = settings
        self._presign_client = None
        self.bucket = s3_service.bucket_name
        self.region = settings.AWS_REGION

    def object_size(self, key: str) -> Optional[int]:
        from botocore.exceptions import ClientError
        try:
            return int(self._client.head_object(Bucket=self.bucket, Key=key)["ContentLength"])
        except ClientError as error:
            if str(error.response.get("Error", {}).get("Code")) in ("404", "NoSuchKey", "NotFound"):
                return None
            raise

    def upload_stream(self, key: str, stream: BinaryIO, content_type: str) -> None:
        from boto3.s3.transfer import TransferConfig
        # Sequential chunks of 8 MB: a large video never needs more memory than about one chunk.
        config = TransferConfig(multipart_threshold=8 * 1024 * 1024, multipart_chunksize=8 * 1024 * 1024,
                                max_concurrency=1, use_threads=False)
        self._client.upload_fileobj(stream, self.bucket, key, ExtraArgs={"ContentType": content_type}, Config=config)

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self.bucket, Key=key)

    def url_for(self, key: str) -> str:
        return build_s3_url(self.bucket, self.region, key)

    def presigned_url(self, key: str, expires_in: int) -> str:
        """Temporary link that opens the private object in a browser / video player (no AWS login needed)."""
        if self._presign_client is None:
            # Own client so the link always uses the regional address (bucket.s3.<region>.amazonaws.com) and SigV4.
            import boto3
            from botocore.config import Config
            self._presign_client = boto3.client(
                "s3", region_name=self.region, endpoint_url=f"https://s3.{self.region}.amazonaws.com",
                aws_access_key_id=self._settings.AWS_ACCESS_KEY_ID, aws_secret_access_key=self._settings.AWS_SECRET_ACCESS_KEY,
                config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}))
        return self._presign_client.generate_presigned_url(
            "get_object", Params={"Bucket": self.bucket, "Key": key}, ExpiresIn=expires_in)


class _CountingReader:
    """Counts the bytes that went through and aborts the transfer when the backend is shutting down."""

    def __init__(self, raw: BinaryIO, stop_event: Optional[threading.Event]):
        self._raw = raw
        self._stop = stop_event
        self.bytes_read = 0

    def read(self, size: int = -1) -> bytes:
        if self._stop is not None and self._stop.is_set():
            raise MigrationAborted("backend is shutting down")
        data = self._raw.read(size) if size is not None and size >= 0 else self._raw.read()
        self.bytes_read += len(data)
        return data


# ----------------------------------------------------------------------------------------------- the service
class AlarmMediaMigrationService:
    """run_cycle() is called by the worker every few seconds. Records are copied in a small thread pool; a record that
    is being copied is never started a second time (in-memory set here + an SQL lock in the repository)."""

    def __init__(self, repo, storage, downloader, cfg: AlarmMediaConfig,
                 clock: Callable[[], float] = time.monotonic, stop_event: Optional[threading.Event] = None):
        self.repo, self.storage, self.downloader, self.cfg = repo, storage, downloader, cfg
        self.clock = clock
        self.stop_event = stop_event or threading.Event()
        self.retries = RetryTracker(cfg)
        self._executor = ThreadPoolExecutor(max_workers=cfg.max_parallel, thread_name_prefix="alarm-media")
        self._lock = threading.Lock()
        self._in_flight: Set[int] = set()
        self._cursor = 0            # id of the last record looked at; the scan continues after it (see run_cycle)

    # ------------------------------------------------------------------ one cycle
    def run_cycle(self) -> int:
        """Start copying new / due records. Returns how many were started."""
        if self.stop_event.is_set():
            return 0
        with self._lock:
            capacity = min(self.cfg.max_parallel - len(self._in_flight), self.cfg.batch_size)
        if capacity <= 0:
            return 0

        rows = self.repo.fetch_pending(self._cursor, self.cfg.scan_limit)
        now = self.clock()
        picked: List[Dict[str, Any]] = []
        stopped_early = False
        for row in rows:
            self._cursor = row["id"]
            with self._lock:
                busy = row["id"] in self._in_flight
            if busy or self.retries.blocked(row["id"], now):
                continue
            picked.append(row)
            if len(picked) >= capacity:
                stopped_early = True
                break
        # Everything after the cursor was looked at -> start again from the beginning next cycle, so records that
        # failed earlier come back once their delay is over (and delayed records never hide the ones behind them).
        if not stopped_early and len(rows) < self.cfg.scan_limit:
            self._cursor = 0

        for row in picked:
            with self._lock:
                self._in_flight.add(row["id"])
            future = self._executor.submit(self._process_safely, row)
            future.add_done_callback(lambda _f, rid=row["id"]: self._finished(rid))
        return len(picked)

    def in_flight_count(self) -> int:
        with self._lock:
            return len(self._in_flight)

    def _finished(self, record_id: int) -> None:
        with self._lock:
            self._in_flight.discard(record_id)

    def wait_idle(self, timeout: float = 30.0) -> bool:
        """Block until nothing is being copied (used by tests and by shutdown)."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._lock:
                if not self._in_flight:
                    return True
            time.sleep(0.005)
        return False

    def shutdown(self, timeout: float = 30.0) -> None:
        """Stop starting new records, abort the running transfers (their records stay NULL) and stop the pool."""
        self.stop_event.set()
        self.wait_idle(timeout)
        self._executor.shutdown(wait=False, cancel_futures=True)

    # ------------------------------------------------------------------ one record
    def _process_safely(self, row: Dict[str, Any]) -> bool:
        record_id = row["id"]
        try:
            self.process_record(row)
            self.retries.success(record_id)
            return True
        except MigrationAborted:
            logger.info("alarm_media id=%s: stopped because the backend is shutting down; will retry after the next start.", record_id)
        except DuplicateMediaError as error:
            delay = self.retries.failure(record_id, self.clock(), park=True)
            logger.warning("alarm_media id=%s NOT saved: its S3 file is already stored for alarm_media id=%s "
                           "(unique index uq_alarm_media_s3). s3_key stays NULL; checked again in %s hours.",
                           record_id, error.owner_id, round(delay / 3600, 1))
        except InvalidMediaRecord as error:
            delay = self.retries.failure(record_id, self.clock(), permanent=True)
            logger.error("alarm_media id=%s FAILED (invalid record): %s | s3_key stays NULL, next check in %ss", record_id, error, int(delay))
        except VendorError as error:
            delay = self.retries.failure(record_id, self.clock())
            logger.warning("alarm_media id=%s FAILED (vendor download): %s | s3_key stays NULL, retry in %ss", record_id, error, int(delay))
        except Exception as error:                                   # S3 upload, database update, anything unexpected
            delay = self.retries.failure(record_id, self.clock())
            logger.exception("alarm_media id=%s FAILED (%s) | s3_key stays NULL, retry in %ss", record_id, error, int(delay))
        return False

    def process_record(self, row: Dict[str, Any]) -> None:
        """Copy one record. Raises on every failure (the caller logs it and schedules the retry)."""
        record_id = row["id"]
        vendor_url = build_vendor_url(self.cfg.vendor_base_url, row.get("vendor_url"))
        key = build_s3_key(self.cfg.s3_prefix, row.get("alarm_time"), row.get("media_type"), row.get("vendor_url"))

        claim = self.repo.claim(record_id)
        if claim is None:
            logger.info("alarm_media id=%s skipped: already being processed elsewhere or already migrated.", record_id)
            return
        with claim:
            response = self.downloader.open(vendor_url)
            try:
                size = self._copy_to_s3(record_id, key, response)
            finally:
                response.close()
            s3_url = self.storage.url_for(key)
            if claim.mark_done(s3_url):
                logger.info("alarm_media id=%s migrated | %s bytes | %s", record_id, size, s3_url)
            else:
                logger.info("alarm_media id=%s already had an s3_key; left unchanged.", record_id)

    def _copy_to_s3(self, record_id: int, key: str, response: VendorResponse) -> int:
        expected = response.content_length
        if expected is not None and self.storage.object_size(key) == expected and expected > 0:
            logger.info("alarm_media id=%s: %s is already in S3 with the same size; upload skipped.", record_id, key)
            return expected

        reader = _CountingReader(response.stream, self.stop_event)
        content_type = guess_content_type(key.rsplit("/", 1)[-1], response.content_type)
        self.storage.upload_stream(key, reader, content_type)
        if reader.bytes_read == 0 or (expected is not None and reader.bytes_read != expected):
            try:
                self.storage.delete(key)                      # never leave a half / empty copy behind
            except Exception:
                logger.warning("alarm_media id=%s: could not delete the incomplete S3 object %s", record_id, key)
            raise VendorError(f"incomplete download: got {reader.bytes_read} bytes, expected {expected}")
        return reader.bytes_read