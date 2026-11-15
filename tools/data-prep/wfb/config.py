"""Mission configuration. Every step reads dates and paths from here; nothing is hard-coded to a task count."""

import contextlib
import fcntl
import os
from datetime import date
from pathlib import Path

TASK_WINDOW_START = date(2026, 7, 1)
TASK_WINDOW_END = date(2026, 11, 14)
FALLBACK_WINDOW_START = date(2026, 1, 1)
HISTORY_START = date(2016, 1, 1)
AGENT_TIMEOUT_SECONDS = 3600

WORKDIR = Path(__file__).resolve().parent.parent      # tools/data-prep: private working data (git-ignored)
REPO = WORKDIR.parents[1]
DATASET = REPO / "dataset"                            # dataset/tasks (published) + dataset/meta (private answer keys)
RAW = WORKDIR / "raw"
REPORTS = WORKDIR / "reports"
MANIFEST = WORKDIR / "provenance.jsonl"  # append-only provenance log, one row per stored raw file

SEC = "https://www.sec.gov"
SEC_DATA = "https://data.sec.gov"

# SEC fair-access: keep total sec.gov request rate under 10/s. Firecrawl scrapes take >=1s each,
# so capping concurrent Firecrawl jobs at 8 keeps the rate below that (observed ~1-3 req/s).
FC_MAX_CONCURRENCY = 20  # per process; up to 5 family processes share Firecrawl's 100-job limit
# Hard ceiling on sec.gov request STARTS per second across ALL processes (SEC fair access: < 10/s total).
# Enforced by a file-locked gate in fc._rate_gate shared by every process on this machine.
SEC_MAX_RPS = 8
FC_BATCH_SIZE = 150
# Hard stop on Firecrawl spend for this pilot (credits). Checked before every batch.
FC_CREDIT_CAP = 100_000

TEN_D_FORMS = ("10-D", "10-D/A")


def window_tag(filed: date) -> str:
    if TASK_WINDOW_START <= filed <= TASK_WINDOW_END:
        return "recent"
    if filed >= FALLBACK_WINDOW_START:
        return "fallback"
    return "historical"


# ---- Pilot scope (user decisions, 2026-11-14; logged as deviations in the dataset card) ----
# Firecrawl is the retrieval engine for every SEC download. Its AI (JSON) extraction is OFF: answer keys and deal
# parameters are read deterministically from report cells / prospectus text and certified by accounting checks,
# continuity and the frozen reference's exact recomputation. Candidates already extracted are kept as a logged
# cross-check only (plan Steps 4 and 5.1 deviation).
FIRECRAWL_AI_EXTRACTION = False
FAMILY_HISTORY_START = date(2024, 11, 1)   # reports used per family: last ~2 years (plan: HISTORY_START)
CATEGORIES = ("C1", "C2")                  # C3, C4, C5 dropped (user decisions)
CATEGORY_TARGETS = {"C1": 15, "C2": 5}     # per family (user decision); C2 shortfall goes to C1
C1_FALLBACK_IF_SHORT = True               # deviation (user decision): a family whose recent pool cannot fill C1 tops up from fallback
PILOT_FAMILIES = ["carmax", "worldomni", "deere", "nissanlease", "navient"]
TASKS_PER_FAMILY = 20
MAX_TASKS_PER_FAMILY_PER_CATEGORY = 15     # plan: 3
RESERVE_FRACTION = 0.25                    # build 20-30% extra test-split tasks as reserves


@contextlib.contextmanager
def shared_lock(name: str = "tables"):
    """Exclusive inter-process lock for read-merge-write of shared tables (several family agents run at once)."""
    with open(WORKDIR / f".{name}.lock", "a+") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def write_atomic(df, path: Path) -> None:
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    df.to_parquet(tmp, index=False)
    os.replace(tmp, path)


def merge_rows(path: Path, df, key: str, values) -> "object":
    """Replace the rows of `path` whose `key` is in `values` with `df` (under the shared lock); returns the full table."""
    import pandas as pd
    with shared_lock():
        if path.exists():
            old = pd.read_parquet(path)
            df = pd.concat([old[~old[key].isin(set(values))], df], ignore_index=True)
        write_atomic(df, path)
    return df


def update_report(name: str, family_id: str, section: str, title: str) -> None:
    """Replace this family's section of reports/<name> under the shared lock."""
    p = REPORTS / name
    with shared_lock("reports"):
        prev = p.read_text() if p.exists() else f"{title}\n"
        marker = f"\n## {family_id}\n"
        if marker in prev:
            head, _, rest = prev.partition(marker)
            nxt = rest.find("\n## ")
            prev = head + (rest[nxt:] if nxt >= 0 else "")
        p.write_text(prev.rstrip() + "\n\n" + section.strip() + "\n")
