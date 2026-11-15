# WaterfallBench data prep

Pipeline that builds `dataset/` from SEC EDGAR. Code only is tracked; everything it downloads or derives
(raw filings, certified values, splits, frozen reference waterfalls in `refs/`, `build/`, `reserves/`) stays local,
and answer keys are written to the git-ignored `dataset/meta/`.

```bash
uv sync
uv run python -m wfb.step1_enumerate                    # every 10-D / 10-D/A from EDGAR indexes
uv run python -m wfb.step2_discover --only "<trust name prefix>,..."   # deals, cover pages, governing documents
uv run python -c "from wfb import step3_retrieve as s; s.run(families=['<family key>'])"   # 2 years of filings
uv run python -m wfb.step4_extract --family <module> --no-extract       # report formats + label maps
uv run python -m wfb.step5_certify --family <module>    # deterministic certification
uv run python -c "from wfb import params; params.run('<module>')"       # deal parameters from the final prospectus
uv run python -m wfb.step7_refs split|dev|freeze|test --family <module> # splits, reference, freeze, single test run
uv run python -m wfb.step8_select --family <module> --mode final        # task selection
uv run python -m wfb.step9_packets --family <module>    # packets, output removal, leakage tests, baselines
uv run python -m wfb.step9_packets --finalize           # dataset/tasks + dataset/meta
uv run python -m wfb.step12_card                        # DATASET_CARD.md
```

Families are modules in `wfb/families/` (scope, certification checks, parameter anchors, stress signals);
`wfb/config.py` holds the windows and pilot scope. All sec.gov requests go through Firecrawl with a shared
8-requests-per-second gate across processes.
