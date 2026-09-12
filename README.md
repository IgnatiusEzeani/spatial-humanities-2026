# Spatial Humanities 2026

Conference resources, research, teaching materials, and demonstration tools for
Spatial Humanities 2026, hosted at the University of Minho in Braga,
23–25 September 2026.

This project builds on the reusable Python library
[`IgnatiusEzeani/spatio-textual`](https://github.com/IgnatiusEzeani/spatio-textual),
which provides core capabilities for spatial annotation, NER, journey extraction,
affect analysis, and evaluation.

## What's included

- **Benchmarks**: Curated research corpora and evaluation datasets
- **Demo**: Interactive Streamlit application showcasing conference themes
- **Workshops**: Tutorial notebooks and instructional materials
- **Docs**: Research protocols, results, and keynote evidence
- **Scripts**: Experiment runners and analysis tools

## Quick start: Run the demo

From the repository root:

```bash
python -m pip install -r requirements-lite.txt
streamlit run demo/streamlit_app.py
```

The demo includes a guided public path that requires no API keys. Optional live LLM
features are available when configured with an `OPENAI_API_KEY`.

## Repository structure

```text
spatial-humanities-2026/
├── README.md
├── ROADMAP.md
├── benchmarks/        # Research corpora and datasets
├── config/            # Experiment configuration
├── demo/              # Streamlit application
├── docs/              # Research protocols and results
├── scripts/           # Experiment and analysis tools
├── tests/             # Regression tests
└── workshop/          # Tutorial notebooks and materials
```

## About the research

The Spatial Humanities 2026 project combines spatial analysis with textual interpretation
to explore how location, movement, and affect shape meaning. This conference brings
together researchers, practitioners, and students working at the intersection of
geography, humanities, and computational methods.

## Learn more

- [Project roadmap](ROADMAP.md) — planned work and milestones
- [spatio-textual library](https://github.com/IgnatiusEzeani/spatio-textual) — core Python package
