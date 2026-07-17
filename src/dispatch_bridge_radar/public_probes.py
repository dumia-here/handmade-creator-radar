from __future__ import annotations

import html
import gzip
import io
import json
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any, Callable, Iterable

from .contract import ContentCandidate, Platform, ProbeRequest, RadarTask
from .probes import ProbeBatch


BILIBILI_HOSTS = ("bilibili.com", "b23.tv")
YOUTUBE_HOSTS = ("youtube.com", "youtu.be")


@dataclass(frozen=True)
class LiveContentCandidate(ContentCandidate):
    creator_id: str | None = None
    creator_name: str | None = None
    source_url: str | None = None
    published_at: str | None = None
    public_metrics: tuple[tuple[str, int], ...] = ()
    fetched_at: str = ""
    missing_fields: tuple[str, ...] = ()

    @property
    def metrics(self) -> dict[str, int]:
        return dict(self.public_metrics)


@dataclass(frozen=True)
class ProbeDiagnostics:
    platform: Platform
    search_pages_read: int
    search_candidates_found: int
    detail_pages_read: int
    parsed_candidates: int
    errors: tuple[str, ...]


class PublicFetchError(RuntimeError):
    def __init__(self, category: str, *, status: int | None = None):
        super().__init__(category)
        self.category = category
        self.status = status


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, validator: Callable[[str], None]):
        super().__init__()
        self._validator = validator

    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> Any:
        self._validator(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class SafePublicHttpClient:
    """Small standard-library client with HTTPS, host, redirect, retry and size guards."""

    def __init__(
        self,
        allowed_hosts: Iterable[str],
        *,
        timeout: float = 8.0,
        retries: int = 1,
        request_interval: float = 0.35,
        max_body_bytes: int = 5_000_000,
        opener: Any = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.allowed_hosts = tuple(host.casefold() for host in allowed_hosts)
        self.timeout = timeout
        self.retries = max(0, retries)
        self.request_interval = max(0.0, request_interval)
        self.max_body_bytes = max_body_bytes
        self._sleeper = sleeper
        self._opener = opener or urllib.request.build_opener(_SafeRedirectHandler(self.validate_url))

    def validate_url(self, url: str) -> None:
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme.casefold() != "https":
            raise ValueError("public probe only allows https")
        host = (parsed.hostname or "").casefold()
        if not any(host == allowed or host.endswith("." + allowed) for allowed in self.allowed_hosts):
            raise ValueError("public probe target host is not allowlisted")

    def fetch_text(self, url: str) -> tuple[str, str, int, str]:
        self.validate_url(url)
        last_error: PublicFetchError | None = None
        for attempt in range(self.retries + 1):
            if attempt:
                self._sleeper(self.request_interval)
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AdamStudioRadar/0.1",
                    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.5",
                    "Accept-Language": "zh-CN,zh;q=0.8,en;q=0.6",
                },
                method="GET",
            )
            try:
                with self._opener.open(request, timeout=self.timeout) as response:
                    final_url = response.geturl()
                    self.validate_url(final_url)
                    compressed = response.read(self.max_body_bytes + 1)
                    if len(compressed) > self.max_body_bytes:
                        raise PublicFetchError("response_too_large", status=response.getcode())
                    body = _decode_body(
                        compressed,
                        response.headers.get("Content-Encoding", ""),
                        self.max_body_bytes,
                    )
                    charset = response.headers.get_content_charset() or "utf-8"
                    return body.decode(charset, errors="replace"), final_url, response.getcode(), _now()
            except urllib.error.HTTPError as exc:
                last_error = PublicFetchError("http", status=exc.code)
                if exc.code not in {429, 500, 502, 503, 504}:
                    break
            except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
                reason = getattr(exc, "reason", exc)
                category = "timeout" if isinstance(reason, (TimeoutError, socket.timeout)) else "network"
                last_error = PublicFetchError(category)
            except PublicFetchError as exc:
                last_error = exc
                break
        raise last_error or PublicFetchError("unknown")


class _MetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.canonical: str | None = None
        self.json_ld: list[str] = []
        self._in_json_ld = False
        self._script_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.casefold(): value for key, value in attrs if value is not None}
        if tag.casefold() == "meta":
            key = (values.get("property") or values.get("name") or "").casefold()
            if key and "content" in values:
                self.meta.setdefault(key, values["content"])
        elif tag.casefold() == "link" and values.get("rel", "").casefold() == "canonical":
            self.canonical = values.get("href")
        elif tag.casefold() == "script" and values.get("type", "").casefold() == "application/ld+json":
            self._in_json_ld = True
            self._script_parts = []

    def handle_data(self, data: str) -> None:
        if self._in_json_ld:
            self._script_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() == "script" and self._in_json_ld:
            self.json_ld.append("".join(self._script_parts))
            self._in_json_ld = False
            self._script_parts = []


def parse_public_video_page(
    page: str,
    *,
    platform: Platform,
    candidate_id: str,
    fetched_at: str,
    page_url: str,
) -> LiveContentCandidate:
    parser = _MetadataParser()
    parser.feed(page)
    objects: list[dict[str, Any]] = []
    for raw in parser.json_ld:
        try:
            decoded = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        objects.extend(_json_objects(decoded))
    video = next((item for item in objects if "videoobject" in str(item.get("@type", "")).casefold()), {})

    title = _first_string(video.get("name"), parser.meta.get("og:title"), parser.meta.get("twitter:title"))
    if not title:
        raise ValueError("public page has no allowed title metadata")
    description = _first_string(
        video.get("description"), parser.meta.get("og:description"), parser.meta.get("description")
    ) or ""
    author = video.get("author")
    author_name: str | None = None
    author_url: str | None = None
    if isinstance(author, dict):
        author_name = _first_string(author.get("name"))
        author_url = _first_string(author.get("url"))
    elif isinstance(author, list):
        first = next((item for item in author if isinstance(item, dict)), None)
        if first:
            author_name = _first_string(first.get("name"))
            author_url = _first_string(first.get("url"))
    author_name = author_name or _first_string(parser.meta.get("author"), parser.meta.get("og:video:actor"))
    published_at = _first_string(video.get("uploadDate"), video.get("datePublished"))
    source_url = _first_string(video.get("url"), parser.meta.get("og:url"), parser.canonical, page_url) or page_url
    metrics = _interaction_metrics(video.get("interactionStatistic"))
    creator_id = _creator_id(author_url)
    missing: list[str] = []
    for name, value in (
        ("creator_id", creator_id),
        ("creator_name", author_name),
        ("description", description),
        ("published_at", published_at),
    ):
        if not value:
            missing.append(name)
    for metric in ("views", "likes", "comments"):
        if metric not in metrics:
            missing.append(metric)
    return LiveContentCandidate(
        candidate_id=candidate_id,
        platform=platform,
        title=html.unescape(title).strip(),
        description=html.unescape(description).strip(),
        creator=author_name,
        url=source_url,
        source_kind="live_public",
        creator_id=creator_id,
        creator_name=author_name,
        source_url=source_url,
        published_at=published_at,
        public_metrics=tuple(sorted(metrics.items())),
        fetched_at=fetched_at,
        missing_fields=tuple(missing),
    )


def discover_bilibili_urls(page: str, limit: int = 20) -> tuple[str, ...]:
    ids = re.findall(r"(?:www\\.)?bilibili\\.com/video/(BV[0-9A-Za-z]{10})", page)
    ids.extend(re.findall(r'"bvid"\s*:\s*"(BV[0-9A-Za-z]{10})"', page))
    return tuple(f"https://www.bilibili.com/video/{item}" for item in _unique(ids, limit))


def discover_youtube_urls(page: str, limit: int = 20) -> tuple[str, ...]:
    ids = re.findall(r'"videoId"\s*:\s*"([A-Za-z0-9_-]{11})"', page)
    return tuple(f"https://www.youtube.com/watch?v={item}" for item in _unique(ids, limit))


class _BasePublicProbe:
    platform: Platform
    search_base: str

    def __init__(
        self,
        client: SafePublicHttpClient,
        *,
        smoke_urls: Iterable[str] = (),
        max_search_candidates: int = 20,
    ) -> None:
        self.client = client
        self.smoke_urls = tuple(smoke_urls)
        self.max_search_candidates = min(20, max(1, max_search_candidates))
        self.last_diagnostics = ProbeDiagnostics(self.platform, 0, 0, 0, 0, ())

    def scan(self, request: ProbeRequest, task: RadarTask) -> ProbeBatch:
        if request.platform != self.platform:
            raise ValueError("probe request platform does not match public probe")
        errors: list[str] = []
        discovered: list[str] = []
        search_reads = 0
        for query in request.queries:
            if len(discovered) >= self.max_search_candidates:
                break
            url = self.search_base + urllib.parse.quote_plus(query)
            try:
                page, _, _, _ = self.client.fetch_text(url)
                search_reads += 1
                discovered.extend(self._discover(page, self.max_search_candidates - len(discovered)))
            except PublicFetchError as exc:
                errors.append(_safe_error("search", exc))
        if not discovered:
            discovered.extend(self.smoke_urls[: self.max_search_candidates])
        discovered = list(_unique(discovered, self.max_search_candidates))

        candidates: list[LiveContentCandidate] = []
        detail_reads = 0
        for url in discovered:
            try:
                page, final_url, _, fetched_at = self.client.fetch_text(url)
                detail_reads += 1
                candidates.append(
                    parse_public_video_page(
                        page,
                        platform=self.platform,
                        candidate_id=self._candidate_id(final_url),
                        fetched_at=fetched_at,
                        page_url=final_url,
                    )
                )
            except PublicFetchError as exc:
                errors.append(_safe_error("detail", exc))
            except ValueError as exc:
                errors.append(f"parse:{type(exc).__name__}")
        self.last_diagnostics = ProbeDiagnostics(
            platform=self.platform,
            search_pages_read=search_reads,
            search_candidates_found=len(discovered),
            detail_pages_read=detail_reads,
            parsed_candidates=len(candidates),
            errors=tuple(errors),
        )
        return ProbeBatch(self.platform, "live_public", tuple(candidates))

    def _discover(self, page: str, limit: int) -> tuple[str, ...]:
        raise NotImplementedError

    def _candidate_id(self, url: str) -> str:
        raise NotImplementedError


class BilibiliPublicProbe(_BasePublicProbe):
    platform = Platform.BILIBILI
    search_base = "https://search.bilibili.com/all?keyword="

    def _discover(self, page: str, limit: int) -> tuple[str, ...]:
        return discover_bilibili_urls(page, limit)

    def _candidate_id(self, url: str) -> str:
        match = re.search(r"/(BV[0-9A-Za-z]{10})", url)
        if not match:
            raise ValueError("Bilibili URL has no BV id")
        return match.group(1)


class YouTubePublicProbe(_BasePublicProbe):
    platform = Platform.YOUTUBE
    search_base = "https://www.youtube.com/results?search_query="

    def _discover(self, page: str, limit: int) -> tuple[str, ...]:
        return discover_youtube_urls(page, limit)

    def _candidate_id(self, url: str) -> str:
        parsed = urllib.parse.urlsplit(url)
        query = urllib.parse.parse_qs(parsed.query)
        if query.get("v"):
            return query["v"][0]
        if parsed.hostname and parsed.hostname.casefold().endswith("youtu.be"):
            return parsed.path.strip("/").split("/")[0]
        raise ValueError("YouTube URL has no video id")


def _json_objects(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        output = [value]
        graph = value.get("@graph")
        if isinstance(graph, list):
            output.extend(item for item in graph if isinstance(item, dict))
        return output
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _interaction_metrics(value: Any) -> dict[str, int]:
    items = value if isinstance(value, list) else [value]
    metrics: dict[str, int] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        interaction = item.get("interactionType", {})
        kind = interaction.get("@type") if isinstance(interaction, dict) else str(interaction)
        target = {"WatchAction": "views", "LikeAction": "likes", "CommentAction": "comments"}.get(str(kind))
        count = item.get("userInteractionCount")
        if target and isinstance(count, (int, float, str)):
            try:
                metrics[target] = int(str(count).replace(",", ""))
            except ValueError:
                pass
    return metrics


def _creator_id(author_url: str | None) -> str | None:
    if not author_url:
        return None
    path = urllib.parse.urlsplit(author_url).path.strip("/")
    return path.split("/")[-1] if path else None


def _first_string(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _unique(values: Iterable[str], limit: int) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            output.append(value)
        if len(output) >= limit:
            break
    return output


def _safe_error(stage: str, error: PublicFetchError) -> str:
    suffix = f":http_{error.status}" if error.status is not None else f":{error.category}"
    return stage + suffix


def _decode_body(body: bytes, content_encoding: str, max_bytes: int) -> bytes:
    encoding = content_encoding.casefold().strip()
    if not encoding or encoding == "identity":
        decoded = body
    elif encoding == "gzip":
        with gzip.GzipFile(fileobj=io.BytesIO(body)) as stream:
            decoded = stream.read(max_bytes + 1)
    elif encoding == "deflate":
        decoder = zlib.decompressobj()
        decoded = decoder.decompress(body, max_bytes + 1)
    else:
        raise PublicFetchError("unsupported_content_encoding")
    if len(decoded) > max_bytes:
        raise PublicFetchError("response_too_large")
    return decoded


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
