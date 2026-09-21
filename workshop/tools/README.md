# Maintainer tools

Not needed to take the workshop. These keep the notebooks runnable and their
outputs current.

| Script | Purpose |
|---|---|
| `execute_notebooks.py` | Runs the self-study notebooks and saves them with outputs. Run from the repository root. |
| `make_workshop_cache.py` | Rebuilds `data/panel_cache.json` from an evaluation run, so the live notebook can show real system outputs without calling any model. |

```bash
python3 workshop/tools/execute_notebooks.py --dir workshop/full_day
python3 workshop/tools/make_workshop_cache.py \
  --panel panel/panel_panel_v1_openrouter.jsonl \
  --results panel/results_snapshot_v2.json \
  --passages workshop/data/workshop_passages.json \
  --out workshop/data/panel_cache.json
```

Clear the live notebook's outputs before a session, so participants open a clean
file. The self-study notebooks should keep theirs.
