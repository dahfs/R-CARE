# Reproduction notes

## Scope

The three Python entrypoints run the final **combined** R-CARE model. The training file includes the historical stage implementations required to reproduce that model; they are materialized in a temporary directory while the command runs. There are no separate ablation entrypoints or versioned source files in the repository.

## Required external resources

- The original LLaVA base model, set by `LLAVA_MODEL_PATH`.
- The original task project, set by `RIFT_ORIG_ROOT`. It must provide its model-loading, data-processing, and official metric scripts.
- The official training and test conversations, extracted multimodal features, and the concept-graph caches expected by the original project.
- A CUDA environment with the dependencies required by the original project. The tiny synthetic examples in `data/` do not replace these resources.

Keep the official test reference available only to the evaluation step. Training and inference read the input conversations and features, not the held-out labels or explanations.

## Commands and outputs

```bash
export RIFT_ORIG_ROOT=/path/to/original-task-project
export LLAVA_MODEL_PATH=/path/to/base-llava-model
export PAPER2_OUTPUT_ROOT=/path/to/output

python train.py --device cuda:0
python infer.py --device cuda:0
python evaluate.py
```

Training writes one persistent checkpoint at `checkpoints_r_care/model.pt` below `PAPER2_OUTPUT_ROOT`. Inference writes `result/r_care/result.csv` and its contract files. Evaluation delegates to the original benchmark metric script and writes its outputs under the configured output root. Use `python train.py --help`, `python infer.py --help`, or `python evaluate.py --help` for path overrides.

The source-only repository omits checkpoints, original benchmark images, feature pickles, generated caches, predictions, and logs. The entrypoints and synthetic data schema have been checked locally; reproducing the paper's full GPU run requires the external resources above.
