# Maintainer tool

This directory contains the reproducible route for rebuilding the cached panel
outputs used by the main workshop notebook. Participants do not need to run it.

From the repository root:

```bash
python workshop/tools/make_workshop_cache.py \
  --panel panel/panel_panel_v1_openrouter.jsonl \
  --results panel/results_snapshot_v2.json \
  --passages workshop/data/workshop_passages.json \
  --out workshop/data/panel_cache.json
```

The builder uses committed panel outputs and does not call a model or require
an API key.
