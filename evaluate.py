"""Evaluate final R-CARE predictions with the original metric script."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from train import _environment, _run, _runtime


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate final R-CARE predictions")
    parser.add_argument("--output-root", type=Path,
                        default=Path(os.environ.get("PAPER2_OUTPUT_ROOT", ".")))
    parser.add_argument("--pred", type=Path)
    parser.add_argument("--true", type=Path)
    args = parser.parse_args()
    output_root = args.output_root.resolve()
    environment = _environment(output_root)
    pred = args.pred or Path("result/r_care/result.csv")
    true = args.true or Path(environment["RIFT_ORIG_ROOT"]) / "data" / "test_ground_truth_v1.6.csv"
    with _runtime() as runtime:
        _run(runtime, environment, "compute_paper2_metrics.py", "--pred", pred,
             "--true", true, "--output_dir", "f1_res_v1.6")


if __name__ == "__main__":
    main()
