#!/usr/bin/env python3
"""
execute_notebooks.py
--------------------
Run the self-study notebooks and save them WITH their outputs.

    python3 workshop/execute_notebooks.py --dir workshop/full_day
    python3 workshop/execute_notebooks.py --dir workshop/full_day --only 01 04

Why this matters more than it sounds
------------------------------------
Five of the ten notebooks are now self-study material, handed over at the end of
the workshop. A notebook with no outputs gives a lone reader no way to tell
whether their result is right: they run a cell, see something, and have nothing
to compare it against. That is the difference between a resource and a folder of
code.

It also proves the notebooks still run, which nothing currently does.

Notes
-----
* Needs `pip install nbclient nbformat`.
* Cells that call an API or need a key will fail. That is expected and reported;
  use --allow-errors to keep going and save what did run.
* Run this from the REPO ROOT so relative paths behave as they do for a reader.
* Execution order matters: 00 first, since later notebooks assume its setup has
  been run at least once in the environment.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, required=True)
    ap.add_argument("--only", nargs="*", default=None,
                    help="prefixes to run, e.g. --only 01 04 09")
    ap.add_argument("--timeout", type=int, default=900,
                    help="seconds per cell")
    ap.add_argument("--allow-errors", action="store_true",
                    help="keep going past a failing cell and save what ran")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    try:
        import nbformat
        from nbclient import NotebookClient
        from nbclient.exceptions import CellExecutionError
    except ImportError:
        print("pip install nbclient nbformat")
        return 1

    files = sorted(a.dir.glob("*.ipynb"))
    if a.only:
        files = [f for f in files if any(f.name.startswith(p) for p in a.only)]
    if not files:
        print(f"nothing to run in {a.dir}")
        return 1

    print(f"{'notebook':44s} {'cells':>6s} {'time':>8s}  result")
    failed = []
    for f in files:
        nb = nbformat.read(f, as_version=4)
        n_code = sum(1 for c in nb.cells if c.cell_type == "code")
        if a.dry_run:
            print(f"{f.name:44s} {n_code:6d} {'':>8s}  (dry run)")
            continue

        t0 = time.time()
        client = NotebookClient(
            nb, timeout=a.timeout, kernel_name="python3",
            resources={"metadata": {"path": str(Path.cwd())}},
            allow_errors=a.allow_errors,
        )
        note = "ok"
        try:
            client.execute()
        except CellExecutionError as exc:
            note = f"FAILED: {str(exc).splitlines()[-1][:60]}"
            failed.append(f.name)
        except Exception as exc:                                  # noqa: BLE001
            note = f"ERROR: {type(exc).__name__}: {str(exc)[:50]}"
            failed.append(f.name)

        # save whatever ran: a partially-executed notebook is still more use to
        # a lone reader than an empty one, as long as the failure is visible
        nbformat.write(nb, f)
        print(f"{f.name:44s} {n_code:6d} {time.time() - t0:7.1f}s  {note}")

    if a.dry_run:
        print("\n--dry-run: nothing executed or written.")
        return 0

    print()
    if failed:
        print(f"{len(failed)} notebook(s) had failures: {', '.join(failed)}")
        print("Open each one and look at the failing cell. If it needs an API "
              "key or a\nnetwork call, that cell should have a cached fallback "
              "rather than a key.")
    else:
        print("All notebooks executed cleanly.")
    print("\nNow check the outputs are worth shipping, then commit:")
    print(f"  git add {a.dir} && git commit -m 'Execute notebooks, commit outputs'")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
