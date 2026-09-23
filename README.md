# Spatial Humanities 2026

[![Open the workshop in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/IgnatiusEzeani/spatial-humanities-2026/blob/main/workshop/SH2026_workshop.ipynb)
[![Notebook checks](https://github.com/IgnatiusEzeani/spatial-humanities-2026/actions/workflows/sh2026-colab-smoke.yml/badge.svg)](https://github.com/IgnatiusEzeani/spatial-humanities-2026/actions/workflows/sh2026-colab-smoke.yml)

Materials for **AI and NLP for Spatial Humanities**, a three-hour hands-on
workshop at Spatial Humanities 2026, University of Minho, Braga,
23 September 2026.

## Start here

Open the workshop using the Colab badge above, then run the first cell.

You need only a browser. The default workshop path requires **no API key, GPU,
paid account, or prior Python experience**. It uses openly shareable historical
passages and cached model outputs.

The workshop covers:

- manual annotation of spatial language;
- rules, gazetteers, and contextual named-entity recognition;
- comparison and adjudication across methods;
- evidence-grounded journey and affect extraction;
- mapping, uncertainty, and responsible spatial AI.

See the [workshop guide](workshop/README.md) for the timetable, data sources,
local setup, and ten extended self-study notebooks.

## Other resources

- [Interactive demo](demo/README.md)
- [Benchmark documentation and results](benchmarks/README.md)
- [Research protocols and evidence](docs/)
- [Reproducible evaluation panel](panel/README.md)
- [Reusable `spatio-textual` library](https://github.com/SpaceTimeNarratives/spatio-textual)

## Run locally

```bash
git clone https://github.com/IgnatiusEzeani/spatial-humanities-2026.git
cd spatial-humanities-2026
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-workshop.txt
jupyter lab workshop/SH2026_workshop.ipynb
```

## Data and responsible use

The participant materials do not redistribute controlled-access testimony.
Oral-history examples are synthetic, and included Corpus of Lake District
Writing passages carry source information. Review the
[data notes](workshop/data/README.md) before reusing or extending the materials.

## Licensing and reuse

This repository contains original, co-authored and third-party material under
different terms. See [the licensing and reuse notice](LICENSING.md) before
redistributing code, data, annotations or teaching materials.

## Acknowledgements

This work builds on the ESRC-funded Spatial Narratives project
(ES/W003473/1, 2022–2025; PI Ian Gregory) and the
[Corpus of Lake District Writing](https://github.com/UCREL/LakeDistrictCorpus).
The workshop was developed by Ignatius Ezeani, Paul Rayson, and Ian Gregory at
UCREL, Lancaster University.
