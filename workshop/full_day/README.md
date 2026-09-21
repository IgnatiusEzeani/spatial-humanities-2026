# Self-study notebooks

Ten notebooks that extend the three-hour session. Each one runs on its own in
Colab, needs no API key or GPU, and has **its outputs committed**, so you can
compare your results against a known-good run.

Take them in order if you are new to the material; each builds on the vocabulary
of the one before. Allow 30 to 60 minutes each.

| | Notebook | What it covers |
|---|---|---|
| 00 | [Setup and orientation](https://colab.research.google.com/github/IgnatiusEzeani/spatial-humanities-2026/blob/main/workshop/full_day/00_setup_and_orientation.ipynb) | Location, locale and sense of place; your first annotation |
| 01 | [Manual annotation](https://colab.research.google.com/github/IgnatiusEzeani/spatial-humanities-2026/blob/main/workshop/full_day/01_manual_annotation.ipynb) | Annotation policy, disagreement, exact versus overlap scoring |
| 02 | [Rules and gazetteers](https://colab.research.google.com/github/IgnatiusEzeani/spatial-humanities-2026/blob/main/workshop/full_day/02_rules_and_gazetteers.ipynb) | Transparent matching and why it fails when it does |
| 03 | [Contextual NER](https://colab.research.google.com/github/IgnatiusEzeani/spatial-humanities-2026/blob/main/workshop/full_day/03_contextual_ner.ipynb) | Statistical NER, and the limit set by its label inventory |
| 04 | [Linking and ambiguity](https://colab.research.google.com/github/IgnatiusEzeani/spatial-humanities-2026/blob/main/workshop/full_day/04_linking_and_ambiguity.ipynb) | Which Cambridge? Historical polities; when not to assign a coordinate |
| 05 | [Affect and events](https://colab.research.google.com/github/IgnatiusEzeani/spatial-humanities-2026/blob/main/workshop/full_day/05_affect_and_events.ipynb) | Emotion lexicons, transformer classifiers, and what "neutral" does not mean |
| 06 | [LLM structured extraction](https://colab.research.google.com/github/IgnatiusEzeani/spatial-humanities-2026/blob/main/workshop/full_day/06_llm_structured_extraction.ipynb) | Evidence-first journey extraction, grounding, and null as a result |
| 07 | [Compare and adjudicate](https://colab.research.google.com/github/IgnatiusEzeani/spatial-humanities-2026/blob/main/workshop/full_day/07_compare_and_adjudicate.ipynb) | Disagreement between systems; review burden versus correction burden |
| 08 | [From text to map](https://colab.research.google.com/github/IgnatiusEzeani/spatial-humanities-2026/blob/main/workshop/full_day/08_from_text_to_map.ipynb) | GeoJSON with an audit trail, and what should not be mapped |
| 09 | [Responsible spatial AI](https://colab.research.google.com/github/IgnatiusEzeani/spatial-humanities-2026/blob/main/workshop/full_day/09_responsible_spatial_ai.ipynb) | Provenance, access control, and questions to ask before publishing |

## A note on notebook 06

It demonstrates model extraction using deterministic teaching clients rather than
a live model, so the behaviour it shows (a grounded quote, an invented quote, a
correctly empty field) is reproducible and inspectable. The validation machinery
is identical to what a live model would pass through.

## If something does not run

Run the first cell again once; it is safe to repeat. If it still fails, check that
you opened the notebook from this repository rather than a downloaded copy, since
the setup cell fetches the shared configuration from here.
