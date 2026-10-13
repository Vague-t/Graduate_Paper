# Extended CasiMedicos-Arg Dataset

This folder contains an extended version of the public [HiTZ/casimedicos-arg](https://huggingface.co/datasets/HiTZ/casimedicos-arg) dataset.

## Processing

Starting from the original dataset, we prepared the files in this folder by:

* normalizing the upstream tokenized `text` and BIO `labels` records into JSONL;
* aligning English support/attack relation files to Spanish, French, and Italian
  records through sentence-level cross-language matching;
* applying manually checked relation fixes from `extended/relations/fix_relations.json`;
* preserving skipped alignment candidates and processing reports under `extended/`;
* adding language suffixes to record IDs where needed;

## Alignment and Relation Projection

The original release provides relation annotations explicitly for English. To make the multilingual files usable for GRACE-style argument mining, we projected the English support/attack relations to Spanish, French, and Italian
records.

The projection was performed in two stages. First, an automatic alignment step matched English relation endpoints to translated records using sentence-level cross-language matching, exact matching, substring overlap, and numeric-pattern
normalization. Then, skipped or ambiguous cases were manually checked and fixed through `extended/relations/fix_relations.json`.

Before manual fixes, the automatic aligner matched most English relations across target languages:

| Target language | Automatic relation alignment coverage |
| --------------- | ------------------------------------: |
| Spanish         |                                99.57% |
| French          |                                99.49% |
| Italian         |                                99.11% |

The remaining cases mostly corresponded to translation artifacts such as acronym localization, numeric formatting changes, and syntactic restructuring. After the manual fixes, the processed relation files reached full intended coverage across
the train, dev, and test splits, after resolving duplicate or inconsistent source pairs.

## Representative Alignment Fixes

The following examples summarize typical alignment failures and the corresponding manual corrections. They are included here for transparency and to document why the manually checked relation-fix file is needed.

| Artifact type                                     | English source structure                                                           | Automated baseline error                                                                                          | Manual pipeline fix                                                                                                      |
| ------------------------------------------------- | ---------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Acronym localization<br>Case `486_45`, Italian    | **Premise:** `... an array or an NGS panel...`<br>**Claim:** `FISH`                | The translated claim appeared as `PESCE`, preventing character-level matching with the English anchor.            | **Premise:** `Tuttavia, sia l'array che l'NGS...`<br>**Claim:** `2- PESCE.`<br>**Relation:** `Attack`                    |
| Numeric formatting<br>Case `524_54`, French       | **Premise:** `the NNT is 33.3`<br>**Claim:** `33.3`                                | Decimal notation changed from `33.3` to `33,3`, causing strict string matching to fail.                           | **Premise:** `Par conséquent... NNT est de 33,3.`<br>**Claim:** `3- 33,3.`<br>**Relation:** `Support`                    |
| Syntactic restructuring<br>Case `260_99`, Spanish | **Premise:** `Pancreatic tumor...`<br>**Claim:** `Multiple endocrine neoplasia...` | A multi-hop relation chain was broken because the acronym and expansion were merged into a single Spanish clause. | **Premise:** `Tumor neuroendocrino... : MEN 1.`<br>**Claim:** `1- Una neoplasia endocrina...`<br>**Relation:** `Support` |

The complete list of manually injected or corrected relations is available in:

```text
extended/relations/fix_relations.json
```

## Dataset Statistics

The table below summarizes the structural differences between the original CasiMedicos-Arg release and the processed version included in this repository.

| Metric                         |                Original dataset |                Processed dataset |
| ------------------------------ | ------------------------------: | -------------------------------: |
| **Structural characteristics** |                                 |                                  |
| File formats                   | Mixed `.tsv`, `.json`, `.jsonl` |                 Unified `.jsonl` |
| Languages with text data       |               4: EN, ES, FR, IT |                4: EN, ES, FR, IT |
| Languages with relation files  |                      1: EN only |                4: EN, ES, FR, IT |
| **Global counts**              |                                 |                                  |
| Clinical cases                 |                             558 |                              558 |
| Claims                         |                           5,021 |                            5,021 |
| Premises                       |                           2,313 |                            2,313 |
| Support relations              |                  2,431, EN only | approximately 2,420 per language |
| Attack relations               |                  1,106, EN only | approximately 1,085 per language |

Minor reductions with respect to the English source relation totals are due to the resolution of duplicate or inconsistent relation pairs during processing.