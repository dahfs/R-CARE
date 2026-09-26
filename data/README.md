# Synthetic example dataset

This folder contains four original, synthetic illustrations and records created only to show the R-CARE data format. It contains no V-FLUTE examples, model features, private data, or benchmark results.

| File | Purpose |
| --- | --- |
| `sample_train.json` | Two training-style conversations with labels and explanations. |
| `sample_test.json` | Two input-only inference conversations. |
| `sample_train_graph.jsonl` | Graph records for the training examples. |
| `sample_test_graph.jsonl` | Graph records for the inference examples. |
| `sample_ground_truth.csv` | Held-out labels and explanations for the two test examples. |
| `sample_predictions.csv` | Example `id,label,explanation` output schema. |
| `image/train/` and `image/test/` | The illustrations referenced by the JSON records. |

The conversation JSON uses `id`, `image`, and `conversations`. Each conversation has a `human` prompt; training records also have a `gpt` answer in `Prediction. Explanation.` form. Test prompts have no answer. The graph JSONL uses the concept-graph fields expected by the method and contains no reference labels or explanations.

These four examples are **format demonstrations only**. Full training requires the official split, extracted multimodal features, graph and warrant caches, the original task project, and the base model. The sample predictions and ground truth must not be used to report benchmark scores.
