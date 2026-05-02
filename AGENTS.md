# CARE repository — agent instructions

## Reference papers

Third-party papers for consultation live under **`literature/`** (PDFs, etc.). Use them when explaining methods, citations, or baseline details if copies exist there.

## Model performance questions

When asked about **model performance** (metrics, Dice, fold CV results):

1. Verify whether **all folds** (usually 0–4) completed using logs and/or `validation/summary.json` (or each model’s metric outputs).
2. If incomplete: state missing folds and report partial results with a clear caveat.
3. If complete: report using the **same document structure and Markdown tables** as `results/metrics/nnUNet.md` (Setup table → label semantics → metric paths → per-dataset fold-wise Mean Val Dice → per-class Dice with Fold0–Fold4 + mean column → optional foreground_mean note → optional log references).

Mirror this layout for non–nnU-Net models; answer in **Simplified Chinese** with English for paths/names as needed.
