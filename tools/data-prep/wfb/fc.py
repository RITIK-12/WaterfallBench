"""Firecrawl-backed fetcher for SEC EDGAR with caching, provenance and block detection.

Every network fetch of sec.gov goes through the Firecrawl CLI (`firecrawl scrape` / `firecrawl
batch-scrape`). Raw bodies are stored gzip-compressed and never overwritten; the SHA-256 recorded in
the provenance log is of the uncompressed bytes. A cached file is never re-fetched (idempotent reruns).
"""

from __future__ import annotations

import fcntl
import gzip
import hashlib
import json
import os
import subprocess
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import config

_LOCK = threading.Lock()
_GATE = threading.Lock()
_LAST_START = [0.0]


_GATE_FILE = config.WORKDIR / ".sec_rate_gate"


def _rate_gate() -> None:
    """Space sec.gov request starts so that ALL processes together start at most config.SEC_MAX_RPS per second.
    The last start time lives in a file guarded by an exclusive flock; waiting happens while holding the lock."""
    with _GATE:
        with open(_GATE_FILE, "a+") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                fh.seek(0)
                s = fh.read().strip()
                last = float(s) if s else 0.0
                wait = last + 1.0 / config.SEC_MAX_RPS - time.time()
                if wait > 0:
                    time.sleep(wait)
                fh.seek(0)
                fh.truncate()
                fh.write(repr(time.time()))
                fh.flush()
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)
_CREDITS_FILE = config.WORKDIR / "fc_credits.json"

BLOCK_MARKERS = (
    "Request Rate Threshold Exceeded",
    "Undeclared Automated Tool",
    "Your Request Originates from an Undeclared",
)


class SecBlocked(RuntimeError):
    """SEC throttled or blocked a request. The mission says stop and report; never work around it."""


class CreditCapReached(RuntimeError):
    pass


class TooLarge(RuntimeError):
    """Firecrawl refuses bodies over its size limit (50 MiB)."""


@dataclass
class Fetched:
    url: str
    path: Path
    text: str
    cached: bool


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _credits_used() -> int:
    if _CREDITS_FILE.exists():
        return json.loads(_CREDITS_FILE.read_text())["credits"]
    return 0


def _add_credits(n: int) -> None:
    with _LOCK, config.shared_lock("credits"):
        total = _credits_used() + int(n or 0)
        _CREDITS_FILE.write_text(json.dumps({"credits": total, "updated": _now()}))


def check_budget(planned: int = 0) -> None:
    used = _credits_used()
    if used + planned > config.FC_CREDIT_CAP:
        raise CreditCapReached(f"Firecrawl credit cap {config.FC_CREDIT_CAP} would be exceeded (used {used}, planned {planned})")


def read_raw(path: Path) -> str:
    with gzip.open(path, "rb") as f:
        return f.read().decode("utf-8", errors="replace")


def _store(url: str, dest: Path, body: str, meta: dict, *, cik: str | None, accession: str | None, kind: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    data = body.encode("utf-8")
    sha = hashlib.sha256(data).hexdigest()
    tmp = dest.with_suffix(dest.suffix + ".part")
    with gzip.open(tmp, "wb", compresslevel=6) as f:
        f.write(data)
    os.replace(tmp, dest)
    row = {
        "url": url,
        "path": str(dest.relative_to(config.WORKDIR)),
        "kind": kind,
        "cik": cik,
        "accession": accession,
        "retrieved_at": _now(),
        "sha256": sha,
        "bytes": len(data),
        "status_code": meta.get("statusCode"),
        "content_type": meta.get("contentType"),
        "firecrawl_scrape_id": meta.get("scrapeId"),
        "firecrawl_cache_state": meta.get("cacheState"),
        "credits": meta.get("creditsUsed"),
    }
    with _LOCK, config.shared_lock("manifest"):
        with open(config.MANIFEST, "a") as f:
            f.write(json.dumps(row) + "\n")


def _validate(url: str, body: str | None, meta: dict) -> str:
    code = meta.get("statusCode")
    # sec.gov/Archives is S3-backed: a key that does not exist (e.g. no daily index on a federal holiday)
    # answers 403 with an S3 <Code>AccessDenied</Code> XML body. That is a missing file, not a fair-access block.
    if code == 403 and body and "AccessDenied" in body[:3000] and not any(m in body[:5000] for m in BLOCK_MARKERS):
        raise FileNotFoundError(f"{url} (S3 AccessDenied: object not present)")
    if code in (403, 429) or (body and any(m in body[:5000] for m in BLOCK_MARKERS)):
        raise SecBlocked(f"SEC refused {url}: status={code}")
    if code == 404:
        raise FileNotFoundError(url)
    if code != 200 or not body:
        raise RuntimeError(f"Bad fetch {url}: status={code} error={meta.get('error')} len={len(body or '')}")
    return body


def _run(cmd: list[str], timeout: int) -> None:
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        msg = (p.stderr or p.stdout)[-2000:]
        if "exceeds size limit" in msg:
            raise TooLarge(msg[:300])
        if "429" in msg or "rate limit" in msg.lower():
            raise RuntimeError(f"Firecrawl rate limited: {msg}")
        raise RuntimeError(f"firecrawl failed ({p.returncode}): {msg}")


def scrape_one(url: str, dest: Path, *, cik: str | None = None, accession: str | None = None,
               kind: str = "raw", retries: int = 3, max_age: int | None = None) -> Fetched:
    """Fetch `url` raw (exact bytes as served) via Firecrawl unless `dest` already exists."""
    if dest.exists():
        return Fetched(url, dest, read_raw(dest), True)
    check_budget(1)
    last: Exception | None = None
    for attempt in range(retries):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            out = tf.name
        try:
            _rate_gate()
            cmd = ["firecrawl", "scrape", url, "--format", "rawHtml", "--json", "-o", out]
            if max_age is not None:
                cmd += ["--max-age", str(max_age)]
            _run(cmd, timeout=600)
            d = json.loads(Path(out).read_text())
            meta = d.get("metadata", {})
            _add_credits(meta.get("creditsUsed") or 1)
            body = _validate(url, d.get("rawHtml"), meta)
            _store(url, dest, body, meta, cik=cik, accession=accession, kind=kind)
            return Fetched(url, dest, body, False)
        except (SecBlocked, FileNotFoundError, CreditCapReached, TooLarge):
            raise
        except Exception as e:  # transient Firecrawl failure: back off and retry
            last = e
            time.sleep(2 * (attempt + 1))
        finally:
            Path(out).unlink(missing_ok=True)
    raise RuntimeError(f"giving up on {url}: {last}")


def scrape_many(jobs: list[tuple[str, Path, dict]], *, kind: str = "raw", progress: bool = True,
                batch_size: int | None = None, max_age: int | None = None) -> dict[str, Exception]:
    """Fetch many (url, dest, attrs), skipping cached dests. Requests are individual Firecrawl scrapes started
    through the rate gate (<= SEC_MAX_RPS starts/second) with up to FC_MAX_CONCURRENCY in flight, so the
    sec.gov request rate is bounded regardless of response latency. Returns {url: exception} for failures;
    raises SecBlocked immediately if SEC throttles or blocks."""
    todo = [(u, d, a) for (u, d, a) in jobs if not d.exists()]
    failures: dict[str, Exception] = {}
    if not todo:
        return failures
    check_budget(len(todo))
    done = [0]
    blocked: list[Exception] = []

    def _one(item):
        u, dest, attrs = item
        if blocked:
            return
        try:
            scrape_one(u, dest, cik=attrs.get("cik"), accession=attrs.get("accession"), kind=kind, max_age=max_age)
        except SecBlocked as e:
            blocked.append(e)
        except Exception as e:
            failures[u] = e
        with _LOCK:
            done[0] += 1
            if progress and done[0] % 100 == 0:
                print(f"  fetched {done[0]}/{len(todo)} (failed={len(failures)}, credits={_credits_used()})", flush=True)

    with ThreadPoolExecutor(config.FC_MAX_CONCURRENCY) as ex:
        list(ex.map(_one, todo))
    if blocked:
        raise blocked[0]
    if progress:
        print(f"  fetched {done[0]}/{len(todo)} (failed={len(failures)}, credits={_credits_used()})", flush=True)
    return failures
