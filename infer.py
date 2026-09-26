"""Run final R-CARE inference using the verified historical loader."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from train import _environment, _run, _runtime


def main() -> None:
    parser = argparse.ArgumentParser(description="Infer with the final R-CARE model")
    parser.add_argument("--output-root", type=Path,
                        default=Path(os.environ.get("PAPER2_OUTPUT_ROOT", ".")))
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--test-graph", type=Path)
    parser.add_argument("--device", default=os.environ.get("PAPER2_DEVICE", "cuda:0"))
    args = parser.parse_args()
    output_root = args.output_root.resolve()
    environment = _environment(output_root)
    checkpoint = (args.checkpoint or output_root / "checkpoints_r_care" / "model.pt").resolve()
    graph = (args.test_graph or output_root / "cache_gpt" /
             "concept_graph_test_v3_origin_fields.jsonl").resolve()
    result = output_root / "result" / "r_care"
    with _runtime() as runtime:
        _run(runtime, environment, "infer_llava_final.py", "--checkpoint", checkpoint,
             "--output", result, "--test-graph", graph, "--device", args.device)


if __name__ == "__main__":
    main()
