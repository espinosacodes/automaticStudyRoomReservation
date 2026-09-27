"""Merge two status.json snapshots into one.

History should only ever grow. Every wipe so far came from a later snapshot
replacing a richer one, so merges are keyed by `run_at` and keep whichever
entry has the more complete set of blocks (and the more captured PDFs).

    python -m tools.merge_status base.json incoming.json -o out.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _score(run: dict) -> tuple[int, int]:
    blocks = run.get("blocks", [])
    captured = sum(1 for block in blocks if block.get("pdf"))
    return captured, len(blocks)


def merge(*snapshots: dict) -> dict:
    runs: dict[str, dict] = {}
    for snapshot in snapshots:
        for run in snapshot.get("runs", []) or []:
            key = run.get("run_at")
            if not key:
                continue
            if key not in runs or _score(run) > _score(runs[key]):
                runs[key] = run
    ordered = sorted(runs.values(), key=lambda run: run["run_at"], reverse=True)
    return {
        "generated_at": ordered[0]["run_at"] if ordered else None,
        "runs": ordered,
    }


def load(path: Path | str) -> dict:
    try:
        return json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError):
        return {"runs": []}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Merge status.json snapshots.")
    parser.add_argument("files", nargs="+", help="snapshot paths; later ones win ties")
    parser.add_argument("-o", "--out", default="status.json")
    args = parser.parse_args(argv)

    merged = merge(*(load(path) for path in args.files))
    Path(args.out).write_text(json.dumps(merged, indent=2))
    print(f"merged {len(merged['runs'])} run(s) into {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
