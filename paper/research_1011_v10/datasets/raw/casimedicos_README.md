---
license: cc-by-4.0
language:
- en
- es
- fr
- it
tags:
- casimedicos
- explainability
- medical exams
- medical question answering
- multilinguality
- argument mining
- argument generation
- LLMs
- LLM
pretty_name: CasiMedicos-Arg
configs:
- config_name: en
  data_files:
  - split: train
    path:
    - en/train_en_all.csv
  - split: validation
    path:
    - en/validation_en_all.csv
  - split: test
    path:
    - en/test_en_all.csv
- config_name: es
  data_files:
  - split: train
    path:
    - es/train_es_ordered.csv
  - split: validation
    path:
    - es/validation_es_ordered.csv
  - split: test
    path:
    - es/test_es_ordered.csv
- config_name: fr
  data_files:
  - split: train
    path:
    - fr/train_fr_ordered.csv
  - split: validation
    path:
    - fr/validation_fr_ordered.csv
  - split: test
    path:
    - fr/test_fr_ordered.csv
- config_name: it
  data_files:
  - split: train
    path:
    - it/train_it_ordered.csv
  - split: validation
    path:
    - it/validation_it_ordered.csv
  - split: test
    path:
    - it/test_it_ordered.csv
task_categories:
- text-generation
- question-answering
- token-classification
size_categories:
- 1K<n<10K
---

<p align="center">
    <br>
    <img src="http://www.ixa.eus/sites/default/files/anitdote.png" style="height: 200px;">
    <br>

# CasiMedicos-Arg: A Medical Question Answering Dataset Annotated with Explanatory Argumentative Structures

[CasiMedicos-Arg](https://huggingface.co/datasets/HiTZ/casimedicos-arg) is, to the best of our knowledge, the first 
multilingual dataset for Medical Question Answering where correct and incorrect diagnoses for a clinical case are 
enriched with a natural language explanation written by doctors. 
The [casimedicos-exp](https://huggingface.co/datasets/HiTZ/casimedicos-exp) have been manually annotated with 
argument components (i.e., premise, claim) and argument relations (i.e., attack, support). 
Thus, Multilingual CasiMedicos-arg dataset consists of 558 clinical cases (English, Spanish, French, Italian) with explanations,
where we annotated 5021 claims, 2313 premises, 2431 support relations, and 1106 attack relations.

<table style="width:33%">
    <tr>
         <th>Antidote CasiMedicos-Arg splits</th>
     <tr>
         <td>train</td>
         <td>434</td>
     </tr>
     <tr>
         <td>validation</td>
         <td>63</td>
     </tr>
     <tr>
         <td>test</td>
         <td>125</td>
     </tr>
 </table>

- 📖 Paper:[CasiMedicos-Arg: A Medical Question Answering Dataset Annotated with Explanatory Argumentative Structures](https://aclanthology.org/2024.emnlp-main.1026/)
- 💻 Github Repo (Data and Code): [https://github.com/ixa-ehu/antidote-casimedicos](https://github.com/ixa-ehu/antidote-casimedicos)
- 🌐 Project Website: [https://univ-cotedazur.eu/antidote](https://univ-cotedazur.eu/antidote)
- Funding: CHIST-ERA XAI 2019 call. Antidote (PCI2020-120717-2) funded by MCIN/AEI /10.13039/501100011033 and by European Union NextGenerationEU/PRTR


## Example of Document in Antidote CasiMedicos Dataset

<p align="center">
<img src="https://github.com/ixa-ehu/antidote-casimedicos/blob/main/casimedicos-arg-example.png?raw=true" style="height: 600px;">
</p>

## Structure of CasiMedicos Dataset

```
id: question id,
text: tokenized text for the argument component detection (list of lists)
labels: labels for the argument component detection (list of lists)
relations: relations between arguments (list of <argument1, argument2, relation> triplets)
```

## Results of Argument Component Detection using LLMs

<p align="left">
<img src="https://github.com/ixa-ehu/antidote-casimedicos/blob/main/multingual-data-transfer.png?raw=true" style="height: 400px;">
</p>

## Citation

If you use CasiMedicos-Arg then please **cite the following paper**:

```bibtex
@inproceedings{sviridova-etal-2024-casimedicos,
    title = {{CasiMedicos-Arg: A Medical Question Answering Dataset Annotated with Explanatory Argumentative Structures}},
    author = "Sviridova, Ekaterina  and
      Yeginbergen, Anar  and
      Estarrona, Ainara  and
      Cabrio, Elena  and
      Villata, Serena  and
      Agerri, Rodrigo",
    booktitle = "Proceedings of the 2024 Conference on Empirical Methods in Natural Language Processing",
    year = "2024",
    url = "https://aclanthology.org/2024.emnlp-main.1026",
    pages = "18463--18475"
}
```

**Contact**: [Rodrigo Agerri](https://ragerri.github.io/)
HiTZ Center - Ixa, University of the Basque Country UPV/EHU