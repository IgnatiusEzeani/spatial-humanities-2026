# Project resources v2.0

Built 2026-09-16 by `build_resources.py` from `/home/claude/gaz2`.

| layer | panel label | role | match | entries | generated | licence |
|---|---|---|---|---|---|---|
| ambiguous_cities | TOPONYM | disambiguation_warning | case_sensitive | 1015 | 0 | project |
| holocaust_camps | TOPONYM | domain_entity | case_sensitive | 1094 | 0 | project |
| geonouns | GEONOUN | feature_type | case_insensitive | 2232 | 1984 | project |
| family_terms | - | relation_cue | case_insensitive | 46 | 27 | project |
| non_verbals | - | transcription_artefact | case_sensitive | 186 | 0 | project |

## Notes

* `gazetteer_hybrid.json` is the flat map the panel's hybrid voter consumes. It contains ONLY layers with a panel label.
* `gazetteer_hybrid_curated_only.json` excludes machine-generated inflected forms, so their contribution can be measured.
* Inflected forms exist because of the road/roads failure: one missing form removes the geography of a sentence.
* Ambiguous cities are a warning layer. A hit should withhold a coordinate, not assign one.
* No victim, survivor or personal data appears in any layer.
