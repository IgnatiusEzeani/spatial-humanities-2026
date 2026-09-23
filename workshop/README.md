# AI and NLP for Spatial Humanities

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/IgnatiusEzeani/spatial-humanities-2026/blob/main/workshop/SH2026_workshop.ipynb)

A three-hour, hands-on workshop on recognising, representing and evaluating
spatial language in historical and narrative text.

**Spatial Humanities 2026** · University of Minho, Braga · Wednesday 23 September 2026, 09:30–12:30
Ignatius Ezeani, Paul Rayson, Ian Gregory · UCREL, Lancaster University

---

## Start here

Open **[`SH2026_workshop.ipynb`](https://colab.research.google.com/github/IgnatiusEzeani/spatial-humanities-2026/blob/main/workshop/SH2026_workshop.ipynb)** in Google Colab and run the first cell.

You need a browser. No API key, no GPU, no paid account and no prior Python are
required. Setup takes about a minute and is the only step that touches the network.

## The session

| Time | Block | The question it answers |
|---|---|---|
| 09:30 | Setup and framing | What does a place-name list keep, and what does it discard? |
| 09:45 | Annotate it yourself | Where exactly does a spatial expression start and stop? |
| 10:20 | Rules and gazetteers | What can a transparent method see, and why does it fail when it does? |
| 10:55 | *Break* | |
| 11:10 | Six systems, one passage | Where do methods disagree, and what does the difference cost? |
| 11:45 | Evidence-first extraction | How do you make a model show its evidence? |
| 12:15 | From text to map | What should, and should not, become a point on a map? |

Every passage comes from the **Corpus of Lake District Writing**, 1622–1900, and is
compared against its human-annotated gold standard.

## After the session

Ten longer notebooks cover each topic in more depth. GitHub Actions executes
all ten in a clean, CPU-only environment without API keys, so their default
paths are continuously checked. Open them in Colab and run the cells to
generate the outputs. See **[`full_day/`](full_day/README.md)**.

## Running locally

```bash
git clone https://github.com/IgnatiusEzeani/spatial-humanities-2026.git
cd spatial-humanities-2026
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-workshop.txt
jupyter lab workshop/SH2026_workshop.ipynb
```

## Data and sources

- **Corpus of Lake District Writing (CLDW)**: passages and the `<cdplace>` gold
  standard, from [UCREL/LakeDistrictCorpus](https://github.com/UCREL/LakeDistrictCorpus).
  The six workshop passages and their gold annotations are included in
  `data/workshop_passages.json` with full source citations.
- **Oral-history examples** are synthetic, written for teaching. No testimony
  from a controlled-access archive appears in this repository.
- **System outputs** shown in the session are real, cached from the evaluation
  described in [`panel/`](../panel/README.md), so no model is called live.

## Software

The workshop uses [`spatio-textual`](https://github.com/SpaceTimeNarratives/spatio-textual),
pinned to v0.4.1 in `requirements-workshop.txt`.

## Acknowledgements

This work comes out of **The Spatial Narratives Project**, funded by the ESRC
(ES/W003473/1, 2022–2025; PI Ian Gregory).
Project site: [spacetimenarratives.github.io](https://spacetimenarratives.github.io/).
Compute was provided by the UCREL Hex team, Lancaster University.
