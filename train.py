"""Train the final R-CARE combined model.

Required environment variables: RIFT_ORIG_ROOT, LLAVA_MODEL_PATH.
The original task project, data, graph cache and base LLaVA model are external.
Only the final combined entrypoint is exposed. Historical modules required by
the verified training protocol are included as readable source below.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile


_BEGIN = "# === BEGIN REQUIRED SOURCE: "
_END = "# === END REQUIRED SOURCE ==="
_HASHES = {'audit_cwct_stage_1_artifacts.py': '75b7ba8b0ee943f3a3b408668986bc9fa5936645f3460150d4f25a171270e880', 'build_cwct_warrant_cache.py': '784a10e22950cfd0448181c68670a12a7a525d025e6c7eab2f52e21702c64668', 'cache_iesfd_stage_11_candidates.py': 'bdad0c6ff2e081cec7fcda779933cd4e108cfef0a284fac26dea354033ddf239', 'compute_paper2_metrics.py': 'a364a8c3137dcbabd40e41e468564d697e06f14cee7cf67a918d884b809de444', 'concept_graph_integration.py': '10af6a2b195dbd116e7c43ffe4eada5aa95f7d992d240ec4858de4ac0fc4a4a4', 'cwct_circuit_tuning.py': 'b1030772df73b56fda6f03f5ea42769c9ea1013d1c4108db2a282d08a1a13db2', 'cwct_warrant_data.py': 'ed0afb92dc7c5546490eaa840dd29794a0a6df1fd5eef6f672b662a371ec4d77', 'dome_ft_data.py': 'e71d33995935b3788b4d24f78229f73993a843cd34a3d0918d3d0f41505d74ac', 'final_original_verifier.py': '7c4cb01e4c27c8607cea383bd809c691003d15d19e907025632d3449317b04bb', 'g_mipo_loss.py': 'fba32f0a1c2f4c20838ba317143e4ff017e6f0538dc235b7e2338c00c0618d0d', 'gesv_stage_2_counterfactual.py': '63c2a35b528d965f0ab38fbfb482430b1178e9cfe40223d2822db00843c1492d', 'iesfd_stage_10.py': 'e8a686153469be37219eab4e2521e234b926e460f3106a80302c1686385d2d74', 'iesfd_stage_11.py': '0bc7d8c6cd2ff6f1b148234c78e9a2c3f982708927fd28ab91304b39e43aa440', 'iesfd_stage_13_repair.py': '9b4b46724abac60ea40416c11a7ae34db353f5ff51f8310eba3d6bb5a27c6993', 'iesfd_stage_14.py': 'd4a0e3aec04420e47937a7b414f2a44ca75a344bc20d069956976b1408912f20', 'iesfd_stage_16.py': 'd481d464ef3d269bc8b45c99b7d2c1b3cd18f9f587bb97986f5af2f6d750a24e', 'infer_llava_final.py': 'b2ea846759f385ed688fddde5739985ce7d008ddc5e05543bd6175024ad39c5b', 'lces_stage_4_polarity.py': '1e4d60e903575e54ff288dd7fb773731fcbe9a431aa8a03a3c988b10bcc5e33b', 'llava_final_runtime.py': '1f265f2527126d47f56d19ac698bd0965f738daa0235e7ff5a5379468ef5ba9d', 'llava_legacy_inference.py': '3a587b86358a7f011546ab91597b98730268cdd92f0559eaedf747fcc93d93d6', 'llava_replay_memory.py': '96a76b9409cae4ec4b71b895b32ea048ca0b0dc71b8b7bf4077ad2a6111559c2', 'llava_replay_standalone.py': '3a13d3fb67564cf642bb9b13df050ab342e24be9466650aead1105df254d26d7', 'oiec_completion.py': 'bae6a229897fc4170742d45eb02de4bad25461cc46f5a86b08a94fbd476f6416', 'paths_paper2.py': '048ce33c9b6658654b6a8f0ce102cb738cf7871f35e424a8146d4f91b2c67db1', 'rgc_hyperlora.py': '31060b45b1565aee72f9289eb0ef40bad63a61e379c89507de21aad02065cf6a', 'rgc_semantic_readout.py': '95fce614cd37f56846d20890551dd18abef5cbf6a7def3514c299caee2de36da', 'rgc_semantic_readout_stage_3.py': 'f58d2612e5af4489077ae34c493329b6fc5c40e6a92433fc5b199a5c38f8da5d', 'rgc_semantic_readout_stage_4.py': '4187f5b99bd392beca97579ebdc53dc7fad02dd8737c06219d2541f7444f7343', 'rgc_semantic_readout_stage_5.py': 'e7b038fb4d03c4fadbc5d27ae712b164cabd1cc4ff9f9729caa120e6cb8fbfaf', 'rgc_semantic_readout_stage_6.py': '897719013cbd56f8756d6bccce61775ab97fe98b3ba1fe02fc53e0f4b3dad9d5', 'rgc_semantic_readout_stage_7.py': '8cb4d2dfbb8814a22b478e655aafc87e3a9c7dee726e3628149585fe4a50e282', 'rgc_semantic_readout_stage_8.py': '8de3e6eb261fa0a59285a2a9b5427409e8c12ece3c230d5f8bb0714a70292916', 'test_llava_claim_graphprompt.py': '86c94169ba84998cac88750e6c57274dda40f4c2d34dd0fbe209e86f29197a0a', 'test_llava_claim_rgc_semantic_readout.py': '1029ee0bdce7f004bb11b6db7005bd2ba71b96aa62a80bad9e687d3eed9f5d72', 'test_llava_claim_rgc_semantic_readout_stage_4.py': '58f8c46ad4e42e29ea2193fe397c5de5e477808100d2d316d0b1ec46a4e322f2', 'test_llava_claim_rgc_semantic_readout_stage_5.py': 'b63b78c86fc6a4164dbcfb92a267bbee54409f8fb6840ae4020776083e0cbc3d', 'test_llava_claim_rgc_semantic_readout_stage_6.py': '305bb894c2ae0ce8eaee01abaeb7173dfec660158cafe42b611d08cce0c59ada', 'test_llava_claim_rgc_semantic_readout_stage_7.py': 'fbebbbd8b4a55423dcebefac0716818c6994fd9d79bde18f2843195a3dfd7cf3', 'test_llava_claim_rgc_semantic_readout_stage_8.py': 'c47b1c8a9fd0999ac9fca0b68bdafe52500eb14ce6e0a2a9a2d01bbb293c06b0', 'train_llava_claim_dome_ft.py': '11d9afed51d1a732682095bd0b70d8df92b609c785e65dfdce6d814671e3405f', 'train_llava_claim_graphprompt.py': 'd1bfe48eb7710f81b33f46c22f7210d58680436c3c1e83c54a533c7a9c69869f', 'train_llava_claim_iesfd_stage_10.py': 'd7c1fba4ca634f6203d3d79d8d939d7493c3a04c28c688fd75361c95c25dd9ea', 'train_llava_claim_oiec_stage_1.py': '7cddc8f2266ce356ca98097c18010161178e77bbaaa0d19082b0d22b313ee20e', 'train_llava_claim_rgc_semantic_readout.py': 'eb916cf055acb95928a6fd4d03e5c86a4a4bdca0eae5e93b53a949231bb35e8f', 'train_llava_claim_rgc_semantic_readout_stage_4.py': '814bbf421aef4c6c805078f50fbaad6d8e65c6fc42ffcdc63195ce4cd7e0eed5', 'train_llava_claim_rgc_semantic_readout_stage_5.py': 'f293673a39c9b638ba0d912b86c792fe15be5eb6eb2d141cda4ccdfc71cb2fee', 'train_llava_claim_rgc_semantic_readout_stage_6.py': '1b0667dd3a270c2c148eb13dd2e40ef1c0ec477442e71dac02d9dc1c57dd4f01', 'train_llava_claim_rgc_semantic_readout_stage_7.py': '64985236d1a89dfb86fd6f9f3e9db9156403783be13f519e061e3d13a19c4a1d', 'train_llava_claim_rgc_semantic_readout_stage_8.py': 'e26c46d95d423a97a4f6a8c6ea76bb22b0dfd2c55beea0d16ce3c6417712d6ff', 'train_llava_final.py': 'a8a300f71ee6850c9e2065a5376e66c320a1e3841cc1897914a028d22b092e02', 'train_llava_replay.py': '6761eab818fe0e7e5c1d2c7ac8186ccb482516369bc6a587dc64994170e3115c', 'tspib_stage_6_losses.py': '62be34baf0f12a58a89d39c5fd869a6f409a9c552830af1ac5fa7014bed3e1a4', 'verify_cwct_stage_1_checkpoint.py': 'f85056a8730219b9a1b1c43bdfa6264982ff6cba99ea97ecab8406caa84c0e77'}


def _sources() -> dict[str, str]:
    sources: dict[str, str] = {}
    current: str | None = None
    lines: list[str] = []
    for line in Path(__file__).read_text(encoding="utf-8").splitlines():
        if line.startswith(_BEGIN) and line.endswith(" ==="):
            if current is not None:
                raise RuntimeError("Nested source section")
            current = line[len(_BEGIN):-4]
            lines = []
        elif line == _END:
            if current is None:
                raise RuntimeError("Unexpected source section end")
            sources[current] = "\n".join(lines) + "\n"
            current = None
        elif current is not None:
            if not line.startswith("#|"):
                raise RuntimeError("Malformed source section")
            lines.append(line[2:])
    if current is not None or set(sources) != set(_HASHES):
        raise RuntimeError("Incomplete required source")
    for name, content in sources.items():
        if hashlib.sha256(content.encode("utf-8")).hexdigest() != _HASHES[name]:
            raise RuntimeError(f"Required source changed: {name}")
    return sources


@contextmanager
def _runtime():
    with tempfile.TemporaryDirectory(prefix="r_care_runtime_") as directory:
        root = Path(directory)
        for name, content in _sources().items():
            (root / name).write_text(content, encoding="utf-8", newline="\n")
        yield root


def _environment(output_root: Path) -> dict[str, str]:
    environment = os.environ.copy()
    for name in ("RIFT_ORIG_ROOT", "LLAVA_MODEL_PATH"):
        if not environment.get(name):
            raise SystemExit(f"Set {name} before running R-CARE")
    environment["PAPER2_OUTPUT_ROOT"] = str(output_root)
    return environment


def _run(root: Path, environment: dict[str, str], script: str, *arguments: str) -> None:
    subprocess.run([sys.executable, "-u", str(root / script), *map(str, arguments)],
                   cwd=root, env=environment, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the final R-CARE combined model")
    parser.add_argument("--output-root", type=Path,
                        default=Path(os.environ.get("PAPER2_OUTPUT_ROOT", ".")))
    parser.add_argument("--device", default=os.environ.get("PAPER2_DEVICE", "cuda:0"))
    parser.add_argument("--train-graph", type=Path)
    parser.add_argument("--warrant-cache", type=Path)
    parser.add_argument("--warrant-manifest", type=Path)
    args = parser.parse_args()
    output_root = args.output_root.resolve()
    environment = _environment(output_root)
    original = Path(environment["RIFT_ORIG_ROOT"]).resolve()
    graph = (args.train_graph or output_root / "cache_gpt" /
             "concept_graph_train_v3_origin_fields.jsonl").resolve()
    warrant = (args.warrant_cache or output_root / "cache_cwct_v1" /
               "warrant_train_v1.jsonl").resolve()
    manifest = (args.warrant_manifest or output_root / "cache_cwct_v1" /
                "warrant_manifest_v1.json").resolve()
    checkpoint = output_root / "checkpoints_r_care"
    output_root.mkdir(parents=True, exist_ok=True)
    with _runtime() as runtime:
        if not warrant.is_file() and not manifest.is_file():
            warrant.parent.mkdir(parents=True, exist_ok=True)
            _run(runtime, environment, "build_cwct_warrant_cache.py",
                 "--train_json", original / "data" / "no_prompt_train.json",
                 "--train_features", original / "data" / "train_ac2_v1.6_cot_merged_features.pkl",
                 "--concept_graph_cache", graph, "--output", warrant,
                 "--manifest", manifest, "--seed", "2026")
        _run(runtime, environment, "audit_cwct_stage_1_artifacts.py", "warrant",
             "--cache", warrant, "--manifest", manifest,
             "--train-json", original / "data" / "no_prompt_train.json",
             "--train-features", original / "data" / "train_ac2_v1.6_cot_merged_features.pkl",
             "--train-graph", graph, "--seed", "2026",
             "--dev-fraction", "0.10", "--minimum-similarity", "0.05")
        _run(runtime, environment, "train_llava_replay.py", "--variant", "combined",
             "--output", checkpoint, "--device", args.device,
             "--train-graph", graph, "--warrant-cache", warrant,
             "--warrant-manifest", manifest)


if __name__ == "__main__":
    main()

# === BEGIN REQUIRED SOURCE: audit_cwct_stage_1_artifacts.py ===
#|"""Strict fingerprint audits for every reusable CWCT v1 artifact."""
#|
#|from __future__ import annotations
#|
#|import argparse
#|import csv
#|import hashlib
#|import json
#|import math
#|from pathlib import Path
#|from typing import Any, Iterable
#|
#|from cwct_circuit_tuning import (
#|    TRACE_MODEL_CONFIG_FIELDS,
#|    load_circuit_manifest,
#|    manifest_sha256,
#|)
#|from cwct_warrant_data import (
#|    MANIFEST_VERSION,
#|    SCHEMA_VERSION,
#|    answer_from_record,
#|    file_sha256,
#|    read_jsonl,
#|    stable_json_hash,
#|    validate_warrant_records,
#|)
#|
#|
#|def _json(path: str | Path):
#|    with Path(path).open("r", encoding="utf-8") as handle:
#|        return json.load(handle)
#|
#|
#|def _tree_sha256(path: str | Path) -> str:
#|    root = Path(path)
#|    digest = hashlib.sha256()
#|    files = sorted(item for item in root.rglob("*") if item.is_file())
#|    if not files:
#|        raise FileNotFoundError(f"empty artifact directory: {root}")
#|    for item in files:
#|        relative = item.relative_to(root).as_posix().encode("utf-8")
#|        digest.update(len(relative).to_bytes(8, "big"))
#|        digest.update(relative)
#|        digest.update(bytes.fromhex(file_sha256(item)))
#|    return digest.hexdigest()
#|
#|
#|def _same_number(left: Any, right: Any, *, tolerance: float = 1e-12) -> bool:
#|    return math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=tolerance)
#|
#|
#|def _require_equal(actual: Any, expected: Any, name: str) -> None:
#|    if actual != expected:
#|        raise RuntimeError(f"CWCT {name} mismatch: actual={actual!r} expected={expected!r}")
#|
#|
#|def _sidecar_payload(kind: str, **values) -> dict[str, Any]:
#|    payload = {"version": "cwct_v1_artifact_audit_v1", "kind": kind, **values}
#|    payload["audit_sha256"] = stable_json_hash(payload)
#|    return payload
#|
#|
#|def _audit_sidecar(path: str | Path, payload, write: bool) -> None:
#|    target = Path(path)
#|    if write:
#|        if target.exists():
#|            raise FileExistsError(f"refusing to overwrite audit sidecar: {target}")
#|        target.parent.mkdir(parents=True, exist_ok=True)
#|        target.write_text(
#|            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
#|            encoding="utf-8",
#|        )
#|    else:
#|        if not target.is_file():
#|            raise FileNotFoundError(f"missing audit sidecar: {target}")
#|        _require_equal(_json(target), payload, f"{payload['kind']} sidecar")
#|
#|
#|def audit_warrant(args) -> None:
#|    cache = Path(args.cache).resolve()
#|    manifest_path = Path(args.manifest).resolve()
#|    train_json = Path(args.train_json).resolve()
#|    features = Path(args.train_features).resolve()
#|    graph = Path(args.train_graph).resolve()
#|    manifest = _json(manifest_path)
#|    _require_equal(manifest.get("manifest_version"), MANIFEST_VERSION, "warrant manifest version")
#|    _require_equal(manifest.get("schema_version"), SCHEMA_VERSION, "warrant schema")
#|    _require_equal(manifest.get("test_accessed"), False, "warrant test access")
#|    _require_equal(manifest.get("record_count"), 4578, "warrant record count")
#|    _require_equal(manifest.get("seed"), args.seed, "warrant seed")
#|    if not _same_number(manifest.get("dev_fraction"), args.dev_fraction):
#|        raise RuntimeError("CWCT warrant dev_fraction mismatch")
#|    if not _same_number(manifest.get("minimum_similarity"), args.minimum_similarity):
#|        raise RuntimeError("CWCT warrant minimum_similarity mismatch")
#|    expected_inputs = {
#|        "train_json": file_sha256(train_json),
#|        "concept_graph": file_sha256(graph),
#|        "train_features": file_sha256(features),
#|    }
#|    _require_equal(manifest.get("input_sha256"), expected_inputs, "warrant inputs")
#|    _require_equal(manifest.get("cache_sha256"), file_sha256(cache), "warrant cache hash")
#|    contract = dict(manifest)
#|    declared = contract.pop("contract_sha256", None)
#|    _require_equal(declared, stable_json_hash(contract), "warrant contract hash")
#|    records = read_jsonl(cache)
#|    raw = _json(train_json)
#|    if not isinstance(raw, list):
#|        raise RuntimeError("CWCT training JSON must be a list")
#|    source_answers = {str(row["id"]): answer_from_record(row) for row in raw}
#|    validate_warrant_records(
#|        records,
#|        expected_ids=source_answers,
#|        source_answers=source_answers,
#|    )
#|    eligible = sum(bool(row.get("auxiliary_eligible")) for row in records)
#|    _require_equal(manifest.get("eligible_count"), eligible, "warrant eligible count")
#|    print(
#|        f"[cwct-audit] warrant passed records={len(records)} eligible={eligible} "
#|        f"schema={SCHEMA_VERSION} exact_source=true"
#|    )
#|
#|
#|def audit_circuit(args) -> None:
#|    path = Path(args.manifest).resolve()
#|    warrant_cache = Path(args.warrant_cache).resolve()
#|    trace_json = Path(args.trace_json).resolve()
#|    train_graph = Path(args.train_graph).resolve()
#|    manifest = load_circuit_manifest(path)
#|    run_config = _json(Path(args.run_config).resolve())
#|    if run_config.get("version") != "cwct_v1_run_config_v1":
#|        raise RuntimeError("unexpected CWCT run-config version")
#|    locked_model = run_config.get("model")
#|    if not isinstance(locked_model, dict) or set(locked_model) != set(
#|        TRACE_MODEL_CONFIG_FIELDS
#|    ):
#|        raise RuntimeError("CWCT run-config model section is incomplete")
#|    _require_equal(
#|        manifest.get("model_config"), locked_model, "circuit model config"
#|    )
#|    source_root = Path(args.source_root).resolve()
#|    source_lora = source_root / f"lora_epoch_{args.source_epoch}{args.source_suffix}"
#|    source_projector = source_root / f"proj_epoch_{args.source_epoch}{args.source_suffix}.pth"
#|    source = manifest["source"]
#|    _require_equal(
#|        source.get("llava_model_path"),
#|        run_config.get("source", {}).get("llava_model_path"),
#|        "circuit base model path",
#|    )
#|    _require_equal(source.get("epoch"), args.source_epoch, "circuit source epoch")
#|    _require_equal(source.get("projector_suffix"), args.source_suffix, "circuit source suffix")
#|    _require_equal(source.get("lora_tree_sha256"), _tree_sha256(source_lora), "source LoRA hash")
#|    _require_equal(source.get("projector_sha256"), file_sha256(source_projector), "source projector hash")
#|    _require_equal(manifest.get("warrant_cache_sha256"), file_sha256(warrant_cache), "circuit warrant hash")
#|    _require_equal(
#|        manifest.get("trace_input_sha256"),
#|        file_sha256(trace_json),
#|        "circuit trace JSON hash",
#|    )
#|    _require_equal(
#|        manifest.get("trace_graph_sha256"),
#|        file_sha256(train_graph),
#|        "circuit trace graph hash",
#|    )
#|    trace = manifest.get("trace_config", {})
#|    expected = {
#|        "layers": args.layers,
#|        "max_samples": args.max_samples,
#|        "top_components": args.top_components,
#|        "seed": args.seed,
#|        "minimum_effect": args.min_effect,
#|        "minimum_samples": args.minimum_samples,
#|        "minimum_fold_samples": args.minimum_fold_samples,
#|        "subspace_rank": args.subspace_rank,
#|        "ridge": args.ridge,
#|        "bootstrap_samples": args.bootstrap_samples,
#|        "minimum_decode_accuracy": args.minimum_decode_accuracy,
#|        "margin_replay_tolerance": args.margin_replay_tolerance,
#|    }
#|    for key, value in expected.items():
#|        actual = trace.get(key)
#|        if isinstance(value, float):
#|            if actual is None or not _same_number(actual, value):
#|                raise RuntimeError(f"CWCT trace config mismatch for {key}")
#|        else:
#|            _require_equal(actual, value, f"trace config {key}")
#|    selected = manifest["selected"]
#|    _require_equal(len(selected), args.top_components, "selected component count")
#|    for fold in manifest["folds"]:
#|        values = {
#|            key: float(fold[key])
#|            for key in (
#|                "selected_ci_lower",
#|                "selected_mean_recovery",
#|                "random_control_mean_recovery",
#|                "label_control_mean_recovery",
#|            )
#|        }
#|        if not all(math.isfinite(value) for value in values.values()):
#|            raise RuntimeError("CWCT circuit contains non-finite fold metrics")
#|        if values["selected_ci_lower"] <= args.min_effect:
#|            raise RuntimeError("CWCT circuit CI does not exceed pre-registered floor")
#|        if values["selected_mean_recovery"] <= values["random_control_mean_recovery"]:
#|            raise RuntimeError("CWCT circuit does not beat random control")
#|        if values["selected_mean_recovery"] <= values["label_control_mean_recovery"]:
#|            raise RuntimeError("CWCT circuit does not beat label control")
#|    _require_equal(manifest.get("manifest_sha256"), manifest_sha256(manifest), "circuit manifest hash")
#|    print(
#|        f"[cwct-audit] circuit passed selected={len(selected)} "
#|        "cross_fitted=true real_multimodal=true"
#|    )
#|
#|
#|def _audit_embedded_checkpoint(args) -> dict[str, Any]:
#|    target = Path(args.target_lora).resolve()
#|    embedded_path = target / "cwct_manifest.json"
#|    if not embedded_path.is_file():
#|        raise FileNotFoundError(f"missing embedded manifest: {embedded_path}")
#|    embedded = _json(embedded_path)
#|    traced = load_circuit_manifest(args.circuit_manifest)
#|    stripped = dict(embedded)
#|    training = stripped.pop("training", None)
#|    if manifest_sha256(stripped) != manifest_sha256(traced):
#|        raise RuntimeError("embedded checkpoint circuit manifest mismatch")
#|    if not isinstance(training, dict):
#|        raise RuntimeError("embedded checkpoint lacks training contract")
#|    _require_equal(
#|        training.get("training_partition"),
#|        "tune",
#|        "checkpoint training partition",
#|    )
#|    _require_equal(
#|        training.get("dev_partition_used_for_optimization"),
#|        False,
#|        "checkpoint dev optimization policy",
#|    )
#|    _require_equal(
#|        training.get("grounding_policy"),
#|        "dual_control_first_verdict_predecessor",
#|        "checkpoint grounding policy",
#|    )
#|    run_config = Path(args.run_config).resolve()
#|    _require_equal(training.get("run_config_sha256"), file_sha256(run_config), "checkpoint run config")
#|    return training
#|
#|
#|def audit_checkpoint(args) -> None:
#|    import verify_cwct_stage_1_checkpoint as verifier
#|
#|    verification = argparse.Namespace(
#|        source_lora=args.source_lora,
#|        target_lora=args.target_lora,
#|        source_projector=args.source_projector,
#|        target_projector=args.target_projector,
#|        circuit_manifest=args.circuit_manifest,
#|        train_lora_factors=args.train_lora_factors,
#|        max_relative_drift=args.max_relative_drift,
#|        tolerance=1e-7,
#|    )
#|    verifier.verify(verification)
#|    _audit_embedded_checkpoint(args)
#|    print("[cwct-audit] checkpoint passed run_config_bound=true")
#|
#|
#|def _test_ids(test_json: Path) -> set[str]:
#|    data = _json(test_json)
#|    if not isinstance(data, list):
#|        raise RuntimeError("test JSON must be a list")
#|    ids = [str(row["id"]) for row in data]
#|    if len(ids) != 723 or len(set(ids)) != len(ids):
#|        raise RuntimeError("test JSON must contain exactly 723 unique IDs")
#|    return set(ids)
#|
#|
#|def _graph_ids(path: Path) -> set[str]:
#|    ids = set()
#|    with path.open("r", encoding="utf-8") as handle:
#|        for line in handle:
#|            if line.strip():
#|                ids.add(str(json.loads(line)["id"]))
#|    return ids
#|
#|
#|def audit_result(args) -> None:
#|    result = Path(args.result).resolve()
#|    test_json = Path(args.test_json).resolve()
#|    test_graph = Path(args.test_graph).resolve()
#|    target_lora = Path(args.target_lora).resolve()
#|    target_projector = Path(args.target_projector).resolve()
#|    circuit = Path(args.circuit_manifest).resolve()
#|    expected = _test_ids(test_json)
#|    _require_equal(_graph_ids(test_graph), expected, "test graph IDs")
#|    with result.open("r", encoding="utf-8-sig", newline="") as handle:
#|        rows = list(csv.DictReader(handle))
#|    actual = [str(row.get("id", "")) for row in rows]
#|    if len(rows) != 723 or set(actual) != expected or len(set(actual)) != 723:
#|        raise RuntimeError("result CSV does not match the exact official test IDs")
#|    if any(not str(row.get("explanation", "")).strip() for row in rows):
#|        raise RuntimeError("result CSV contains empty explanations")
#|    valid_labels = {"0", "1", "0.0", "1.0"}
#|    if any(str(row.get("label", "")).strip() not in valid_labels for row in rows):
#|        raise RuntimeError("result CSV contains an invalid label")
#|    payload = _sidecar_payload(
#|        "result",
#|        result_sha256=file_sha256(result),
#|        test_json_sha256=file_sha256(test_json),
#|        test_graph_sha256=file_sha256(test_graph),
#|        target_lora_tree_sha256=_tree_sha256(target_lora),
#|        target_projector_sha256=file_sha256(target_projector),
#|        circuit_manifest_sha256=file_sha256(circuit),
#|        epoch=int(args.epoch),
#|        output_tag=args.output_tag,
#|        rows=len(rows),
#|    )
#|    _audit_sidecar(args.sidecar, payload, args.write_sidecar)
#|    print(f"[cwct-audit] result passed rows={len(rows)} sidecar={args.sidecar}")
#|
#|
#|def _csv_rows(path: Path):
#|    with path.open("r", encoding="utf-8-sig", newline="") as handle:
#|        return list(csv.DictReader(handle))
#|
#|
#|def _all_finite_rows(rows: Iterable[dict[str, str]]) -> bool:
#|    count = 0
#|    for row in rows:
#|        for value in row.values():
#|            if value is None or not str(value).strip():
#|                continue
#|            try:
#|                number = float(value)
#|            except ValueError:
#|                continue
#|            count += 1
#|            if not math.isfinite(number):
#|                return False
#|    return count > 0
#|
#|
#|def audit_metrics(args) -> None:
#|    root = Path(args.metric_root).resolve()
#|    result = Path(args.result).resolve()
#|    truth = Path(args.truth).resolve()
#|    primary = root / "f1_at_thresh.csv"
#|    semantic = root / "f1_bscore_bleurt.csv"
#|    if not primary.is_file() or not semantic.is_file():
#|        raise FileNotFoundError("missing CWCT metric CSV")
#|    primary_rows = _csv_rows(primary)
#|    semantic_rows = _csv_rows(semantic)
#|    if len(primary_rows) != 101:
#|        raise RuntimeError(
#|            f"primary metric CSV must contain exactly 101 rows, got {len(primary_rows)}"
#|        )
#|    if len(semantic_rows) != 723:
#|        raise RuntimeError(
#|            f"semantic metric CSV must contain exactly 723 rows, got {len(semantic_rows)}"
#|        )
#|    if not _all_finite_rows(primary_rows) or not _all_finite_rows(semantic_rows):
#|        raise RuntimeError("CWCT metric CSV contains no finite measurements")
#|    thresholds = set()
#|    for row in primary_rows:
#|        try:
#|            threshold, score = float(row["threshold"]), float(row["f1"])
#|        except (KeyError, TypeError, ValueError) as error:
#|            raise RuntimeError("malformed f1_at_thresh.csv") from error
#|        if not math.isfinite(score):
#|            raise RuntimeError("non-finite primary F1")
#|        thresholds.add(round(threshold, 8))
#|        if str(row.get("model_name", "")) != args.output_tag:
#|            raise RuntimeError("primary metric CSV model_name/output_tag mismatch")
#|    expected_thresholds = {round(index / 100.0, 8) for index in range(101)}
#|    if thresholds != expected_thresholds:
#|        raise RuntimeError("primary metric CSV is not the complete 0.00..1.00 grid")
#|    with result.open("r", encoding="utf-8-sig", newline="") as handle:
#|        result_rows = list(csv.DictReader(handle))
#|    result_ids = {str(row.get("id", "")) for row in result_rows}
#|    semantic_ids = [str(row.get("id", "")) for row in semantic_rows]
#|    if (
#|        len(result_rows) != 723
#|        or len(result_ids) != 723
#|        or len(set(semantic_ids)) != 723
#|        or set(semantic_ids) != result_ids
#|    ):
#|        raise RuntimeError("semantic metric IDs do not exactly match the result CSV")
#|    numeric_columns = ("label_pred", "label_true", "bertscore", "bleurt", "bleurt_bertscore")
#|    for row in semantic_rows:
#|        for column in numeric_columns:
#|            try:
#|                value = float(row[column])
#|            except (KeyError, TypeError, ValueError) as error:
#|                raise RuntimeError(f"semantic metric column {column} is malformed") from error
#|            if not math.isfinite(value):
#|                raise RuntimeError(f"semantic metric column {column} is non-finite")
#|    payload = _sidecar_payload(
#|        "metrics",
#|        result_sha256=file_sha256(result),
#|        truth_sha256=file_sha256(truth),
#|        primary_sha256=file_sha256(primary),
#|        semantic_sha256=file_sha256(semantic),
#|        output_tag=args.output_tag,
#|        primary_rows=len(primary_rows),
#|        semantic_rows=len(semantic_rows),
#|    )
#|    _audit_sidecar(args.sidecar, payload, args.write_sidecar)
#|    print(f"[cwct-audit] metrics passed root={root} sidecar={args.sidecar}")
#|
#|
#|def build_parser():
#|    parser = argparse.ArgumentParser()
#|    commands = parser.add_subparsers(dest="command", required=True)
#|
#|    warrant = commands.add_parser("warrant")
#|    warrant.add_argument("--cache", required=True)
#|    warrant.add_argument("--manifest", required=True)
#|    warrant.add_argument("--train-json", required=True)
#|    warrant.add_argument("--train-features", required=True)
#|    warrant.add_argument("--train-graph", required=True)
#|    warrant.add_argument("--seed", type=int, required=True)
#|    warrant.add_argument("--dev-fraction", type=float, required=True)
#|    warrant.add_argument("--minimum-similarity", type=float, required=True)
#|    warrant.set_defaults(function=audit_warrant)
#|
#|    circuit = commands.add_parser("circuit")
#|    circuit.add_argument("--manifest", required=True)
#|    circuit.add_argument("--warrant-cache", required=True)
#|    circuit.add_argument("--trace-json", required=True)
#|    circuit.add_argument("--train-graph", required=True)
#|    circuit.add_argument("--run-config", required=True)
#|    circuit.add_argument("--source-root", required=True)
#|    circuit.add_argument("--source-epoch", type=int, required=True)
#|    circuit.add_argument("--source-suffix", required=True)
#|    circuit.add_argument("--layers", required=True)
#|    circuit.add_argument("--max-samples", type=int, required=True)
#|    circuit.add_argument("--top-components", type=int, required=True)
#|    circuit.add_argument("--seed", type=int, required=True)
#|    circuit.add_argument("--min-effect", type=float, required=True)
#|    circuit.add_argument("--minimum-samples", type=int, required=True)
#|    circuit.add_argument("--minimum-fold-samples", type=int, required=True)
#|    circuit.add_argument("--subspace-rank", type=int, required=True)
#|    circuit.add_argument("--ridge", type=float, required=True)
#|    circuit.add_argument("--bootstrap-samples", type=int, required=True)
#|    circuit.add_argument("--minimum-decode-accuracy", type=float, required=True)
#|    circuit.add_argument("--margin-replay-tolerance", type=float, required=True)
#|    circuit.set_defaults(function=audit_circuit)
#|
#|    checkpoint = commands.add_parser("checkpoint")
#|    checkpoint.add_argument("--source-lora", required=True)
#|    checkpoint.add_argument("--target-lora", required=True)
#|    checkpoint.add_argument("--source-projector", required=True)
#|    checkpoint.add_argument("--target-projector", required=True)
#|    checkpoint.add_argument("--circuit-manifest", required=True)
#|    checkpoint.add_argument("--train-lora-factors", required=True)
#|    checkpoint.add_argument("--max-relative-drift", type=float, required=True)
#|    checkpoint.add_argument("--run-config", required=True)
#|    checkpoint.set_defaults(function=audit_checkpoint)
#|
#|    result = commands.add_parser("result")
#|    result.add_argument("--result", required=True)
#|    result.add_argument("--test-json", required=True)
#|    result.add_argument("--test-graph", required=True)
#|    result.add_argument("--target-lora", required=True)
#|    result.add_argument("--target-projector", required=True)
#|    result.add_argument("--circuit-manifest", required=True)
#|    result.add_argument("--epoch", type=int, required=True)
#|    result.add_argument("--output-tag", required=True)
#|    result.add_argument("--sidecar", required=True)
#|    result.add_argument("--write-sidecar", action="store_true")
#|    result.set_defaults(function=audit_result)
#|
#|    metrics = commands.add_parser("metrics")
#|    metrics.add_argument("--metric-root", required=True)
#|    metrics.add_argument("--result", required=True)
#|    metrics.add_argument("--truth", required=True)
#|    metrics.add_argument("--output-tag", required=True)
#|    metrics.add_argument("--sidecar", required=True)
#|    metrics.add_argument("--write-sidecar", action="store_true")
#|    metrics.set_defaults(function=audit_metrics)
#|    return parser
#|
#|
#|def main() -> None:
#|    args = build_parser().parse_args()
#|    args.function(args)
#|
#|
#|if __name__ == "__main__":
#|    main()
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: build_cwct_warrant_cache.py ===
#|"""Build the auditable CWCT v2 data contract (v1 experiment filenames)."""
#|
#|from __future__ import annotations
#|
#|import argparse
#|from collections import Counter
#|import json
#|from pathlib import Path
#|import pickle
#|from typing import Any
#|
#|from cwct_warrant_data import (
#|    MANIFEST_VERSION,
#|    MAX_CLAIM_COVERAGE,
#|    MAX_CLAIM_JACCARD,
#|    MAX_MISMATCH_SURFACE_SIMILARITY,
#|    MAX_WARRANT_CLAIM_COVERAGE,
#|    MIN_DONOR_LENGTH_RATIO,
#|    SCHEMA_VERSION,
#|    answer_from_record,
#|    build_warrant_records,
#|    file_sha256,
#|    stable_json_hash,
#|    validate_warrant_records,
#|)
#|from paths_paper2 import Paper2Paths
#|
#|
#|def _load_json(path: Path):
#|    with path.open("r", encoding="utf-8") as handle:
#|        return json.load(handle)
#|
#|
#|def _load_graph(path: Path) -> dict[str, dict[str, Any]]:
#|    output = {}
#|    with path.open("r", encoding="utf-8") as handle:
#|        for line_number, line in enumerate(handle, 1):
#|            if not line.strip():
#|                continue
#|            record = json.loads(line)
#|            key = str(record["id"])
#|            if key in output:
#|                raise ValueError(f"duplicate graph id at {path}:{line_number}: {key}")
#|            output[key] = record
#|    return output
#|
#|
#|def _load_features(path: Path):
#|    with path.open("rb") as handle:
#|        return pickle.load(handle)
#|
#|
#|def build(args: argparse.Namespace) -> None:
#|    paths = Paper2Paths.from_env()
#|    train_json = paths.resolve_output_path(args.train_json)
#|    graph_path = paths.resolve_output_path(args.concept_graph_cache)
#|    feature_path = paths.resolve_output_path(args.train_features)
#|    output = paths.resolve_output_path(args.output)
#|    manifest_path = paths.resolve_output_path(args.manifest)
#|    for path in (train_json, graph_path, feature_path):
#|        if not path.is_file():
#|            raise FileNotFoundError(path)
#|        lowered = path.name.lower()
#|        if "test" in lowered:
#|            raise ValueError(f"CWCT cache builder rejects test-named input: {path}")
#|
#|    train_records = _load_json(train_json)
#|    graph = _load_graph(graph_path)
#|    features = _load_features(feature_path)
#|    train_ids = {str(record["id"]) for record in train_records}
#|    graph_ids = set(graph)
#|    feature_ids = {str(key) for key in features}
#|    if train_ids != graph_ids or train_ids != feature_ids:
#|        raise ValueError(
#|            "CWCT train/json/graph/features id mismatch: "
#|            f"json={len(train_ids)} graph={len(graph_ids)} features={len(feature_ids)}"
#|        )
#|
#|    records = build_warrant_records(
#|        train_records,
#|        graph,
#|        features,
#|        seed=args.seed,
#|        dev_fraction=args.dev_fraction,
#|        minimum_similarity=args.minimum_similarity,
#|    )
#|    source_answers = {
#|        str(record["id"]): answer_from_record(record) for record in train_records
#|    }
#|    # Revalidate at the I/O boundary, including source hash and exact offsets.
#|    validate_warrant_records(
#|        records,
#|        expected_ids=train_ids,
#|        source_answers=source_answers,
#|    )
#|    output.parent.mkdir(parents=True, exist_ok=True)
#|    with output.open("w", encoding="utf-8") as handle:
#|        for record in records:
#|            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
#|    eligible = [record for record in records if record["auxiliary_eligible"]]
#|    partition_counts = {
#|        partition: sum(record["partition"] == partition for record in records)
#|        for partition in ("tune", "dev")
#|    }
#|    eligible_by_partition = {
#|        partition: sum(
#|            record["partition"] == partition and record["auxiliary_eligible"]
#|            for record in records
#|        )
#|        for partition in ("tune", "dev")
#|    }
#|    silver_records = [record for record in records if record["silver_warrant"]]
#|    family_counts = Counter(
#|        record["silver_warrant"]["rule_family"] for record in silver_records
#|    )
#|    reason_counts = Counter(
#|        str(record["ineligible_reason"])
#|        for record in records
#|        if not record["auxiliary_eligible"]
#|    )
#|    same_controls = [
#|        record["same_label_hard_mismatch"] for record in eligible
#|    ]
#|    opposite_controls = [
#|        record["opposite_label_matched_warrant"] for record in eligible
#|    ]
#|
#|    def metric_summary(controls, field):
#|        values = [float(control[field]) for control in controls]
#|        if not values:
#|            return {"count": 0, "min": None, "mean": None, "max": None}
#|        return {
#|            "count": len(values),
#|            "min": min(values),
#|            "mean": sum(values) / len(values),
#|            "max": max(values),
#|        }
#|
#|    manifest = {
#|        "manifest_version": MANIFEST_VERSION,
#|        "schema_version": SCHEMA_VERSION,
#|        "method": "exact_span_silver_warrant_partition_local_dual_control_retrieval",
#|        "split_policy": "hash_train_only",
#|        "test_accessed": False,
#|        "donor_interpretation": (
#|            "retrieved_exact-span controls; not logical counterfactuals"
#|        ),
#|        "donor_contract": {
#|            "same_label_hard_mismatch": (
#|                "same partition/label/family, context-near, warrant-surface-mismatched"
#|            ),
#|            "opposite_label_matched_warrant": (
#|                "same partition/family, opposite label, context-near"
#|            ),
#|            "assignment": "atomic_both_or_neither",
#|            "cross_partition_retrieval": False,
#|            "synthetic_fallback": False,
#|            "family_relaxation": False,
#|        },
#|        "forbidden_retrieval_fields": [
#|            "description",
#|            "E_desc",
#|            "dataset",
#|            "source_dataset",
#|            "phenomenon",
#|            "inferred_phenomenon",
#|        ],
#|        "retrieval_features": ["E_image", "E_text"],
#|        "featureless_unit_test_fallback": ["visual_nodes", "claim_nodes"],
#|        "retrieval_shortlists": ["same_label", "opposite_label"],
#|        "extraction_quality_policy": {
#|            "accepted_quality": "high",
#|            "reject_conclusion_or_claim_markers": True,
#|            "reject_conclusion_prefix": True,
#|            "reject_deictic_restatement_prefix": True,
#|            "overlap_rejection_rule": (
#|                "jaccard >= max_claim_jaccard OR "
#|                "(claim_coverage >= max_claim_coverage AND "
#|                "warrant_coverage >= max_warrant_claim_coverage)"
#|            ),
#|            "max_claim_jaccard_exclusive": MAX_CLAIM_JACCARD,
#|            "max_claim_coverage_exclusive": MAX_CLAIM_COVERAGE,
#|            "max_warrant_claim_coverage_exclusive": MAX_WARRANT_CLAIM_COVERAGE,
#|        },
#|        "donor_quality_policy": {
#|            "minimum_length_ratio": MIN_DONOR_LENGTH_RATIO,
#|            "maximum_same_label_surface_similarity": (
#|                MAX_MISMATCH_SURFACE_SIMILARITY
#|            ),
#|        },
#|        "seed": args.seed,
#|        "dev_fraction": args.dev_fraction,
#|        "minimum_similarity": args.minimum_similarity,
#|        "record_count": len(records),
#|        "eligible_count": len(eligible),
#|        "partition_counts": partition_counts,
#|        "quality_statistics": {
#|            "silver_high_count": len(silver_records),
#|            "no_silver_count": len(records) - len(silver_records),
#|            "eligible_by_partition": eligible_by_partition,
#|            "silver_rule_family_counts": dict(sorted(family_counts.items())),
#|            "ineligible_reason_counts": dict(sorted(reason_counts.items())),
#|            "same_label_semantic_similarity": metric_summary(
#|                same_controls, "semantic_similarity"
#|            ),
#|            "opposite_label_semantic_similarity": metric_summary(
#|                opposite_controls, "semantic_similarity"
#|            ),
#|            "same_label_length_ratio": metric_summary(
#|                same_controls, "length_ratio"
#|            ),
#|            "opposite_label_length_ratio": metric_summary(
#|                opposite_controls, "length_ratio"
#|            ),
#|        },
#|        "input_sha256": {
#|            "train_json": file_sha256(train_json),
#|            "concept_graph": file_sha256(graph_path),
#|            "train_features": file_sha256(feature_path),
#|        },
#|        "cache_sha256": file_sha256(output),
#|    }
#|    manifest["contract_sha256"] = stable_json_hash(manifest)
#|    manifest_path.parent.mkdir(parents=True, exist_ok=True)
#|    with manifest_path.open("w", encoding="utf-8") as handle:
#|        json.dump(manifest, handle, ensure_ascii=False, indent=2, sort_keys=True)
#|        handle.write("\n")
#|    print(
#|        f"[cwct-cache] records={len(records)} silver_high={len(silver_records)} "
#|        f"eligible={len(eligible)} "
#|        f"tune={partition_counts['tune']} dev={partition_counts['dev']} "
#|        f"eligible_tune={eligible_by_partition['tune']} "
#|        f"eligible_dev={eligible_by_partition['dev']} "
#|        "test_accessed=false"
#|    )
#|    print(f"[cwct-cache] cache={output}")
#|    print(f"[cwct-cache] manifest={manifest_path}")
#|
#|
#|def parse_args() -> argparse.Namespace:
#|    parser = argparse.ArgumentParser()
#|    parser.add_argument("--train_json", default="../创新点/data/no_prompt_train.json")
#|    parser.add_argument(
#|        "--train_features",
#|        default="../创新点/data/train_ac2_v1.6_cot_merged_features.pkl",
#|    )
#|    parser.add_argument(
#|        "--concept_graph_cache",
#|        default="cache_gpt/concept_graph_train_v3_origin_fields.jsonl",
#|    )
#|    parser.add_argument("--output", default="cache_cwct_v1/warrant_train_v1.jsonl")
#|    parser.add_argument(
#|        "--manifest", default="cache_cwct_v1/warrant_manifest_v1.json"
#|    )
#|    parser.add_argument("--seed", type=int, default=2026)
#|    parser.add_argument("--dev_fraction", type=float, default=0.10)
#|    parser.add_argument("--minimum_similarity", type=float, default=0.05)
#|    return parser.parse_args()
#|
#|
#|if __name__ == "__main__":
#|    build(parse_args())
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: cache_iesfd_stage_11_candidates.py ===
#|"""Cache generated candidates and graph-free token/role codes on either split.
#|
#|Train references are stored only in the train cache, never passed to generation
#|or feature extraction. Test labels/references are not read by this script.
#|"""
#|from __future__ import annotations
#|
#|import json
#|import os
#|import pickle
#|from pathlib import Path
#|
#|from iesfd_stage_11 import SCHEMA, explanation, explanation_token_mask, sha256
#|
#|
#|def load_generator(args, paths, v8_test, torch):
#|    from iesfd_stage_10 import make_iesfd_v10_readout_classes
#|    base = v8_test.base_v7_test.base_v6_test.base_v5_test.base_v4_test.base_test
#|    base.PROJECTOR_SUFFIX = args.source_suffix
#|    warm = torch.load(args.verifier_source, map_location="cpu")
#|    warm = {key: value for key, value in warm.items() if key.startswith("iesfd_v10_")}
#|    if not warm:
#|        raise ValueError("v11 requires the trained v10 token/role encoder")
#|    module = base.load_original_test_module(paths)
#|    _, Controller = make_iesfd_v10_readout_classes(torch, torch.nn)
#|    config = v8_test.config_from_args(args)
#|
#|    class InferenceController(Controller):
#|        def __init__(self, hidden_size, num_tokens=0):
#|            super().__init__(hidden_size, num_tokens, config, training_graph_dropout=False)
#|
#|        def load_state_dict(self, state, strict=True):
#|            if any(key.startswith("iesfd_v10_") for key in state):
#|                raise ValueError("generator source must be clean-v8, not v10")
#|            merged = dict(state)
#|            merged.update(warm)
#|            return super().load_state_dict(merged, strict=strict)
#|
#|    module.MoE_LLM_Projector = InferenceController
#|    tokenizer, model, processor, projector = base.load_model(module, paths, args)
#|    for parameter in model.parameters():
#|        parameter.requires_grad_(False)
#|    for parameter in projector.parameters():
#|        parameter.requires_grad_(False)
#|    model.eval()
#|    projector.eval()
#|    return module, tokenizer, model, processor, projector
#|
#|
#|def prepare_prompt(module, tokenizer, model, processor, image_path, question, device):
#|    torch = module.torch
#|    clean = question.replace("<image>", "").strip()
#|    image_token = module.DEFAULT_IMAGE_TOKEN
#|    if model.config.mm_use_im_start_end:
#|        image_token = module.DEFAULT_IM_START_TOKEN + image_token + module.DEFAULT_IM_END_TOKEN
#|    conv = module.conv_templates["vicuna_v1"].copy()
#|    conv.append_message(conv.roles[0], image_token + "\n" + clean)
#|    conv.append_message(conv.roles[1], None)
#|    ids = module.tokenizer_image_token(conv.get_prompt(), tokenizer, module.IMAGE_TOKEN_INDEX,
#|                                       return_tensors="pt").unsqueeze(0).to(device)
#|    images, sizes = module.process_image_pad(image_path, processor, device, dtype=torch.bfloat16)
#|    prepare = getattr(model, "prepare_inputs_labels_for_multimodal", None)
#|    if prepare is None:
#|        prepare = getattr(model.model, "prepare_inputs_labels_for_multimodal")
#|    result = prepare(input_ids=ids, position_ids=None, attention_mask=torch.ones_like(ids),
#|                     past_key_values=None, labels=None, images=images, image_sizes=sizes)
#|    if isinstance(result, dict):
#|        embeds, mask = result.get("inputs_embeds"), result.get("attention_mask")
#|    else:
#|        mask, embeds = (result[2], result[4]) if len(result) == 6 else (result[1], result[3])
#|    if embeds is None:
#|        raise RuntimeError("no multimodal prompt embeddings")
#|    if mask is None:
#|        mask = torch.ones(embeds.shape[:2], device=device, dtype=torch.long)
#|    stop = conv.sep if conv.sep_style != module.SeparatorStyle.TWO else conv.sep2
#|    return embeds.to(torch.bfloat16), mask.long(), stop
#|
#|
#|def encode_candidates(module, tokenizer, model, projector, embeds, mask, texts):
#|    """One canonical post-token, special-token-free path for both splits.
#|
#|    Score one candidate at a time to bound 7B logits/hidden-state memory. The
#|    input sequence has no synthetic generation BOS after the actual prompt.
#|    """
#|    torch = module.torch
#|    candidates = []
#|    readout = projector.semantic_readout
#|    for text in texts:
#|        ids = tokenizer(text, add_special_tokens=False, return_tensors="pt").input_ids.to(embeds.device)
#|        try:
#|            body = explanation_token_mask(torch, ids[0], tokenizer)
#|        except ValueError:
#|            # Preserve a malformed original output as baseline, but never use
#|            # it to train the ranker or silently replace its verdict.
#|            candidates.append({'text': text, 'label': module.parse_label(text),
#|                               'tokens': torch.zeros(1,128,dtype=torch.float16),
#|                               'v10_score': 0.0, 'scorable': False})
#|            continue
#|        candidate_embeds = model.get_input_embeddings()(ids)
#|        joint = torch.cat((embeds.to(candidate_embeds.dtype), candidate_embeds), dim=1)
#|        joint_mask = torch.cat((mask, torch.ones_like(ids)), dim=1)
#|        scale = torch.ones((*joint.shape[:2], 1), device=embeds.device)
#|        # Reproduce the generation-time final-norm scaling: prompt pass is
#|        # verdict-scaled, then the first label_count-1 generated-token states.
#|        scale[:, :embeds.size(1) + max(0, projector.config.label_token_count-1)] = projector.config.label_readout_scale
#|        captured = []
#|        from rgc_semantic_readout import find_final_decoder_norm
#|        _, norm = find_final_decoder_norm(model)
#|        handle = norm.register_forward_hook(lambda _m, _i, output: captured.append(output))
#|        readout.reset_generation()
#|        readout.set_token_scale(scale)
#|        try:
#|            output = model(inputs_embeds=joint, attention_mask=joint_mask,
#|                           use_cache=False, return_dict=True)
#|            hidden = captured[-1][:, -ids.size(1):, :]
#|            score, _ = projector.score_evidence_candidates(hidden, body[None, :])
#|            codes = torch.nn.functional.normalize(projector.iesfd_v10_hidden(hidden.float()), dim=-1)
#|            candidates.append({"text": text, "label": module.parse_label(text),
#|                               "tokens": codes[0, body].detach().half().cpu(),
#|                               "v10_score": float(score.item()), 'scorable': True})
#|            del output, hidden, codes
#|        finally:
#|            handle.remove()
#|            readout.reset_generation()
#|    roles = torch.nn.functional.normalize(projector.iesfd_v10_role(projector._iesfd_v10_roles.float()), dim=-1)
#|    return candidates, roles[0].detach().half().cpu()
#|
#|
#|def main():
#|    # Keep the generator source namespace independent of v10/v11 outputs.
#|    os.environ["RGC_SR_V8_CKPT_NAME"] = os.environ.get("IESFD_SOURCE_ROOT", "checkpoints_llava_claim_rgc_semantic_readout_v8")
#|    os.environ["RGC_SR_V8_PROJECTOR_SUFFIX"] = os.environ.get("IESFD_SOURCE_SUFFIX", "_claim_rgc_semantic_readout_v8")
#|    import torch
#|    import test_llava_claim_rgc_semantic_readout_stage_8 as v8_test
#|    from paths_paper2 import Paper2Paths
#|    from concept_graph_integration import require_concept_graph_cache
#|    from rgc_semantic_readout import load_graph_semantic_text_map, safe_token_embeddings, tokenize_graph_semantic_text
#|
#|    parser = v8_test.build_parser()
#|    parser.set_defaults(epoch=1, num_tokens=0)
#|    parser.add_argument("--split", choices=("train", "test"), required=True)
#|    parser.add_argument("--cache-dir", required=True)
#|    parser.add_argument("--candidate-beams", type=int, default=5)
#|    parser.add_argument("--verifier-source", required=True)
#|    parser.add_argument("--source-suffix", default=os.environ["RGC_SR_V8_PROJECTOR_SUFFIX"])
#|    args = parser.parse_args()
#|    if args.candidate_beams < 2 or args.num_tokens != 0:
#|        raise ValueError("requires >=2 candidate beams and no graph prompt tokens")
#|    paths = Paper2Paths.from_env()
#|    torch.manual_seed(2026)
#|    source_json = paths.train_json if args.split == "train" else paths.test_json
#|    source_features = paths.train_features if args.split == "train" else paths.test_features
#|    graph_path = paths.resolve_output_path(args.concept_graph_cache or (
#|        paths.train_concept_graph_cache if args.split == "train" else paths.test_concept_graph_cache))
#|    data = json.loads(source_json.read_text(encoding="utf-8"))
#|    if len({str(row['id']) for row in data}) != len(data):
#|        raise ValueError("duplicate source IDs")
#|    if getattr(args, 'max_samples', None):
#|        raise ValueError("v11 full-cache protocol does not permit --max_samples")
#|    proj_path = paths.checkpoint_dir / f"proj_epoch_{args.epoch}{args.source_suffix}.pth"
#|    lora = paths.checkpoint_dir / f"lora_epoch_{args.epoch}{args.source_suffix}"
#|    adapters = sorted(lora.glob("adapter_model.*"))
#|    if not adapters:
#|        raise FileNotFoundError("missing clean-v8 adapter")
#|    manifest = {"schema": SCHEMA, "split": args.split, "records": len(data),
#|                "source_json_sha256": sha256(source_json), "features_sha256": sha256(source_features),
#|                "graph_sha256": sha256(graph_path), "source_projector_sha256": sha256(proj_path),
#|                "source_lora_sha256": {p.name: sha256(p) for p in adapters},
#|                "encoder_sha256": sha256(args.verifier_source),
#|                "candidate_beams": args.candidate_beams, "baseline": "original_get_response_beam3",
#|                "base_model": str(paths.llm_path), "config": vars(v8_test.config_from_args(args)),
#|                "feature_protocol": "v11_post_token_shared_no_synthetic_bos",
#|                "extractor_sha256": sha256(__file__), "core_sha256": sha256(Path(__file__).with_name('iesfd_stage_11.py'))}
#|    manifest = json.loads(json.dumps(manifest))
#|    directory = Path(args.cache_dir)
#|    directory.mkdir(parents=True, exist_ok=True)
#|    manifest_path = directory / "manifest.json"
#|    if manifest_path.exists():
#|        if json.loads(manifest_path.read_text(encoding="utf-8")) != manifest:
#|            raise ValueError("stale candidate cache; use a new --cache-dir")
#|    else:
#|        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
#|    if (directory / 'complete.json').exists():
#|        from iesfd_stage_11 import read_manifest
#|        read_manifest(directory, args.split)
#|        if len(list(directory.glob('item_*.pt'))) == len(data):
#|            print(f"[iesfd-v11-cache] complete cache retained: {directory}")
#|            return
#|        raise ValueError("completed cache is missing item files")
#|    _, graph_features, _ = require_concept_graph_cache(graph_path, split=args.split, allow_phenomenon_fallback=False)
#|    semantics = load_graph_semantic_text_map(graph_path, allow_phenomenon_fallback=False)
#|    with source_features.open('rb') as handle:
#|        features = pickle.load(handle)
#|    module, tokenizer, model, processor, projector = load_generator(args, paths, v8_test, torch)
#|    from tqdm import tqdm
#|    for index, row in enumerate(tqdm(data, desc=f"v11 {args.split} candidates")):
#|        item_path = directory / f"item_{index:05d}.pt"
#|        if item_path.exists():
#|            saved = torch.load(item_path, map_location='cpu')
#|            if str(saved['id']) != str(row['id']) or saved['split'] != args.split:
#|                raise ValueError("candidate resume ID mismatch")
#|            continue
#|        sample = features[row['id']]
#|        question = row['conversations'][0]['value']
#|        image_path = str(paths.image_folder / row['image'])
#|        ids, semantic_mask = tokenize_graph_semantic_text(tokenizer, semantics.get(row['id'], ''), args.semantic_max_length)
#|        with torch.inference_mode():
#|            semantic_embeddings, semantic_mask = safe_token_embeddings(
#|                model.get_input_embeddings(), ids[None].to(args.device), semantic_mask[None].to(args.device),
#|                vocab_size=model.config.vocab_size)
#|            projector(sample['E_image'][None].to(args.device), sample['E_text'][None].to(args.device),
#|                      sample['E_desc'][None].to(args.device), graph_feature=graph_features[row['id']][None].to(args.device),
#|                      semantic_token_embeddings=semantic_embeddings, semantic_mask=semantic_mask)
#|            baseline = module.get_response(image_path, question, tokenizer, model, processor, projector, None, args.device)
#|            embeds, mask, stop = prepare_prompt(module, tokenizer, model, processor, image_path, question, args.device)
#|            projector.semantic_readout.reset_generation()
#|            generated = module.GenerationMixin.generate(model, inputs_embeds=embeds, attention_mask=mask,
#|                do_sample=False, temperature=0, num_beams=args.candidate_beams,
#|                num_return_sequences=args.candidate_beams, pad_token_id=tokenizer.pad_token_id,
#|                max_new_tokens=256, use_cache=True, repetition_penalty=1.02, early_stopping=True)
#|            texts = [baseline]
#|            label = module.parse_label(baseline)
#|            for text in tokenizer.batch_decode(generated, skip_special_tokens=True):
#|                text = text.strip()
#|                if stop and text.endswith(stop):
#|                    text = text[:-len(stop)].strip()
#|                if text not in texts and explanation(text) and module.parse_label(text) == label:
#|                    texts.append(text)
#|            candidates, roles = encode_candidates(module, tokenizer, model, projector, embeds, mask, texts)
#|        item = {'id': row['id'], 'split': args.split, 'roles': roles, 'candidates': candidates}
#|        if args.split == 'train':
#|            answers = [c['value'] for c in row['conversations'] if c['from'] in ('gpt', 'assistant')]
#|            if len(answers) != 1 or not explanation(answers[0]):
#|                raise ValueError('missing/ambiguous TRAIN reference')
#|            item['reference'] = explanation(answers[0])
#|            item['label_true'] = module.parse_label(answers[0])
#|        temp = item_path.with_suffix('.tmp')
#|        torch.save(item, temp)
#|        temp.replace(item_path)
#|        if (index+1) % 50 == 0:
#|            print(f"[iesfd-v11-cache] split={args.split} completed={index+1}/{len(data)}", flush=True)
#|    (directory/'complete.json').write_text(json.dumps({'records': len(data), 'manifest_sha256': sha256(manifest_path)}), encoding='utf-8')
#|    print(f"[iesfd-v11-cache] complete split={args.split} records={len(data)}")
#|
#|
#|if __name__ == '__main__':
#|    main()
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: compute_paper2_metrics.py ===
#|"""Path wrapper around the original RIFT metric script.
#|
#|Important: this file intentionally does not reimplement F1, BERTScore, BLEURT,
#|dataset grouping, thresholding, or cache behavior. It changes only the working
#|directory and command-line defaults, then runs the original
#|``compute_metrics_bscore_bleurt.py`` as ``__main__``.
#|"""
#|
#|from __future__ import annotations
#|
#|import argparse
#|import os
#|import runpy
#|import sys
#|from pathlib import Path
#|
#|from paths_paper2 import Paper2Paths
#|
#|
#|def main() -> None:
#|    parser = argparse.ArgumentParser()
#|    parser.add_argument("--pred", type=str, default=None)
#|    parser.add_argument("--true", type=str, default=None)
#|    parser.add_argument("--output_dir", type=str, default="f1_res_v1.6")
#|    parser.add_argument("--dummy_bleurt", action="store_true")
#|    parser.add_argument("--freq_words_file", type=str, default=None)
#|    args = parser.parse_args()
#|
#|    paths = Paper2Paths.from_env()
#|    paths.ensure_output_dirs()
#|    pred = args.pred or str(Path("result") / "paper2_care_rift_epoch4" / "result.csv")
#|    true = args.true or str(paths.default_true_csv)
#|
#|    sys.path.insert(0, str(paths.orig_root))
#|    os.chdir(paths.output_root)
#|    argv = [
#|        str(paths.original_metrics_script),
#|        "--pred",
#|        pred,
#|        "--true",
#|        true,
#|        "--output_dir",
#|        args.output_dir,
#|    ]
#|    if args.dummy_bleurt:
#|        argv.append("--dummy_bleurt")
#|    if args.freq_words_file:
#|        argv.extend(["--freq_words_file", args.freq_words_file])
#|    sys.argv = argv
#|    print("[paper2] running original metric script without changing metric logic")
#|    runpy.run_path(str(paths.original_metrics_script), run_name="__main__")
#|
#|
#|if __name__ == "__main__":
#|    main()
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: concept_graph_integration.py ===
#|"""Concept-graph feature integration for paper-2 CARE-RIFT.
#|
#|The second paper replaces the first paper's MoE soft-prompt fusion with a
#|concept-graph prompt projector. The original RAG/rationale branch can remain as
#|an external-knowledge component, but the primary soft prompt is now generated
#|from graph-grounded multimodal relation features rather than MoE experts.
#|"""
#|
#|from __future__ import annotations
#|
#|import json
#|import math
#|from pathlib import Path
#|from typing import Any
#|
#|
#|GRAPH_FEATURE_DIM = 20
#|
#|KNOWN_PHENOMENA = {"idiom", "metaphor", "simile", "sarcasm", "humor", "idiom_like"}
#|SUPPORT_EDGE_TYPES = {"lexical_overlap", "visual_support", "anchor_to_visual"}
#|FIGURATIVE_EDGE_TYPES = {"figurative_gap", "contrast"}
#|MAPPING_FEATURE_SCALE = 0.25
#|MAPPING_TEXT_MAX_LENGTH = 48
#|
#|
#|def _safe_len(value: Any) -> float:
#|    return float(len(value)) if value is not None else 0.0
#|
#|
#|def _log_count(value: float) -> float:
#|    return math.log1p(max(0.0, value)) / 4.0
#|
#|
#|def _text_len(text: str) -> float:
#|    return min(len(str(text).split()) / 80.0, 1.0)
#|
#|
#|def _as_list(value: Any) -> list[Any]:
#|    return value if isinstance(value, list) else []
#|
#|
#|def _clean_text(value: Any) -> str:
#|    return str(value or "").strip().lower()
#|
#|
#|def _tokens(value: Any) -> set[str]:
#|    text = _clean_text(value)
#|    for char in ",.;:!?()[]{}\"'`/\\|@#$%^&*_+=~":
#|        text = text.replace(char, " ")
#|    return {token for token in text.replace("-", " ").split() if token}
#|
#|
#|def _phrase_or_token_overlap(left: Any, right_values: list[Any] | set[str]) -> bool:
#|    left_text = _clean_text(left)
#|    if not left_text:
#|        return False
#|    if isinstance(right_values, set):
#|        right_texts = right_values
#|    else:
#|        right_texts = {_clean_text(item) for item in right_values if _clean_text(item)}
#|    if left_text in right_texts:
#|        return True
#|    if any(left_text in text or text in left_text for text in right_texts):
#|        return True
#|    left_tokens = _tokens(left_text)
#|    right_tokens = {
#|        token
#|        for text in right_texts
#|        for token in _tokens(text)
#|    }
#|    return bool(left_tokens and left_tokens.intersection(right_tokens))
#|
#|
#|def _relation_matches_phenomenon(relation: str, phenomenon: str) -> bool:
#|    relation = _clean_text(relation)
#|    phenomenon = _clean_text(phenomenon)
#|    if not relation or not phenomenon:
#|        return False
#|    if phenomenon == "idiom_like":
#|        phenomenon = "idiom"
#|    return phenomenon in relation or relation in phenomenon
#|
#|
#|def _select_record_phenomenon(
#|    record: dict[str, Any],
#|    *,
#|    allow_phenomenon_fallback: bool = True,
#|) -> str:
#|    inferred = _clean_text(record.get("inferred_phenomenon", ""))
#|    if inferred or not allow_phenomenon_fallback:
#|        return inferred
#|    return _clean_text(record.get("phenomenon", ""))
#|
#|
#|def extract_trusted_mapping_text(
#|    record: dict[str, Any],
#|    *,
#|    allow_phenomenon_fallback: bool = True,
#|) -> str:
#|    anchors = _as_list(record.get("figurative_anchors", []))
#|    claim_nodes = _as_list(record.get("claim_nodes", []))
#|    mappings = _as_list(record.get("concept_mappings", []))
#|    phenomenon = _select_record_phenomenon(
#|        record,
#|        allow_phenomenon_fallback=allow_phenomenon_fallback,
#|    )
#|    anchor_set = {_clean_text(anchor) for anchor in anchors if _clean_text(anchor)}
#|    claim_set = {_clean_text(node) for node in claim_nodes if _clean_text(node)}
#|
#|    texts = []
#|    for item in mappings:
#|        if not isinstance(item, dict):
#|            continue
#|        source = _clean_text(item.get("source", ""))
#|        target = _clean_text(item.get("target", ""))
#|        relation = _clean_text(item.get("relation", ""))
#|        meaning = _clean_text(item.get("meaning", ""))
#|        source_supported = (
#|            _phrase_or_token_overlap(source, anchor_set)
#|            or _phrase_or_token_overlap(source, claim_set)
#|        )
#|        relation_supported = (
#|            _relation_matches_phenomenon(relation, phenomenon)
#|            or (not phenomenon and relation in KNOWN_PHENOMENA)
#|        )
#|        if not source_supported or not relation_supported or not (target or meaning):
#|            continue
#|        parts = []
#|        if relation:
#|            parts.append(f"relation: {relation}")
#|        if target:
#|            parts.append(f"concept: {target}")
#|        if meaning and meaning != target:
#|            parts.append(f"meaning: {meaning}")
#|        if parts:
#|            texts.append(". ".join(parts))
#|    return " ".join(texts)
#|
#|
#|def encode_graph_record(
#|    record: dict[str, Any],
#|    *,
#|    allow_phenomenon_fallback: bool = True,
#|) -> list[float]:
#|    visual_nodes = _as_list(record.get("visual_nodes", []))
#|    claim_nodes = _as_list(record.get("claim_nodes", []))
#|    anchors = _as_list(record.get("figurative_anchors", []))
#|    mappings = _as_list(record.get("concept_mappings", []))
#|    edges = _as_list(record.get("evidence_edges", []))
#|    phenomenon = _select_record_phenomenon(
#|        record,
#|        allow_phenomenon_fallback=allow_phenomenon_fallback,
#|    )
#|    dataset = str(record.get("dataset", "") or "").lower()
#|
#|    visual_set = {_clean_text(item) for item in visual_nodes if _clean_text(item)}
#|    claim_set = {_clean_text(item) for item in claim_nodes if _clean_text(item)}
#|    anchor_set = {_clean_text(anchor) for anchor in anchors if _clean_text(anchor)}
#|    anchor_tokens = {
#|        token
#|        for anchor in anchors
#|        for token in _tokens(anchor)
#|        if token
#|    }
#|    overlap = len(visual_set.intersection(claim_set))
#|    denom = max(1, len(visual_set.union(claim_set)))
#|    anchor_visual_overlap = len(anchor_tokens.intersection(visual_set)) / max(1, len(anchor_tokens))
#|    claim_visual_overlap = overlap / max(1, len(claim_set))
#|
#|    trusted_mappings = []
#|    for item in mappings:
#|        if not isinstance(item, dict):
#|            continue
#|        source = _clean_text(item.get("source", ""))
#|        target = _clean_text(item.get("target", ""))
#|        relation = _clean_text(item.get("relation", ""))
#|        meaning = _clean_text(item.get("meaning", ""))
#|        source_supported = (
#|            _phrase_or_token_overlap(source, anchor_set)
#|            or _phrase_or_token_overlap(source, claim_set)
#|        )
#|        relation_supported = (
#|            _relation_matches_phenomenon(relation, phenomenon)
#|            or (not phenomenon and relation in KNOWN_PHENOMENA)
#|        )
#|        semantic_payload = bool(target or meaning)
#|        visual_supported = _phrase_or_token_overlap(target, visual_set)
#|        if source_supported and relation_supported and (semantic_payload or visual_supported):
#|            trusted_mappings.append(item)
#|
#|    trusted_edges = []
#|    for edge in edges:
#|        if not isinstance(edge, dict):
#|            continue
#|        edge_type = _clean_text(edge.get("type", ""))
#|        source = _clean_text(edge.get("source", ""))
#|        target = _clean_text(edge.get("target", ""))
#|        source_supported = (
#|            _phrase_or_token_overlap(source, anchor_set)
#|            or _phrase_or_token_overlap(source, claim_set)
#|        )
#|        target_supported = _phrase_or_token_overlap(target, visual_set)
#|        direct_support = edge_type in SUPPORT_EDGE_TYPES and source_supported and target_supported
#|        figurative_support = edge_type in FIGURATIVE_EDGE_TYPES and source_supported
#|        if direct_support or figurative_support:
#|            trusted_edges.append(edge)
#|
#|    trusted_mapping_relations = {
#|        _clean_text(item.get("relation", ""))
#|        for item in trusted_mappings
#|        if isinstance(item, dict)
#|    }
#|    trusted_mapping_sources = {
#|        _clean_text(item.get("source", ""))
#|        for item in trusted_mappings
#|        if isinstance(item, dict)
#|    }
#|    trusted_mapping_targets = {
#|        _clean_text(item.get("target", ""))
#|        for item in trusted_mappings
#|        if isinstance(item, dict)
#|    }
#|    trusted_mapping_has_meaning = any(
#|        _clean_text(item.get("meaning", ""))
#|        for item in trusted_mappings
#|        if isinstance(item, dict)
#|    )
#|    mapping_relation_matches = any(
#|        _relation_matches_phenomenon(relation, phenomenon)
#|        for relation in trusted_mapping_relations
#|    )
#|    mapping_anchor_overlap = len(trusted_mapping_sources.intersection(anchor_set)) / max(1, len(anchor_set))
#|    mapping_target_visual_overlap = len(trusted_mapping_targets.intersection(visual_set)) / max(1, len(trusted_mapping_targets))
#|    trusted_anchor_visual_overlap = anchor_visual_overlap if trusted_edges or trusted_mappings else 0.0
#|    trusted_evidence_density = min(_safe_len(trusted_edges) / max(1.0, _safe_len(anchors)), 1.0)
#|    graph_quality = min(
#|        1.0,
#|        0.35 * min(_safe_len(trusted_mappings), 1.0)
#|        + 0.35 * min(_safe_len(trusted_edges) / 2.0, 1.0)
#|        + 0.15 * (1.0 if mapping_relation_matches else 0.0)
#|        + 0.15 * min(claim_visual_overlap + trusted_anchor_visual_overlap, 1.0),
#|    )
#|
#|    return [
#|        _log_count(_safe_len(visual_nodes)),
#|        _log_count(_safe_len(claim_nodes)),
#|        _log_count(_safe_len(anchors)),
#|        _log_count(_safe_len(trusted_edges)),
#|        overlap / denom,
#|        1.0 if "irfl" in dataset else 0.0,
#|        1.0 if phenomenon == "idiom" else 0.0,
#|        1.0 if phenomenon in {"metaphor", "simile"} else 0.0,
#|        1.0 if phenomenon == "sarcasm" else 0.0,
#|        1.0 if phenomenon == "humor" else 0.0,
#|        trusted_anchor_visual_overlap,
#|        claim_visual_overlap,
#|        1.0 if any(" " in str(anchor).strip() for anchor in anchors) else 0.0,
#|        trusted_evidence_density,
#|        _text_len(record.get("claim", "")),
#|        _text_len(record.get("description", "")),
#|        _log_count(_safe_len(trusted_mappings)) * MAPPING_FEATURE_SCALE,
#|        mapping_anchor_overlap * MAPPING_FEATURE_SCALE,
#|        (1.0 if mapping_relation_matches else 0.0) * MAPPING_FEATURE_SCALE,
#|        max(1.0 if trusted_mapping_has_meaning else 0.0, mapping_target_visual_overlap) * graph_quality * MAPPING_FEATURE_SCALE,
#|    ]
#|
#|
#|def load_graph_feature_map(
#|    cache_path: str | Path | None,
#|    *,
#|    allow_phenomenon_fallback: bool = True,
#|):
#|    torch, _ = _require_torch()
#|    if cache_path is None:
#|        return {}
#|    path = Path(cache_path)
#|    if not path.exists():
#|        return {}
#|    features = {}
#|    with path.open("r", encoding="utf-8") as handle:
#|        for line in handle:
#|            if not line.strip():
#|                continue
#|            record = json.loads(line)
#|            features[record["id"]] = torch.tensor(
#|                encode_graph_record(
#|                    record,
#|                    allow_phenomenon_fallback=allow_phenomenon_fallback,
#|                ),
#|                dtype=torch.float32,
#|            )
#|    return features
#|
#|
#|def load_trusted_mapping_text_map(
#|    cache_path: str | Path | None,
#|    *,
#|    allow_phenomenon_fallback: bool = True,
#|) -> dict[Any, str]:
#|    if cache_path is None:
#|        return {}
#|    path = Path(cache_path)
#|    if not path.exists():
#|        return {}
#|    texts = {}
#|    with path.open("r", encoding="utf-8") as handle:
#|        for line in handle:
#|            if not line.strip():
#|                continue
#|            record = json.loads(line)
#|            text = extract_trusted_mapping_text(
#|                record,
#|                allow_phenomenon_fallback=allow_phenomenon_fallback,
#|            )
#|            if text:
#|                texts[record["id"]] = text
#|    return texts
#|
#|
#|def require_concept_graph_cache(
#|    cache_path: str | Path | None,
#|    *,
#|    split: str,
#|    allow_phenomenon_fallback: bool | None = None,
#|) -> tuple[Path, dict[Any, Any], dict[Any, str]]:
#|    if cache_path is None:
#|        raise FileNotFoundError(f"Missing {split} concept graph cache path")
#|    path = Path(cache_path)
#|    if not path.is_file():
#|        raise FileNotFoundError(f"Missing {split} concept graph cache: {path}")
#|
#|    if allow_phenomenon_fallback is None:
#|        allow_phenomenon_fallback = split.lower() != "test"
#|
#|    graph_features = load_graph_feature_map(
#|        path,
#|        allow_phenomenon_fallback=allow_phenomenon_fallback,
#|    )
#|    mapping_texts = load_trusted_mapping_text_map(
#|        path,
#|        allow_phenomenon_fallback=allow_phenomenon_fallback,
#|    )
#|    if not graph_features:
#|        raise ValueError(f"{split} concept graph cache contains no usable records: {path}")
#|
#|    mapping_rate = len(mapping_texts) / len(graph_features)
#|    print(
#|        f"[paper2-claim-graphprompt] {split} concept graph cache: {path} "
#|        f"(graph_records={len(graph_features)}, trusted_mappings={len(mapping_texts)}, "
#|        f"mapping_rate={mapping_rate:.2%}, "
#|        f"phenomenon_fallback={'enabled' if allow_phenomenon_fallback else 'disabled'})"
#|    )
#|    return path, graph_features, mapping_texts
#|
#|
#|def _require_torch():
#|    try:
#|        import torch
#|        import torch.nn as nn
#|    except ModuleNotFoundError as exc:
#|        raise ModuleNotFoundError("concept_graph_integration requires torch for model integration.") from exc
#|    return torch, nn
#|
#|
#|def _zero_graph(batch_size: int, device):
#|    torch, _ = _require_torch()
#|    return torch.zeros((batch_size, GRAPH_FEATURE_DIM), device=device, dtype=torch.float32)
#|
#|
#|def install_training_graph_integration(module, graph_cache_path: str | Path | None):
#|    """Patch the original train_v45 module with graph-aware dataset/projector/model."""
#|
#|    torch, nn = _require_torch()
#|    BaseDataset = module.HybridDataset if hasattr(module, "HybridDataset") else None
#|    BaseProjector = module.MoE_LLM_Projector
#|    BaseModel = module.Hybrid_MoE_LLaVA_v45 if hasattr(module, "Hybrid_MoE_LLaVA_v45") else None
#|    original_collate = module.collate_fn if hasattr(module, "collate_fn") else None
#|
#|    class GraphAwareProjector(BaseProjector):
#|        def __init__(self, *args, graph_dim: int = GRAPH_FEATURE_DIM, **kwargs):
#|            super().__init__(*args, **kwargs)
#|            self.graph_dim = graph_dim
#|            prompt_input_dim = self.img_proj.out_features * 5 + graph_dim
#|            if hasattr(self, "experts"):
#|                del self.experts
#|            if hasattr(self, "gate"):
#|                del self.gate
#|            self.graph_prompt = nn.Sequential(
#|                nn.Linear(prompt_input_dim, 2048),
#|                nn.LayerNorm(2048),
#|                nn.GELU(),
#|                nn.Linear(2048, self.hidden_size * self.num_tokens),
#|            )
#|            for layer in self.graph_prompt:
#|                if isinstance(layer, nn.Linear):
#|                    nn.init.xavier_uniform_(layer.weight)
#|                    nn.init.zeros_(layer.bias)
#|
#|        def forward(self, e_img, e_txt, e_desc, relation_q=None, labels=None, disable_rag=False, graph_feature=None):
#|            e_img = e_img.float()
#|            e_txt = e_txt.float()
#|            e_desc = e_desc.float()
#|
#|            p_img = self.img_norm(self.img_proj(e_img))
#|            p_txt = self.txt_norm(self.txt_proj(e_txt))
#|            p_desc = self.desc_norm(self.desc_proj(e_desc))
#|            x_full = torch.cat([p_img, p_txt, p_desc], dim=-1)
#|            x_relation = torch.cat([p_img, p_desc, p_txt, torch.abs(p_desc - p_txt), p_desc * p_txt], dim=-1)
#|
#|            if graph_feature is None:
#|                graph_feature = _zero_graph(e_img.size(0), e_img.device)
#|            graph_feature = graph_feature.to(e_img.device).float()
#|            graph_input = torch.cat([x_relation, graph_feature], dim=-1)
#|            fused = self.graph_prompt(graph_input).view(-1, self.num_tokens, self.hidden_size)
#|            graph_prompt_norm = fused.detach().float().norm(dim=-1).mean()
#|            weights = torch.zeros((e_img.size(0), 3), device=e_img.device)
#|
#|            if disable_rag:
#|                rag_prompt = torch.zeros((e_img.size(0), self.rag_tokens, self.hidden_size), device=e_img.device)
#|                rag_context = {
#|                    "rag_weight": torch.zeros((e_img.size(0), 1), device=e_img.device),
#|                    "confidence": torch.zeros((e_img.size(0), 1), device=e_img.device),
#|                    "query_loss": torch.tensor(0.0, device=e_img.device),
#|                    "label_loss": torch.tensor(0.0, device=e_img.device),
#|                    "label_prob": torch.zeros((e_img.size(0), 1), device=e_img.device),
#|                    "router_prob": torch.zeros((e_img.size(0), 1), device=e_img.device),
#|                    "dual_mix": torch.zeros((e_img.size(0), 1), device=e_img.device),
#|                    "branch_gap": torch.zeros((e_img.size(0), 1), device=e_img.device),
#|                    "global_confidence": torch.zeros((e_img.size(0), 1), device=e_img.device),
#|                    "pos_confidence": torch.zeros((e_img.size(0), 1), device=e_img.device),
#|                    "neg_confidence": torch.zeros((e_img.size(0), 1), device=e_img.device),
#|                    "relation_mix": torch.sigmoid(self.flute_retriever.relation_query_mix_logit).detach(),
#|                    "graph_prompt_norm": graph_prompt_norm,
#|                }
#|            else:
#|                rag_prompt, rag_context = self.flute_retriever(
#|                    x_relation,
#|                    relation_q=relation_q,
#|                    labels=labels,
#|                )
#|                rag_context["graph_prompt_norm"] = graph_prompt_norm
#|
#|            fused = self.output_norm(fused) * self.projector_scale
#|            prompt_tokens = torch.cat([fused, rag_prompt], dim=1)
#|            balance_loss = torch.tensor(0.0, device=e_img.device)
#|            return prompt_tokens, balance_loss, weights, rag_context
#|
#|    module.MoE_LLM_Projector = GraphAwareProjector
#|
#|    if BaseDataset is not None:
#|        class GraphAwareDataset(BaseDataset):
#|            def __init__(self, *args, concept_graph_path: str | Path | None = graph_cache_path, **kwargs):
#|                super().__init__(*args, **kwargs)
#|                self.graph_features = load_graph_feature_map(concept_graph_path)
#|
#|            def __getitem__(self, idx):
#|                item = super().__getitem__(idx)
#|                sample_id = self.samples[idx]["id"]
#|                item["graph_feature"] = self.graph_features.get(
#|                    sample_id,
#|                    torch.zeros(GRAPH_FEATURE_DIM, dtype=torch.float32),
#|                )
#|                return item
#|
#|        module.HybridDataset = GraphAwareDataset
#|
#|    if original_collate is not None:
#|        def graph_collate_fn(batch):
#|            output = original_collate(batch)
#|            output["graph_feature"] = torch.stack([item["graph_feature"] for item in batch])
#|            return output
#|
#|        module.collate_fn = graph_collate_fn
#|
#|    if BaseModel is not None:
#|        class GraphAwareHybridModel(BaseModel):
#|            def forward(
#|                self,
#|                images,
#|                image_sizes,
#|                e_img,
#|                e_txt,
#|                e_desc,
#|                relation_q,
#|                graph_feature,
#|                input_ids,
#|                attention_mask,
#|                labels,
#|                cf_labels,
#|                alpha=None,
#|            ):
#|                alpha = module.CF_LOSS_WEIGHT if alpha is None else alpha
#|                moe_embeds, balance_loss, gate_weights, rag_context = self.projector(
#|                    e_img,
#|                    e_txt,
#|                    e_desc,
#|                    relation_q=relation_q,
#|                    labels=cf_labels,
#|                    graph_feature=graph_feature,
#|                )
#|                moe_embeds = moe_embeds.to(dtype=torch.bfloat16)
#|                batch_size = e_img.size(0)
#|
#|                with torch.no_grad():
#|                    cf_embeds, _, _, _ = self.projector(
#|                        torch.zeros_like(e_img),
#|                        e_txt,
#|                        e_desc,
#|                        relation_q=None,
#|                        labels=None,
#|                        disable_rag=True,
#|                        graph_feature=torch.zeros_like(graph_feature),
#|                    )
#|                contrastive_loss = module.safe_contrastive_loss(moe_embeds, cf_embeds.detach(), cf_labels)
#|
#|                base_model = self.llm.base_model.model if hasattr(self.llm, "base_model") else self.llm.model
#|                prepared_out = base_model.prepare_inputs_labels_for_multimodal(
#|                    input_ids=input_ids,
#|                    position_ids=None,
#|                    attention_mask=attention_mask,
#|                    past_key_values=None,
#|                    labels=labels,
#|                    images=images,
#|                    image_sizes=image_sizes,
#|                )
#|                llava_mask, llava_embeds, llava_labels = module.unpack_prepared(prepared_out, self.hidden_size)
#|
#|                if isinstance(llava_embeds, list):
#|                    llava_embeds = torch.cat(llava_embeds, dim=0)
#|                if isinstance(llava_mask, list):
#|                    llava_mask = torch.cat(llava_mask, dim=0)
#|                if isinstance(llava_labels, list):
#|                    llava_labels = torch.cat(llava_labels, dim=0)
#|
#|                if llava_embeds is None:
#|                    embed_layer = (
#|                        base_model.get_input_embeddings()
#|                        if hasattr(base_model, "get_input_embeddings")
#|                        else base_model.get_model().embed_tokens
#|                    )
#|                    safe_ids = input_ids.clone().clamp(min=0, max=self.vocab_size - 1)
#|                    llava_embeds = embed_layer(safe_ids)
#|
#|                if llava_embeds.dim() == 2:
#|                    llava_embeds = llava_embeds.unsqueeze(0)
#|                llava_seq = llava_embeds.size(1)
#|
#|                if llava_mask is None:
#|                    llava_mask = torch.ones((batch_size, llava_seq), device=e_img.device, dtype=torch.long)
#|                else:
#|                    llava_mask = llava_mask.reshape(-1)[: batch_size * llava_seq].reshape(batch_size, llava_seq)
#|
#|                if llava_labels is None:
#|                    llava_labels = torch.full((batch_size, llava_seq), module.IGNORE_INDEX, device=e_img.device, dtype=torch.long)
#|                else:
#|                    llava_labels = llava_labels.reshape(-1)[: batch_size * llava_seq].reshape(batch_size, llava_seq)
#|
#|                inputs_embeds = torch.cat([moe_embeds, llava_embeds.to(torch.bfloat16)], dim=1)
#|                inputs_embeds = inputs_embeds.nan_to_num(nan=0.0, posinf=100.0, neginf=-100.0).clamp(-100.0, 100.0)
#|
#|                prompt_len = moe_embeds.size(1)
#|                p_mask = torch.ones((batch_size, prompt_len), device=e_img.device, dtype=torch.long)
#|                p_lab = torch.full((batch_size, prompt_len), module.IGNORE_INDEX, device=e_img.device, dtype=torch.long)
#|                final_mask = (torch.cat([p_mask, llava_mask.long()], dim=1) > 0).long()
#|                final_labels = torch.cat([p_lab, llava_labels.long()], dim=1)
#|
#|                limit = self.max_seq_len - 8
#|                if inputs_embeds.size(1) > limit:
#|                    keep_tail = limit - prompt_len
#|                    inputs_embeds = torch.cat(
#|                        [inputs_embeds[:, :prompt_len, :], inputs_embeds[:, prompt_len:, :][:, -keep_tail:, :]],
#|                        dim=1,
#|                    )
#|                    final_mask = torch.cat([final_mask[:, :prompt_len], final_mask[:, prompt_len:][:, -keep_tail:]], dim=1)
#|                    final_labels = torch.cat([final_labels[:, :prompt_len], final_labels[:, prompt_len:][:, -keep_tail:]], dim=1)
#|
#|                rem = inputs_embeds.size(1) % 8
#|                if rem:
#|                    pad = 8 - rem
#|                    inputs_embeds = module.F.pad(inputs_embeds, (0, 0, 0, pad))
#|                    final_mask = module.F.pad(final_mask, (0, pad), value=0)
#|                    final_labels = module.F.pad(final_labels, (0, pad), value=module.IGNORE_INDEX)
#|
#|                outputs = self.llm(
#|                    inputs_embeds=inputs_embeds.to(torch.bfloat16).contiguous(),
#|                    attention_mask=final_mask.contiguous(),
#|                    labels=final_labels.contiguous(),
#|                )
#|                lm_loss = outputs.loss
#|                if torch.isnan(lm_loss) or torch.isinf(lm_loss):
#|                    lm_loss = torch.tensor(0.0, device=e_img.device, requires_grad=True)
#|                if torch.isnan(contrastive_loss) or torch.isinf(contrastive_loss):
#|                    contrastive_loss = torch.tensor(0.0, device=e_img.device)
#|
#|                query_loss = rag_context["query_loss"]
#|                label_loss = rag_context["label_loss"]
#|                total = (
#|                    lm_loss
#|                    + alpha * contrastive_loss
#|                    + module.BALANCE_LOSS_WEIGHT * balance_loss.to(lm_loss.device)
#|                    + module.QUERY_LOSS_WEIGHT * query_loss.to(lm_loss.device)
#|                    + module.LABEL_LOSS_WEIGHT * label_loss.to(lm_loss.device)
#|                )
#|                return total, lm_loss, contrastive_loss, query_loss, label_loss, gate_weights, rag_context
#|
#|        module.Hybrid_MoE_LLaVA_v45 = GraphAwareHybridModel
#|
#|    return module
#|
#|
#|def install_inference_graph_integration(module, graph_cache_path: str | Path | None):
#|    """Patch the original test_v45 module with graph-aware projector inference."""
#|
#|    torch, nn = _require_torch()
#|    BaseProjector = module.MoE_LLM_Projector
#|    graph_features = load_graph_feature_map(graph_cache_path)
#|
#|    class GraphAwareInferenceProjector(BaseProjector):
#|        def __init__(self, *args, graph_dim: int = GRAPH_FEATURE_DIM, **kwargs):
#|            super().__init__(*args, **kwargs)
#|            self.graph_dim = graph_dim
#|            prompt_input_dim = self.img_proj.out_features * 5 + graph_dim
#|            if hasattr(self, "experts"):
#|                del self.experts
#|            if hasattr(self, "gate"):
#|                del self.gate
#|            self.graph_prompt = nn.Sequential(
#|                nn.Linear(prompt_input_dim, 2048),
#|                nn.LayerNorm(2048),
#|                nn.GELU(),
#|                nn.Linear(2048, self.hidden_size * self.num_tokens),
#|            )
#|            for layer in self.graph_prompt:
#|                if isinstance(layer, nn.Linear):
#|                    nn.init.xavier_uniform_(layer.weight)
#|                    nn.init.zeros_(layer.bias)
#|            self._paper2_current_graph_feature = None
#|
#|        def forward(self, e_img, e_txt, e_desc, relation_q=None, disable_rag=False, graph_feature=None):
#|            e_img = e_img.float()
#|            e_txt = e_txt.float()
#|            e_desc = e_desc.float()
#|
#|            p_img = self.img_norm(self.img_proj(e_img))
#|            p_txt = self.txt_norm(self.txt_proj(e_txt))
#|            p_desc = self.desc_norm(self.desc_proj(e_desc))
#|            x_full = torch.cat([p_img, p_txt, p_desc], dim=-1)
#|            x_relation = torch.cat([p_img, p_desc, p_txt, torch.abs(p_desc - p_txt), p_desc * p_txt], dim=-1)
#|
#|            if graph_feature is None:
#|                graph_feature = self._paper2_current_graph_feature
#|            if graph_feature is None:
#|                graph_feature = _zero_graph(e_img.size(0), e_img.device)
#|            if graph_feature.dim() == 1:
#|                graph_feature = graph_feature.unsqueeze(0)
#|            graph_feature = graph_feature.to(e_img.device).float()
#|
#|            graph_input = torch.cat([x_relation, graph_feature], dim=-1)
#|            fused = self.graph_prompt(graph_input).view(-1, self.num_tokens, self.hidden_size)
#|            graph_prompt_norm = fused.detach().float().norm(dim=-1).mean()
#|            weights = torch.zeros((e_img.size(0), 3), device=e_img.device)
#|
#|            if disable_rag:
#|                rag_context = {
#|                    "rag_weight": torch.zeros((e_img.size(0), 1), device=e_img.device),
#|                    "confidence": torch.zeros((e_img.size(0), 1), device=e_img.device),
#|                    "global_topk_indices": torch.empty((e_img.size(0), 0), device=e_img.device, dtype=torch.long),
#|                    "global_topk_scores": torch.empty((e_img.size(0), 0), device=e_img.device),
#|                    "global_valid_mask": torch.empty((e_img.size(0), 0), device=e_img.device),
#|                    "pos_topk_indices": torch.empty((e_img.size(0), 0), device=e_img.device, dtype=torch.long),
#|                    "neg_topk_indices": torch.empty((e_img.size(0), 0), device=e_img.device, dtype=torch.long),
#|                    "pos_topk_scores": torch.empty((e_img.size(0), 0), device=e_img.device),
#|                    "neg_topk_scores": torch.empty((e_img.size(0), 0), device=e_img.device),
#|                    "pos_valid_mask": torch.empty((e_img.size(0), 0), device=e_img.device),
#|                    "neg_valid_mask": torch.empty((e_img.size(0), 0), device=e_img.device),
#|                    "label_prob": torch.zeros((e_img.size(0), 1), device=e_img.device),
#|                    "router_prob": torch.zeros((e_img.size(0), 1), device=e_img.device),
#|                    "dual_mix": torch.zeros((e_img.size(0), 1), device=e_img.device),
#|                    "branch_gap": torch.zeros((e_img.size(0), 1), device=e_img.device),
#|                    "global_confidence": torch.zeros((e_img.size(0), 1), device=e_img.device),
#|                    "pos_confidence": torch.zeros((e_img.size(0), 1), device=e_img.device),
#|                    "neg_confidence": torch.zeros((e_img.size(0), 1), device=e_img.device),
#|                    "relation_mix": torch.sigmoid(self.flute_retriever.relation_query_mix_logit).detach(),
#|                    "graph_prompt_norm": graph_prompt_norm,
#|                }
#|                rag_prompt = torch.zeros((e_img.size(0), self.rag_tokens, self.hidden_size), device=e_img.device)
#|            else:
#|                rag_prompt, rag_context = self.flute_retriever(
#|                    x_relation,
#|                    relation_q=relation_q,
#|                    disable_dropout=True,
#|                )
#|                rag_context["graph_prompt_norm"] = graph_prompt_norm
#|
#|            fused = self.output_norm(fused) * self.projector_scale
#|            prompt_tokens = torch.cat([fused, rag_prompt], dim=1)
#|            gate_weights = weights.squeeze(0).detach().cpu().tolist()
#|            return prompt_tokens, rag_context, gate_weights
#|
#|    original_get_response = module.get_response
#|
#|    def graph_get_response(image_path, qs, tokenizer, model, image_processor, projector, relation_q, features, device="cuda:0"):
#|        try:
#|            sample_id = int(Path(image_path).stem)
#|        except ValueError:
#|            sample_id = None
#|        projector._paper2_current_graph_feature = graph_features.get(sample_id)
#|        return original_get_response(
#|            image_path,
#|            qs,
#|            tokenizer,
#|            model,
#|            image_processor,
#|            projector,
#|            relation_q,
#|            features,
#|            device,
#|        )
#|
#|    module.MoE_LLM_Projector = GraphAwareInferenceProjector
#|    module.get_response = graph_get_response
#|    return module
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: cwct_circuit_tuning.py ===
#|"""Fixed-circuit contracts and warrant mediation loss for CWCT v1."""
#|
#|from __future__ import annotations
#|
#|from dataclasses import dataclass
#|import hashlib
#|import json
#|import math
#|from pathlib import Path
#|import re
#|from typing import Any, Iterable, Mapping
#|
#|from rgc_semantic_readout_stage_7 import masked_mean
#|from rgc_semantic_readout_stage_8 import (
#|    ReliabilityTrustReadoutConfig,
#|    collect_v8_metrics,
#|    make_v8_readout_classes,
#|    validate_v8_config,
#|)
#|
#|
#|CIRCUIT_VERSION = "cwct_circuit_manifest_v2"
#|TRACE_INPUT_POLICY = (
#|    "claim_only_real_image_e_image_e_text_e_desc_zero_graph_vector_zero_"
#|    "visual_claim_semantics_only"
#|)
#|TRACE_ALLOWED_GRAPH_FIELDS = ("visual_nodes", "claim_nodes")
#|TRACE_FORBIDDEN_GRAPH_FIELDS = (
#|    "description",
#|    "dataset",
#|    "source_dataset",
#|    "phenomenon",
#|    "inferred_phenomenon",
#|    "figurative_anchors",
#|    "concept_mappings",
#|    "evidence_edges",
#|)
#|TRACE_MODEL_CONFIG_FIELDS = (
#|    "num_tokens",
#|    "graph_dropout",
#|    "graph_gate_init",
#|    "graph_gate_cap",
#|    "relation_dim",
#|    "condition_dim",
#|    "controller_dropout",
#|    "readout_rank",
#|    "readout_gate_init",
#|    "readout_gate_cap",
#|    "rank_modulation_cap",
#|    "readout_residual_ratio",
#|    "graph_residual_gate_floor",
#|    "graph_residual_gate_init",
#|    "graph_residual_gate_cap",
#|    "semantic_residual_gate_floor",
#|    "semantic_residual_gate_init",
#|    "semantic_residual_gate_cap",
#|    "label_token_count",
#|    "label_readout_scale",
#|    "label_loss_weight",
#|    "semantic_max_length",
#|    "dro_eta",
#|    "dro_ema",
#|    "dro_entropy_reg",
#|    "dro_logit_cap",
#|    "dro_prior_floor",
#|    "dro_sample_weight_cap",
#|    "dro_warmup_steps",
#|    "alignment_queue_size",
#|    "alignment_temperature",
#|    "alignment_nce_weight",
#|    "alignment_final_nce_weight",
#|    "alignment_decay_start",
#|    "same_group_negative_scale",
#|    "soft_negative_mad_floor",
#|    "soft_negative_min_weight",
#|    "tail_error_ema",
#|    "tail_error_scale_floor",
#|    "tail_weight_floor",
#|    "tail_weight_cap",
#|    "decoder_alignment_dim",
#|    "decoder_alignment_weight",
#|    "decoder_alignment_temperature",
#|    "decoder_alignment_ema",
#|    "decoder_min_explanation_tokens",
#|    "reliability_temperature",
#|    "reliability_absolute_temperature",
#|    "reliability_deviation_floor",
#|    "trust_radius",
#|    "trust_dual_lr",
#|    "trust_augmented_weight",
#|    "trust_dual_cap",
#|)
#|COMPONENT_MODULES = {
#|    "self_attn": ("q_proj", "k_proj", "v_proj", "o_proj"),
#|    "mlp": ("gate_proj", "up_proj", "down_proj"),
#|}
#|_LORA_RE = re.compile(
#|    r"(?:^|\.)layers\.(\d+)\.(self_attn|mlp)\.([^.]+)\.lora_([AB])(?:\.|$)"
#|)
#|
#|
#|@dataclass(frozen=True)
#|class CWCTConfig(ReliabilityTrustReadoutConfig):
#|    warrant_max_length: int = 64
#|    warrant_loss_weight: float = 0.04
#|    warrant_margin: float = 0.10
#|    warrant_temperature: float = 0.07
#|    warrant_min_tokens: int = 4
#|    warrant_opposite_weight: float = 0.35
#|
#|
#|def validate_cwct_config(config: CWCTConfig) -> None:
#|    validate_v8_config(config)
#|    if config.warrant_max_length <= 0:
#|        raise ValueError("warrant_max_length must be positive")
#|    if not 0.0 < config.warrant_loss_weight <= 0.25:
#|        raise ValueError("warrant_loss_weight must be in (0, 0.25]")
#|    if config.warrant_margin < 0.0:
#|        raise ValueError("warrant_margin must be non-negative")
#|    if config.warrant_temperature <= 0.0:
#|        raise ValueError("warrant_temperature must be positive")
#|    if config.warrant_min_tokens <= 0:
#|        raise ValueError("warrant_min_tokens must be positive")
#|    if not 0.0 < config.warrant_opposite_weight <= 1.0:
#|        raise ValueError("warrant_opposite_weight must be in (0, 1]")
#|
#|
#|def manifest_sha256(manifest: Mapping[str, Any]) -> str:
#|    value = dict(manifest)
#|    value.pop("manifest_sha256", None)
#|    encoded = json.dumps(
#|        value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
#|    ).encode("utf-8")
#|    return hashlib.sha256(encoded).hexdigest()
#|
#|
#|def _finite_number(value: Any, name: str) -> float:
#|    if isinstance(value, bool):
#|        raise ValueError(f"CWCT {name} must be a finite number")
#|    try:
#|        number = float(value)
#|    except (TypeError, ValueError) as error:
#|        raise ValueError(f"CWCT {name} must be a finite number") from error
#|    if not math.isfinite(number):
#|        raise ValueError(f"CWCT {name} must be finite")
#|    return number
#|
#|
#|def _positive_integer(value: Any, name: str) -> int:
#|    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
#|        raise ValueError(f"CWCT {name} must be a positive integer")
#|    return int(value)
#|
#|
#|def _sha256_string(value: Any, name: str) -> str:
#|    if (
#|        not isinstance(value, str)
#|        or len(value) != 64
#|        or any(character not in "0123456789abcdef" for character in value)
#|    ):
#|        raise ValueError(f"CWCT {name} must be a lowercase SHA-256 digest")
#|    return value
#|
#|
#|def _same_number(left: Any, right: Any) -> bool:
#|    try:
#|        return math.isclose(
#|            float(left), float(right), rel_tol=0.0, abs_tol=1e-12
#|        )
#|    except (TypeError, ValueError):
#|        return False
#|
#|
#|def validate_circuit_manifest(manifest: Mapping[str, Any]) -> None:
#|    if not isinstance(manifest, Mapping):
#|        raise ValueError("CWCT circuit manifest must be an object")
#|    if manifest.get("version") != CIRCUIT_VERSION:
#|        raise ValueError("unexpected CWCT circuit manifest version")
#|    if manifest.get("trace_split") != "train":
#|        raise ValueError("CWCT circuit must be traced on train only")
#|    if manifest.get("test_accessed") is not False:
#|        raise ValueError("CWCT manifest must assert test_accessed=false")
#|    if any(key in manifest for key in ("sample_routes", "per_sample", "router")):
#|        raise ValueError("CWCT forbids per-sample circuit routing")
#|    if manifest.get("method") != "cross_fitted_within_label_warrant_subspace_ablation":
#|        raise ValueError("CWCT manifest has an unexpected tracing method")
#|    if manifest.get("probe_partition") != "dev":
#|        raise ValueError("CWCT circuits must be selected on the held-out dev partition")
#|    if manifest.get("inference_policy") != "global_fixed_circuit_single_pass":
#|        raise ValueError("CWCT manifest has an unexpected inference policy")
#|    if manifest.get("trace_input_policy") != TRACE_INPUT_POLICY:
#|        raise ValueError("CWCT manifest has an unexpected trace-input policy")
#|    _sha256_string(manifest.get("trace_graph_sha256"), "trace graph hash")
#|    if manifest.get("graph_vector_policy") != (
#|        "all_zero_no_source_graph_coordinates"
#|    ):
#|        raise ValueError("CWCT trace must zero the shortcut-bearing graph vector")
#|    if manifest.get("semantic_policy") != (
#|        "retokenized_visual_nodes_and_claim_nodes_only"
#|    ):
#|        raise ValueError("CWCT trace semantic side channel is not allowlisted")
#|    if tuple(manifest.get("trace_allowed_graph_fields", ())) != (
#|        TRACE_ALLOWED_GRAPH_FIELDS
#|    ):
#|        raise ValueError("CWCT trace allowed graph fields mismatch")
#|    if tuple(manifest.get("trace_forbidden_graph_fields", ())) != (
#|        TRACE_FORBIDDEN_GRAPH_FIELDS
#|    ):
#|        raise ValueError("CWCT trace forbidden graph fields mismatch")
#|
#|    trace = manifest.get("trace_config")
#|    if not isinstance(trace, Mapping):
#|        raise ValueError("CWCT manifest lacks trace_config")
#|    required_trace = {
#|        "layers",
#|        "max_samples",
#|        "top_components",
#|        "seed",
#|        "minimum_effect",
#|        "minimum_samples",
#|        "minimum_fold_samples",
#|        "subspace_rank",
#|        "ridge",
#|        "bootstrap_samples",
#|        "minimum_decode_accuracy",
#|        "margin_replay_tolerance",
#|    }
#|    if set(trace) != required_trace:
#|        raise ValueError(
#|            "CWCT trace_config keys differ from the registered contract: "
#|            f"missing={sorted(required_trace-set(trace))} "
#|            f"extra={sorted(set(trace)-required_trace)}"
#|        )
#|    if not isinstance(trace["layers"], str):
#|        raise ValueError("CWCT trace_config.layers must be a comma-separated string")
#|    try:
#|        traced_layers = [
#|            int(value) for value in trace["layers"].split(",") if value.strip()
#|        ]
#|    except ValueError as error:
#|        raise ValueError("CWCT trace_config.layers contains a non-integer") from error
#|    if not traced_layers or len(set(traced_layers)) != len(traced_layers):
#|        raise ValueError("CWCT trace_config.layers must be nonempty and unique")
#|    if any(layer < 0 for layer in traced_layers):
#|        raise ValueError("CWCT trace_config.layers contains a negative layer")
#|    max_samples = _positive_integer(trace["max_samples"], "trace max_samples")
#|    top_components = _positive_integer(
#|        trace["top_components"], "trace top_components"
#|    )
#|    if isinstance(trace["seed"], bool) or not isinstance(trace["seed"], int):
#|        raise ValueError("CWCT trace seed must be an integer")
#|    minimum_effect = _finite_number(
#|        trace["minimum_effect"], "trace minimum_effect"
#|    )
#|    if minimum_effect < 0.0:
#|        raise ValueError("CWCT trace minimum_effect must be non-negative")
#|    minimum_samples = _positive_integer(
#|        trace["minimum_samples"], "trace minimum_samples"
#|    )
#|    minimum_fold_samples = _positive_integer(
#|        trace["minimum_fold_samples"], "trace minimum_fold_samples"
#|    )
#|    if max_samples < minimum_samples or minimum_samples < 2 * minimum_fold_samples:
#|        raise ValueError("CWCT trace sample thresholds are internally inconsistent")
#|    subspace_rank = _positive_integer(
#|        trace["subspace_rank"], "trace subspace_rank"
#|    )
#|    ridge = _finite_number(trace["ridge"], "trace ridge")
#|    if ridge <= 0.0:
#|        raise ValueError("CWCT trace ridge must be positive")
#|    _positive_integer(trace["bootstrap_samples"], "trace bootstrap_samples")
#|    minimum_decode = _finite_number(
#|        trace["minimum_decode_accuracy"], "trace minimum_decode_accuracy"
#|    )
#|    if not 0.0 <= minimum_decode <= 1.0:
#|        raise ValueError("CWCT minimum decode accuracy must lie in [0, 1]")
#|    replay_tolerance = _finite_number(
#|        trace["margin_replay_tolerance"], "trace margin_replay_tolerance"
#|    )
#|    if replay_tolerance < 0.0:
#|        raise ValueError("CWCT margin replay tolerance must be non-negative")
#|
#|    model_config = manifest.get("model_config")
#|    if not isinstance(model_config, Mapping) or set(model_config) != set(
#|        TRACE_MODEL_CONFIG_FIELDS
#|    ):
#|        raise ValueError("CWCT manifest model_config keys mismatch")
#|    for name in TRACE_MODEL_CONFIG_FIELDS:
#|        _finite_number(model_config[name], f"model_config {name}")
#|    if int(model_config["num_tokens"]) != 0:
#|        raise ValueError("CWCT trace model_config must use zero graph prompt tokens")
#|    if float(model_config["graph_dropout"]) != 0.0:
#|        raise ValueError("CWCT trace model_config must disable graph dropout")
#|
#|    intervention = manifest.get("intervention")
#|    if not isinstance(intervention, Mapping):
#|        raise ValueError("CWCT manifest lacks intervention metadata")
#|    expected_intervention = {
#|        "position": "first_non_ignore_label_index_minus_one",
#|        "metric": "sum_logP(gold_verbalizer)-sum_logP(opposite_verbalizer)",
#|        "random_control": "equal_rank",
#|        "label_control": "equal_rank",
#|    }
#|    for name, expected in expected_intervention.items():
#|        if intervention.get(name) != expected:
#|            raise ValueError(f"CWCT intervention {name} mismatch")
#|    linked_intervention = {
#|        "subspace_rank": subspace_rank,
#|        "bootstrap_samples": trace["bootstrap_samples"],
#|        "minimum_effect": minimum_effect,
#|        "minimum_decode_accuracy": minimum_decode,
#|        "margin_replay_tolerance": replay_tolerance,
#|    }
#|    for name, expected in linked_intervention.items():
#|        actual = intervention.get(name)
#|        if not _same_number(actual, expected):
#|            raise ValueError(f"CWCT intervention/trace_config mismatch for {name}")
#|    candidate_count = len(traced_layers) * len(COMPONENT_MODULES)
#|    family_hypotheses = candidate_count * 2
#|    family_alpha = _finite_number(
#|        intervention.get("bootstrap_family_alpha"),
#|        "bootstrap family alpha",
#|    )
#|    interval_alpha = _finite_number(
#|        intervention.get("bootstrap_interval_alpha"),
#|        "bootstrap interval alpha",
#|    )
#|    if not 0.0 < family_alpha < 1.0:
#|        raise ValueError("CWCT bootstrap family alpha must lie in (0, 1)")
#|    if intervention.get("bootstrap_candidate_count") != candidate_count:
#|        raise ValueError("CWCT bootstrap candidate count mismatch")
#|    if intervention.get("bootstrap_hypotheses") != family_hypotheses:
#|        raise ValueError("CWCT bootstrap hypothesis count mismatch")
#|    if not _same_number(interval_alpha, family_alpha / family_hypotheses):
#|        raise ValueError("CWCT Bonferroni interval alpha mismatch")
#|    if intervention.get("multiple_comparison_correction") != (
#|        "bonferroni_fixed_candidates_x_folds"
#|    ):
#|        raise ValueError("CWCT multiple-comparison correction mismatch")
#|
#|    source = manifest.get("source")
#|    if not isinstance(source, Mapping):
#|        raise ValueError("CWCT manifest lacks source metadata")
#|    if not isinstance(source.get("checkpoint_root"), str) or not source.get(
#|        "checkpoint_root"
#|    ):
#|        raise ValueError("CWCT source checkpoint_root is missing")
#|    if not isinstance(source.get("llava_model_path"), str) or not source.get(
#|        "llava_model_path"
#|    ):
#|        raise ValueError("CWCT source llava_model_path is missing")
#|    _positive_integer(source.get("epoch"), "source epoch")
#|    if not isinstance(source.get("projector_suffix"), str) or not source.get(
#|        "projector_suffix"
#|    ):
#|        raise ValueError("CWCT source projector_suffix is missing")
#|    _sha256_string(source.get("lora_tree_sha256"), "source LoRA hash")
#|    _sha256_string(source.get("projector_sha256"), "source projector hash")
#|    _sha256_string(manifest.get("warrant_cache_sha256"), "warrant cache hash")
#|    _sha256_string(manifest.get("trace_input_sha256"), "trace input hash")
#|
#|    selected = manifest.get("selected")
#|    if not isinstance(selected, list) or not selected:
#|        raise ValueError("CWCT manifest has no globally selected components")
#|    if len(selected) != top_components:
#|        raise ValueError("CWCT selected component count differs from top_components")
#|    keys = set()
#|    for item in selected:
#|        if not isinstance(item, Mapping):
#|            raise ValueError("CWCT selected entry must be an object")
#|        layer = int(item.get("layer", -1))
#|        component = item.get("component")
#|        if layer not in traced_layers or component not in COMPONENT_MODULES:
#|            raise ValueError(f"invalid CWCT component: {item}")
#|        minimum_ci = _finite_number(
#|            item.get("minimum_ci_lower"), "selected minimum_ci_lower"
#|        )
#|        _finite_number(
#|            item.get("mean_corrected_effect"), "selected mean_corrected_effect"
#|        )
#|        if minimum_ci <= minimum_effect:
#|            raise ValueError("CWCT selected component CI does not clear the floor")
#|        key = (layer, component)
#|        if key in keys:
#|            raise ValueError(f"duplicate CWCT component: {key}")
#|        keys.add(key)
#|    if manifest.get("cross_fitted") is not True:
#|        raise ValueError("CWCT manifest must be cross-fitted")
#|    if manifest.get("real_multimodal") is not True:
#|        raise ValueError("CWCT manifest must trace the real multimodal path")
#|    if manifest.get("first_verdict_margin") is not True:
#|        raise ValueError("CWCT manifest must score the first-verdict margin")
#|    folds = manifest.get("folds")
#|    if not isinstance(folds, list) or len(folds) != 2:
#|        raise ValueError("CWCT manifest must report two held-out folds")
#|    if {str(row.get("fold")) for row in folds if isinstance(row, Mapping)} != {
#|        "a",
#|        "b",
#|    }:
#|        raise ValueError("CWCT held-out fold names must be a and b")
#|    fold_by_name = {}
#|    for row in folds:
#|        if not isinstance(row, Mapping):
#|            raise ValueError("CWCT fold entry must be an object")
#|        fold_name = str(row["fold"])
#|        fold_by_name[fold_name] = row
#|        required = (
#|            "selected_ci_lower",
#|            "selected_mean_recovery",
#|            "random_control_mean_recovery",
#|            "label_control_mean_recovery",
#|        )
#|        if any(key not in row for key in required):
#|            raise ValueError(f"CWCT fold lacks causal controls: {row}")
#|        values = {key: _finite_number(row[key], f"fold {fold_name} {key}") for key in required}
#|        heldout = _positive_integer(
#|            row.get("heldout_measurements"), f"fold {fold_name} heldout_measurements"
#|        )
#|        if values["selected_ci_lower"] <= minimum_effect:
#|            raise ValueError(f"CWCT fold {fold_name} CI does not clear the floor")
#|        if values["selected_mean_recovery"] <= values["random_control_mean_recovery"]:
#|            raise ValueError(f"CWCT fold {fold_name} does not beat random control")
#|        if values["selected_mean_recovery"] <= values["label_control_mean_recovery"]:
#|            raise ValueError(f"CWCT fold {fold_name} does not beat label control")
#|        if row.get("effect_definition") != (
#|            "min(warrant_drop-random_drop,warrant_drop-label_drop)"
#|        ):
#|            raise ValueError(f"CWCT fold {fold_name} effect definition mismatch")
#|        correction = {
#|            "bootstrap_family_alpha": family_alpha,
#|            "bootstrap_candidate_count": candidate_count,
#|            "bootstrap_hypotheses": family_hypotheses,
#|            "bootstrap_interval_alpha": interval_alpha,
#|            "multiple_comparison_correction": (
#|                "bonferroni_fixed_candidates_x_folds"
#|            ),
#|        }
#|        for name, expected in correction.items():
#|            actual = row.get(name)
#|            if isinstance(expected, float):
#|                if not _same_number(actual, expected):
#|                    raise ValueError(
#|                        f"CWCT fold {fold_name} correction mismatch for {name}"
#|                    )
#|            elif actual != expected:
#|                raise ValueError(
#|                    f"CWCT fold {fold_name} correction mismatch for {name}"
#|                )
#|        if heldout < minimum_fold_samples:
#|            raise ValueError(f"CWCT fold {fold_name} is smaller than registered")
#|
#|    summary = manifest.get("summary")
#|    if not isinstance(summary, Mapping):
#|        raise ValueError("CWCT manifest lacks summary")
#|    requested = _positive_integer(
#|        summary.get("requested_samples"), "summary requested_samples"
#|    )
#|    usable = _positive_integer(summary.get("usable_samples"), "summary usable_samples")
#|    if requested > max_samples or requested < minimum_samples or usable > requested:
#|        raise ValueError("CWCT summary sample counts are inconsistent")
#|    fold_counts = summary.get("fold_counts")
#|    if not isinstance(fold_counts, Mapping) or set(fold_counts) != {"a", "b"}:
#|        raise ValueError("CWCT summary fold_counts must contain a and b")
#|    fold_counts = {
#|        name: _positive_integer(fold_counts[name], f"summary fold {name}")
#|        for name in ("a", "b")
#|    }
#|    if sum(fold_counts.values()) != usable:
#|        raise ValueError("CWCT summary fold counts do not sum to usable_samples")
#|    if any(value < minimum_fold_samples for value in fold_counts.values()):
#|        raise ValueError("CWCT summary contains an undersized fold")
#|    for name, row in fold_by_name.items():
#|        if int(row["heldout_measurements"]) != fold_counts[name]:
#|            raise ValueError(f"CWCT aggregate fold {name} count mismatch")
#|
#|    all_components = summary.get("all_components")
#|    if not isinstance(all_components, list) or not all_components:
#|        raise ValueError("CWCT summary has no component diagnostics")
#|    expected_components = {
#|        (layer, component)
#|        for layer in traced_layers
#|        for component in COMPONENT_MODULES
#|    }
#|    component_rows = {}
#|    for row in all_components:
#|        if not isinstance(row, Mapping):
#|            raise ValueError("CWCT component diagnostic must be an object")
#|        key = (int(row.get("layer", -1)), row.get("component"))
#|        if key in component_rows or key not in expected_components:
#|            raise ValueError(f"CWCT invalid/duplicate component diagnostic: {key}")
#|        component_rows[key] = row
#|        _finite_number(row.get("minimum_ci_lower"), f"component {key} minimum CI")
#|        _finite_number(
#|            row.get("mean_corrected_effect"), f"component {key} mean effect"
#|        )
#|        if not isinstance(row.get("stable"), bool):
#|            raise ValueError(f"CWCT component {key} stable flag is invalid")
#|        component_folds = row.get("folds")
#|        if not isinstance(component_folds, list) or len(component_folds) != 2:
#|            raise ValueError(f"CWCT component {key} lacks two fold diagnostics")
#|        names = {str(value.get("fold")) for value in component_folds if isinstance(value, Mapping)}
#|        if names != {"a", "b"}:
#|            raise ValueError(f"CWCT component {key} fold names are invalid")
#|        for diagnostic in component_folds:
#|            fold_name = str(diagnostic["fold"])
#|            train_samples = _positive_integer(
#|                diagnostic.get("train_samples"), f"component {key} train_samples"
#|            )
#|            heldout_samples = _positive_integer(
#|                diagnostic.get("heldout_samples"), f"component {key} heldout_samples"
#|            )
#|            rank = _positive_integer(diagnostic.get("rank"), f"component {key} rank")
#|            if rank > subspace_rank:
#|                raise ValueError(f"CWCT component {key} exceeds registered rank")
#|            if heldout_samples != fold_counts[fold_name]:
#|                raise ValueError(f"CWCT component {key} heldout count mismatch")
#|            other = "b" if fold_name == "a" else "a"
#|            if train_samples != fold_counts[other]:
#|                raise ValueError(f"CWCT component {key} training-fold count mismatch")
#|            for metric in (
#|                "warrant_margin_drop",
#|                "random_margin_drop",
#|                "label_margin_drop",
#|                "corrected_effect",
#|                "corrected_ci_lower",
#|            ):
#|                _finite_number(
#|                    diagnostic.get(metric), f"component {key} {fold_name} {metric}"
#|                )
#|            for metric in (
#|                "decode_vs_same_accuracy",
#|                "decode_vs_opposite_accuracy",
#|            ):
#|                accuracy = _finite_number(
#|                    diagnostic.get(metric), f"component {key} {fold_name} {metric}"
#|                )
#|                if not 0.0 <= accuracy <= 1.0:
#|                    raise ValueError(f"CWCT component {key} has invalid decode accuracy")
#|            for name, expected in (
#|                ("bootstrap_family_alpha", family_alpha),
#|                ("bootstrap_hypotheses", family_hypotheses),
#|                ("bootstrap_interval_alpha", interval_alpha),
#|            ):
#|                if not _same_number(diagnostic.get(name), expected):
#|                    raise ValueError(
#|                        f"CWCT component {key} {fold_name} correction mismatch for {name}"
#|                    )
#|    if set(component_rows) != expected_components:
#|        raise ValueError("CWCT summary does not cover every registered component")
#|
#|    for item in selected:
#|        key = (int(item["layer"]), str(item["component"]))
#|        diagnostic = component_rows[key]
#|        if diagnostic.get("stable") is not True:
#|            raise ValueError(f"CWCT selected component {key} is not stable")
#|        if not _same_number(item["minimum_ci_lower"], diagnostic["minimum_ci_lower"]):
#|            raise ValueError(f"CWCT selected component {key} minimum CI mismatch")
#|        if not _same_number(
#|            item["mean_corrected_effect"], diagnostic["mean_corrected_effect"]
#|        ):
#|            raise ValueError(f"CWCT selected component {key} mean effect mismatch")
#|        for diagnostic_fold in diagnostic["folds"]:
#|            if (
#|                float(diagnostic_fold["corrected_ci_lower"]) <= minimum_effect
#|                or float(diagnostic_fold["decode_vs_same_accuracy"]) < minimum_decode
#|                or float(diagnostic_fold["decode_vs_opposite_accuracy"]) < minimum_decode
#|                or float(diagnostic_fold["warrant_margin_drop"])
#|                <= float(diagnostic_fold["random_margin_drop"])
#|                or float(diagnostic_fold["warrant_margin_drop"])
#|                <= float(diagnostic_fold["label_margin_drop"])
#|            ):
#|                raise ValueError(f"CWCT selected component {key} fails a held-out gate")
#|
#|    declared = _sha256_string(
#|        manifest.get("manifest_sha256"), "manifest_sha256"
#|    )
#|    if declared != manifest_sha256(manifest):
#|        raise ValueError("CWCT manifest hash mismatch")
#|
#|
#|def load_circuit_manifest(path: str | Path) -> dict[str, Any]:
#|    with Path(path).open("r", encoding="utf-8") as handle:
#|        manifest = json.load(handle)
#|    validate_circuit_manifest(manifest)
#|    return manifest
#|
#|
#|def selected_circuits(manifest: Mapping[str, Any]) -> set[tuple[int, str]]:
#|    validate_circuit_manifest(manifest)
#|    return {
#|        (int(item["layer"]), str(item["component"]))
#|        for item in manifest["selected"]
#|    }
#|
#|
#|def parse_lora_parameter(name: str) -> tuple[int, str, str, str] | None:
#|    match = _LORA_RE.search(name)
#|    if match is None:
#|        return None
#|    return int(match.group(1)), match.group(2), match.group(3), match.group(4)
#|
#|
#|def select_circuit_lora_parameters(
#|    named_parameters: Iterable[tuple[str, Any]],
#|    manifest: Mapping[str, Any],
#|    *,
#|    train_factors: tuple[str, ...] = ("B",),
#|) -> tuple[list[tuple[str, Any]], dict[tuple[int, str], dict[str, int]]]:
#|    selected = selected_circuits(manifest)
#|    hits = {key: {"A": 0, "B": 0} for key in selected}
#|    trainable = []
#|    allowed_factors = set(train_factors)
#|    for name, parameter in named_parameters:
#|        parsed = parse_lora_parameter(name)
#|        active = False
#|        if parsed is not None:
#|            layer, component, module_name, factor = parsed
#|            key = (layer, component)
#|            if key in selected and module_name in COMPONENT_MODULES[component]:
#|                hits[key][factor] += 1
#|                active = factor in allowed_factors
#|        parameter.requires_grad = bool(active)
#|        if active:
#|            trainable.append((name, parameter))
#|    missing = [key for key, value in hits.items() if not value["A"] or not value["B"]]
#|    if missing:
#|        raise RuntimeError(f"CWCT selected circuits did not match LoRA A/B: {missing}")
#|    if not trainable:
#|        raise RuntimeError("CWCT selected no trainable LoRA tensors")
#|    return trainable, hits
#|
#|
#|def pairwise_warrant_ranking(
#|    torch,
#|    decoder_state,
#|    positive_state,
#|    negative_state,
#|    eligible,
#|    *,
#|    margin: float,
#|    temperature: float,
#|):
#|    decoder_state = torch.nn.functional.normalize(decoder_state.float(), dim=-1)
#|    positive_state = torch.nn.functional.normalize(positive_state.float(), dim=-1)
#|    negative_state = torch.nn.functional.normalize(negative_state.float(), dim=-1)
#|    positive = (decoder_state * positive_state).sum(dim=-1)
#|    negative = (decoder_state * negative_state).sum(dim=-1)
#|    gap = positive - negative
#|    losses = torch.nn.functional.softplus(
#|        (float(margin) - gap) / float(temperature)
#|    ) * float(temperature)
#|    mask = eligible.to(losses.device).bool()
#|    loss = (losses * mask.to(losses.dtype)).sum()
#|    loss = loss / mask.float().sum().clamp_min(1.0)
#|    return loss, gap, positive, negative
#|
#|
#|def make_cwct_readout_classes(torch, nn):
#|    Readout, V8Controller = make_v8_readout_classes(torch, nn)
#|
#|    class CWCTController(V8Controller):
#|        def __init__(
#|            self,
#|            hidden_size: int,
#|            num_tokens: int,
#|            config: CWCTConfig,
#|            *,
#|            training_graph_dropout: bool,
#|        ):
#|            validate_cwct_config(config)
#|            super().__init__(
#|                hidden_size,
#|                num_tokens,
#|                config,
#|                training_graph_dropout=training_graph_dropout,
#|            )
#|            self._warrant_embed_layer = None
#|            self._warrant_context = None
#|            self.last_cwct_loss = torch.tensor(0.0)
#|            self.last_cwct_same_gap = torch.tensor(0.0)
#|            self.last_cwct_opposite_gap = torch.tensor(0.0)
#|            self.last_cwct_positive = torch.tensor(0.0)
#|            self.last_cwct_same_negative = torch.tensor(0.0)
#|            self.last_cwct_opposite_negative = torch.tensor(0.0)
#|            self.last_cwct_eligible = torch.tensor(0.0)
#|
#|        def bind_warrant_embedding(self, embed_layer) -> None:
#|            # object.__setattr__ avoids registering the LLM embedding as a
#|            # projector submodule and therefore preserves the v8 state_dict.
#|            object.__setattr__(self, "_warrant_embed_layer", embed_layer)
#|
#|        def set_warrant_context(
#|            self,
#|            positive_ids,
#|            positive_mask,
#|            same_label_ids,
#|            same_label_mask,
#|            opposite_label_ids,
#|            opposite_label_mask,
#|            eligible,
#|        ) -> None:
#|            self._warrant_context = (
#|                positive_ids,
#|                positive_mask,
#|                same_label_ids,
#|                same_label_mask,
#|                opposite_label_ids,
#|                opposite_label_mask,
#|                eligible,
#|            )
#|
#|        def clear_warrant_context(self) -> None:
#|            self._warrant_context = None
#|
#|        def on_optimizer_step(self) -> None:
#|            # CWCT updates only the selected LLM LoRA tensors.  In particular,
#|            # do not mutate the source v8 controller's persistent GroupDRO
#|            # buffers; byte-equality of the saved projector is part of the
#|            # checkpoint contract.
#|            return None
#|
#|        def _encode_warrant(self, ids, mask, device):
#|            embed_layer = self._warrant_embed_layer
#|            if embed_layer is None:
#|                raise RuntimeError("CWCT warrant embedding layer is not bound")
#|            safe = ids.to(device).long().clone()
#|            valid = mask.to(device).bool()
#|            vocabulary = int(embed_layer.weight.size(0))
#|            valid = valid & safe.ge(0) & safe.lt(vocabulary)
#|            safe[~valid] = 0
#|            with torch.no_grad():
#|                embeddings = embed_layer(safe).float()
#|            enough = valid.long().sum(dim=1).ge(
#|                int(self.config.warrant_min_tokens)
#|            )
#|            pooled = masked_mean(torch, embeddings, valid)
#|            # The embedding and the frozen v8 projection are targets only.
#|            # Gradients flow through the projected decision state, never into
#|            # the warrant embedding table or the byte-frozen projector.
#|            with torch.no_grad():
#|                projected = self.decoder_alignment_projection(pooled)
#|            return projected, enough
#|
#|        def decoder_alignment_loss(self, labels, ignore_index: int):
#|            hidden = self.semantic_readout.decoder_alignment_hidden
#|            if hidden is None:
#|                raise RuntimeError("CWCT final decoder state was not captured")
#|            if hidden.size(1) != labels.size(1):
#|                raise RuntimeError(
#|                    "CWCT decoder/label sequence mismatch: "
#|                    f"{hidden.size(1)} != {labels.size(1)}"
#|                )
#|            context = self._warrant_context
#|            if context is None:
#|                raise RuntimeError("CWCT training batch lacks warrant context")
#|            (
#|                positive_ids,
#|                positive_mask,
#|                same_label_ids,
#|                same_label_mask,
#|                opposite_label_ids,
#|                opposite_label_mask,
#|                eligible,
#|            ) = context
#|
#|            # Consume the inherited v7/v8 transient captures exactly once.  We
#|            # retain the graph-connected tensor reference above, while the
#|            # inherited implementation clears its hook/graph/target state and
#|            # computes the unchanged clean-v8 decoder alignment objective.
#|            base_loss = super().decoder_alignment_loss(labels, ignore_index)
#|
#|            # In a causal LM hidden[t] predicts labels[t + 1].  If j is the
#|            # first supervised label (the first verdict token), hidden[j - 1]
#|            # is therefore the last state that cannot have observed any gold
#|            # answer/warrant token.  This is the only state used by CWCT.
#|            supervised = labels.ne(int(ignore_index))
#|            has_supervised = supervised.any(dim=1)
#|            first_supervised = supervised.long().argmax(dim=1)
#|            causal_position = first_supervised.gt(0)
#|            decision_index = (first_supervised - 1).clamp(
#|                min=0,
#|                max=max(0, hidden.size(1) - 1),
#|            )
#|            batch_index = torch.arange(hidden.size(0), device=hidden.device)
#|            decision_hidden = hidden[
#|                batch_index,
#|                decision_index.to(hidden.device),
#|                :,
#|            ].float()
#|            decision_state = self.decoder_alignment_projection(decision_hidden)
#|
#|            positive_state, positive_present = self._encode_warrant(
#|                positive_ids, positive_mask, hidden.device
#|            )
#|            same_state, same_present = self._encode_warrant(
#|                same_label_ids, same_label_mask, hidden.device
#|            )
#|            opposite_state, opposite_present = self._encode_warrant(
#|                opposite_label_ids, opposite_label_mask, hidden.device
#|            )
#|            active = (
#|                eligible.to(hidden.device).bool()
#|                & positive_present
#|                & same_present
#|                & opposite_present
#|                & has_supervised.to(hidden.device)
#|                & causal_position.to(hidden.device)
#|            )
#|            same_ranking, same_gap, positive, same_negative = pairwise_warrant_ranking(
#|                torch,
#|                decision_state,
#|                positive_state,
#|                same_state,
#|                active,
#|                margin=float(self.config.warrant_margin),
#|                temperature=float(self.config.warrant_temperature),
#|            )
#|            (
#|                opposite_ranking,
#|                opposite_gap,
#|                _positive_again,
#|                opposite_negative,
#|            ) = pairwise_warrant_ranking(
#|                torch,
#|                decision_state,
#|                positive_state,
#|                opposite_state,
#|                active,
#|                margin=float(self.config.warrant_margin),
#|                temperature=float(self.config.warrant_temperature),
#|            )
#|            # Dual-control discriminative grounding: the same-label hard
#|            # mismatch is the primary semantic control; the opposite-label
#|            # matched warrant is deliberately down-weighted so label polarity
#|            # cannot dominate the target geometry.
#|            opposite_weight = float(self.config.warrant_opposite_weight)
#|            ranking = (
#|                same_ranking + opposite_weight * opposite_ranking
#|            ) / (1.0 + opposite_weight)
#|            weighted = float(self.config.warrant_loss_weight) * ranking
#|            self.last_cwct_loss = weighted.detach()
#|            active_float = active.to(same_gap.dtype)
#|            denominator = active_float.sum().clamp_min(1.0)
#|            self.last_cwct_same_gap = (
#|                same_gap * active_float
#|            ).sum().detach() / denominator
#|            self.last_cwct_opposite_gap = (
#|                opposite_gap * active_float
#|            ).sum().detach() / denominator
#|            self.last_cwct_positive = (
#|                positive * active_float
#|            ).sum().detach() / denominator
#|            self.last_cwct_same_negative = (
#|                same_negative * active_float
#|            ).sum().detach() / denominator
#|            self.last_cwct_opposite_negative = (
#|                opposite_negative * active_float
#|            ).sum().detach() / denominator
#|            self.last_cwct_eligible = active_float.mean().detach()
#|            return base_loss + weighted
#|
#|    return Readout, CWCTController
#|
#|
#|def collect_cwct_metrics(model, torch) -> dict[str, str]:
#|    metrics = collect_v8_metrics(model, torch)
#|    projector = model.projector
#|    metrics.update(
#|        {
#|            "CW_L": f"{projector.last_cwct_loss.item():.4f}",
#|            "CW_GS": f"{projector.last_cwct_same_gap.item():+.4f}",
#|            "CW_GO": f"{projector.last_cwct_opposite_gap.item():+.4f}",
#|            "CW_P": f"{projector.last_cwct_positive.item():+.4f}",
#|            "CW_NS": f"{projector.last_cwct_same_negative.item():+.4f}",
#|            "CW_NO": f"{projector.last_cwct_opposite_negative.item():+.4f}",
#|            "CW_E": f"{projector.last_cwct_eligible.item():.2f}",
#|        }
#|    )
#|    return metrics
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: cwct_warrant_data.py ===
#|"""Train-only silver-warrant data utilities for the CWCT experiment.
#|
#|CWCT deliberately separates three objects that older experiments conflated:
#|
#|* an observation, which is directly visible in the image/text;
#|* a warrant, which is the implicit rule that licenses the prediction; and
#|* a verdict, which is the entailment/contradiction decision.
#|
#|The cache builder extracts an *exact span* from a gold training explanation and
#|retrieves two auditable controls independently inside each tune/dev partition:
#|a same-label hard mismatch and an opposite-label matched warrant.  Neither
#|retrieved span is claimed to be a logical counterfactual.  The builder never
#|synthesizes fallback text.  All retrieval features are allow-listed;
#|description embeddings, dataset/source metadata, and annotated phenomenon
#|labels are excluded.
#|"""
#|
#|from __future__ import annotations
#|
#|from dataclasses import dataclass
#|import hashlib
#|import json
#|import math
#|from pathlib import Path
#|import re
#|from typing import Any, Iterable, Iterator, Mapping, Sequence
#|
#|
#|SCHEMA_VERSION = "cwct_warrant_v2"
#|MANIFEST_VERSION = "cwct_warrant_manifest_v2"
#|LABELS = {"entailment": 1, "contradiction": 0}
#|
#|_LABEL_RE = re.compile(r"^\s*(entailment|contradiction)\s*\.\s*", re.I)
#|_SENTENCE_RE = re.compile(r"[^.!?]+(?:[.!?]+|$)", re.S)
#|_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'_-]*")
#|_SPACE_RE = re.compile(r"\s+")
#|
#|_FAMILY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
#|    (
#|        "figurative_rule",
#|        re.compile(
#|            r"\b(?:metaphor|metaphorical|simile|idiom|figurative|sarcasm|"
#|            r"sarcastic|irony|ironic|humor|humorous|joke|play on)\b",
#|            re.I,
#|        ),
#|    ),
#|    (
#|        "semantic_bridge",
#|        re.compile(
#|            r"\b(?:imply|implies|implied|suggest|suggests|suggesting|"
#|            r"indicate|indicates|indicating|mean|means|meaning|symbolize|"
#|            r"symbolizes|symbolising|represent|represents|representing|"
#|            r"convey|conveys|conveyed|associate|associated|refer|refers|"
#|            r"referred|denote|denotes)\b",
#|            re.I,
#|        ),
#|    ),
#|    (
#|        "causal_rule",
#|        re.compile(
#|            r"\b(?:because|since|therefore|thus|hence|as a result|"
#|            r"leading to|due to|so that)\b",
#|            re.I,
#|        ),
#|    ),
#|    (
#|        "norm_conflict",
#|        re.compile(
#|            r"\b(?:contrary to|contrasts? with|despite|even though|"
#|            r"rather than|instead of|while|whereas|goes against)\b",
#|            re.I,
#|        ),
#|    ),
#|    (
#|        "analogy_rule",
#|        re.compile(r"\b(?:akin to|much like|as if|similar to|compared to)\b", re.I),
#|    ),
#|)
#|
#|_OBSERVATION_PREFIX = re.compile(
#|    r"^\s*[\"'“”‘’.,;:()\[\]-]*\s*(?:the\s+)?"
#|    r"(?:image|picture|photo|cartoon|meme|screenshot|"
#|    r"illustration|painting|scene)\s+(?:shows?|depicts?|displays?|features?)\b",
#|    re.I,
#|)
#|_CONCLUSION_MARKERS = re.compile(
#|    r"\b(?:claim|verdict|label|conclusion|concludes?|concluded|entailment|"
#|    r"contradiction|entails?|entailed|"
#|    r"contradicts?|contradicted|supports?|supported|refutes?|refuted|"
#|    r"consistent with|inconsistent with|aligns? with|conflicts? with)\b",
#|    re.I,
#|)
#|_RESTATEMENT_PREFIX = re.compile(
#|    r"^\s*[\"'“”‘’.,;:()\[\]-]*\s*(?:(?:this|that)(?:\s+(?:image|picture|"
#|    r"photo|cartoon|meme|screenshot|illustration|painting|scene|visual(?:\s+"
#|    r"(?:comparison|evidence|metaphor))?|imagery|humou?r|metaphor|simile|"
#|    r"idiom|sarcasm|juxtaposition|comparison|evidence|caption|text|depiction))?"
#|    r"|it|which|(?:the\s+)?(?:image|picture|photo|cartoon|meme|screenshot|"
#|    r"illustration|painting|scene|visual|imagery|humou?r|metaphor|simile|"
#|    r"idiom|sarcasm|juxtaposition))\s+(?:(?:clearly|directly|visually|vividly|"
#|    r"strongly|explicitly|humorously|metaphorically|sarcastically|ultimately)\s+)?"
#|    r"(?:shows?|demonstrates?|establishes?|suggests?|implies?|indicates?|"
#|    r"means?|represents?|symbolizes?|conveys?|captures?|evokes?|portrays?|"
#|    r"illustrates?|reflects?|signifies?|reinforces?)\s+(?:that\s+)?",
#|    re.I,
#|)
#|_CONCLUSION_PREFIX = re.compile(
#|    r"^\s*[\"'“”‘’.,;:()\[\]-]*\s*(?:therefore|thus|hence|overall|"
#|    r"consequently|accordingly|as\s+a\s+result)\b",
#|    re.I,
#|)
#|_WARRANT_FORM = re.compile(
#|    r"\b(?:term|phrase|word|expression|caption|metaphor|simile|idiom|sarcasm|"
#|    r"irony|joke|because|since|due to|akin to|much like|as if|contrary to|"
#|    r"rather than|means?|refers? to|associated with|used to|normally|"
#|    r"typically|generally|often|would|expect(?:ed|ation)?)\b",
#|    re.I,
#|)
#|MAX_CLAIM_JACCARD = 0.34
#|MAX_CLAIM_COVERAGE = 0.70
#|MAX_WARRANT_CLAIM_COVERAGE = 0.55
#|MAX_MISMATCH_SURFACE_SIMILARITY = 0.25
#|MIN_DONOR_LENGTH_RATIO = 0.50
#|_STOPWORDS = {
#|    "a", "an", "and", "are", "as", "at", "be", "because", "been", "being",
#|    "by", "for", "from", "has", "have", "he", "her", "his", "i", "if", "in",
#|    "is", "it", "its", "of", "on", "or", "she", "that", "the", "their", "them",
#|    "there", "they", "this", "to", "was", "were", "which", "while", "with", "you",
#|}
#|
#|
#|@dataclass(frozen=True)
#|class WarrantSpan:
#|    text: str
#|    char_start: int
#|    char_end: int
#|    rule_family: str
#|    quality: str
#|
#|
#|def stable_json_hash(value: Any) -> str:
#|    encoded = json.dumps(
#|        value,
#|        ensure_ascii=False,
#|        sort_keys=True,
#|        separators=(",", ":"),
#|    ).encode("utf-8")
#|    return hashlib.sha256(encoded).hexdigest()
#|
#|
#|def file_sha256(path: str | Path) -> str:
#|    digest = hashlib.sha256()
#|    with Path(path).open("rb") as handle:
#|        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
#|            digest.update(chunk)
#|    return digest.hexdigest()
#|
#|
#|def normalize_text(value: Any) -> str:
#|    return _SPACE_RE.sub(" ", str(value or "")).strip()
#|
#|
#|def content_tokens(value: Any) -> tuple[str, ...]:
#|    return tuple(
#|        token
#|        for token in (item.lower() for item in _WORD_RE.findall(str(value or "")))
#|        if token not in _STOPWORDS and len(token) > 1
#|    )
#|
#|
#|def parse_label(answer: str) -> tuple[str, int]:
#|    match = _LABEL_RE.match(str(answer or ""))
#|    if match is None:
#|        raise ValueError("answer does not start with entailment. or contradiction.")
#|    name = match.group(1).lower()
#|    return name, LABELS[name]
#|
#|
#|def answer_from_record(record: Mapping[str, Any]) -> str:
#|    conversations = record.get("conversations")
#|    if not isinstance(conversations, list):
#|        raise ValueError(f"sample {record.get('id')} has no conversations")
#|    assistants = [
#|        turn.get("value", "")
#|        for turn in conversations
#|        if isinstance(turn, Mapping) and turn.get("from") == "gpt"
#|    ]
#|    if len(assistants) != 1:
#|        raise ValueError(
#|            f"sample {record.get('id')} must contain exactly one assistant answer"
#|        )
#|    return str(assistants[0])
#|
#|
#|def claim_from_record(record: Mapping[str, Any]) -> str:
#|    conversations = record.get("conversations")
#|    if not isinstance(conversations, list):
#|        return ""
#|    humans = [
#|        str(turn.get("value", ""))
#|        for turn in conversations
#|        if isinstance(turn, Mapping) and turn.get("from") == "human"
#|    ]
#|    if not humans:
#|        return ""
#|    value = humans[0].replace("<image>", " ")
#|    return normalize_text(value)
#|
#|
#|def assert_train_only_record(record: Mapping[str, Any]) -> None:
#|    image = str(record.get("image", "")).replace("\\", "/").lower()
#|    if "/test/" in f"/{image.lstrip('/')}":
#|        raise ValueError(f"CWCT train cache rejected test image: {image}")
#|    split = str(record.get("split", record.get("partition", ""))).lower()
#|    if split == "test":
#|        raise ValueError(f"CWCT train cache rejected test record: {record.get('id')}")
#|
#|
#|def _trim_span(answer: str, start: int, end: int) -> tuple[int, int]:
#|    while start < end and answer[start].isspace():
#|        start += 1
#|    while end > start and answer[end - 1].isspace():
#|        end -= 1
#|    return start, end
#|
#|
#|def _clause_candidates(answer: str, start: int, end: int) -> Iterator[tuple[int, int]]:
#|    """Yield exact subclauses while keeping character offsets auditable."""
#|
#|    text = answer[start:end]
#|    boundaries = [0]
#|    for match in re.finditer(r"[,;:]\s+|\s+--+\s+|\s+---+\s+", text):
#|        boundaries.extend((match.start(), match.end()))
#|    boundaries.append(len(text))
#|    unique = sorted(set(boundaries))
#|    for left, right in zip(unique, unique[1:]):
#|        absolute_left, absolute_right = _trim_span(
#|            answer, start + left, start + right
#|        )
#|        if absolute_left < absolute_right:
#|            yield absolute_left, absolute_right
#|
#|
#|def _span_family(text: str) -> tuple[str, int]:
#|    for priority, (family, pattern) in enumerate(_FAMILY_PATTERNS):
#|        if pattern.search(text):
#|            return family, len(_FAMILY_PATTERNS) - priority
#|    return "implicit_rule", 0
#|
#|
#|def _candidate_score(text: str, claim_tokens: set[str]) -> tuple[float, str, str]:
#|    tokens = content_tokens(text)
#|    family, trigger_score = _span_family(text)
#|    if not 4 <= len(tokens) <= 64:
#|        return -math.inf, family, "low"
#|    # A warrant must contain an explicit bridge/rule cue.  Unmarked rationale
#|    # prose is too easy to confuse with an observation or a conclusion.
#|    if family == "implicit_rule":
#|        return -math.inf, family, "low"
#|    if _OBSERVATION_PREFIX.search(text):
#|        return -math.inf, family, "low"
#|    if _CONCLUSION_MARKERS.search(text):
#|        return -math.inf, family, "low"
#|    if _RESTATEMENT_PREFIX.search(text):
#|        return -math.inf, family, "low"
#|    if _CONCLUSION_PREFIX.search(text):
#|        return -math.inf, family, "low"
#|    token_set = set(tokens)
#|    shared = len(token_set & claim_tokens)
#|    jaccard = shared / max(1, len(token_set | claim_tokens))
#|    claim_coverage = shared / max(1, len(claim_tokens))
#|    warrant_coverage = shared / max(1, len(token_set))
#|    # The two coverage terms catch long restatements for which Jaccard alone
#|    # can look deceptively small.  These are hard exclusions, not score nudges.
#|    if jaccard >= MAX_CLAIM_JACCARD or (
#|        claim_coverage >= MAX_CLAIM_COVERAGE
#|        and warrant_coverage >= MAX_WARRANT_CLAIM_COVERAGE
#|    ):
#|        return -math.inf, family, "low"
#|    score = float(trigger_score * 3)
#|    if 7 <= len(tokens) <= 40:
#|        score += 2.0
#|    if _WARRANT_FORM.search(text):
#|        score += 2.0
#|    quality = "high" if score >= 7.0 else "low"
#|    return score, family, quality
#|
#|
#|def extract_silver_warrant(answer: str, claim: str = "") -> WarrantSpan | None:
#|    """Select a deterministic exact span; never invent a warrant."""
#|
#|    parse_label(answer)
#|    label_match = _LABEL_RE.match(answer)
#|    if label_match is None:
#|        raise ValueError("answer label prefix disappeared after validation")
#|    claim_tokens = set(content_tokens(claim))
#|    candidates: list[tuple[float, int, int, str, str]] = []
#|    rationale_start = label_match.end()
#|    for sentence in _SENTENCE_RE.finditer(answer, rationale_start):
#|        sentence_start, sentence_end = _trim_span(
#|            answer, sentence.start(), sentence.end()
#|        )
#|        spans = {(sentence_start, sentence_end)}
#|        spans.update(_clause_candidates(answer, sentence_start, sentence_end))
#|        for start, end in spans:
#|            text = answer[start:end]
#|            score, family, quality = _candidate_score(text, claim_tokens)
#|            if math.isfinite(score):
#|                candidates.append((score, start, end, family, quality))
#|    if not candidates:
#|        return None
#|    # Stable under input-record reordering: offsets, not iteration order, break ties.
#|    score, start, end, family, quality = max(
#|        candidates,
#|        key=lambda row: (row[0], -(row[2] - row[1]), -row[1]),
#|    )
#|    if quality != "high":
#|        return None
#|    text = answer[start:end]
#|    if answer[start:end] != text:
#|        raise AssertionError("CWCT exact-span invariant failed")
#|    return WarrantSpan(text, start, end, family, quality)
#|
#|
#|def _id_key(value: Any) -> tuple[int, str]:
#|    text = str(value)
#|    try:
#|        return 0, f"{int(text):020d}"
#|    except ValueError:
#|        return 1, text
#|
#|
#|def _tensor_to_vector(value: Any) -> list[float]:
#|    if hasattr(value, "detach"):
#|        value = value.detach()
#|    if hasattr(value, "cpu"):
#|        value = value.cpu()
#|    if hasattr(value, "float"):
#|        value = value.float()
#|    if hasattr(value, "reshape"):
#|        value = value.reshape(-1)
#|    if hasattr(value, "tolist"):
#|        value = value.tolist()
#|    return [float(item) for item in value]
#|
#|
#|def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
#|    if len(left) != len(right) or not left:
#|        return -1.0
#|    dot = sum(a * b for a, b in zip(left, right))
#|    ln = math.sqrt(sum(a * a for a in left))
#|    rn = math.sqrt(sum(b * b for b in right))
#|    if ln <= 0.0 or rn <= 0.0:
#|        return -1.0
#|    return dot / (ln * rn)
#|
#|
#|def _jaccard(left: Iterable[str], right: Iterable[str]) -> float:
#|    a, b = set(left), set(right)
#|    if not a and not b:
#|        return 0.0
#|    return len(a & b) / max(1, len(a | b))
#|
#|
#|def inference_safe_signature(graph_record: Mapping[str, Any] | None) -> tuple[str, ...]:
#|    """Allow-list graph fields; deliberately ignores descriptions and metadata."""
#|
#|    if graph_record is None:
#|        return ()
#|    values: list[str] = []
#|    for key in ("visual_nodes", "claim_nodes"):
#|        field = graph_record.get(key, [])
#|        if isinstance(field, list):
#|            for item in field:
#|                values.extend(content_tokens(item))
#|    return tuple(sorted(set(values)))
#|
#|
#|def multimodal_similarity(
#|    source_feature: Mapping[str, Any],
#|    donor_feature: Mapping[str, Any],
#|) -> float:
#|    """Similarity over E_image/E_text only; E_desc is intentionally unreachable."""
#|
#|    image = _cosine(
#|        _tensor_to_vector(source_feature["E_image"]),
#|        _tensor_to_vector(donor_feature["E_image"]),
#|    )
#|    text = _cosine(
#|        _tensor_to_vector(source_feature["E_text"]),
#|        _tensor_to_vector(donor_feature["E_text"]),
#|    )
#|    return 0.55 * image + 0.45 * text
#|
#|
#|def _surface_similarity(left: str, right: str) -> float:
#|    return _jaccard(content_tokens(left), content_tokens(right))
#|
#|
#|def _donor_similarity(
#|    source: Mapping[str, Any],
#|    donor: Mapping[str, Any],
#|    features: Mapping[Any, Mapping[str, Any]] | None = None,
#|    *,
#|    precomputed_similarity: Mapping[str, float] | None = None,
#|) -> float:
#|    feature_score = None
#|    if precomputed_similarity is not None:
#|        feature_score = precomputed_similarity.get(str(donor["id"]))
#|    elif features is not None:
#|        source_id, donor_id = source["id"], donor["id"]
#|        source_feature = features.get(source_id, features.get(str(source_id)))
#|        donor_feature = features.get(donor_id, features.get(str(donor_id)))
#|        if source_feature is not None and donor_feature is not None:
#|            feature_score = multimodal_similarity(source_feature, donor_feature)
#|    if feature_score is not None:
#|        return float(feature_score)
#|    return _jaccard(source.get("signature", ()), donor.get("signature", ()))
#|
#|
#|def _select_warrant_donor(
#|    source: Mapping[str, Any],
#|    candidates: Sequence[Mapping[str, Any]],
#|    features: Mapping[Any, Mapping[str, Any]] | None = None,
#|    *,
#|    relation: str,
#|    minimum_similarity: float = 0.05,
#|    precomputed_similarity: Mapping[str, float] | None = None,
#|) -> tuple[Mapping[str, Any], float, float, float] | None:
#|    """Select an exact-span retrieval control under a strict relation."""
#|
#|    if relation not in {"same_label_hard_mismatch", "opposite_label_matched"}:
#|        raise ValueError(f"unknown CWCT donor relation: {relation}")
#|
#|    source_id = source["id"]
#|    source_label = int(source["label"])
#|    source_partition = str(source["partition"])
#|    source_span = source.get("silver_warrant")
#|    if not isinstance(source_span, Mapping):
#|        return None
#|    source_warrant = str(source_span["text"])
#|    source_tokens = content_tokens(source_warrant)
#|    best = None
#|    for donor in sorted(candidates, key=lambda row: _id_key(row["id"])):
#|        donor_label = int(donor["label"])
#|        if donor["id"] == source_id:
#|            continue
#|        # This check is deliberately repeated here rather than relying only on
#|        # the caller's pool construction: tune/dev leakage must fail closed.
#|        if str(donor.get("partition")) != source_partition:
#|            continue
#|        donor_warrant = donor.get("silver_warrant")
#|        if not isinstance(donor_warrant, Mapping):
#|            continue
#|        if donor_warrant.get("rule_family") != source_span.get("rule_family"):
#|            continue
#|        if relation == "same_label_hard_mismatch" and donor_label != source_label:
#|            continue
#|        if relation == "opposite_label_matched" and donor_label == source_label:
#|            continue
#|        donor_text = str(donor_warrant["text"])
#|        length_ratio = min(
#|            len(source_tokens), len(content_tokens(donor_text))
#|        ) / max(1, max(len(source_tokens), len(content_tokens(donor_text))))
#|        if length_ratio < MIN_DONOR_LENGTH_RATIO:
#|            continue
#|        surface = _surface_similarity(source_warrant, donor_text)
#|        if (
#|            relation == "same_label_hard_mismatch"
#|            and (
#|                donor_text == source_warrant
#|                or surface > MAX_MISMATCH_SURFACE_SIMILARITY
#|            )
#|        ):
#|            continue
#|        semantic = _donor_similarity(
#|            source,
#|            donor,
#|            features,
#|            precomputed_similarity=precomputed_similarity,
#|        )
#|        if semantic < minimum_similarity:
#|            continue
#|        if relation == "same_label_hard_mismatch":
#|            score = (semantic, length_ratio, -surface)
#|        else:
#|            score = (semantic, length_ratio, surface)
#|        # Candidates are ID-sorted, and ``>`` preserves the first ID on an
#|        # exact score tie.  This makes shuffled input files produce the same
#|        # donor assignment.
#|        if best is None or score > best[0]:
#|            best = (score, donor, semantic, length_ratio, surface)
#|    if best is None:
#|        return None
#|    _, donor, similarity, length_ratio, surface = best
#|    return donor, float(similarity), float(length_ratio), float(surface)
#|
#|
#|def select_same_label_hard_mismatch(
#|    source: Mapping[str, Any],
#|    candidates: Sequence[Mapping[str, Any]],
#|    features: Mapping[Any, Mapping[str, Any]] | None = None,
#|    *,
#|    minimum_similarity: float = 0.05,
#|    precomputed_similarity: Mapping[str, float] | None = None,
#|) -> tuple[Mapping[str, Any], float, float, float] | None:
#|    """Return a same-label, context-near, warrant-surface-mismatched donor."""
#|
#|    return _select_warrant_donor(
#|        source,
#|        candidates,
#|        features,
#|        relation="same_label_hard_mismatch",
#|        minimum_similarity=minimum_similarity,
#|        precomputed_similarity=precomputed_similarity,
#|    )
#|
#|
#|def select_opposite_label_matched_warrant(
#|    source: Mapping[str, Any],
#|    candidates: Sequence[Mapping[str, Any]],
#|    features: Mapping[Any, Mapping[str, Any]] | None = None,
#|    *,
#|    minimum_similarity: float = 0.05,
#|    precomputed_similarity: Mapping[str, float] | None = None,
#|) -> tuple[Mapping[str, Any], float, float, float] | None:
#|    """Return an opposite-label, context/rule-family-matched donor."""
#|
#|    return _select_warrant_donor(
#|        source,
#|        candidates,
#|        features,
#|        relation="opposite_label_matched",
#|        minimum_similarity=minimum_similarity,
#|        precomputed_similarity=precomputed_similarity,
#|    )
#|
#|
#|def _feature_neighbor_map(
#|    rows: Sequence[Mapping[str, Any]],
#|    features: Mapping[Any, Mapping[str, Any]],
#|    *,
#|    top_k: int = 256,
#|    batch_size: int = 128,
#|) -> dict[str, dict[str, dict[str, float]]]:
#|    """Vectorized, separately retained same/opposite-label shortlists.
#|
#|    A full Python O(N^2 D) loop is prohibitively slow for 4,578 examples.
#|    This helper computes the same allow-listed E_image/E_text score with
#|    batched matrix multiplication.  Rows must come from one partition; the
#|    caller builds tune and dev maps independently.
#|    """
#|
#|    try:
#|        import torch
#|    except ModuleNotFoundError:
#|        return {}
#|    if not rows:
#|        return {}
#|    rows = sorted(rows, key=lambda row: _id_key(row["id"]))
#|    partitions = {str(row.get("partition")) for row in rows}
#|    if len(partitions) != 1:
#|        raise ValueError("CWCT feature shortlist may contain only one partition")
#|
#|    def feature_for(sample_id: Any):
#|        value = features.get(sample_id, features.get(str(sample_id)))
#|        if value is None:
#|            raise KeyError(f"missing CWCT training feature: {sample_id}")
#|        return value
#|
#|    images = torch.stack(
#|        [
#|            torch.as_tensor(
#|                _tensor_to_vector(feature_for(row["id"])["E_image"]),
#|                dtype=torch.float32,
#|            )
#|            for row in rows
#|        ]
#|    )
#|    texts = torch.stack(
#|        [
#|            torch.as_tensor(
#|                _tensor_to_vector(feature_for(row["id"])["E_text"]),
#|                dtype=torch.float32,
#|            )
#|            for row in rows
#|        ]
#|    )
#|    images = torch.nn.functional.normalize(images, dim=1)
#|    texts = torch.nn.functional.normalize(texts, dim=1)
#|    labels = torch.tensor([int(row["label"]) for row in rows], dtype=torch.long)
#|    count = len(rows)
#|    keep = min(int(top_k), max(1, count - 1))
#|    output: dict[str, dict[str, dict[str, float]]] = {}
#|    with torch.no_grad():
#|        for start in range(0, count, int(batch_size)):
#|            end = min(count, start + int(batch_size))
#|            base_similarity = (
#|                0.55 * (images[start:end] @ images.transpose(0, 1))
#|                + 0.45 * (texts[start:end] @ texts.transpose(0, 1))
#|            )
#|            for local, source_row in enumerate(rows[start:end]):
#|                global_index = start + local
#|                same_invalid = labels.ne(labels[global_index])
#|                same_invalid[global_index] = True
#|                opposite_invalid = labels.eq(labels[global_index])
#|                groups = {
#|                    "same_label": same_invalid,
#|                    "opposite_label": opposite_invalid,
#|                }
#|                retained: dict[str, dict[str, float]] = {}
#|                for name, invalid in groups.items():
#|                    scores = base_similarity[local].masked_fill(
#|                        invalid, float("-inf")
#|                    )
#|                    # Stable sort over ID-sorted rows gives an ID tie-break and
#|                    # avoids top-k boundary nondeterminism.
#|                    indices = torch.argsort(
#|                        scores, descending=True, stable=True
#|                    )[:keep]
#|                    pairs: list[tuple[str, float]] = []
#|                    for index in indices.tolist():
#|                        value = float(scores[index].item())
#|                        if math.isfinite(value):
#|                            pairs.append((str(rows[index]["id"]), value))
#|                    retained[name] = dict(pairs)
#|                output[str(source_row["id"])] = retained
#|    return output
#|
#|
#|def _partition(sample_id: Any, dev_fraction: float, seed: int) -> str:
#|    digest = hashlib.sha256(f"{seed}:{sample_id}".encode("utf-8")).digest()
#|    value = int.from_bytes(digest[:8], "big") / float(2**64)
#|    return "dev" if value < dev_fraction else "tune"
#|
#|
#|def _pack_donor_control(
#|    selected: tuple[Mapping[str, Any], float, float, float]
#|) -> dict[str, Any]:
#|    donor, semantic, length_ratio, _surface = selected
#|    donor_span = donor["silver_warrant"]
#|    return {
#|        "text": donor_span["text"],
#|        "donor_id": donor["id"],
#|        "donor_label": donor["label"],
#|        "semantic_similarity": semantic,
#|        "length_ratio": length_ratio,
#|        "rule_family": donor_span["rule_family"],
#|        # There is deliberately no relaxed cross-family fallback in v2.
#|        "relaxation_level": 0,
#|    }
#|
#|
#|def build_warrant_records(
#|    train_records: Sequence[Mapping[str, Any]],
#|    graph_by_id: Mapping[Any, Mapping[str, Any]] | None = None,
#|    features: Mapping[Any, Mapping[str, Any]] | None = None,
#|    *,
#|    seed: int = 2026,
#|    dev_fraction: float = 0.10,
#|    minimum_similarity: float = 0.05,
#|) -> list[dict[str, Any]]:
#|    if not 0.0 < dev_fraction < 0.5:
#|        raise ValueError("dev_fraction must be in (0, 0.5)")
#|    graph_by_id = graph_by_id or {}
#|    seen: set[str] = set()
#|    provisional: list[dict[str, Any]] = []
#|    for raw in sorted(train_records, key=lambda row: _id_key(row.get("id"))):
#|        assert_train_only_record(raw)
#|        sample_id = raw.get("id")
#|        key = str(sample_id)
#|        if key in seen:
#|            raise ValueError(f"duplicate CWCT training id: {sample_id}")
#|        seen.add(key)
#|        answer = answer_from_record(raw)
#|        label_name, label = parse_label(answer)
#|        claim = claim_from_record(raw)
#|        span = extract_silver_warrant(answer, claim)
#|        graph = graph_by_id.get(sample_id, graph_by_id.get(key))
#|        row: dict[str, Any] = {
#|            "schema_version": SCHEMA_VERSION,
#|            "id": sample_id,
#|            "partition": _partition(sample_id, dev_fraction, seed),
#|            "label": label,
#|            "label_name": label_name,
#|            "answer_sha256": hashlib.sha256(answer.encode("utf-8")).hexdigest(),
#|            "signature": inference_safe_signature(graph),
#|            "silver_warrant": None,
#|            "same_label_hard_mismatch": None,
#|            "opposite_label_matched_warrant": None,
#|            "auxiliary_eligible": False,
#|            "ineligible_reason": "no_reliable_silver_warrant",
#|        }
#|        if span is not None:
#|            row["silver_warrant"] = {
#|                "text": span.text,
#|                "char_start": span.char_start,
#|                "char_end": span.char_end,
#|                "rule_family": span.rule_family,
#|                "quality": span.quality,
#|            }
#|        provisional.append(row)
#|
#|    pools = {
#|        partition: [
#|            row
#|            for row in provisional
#|            if row["partition"] == partition and row["silver_warrant"] is not None
#|        ]
#|        for partition in ("tune", "dev")
#|    }
#|    neighbor_map: dict[str, dict[str, dict[str, float]]] = {}
#|    if features is not None:
#|        for partition in ("tune", "dev"):
#|            neighbor_map.update(_feature_neighbor_map(pools[partition], features))
#|
#|    for partition in ("tune", "dev"):
#|        pool = pools[partition]
#|        pool_by_id = {str(candidate["id"]): candidate for candidate in pool}
#|        for row in pool:
#|            shortlists = neighbor_map.get(str(row["id"]))
#|            if shortlists is None:
#|                same_candidates = pool
#|                opposite_candidates = pool
#|                same_similarity = None
#|                opposite_similarity = None
#|                selector_features = features
#|            else:
#|                same_similarity = shortlists.get("same_label", {})
#|                opposite_similarity = shortlists.get("opposite_label", {})
#|                same_candidates = [
#|                    pool_by_id[key]
#|                    for key in same_similarity
#|                    if key in pool_by_id
#|                ]
#|                opposite_candidates = [
#|                    pool_by_id[key]
#|                    for key in opposite_similarity
#|                    if key in pool_by_id
#|                ]
#|                selector_features = None
#|            same_selected = select_same_label_hard_mismatch(
#|                row,
#|                same_candidates,
#|                selector_features,
#|                minimum_similarity=minimum_similarity,
#|                precomputed_similarity=same_similarity,
#|            )
#|            opposite_selected = select_opposite_label_matched_warrant(
#|                row,
#|                opposite_candidates,
#|                selector_features,
#|                minimum_similarity=minimum_similarity,
#|                precomputed_similarity=opposite_similarity,
#|            )
#|            # The contract is atomic: a record exposes both controls or neither.
#|            # Partial donor assignments cannot silently change the training set.
#|            if same_selected is None or opposite_selected is None:
#|                if same_selected is None and opposite_selected is None:
#|                    reason = "missing_both_partition_local_controls"
#|                elif same_selected is None:
#|                    reason = "missing_same_label_hard_mismatch"
#|                else:
#|                    reason = "missing_opposite_label_matched_warrant"
#|                row["ineligible_reason"] = reason
#|                continue
#|            row["same_label_hard_mismatch"] = _pack_donor_control(same_selected)
#|            row["opposite_label_matched_warrant"] = _pack_donor_control(
#|                opposite_selected
#|            )
#|            row["auxiliary_eligible"] = True
#|            row["ineligible_reason"] = None
#|
#|    for row in provisional:
#|        row["signature"] = list(row["signature"])
#|    source_answers = {
#|        str(raw["id"]): answer_from_record(raw) for raw in train_records
#|    }
#|    validate_warrant_records(
#|        provisional,
#|        expected_ids=seen,
#|        source_answers=source_answers,
#|    )
#|    return provisional
#|
#|
#|def validate_warrant_records(
#|    records: Sequence[Mapping[str, Any]],
#|    *,
#|    expected_ids: Iterable[Any] | None = None,
#|    source_answers: Mapping[Any, str] | None = None,
#|) -> None:
#|    seen: set[str] = set()
#|    by_id: dict[str, Mapping[str, Any]] = {}
#|    for record in records:
#|        key = str(record["id"])
#|        if key in by_id:
#|            raise ValueError(f"duplicate CWCT warrant id: {key}")
#|        by_id[key] = record
#|    normalized_answers = (
#|        {str(key): str(value) for key, value in source_answers.items()}
#|        if source_answers is not None
#|        else None
#|    )
#|
#|    for record in records:
#|        if record.get("schema_version") != SCHEMA_VERSION:
#|            raise ValueError("unexpected CWCT warrant schema")
#|        key = str(record["id"])
#|        if key in seen:
#|            raise ValueError(f"duplicate CWCT warrant id: {key}")
#|        seen.add(key)
#|        partition = record.get("partition")
#|        if partition not in {"tune", "dev"}:
#|            raise ValueError(f"invalid train-only partition for {key}")
#|        if "counter_warrant" in record or "counter_answer" in record:
#|            raise ValueError(f"sample {key} contains legacy counterfactual fields")
#|
#|        expected_label_name = next(
#|            (name for name, value in LABELS.items() if value == int(record["label"])),
#|            None,
#|        )
#|        if record.get("label_name") != expected_label_name:
#|            raise ValueError(f"sample {key} has inconsistent label fields")
#|        silver = record.get("silver_warrant")
#|        if silver is not None:
#|            if not isinstance(silver, Mapping):
#|                raise ValueError(f"sample {key} has malformed silver warrant")
#|            if silver.get("quality") != "high":
#|                raise ValueError(f"sample {key} has non-high-quality silver warrant")
#|            if silver.get("rule_family") == "implicit_rule":
#|                raise ValueError(f"sample {key} has ungrounded implicit-rule span")
#|            if not normalize_text(silver.get("text")):
#|                raise ValueError(f"sample {key} has an empty silver warrant")
#|
#|        if normalized_answers is not None:
#|            if key not in normalized_answers:
#|                raise ValueError(f"sample {key} lacks a source answer for validation")
#|            answer = normalized_answers[key]
#|            answer_hash = hashlib.sha256(answer.encode("utf-8")).hexdigest()
#|            if record.get("answer_sha256") != answer_hash:
#|                raise ValueError(f"sample {key} answer SHA256 mismatch")
#|            label_name, label = parse_label(answer)
#|            if label != int(record["label"]) or label_name != record.get("label_name"):
#|                raise ValueError(f"sample {key} source answer label mismatch")
#|            if isinstance(silver, Mapping):
#|                start, end = silver.get("char_start"), silver.get("char_end")
#|                if not isinstance(start, int) or not isinstance(end, int):
#|                    raise ValueError(f"sample {key} has non-integer warrant offsets")
#|                if start < 0 or end <= start or end > len(answer):
#|                    raise ValueError(f"sample {key} has out-of-range warrant offsets")
#|                if answer[start:end] != silver.get("text"):
#|                    raise ValueError(f"sample {key} silver warrant is not source-exact")
#|
#|        same = record.get("same_label_hard_mismatch")
#|        opposite = record.get("opposite_label_matched_warrant")
#|        if record.get("auxiliary_eligible"):
#|            if not isinstance(silver, Mapping):
#|                raise ValueError(f"eligible sample {key} lacks a silver warrant")
#|            if not isinstance(same, Mapping) or not isinstance(opposite, Mapping):
#|                raise ValueError(f"eligible sample {key} lacks its dual controls")
#|            if record.get("ineligible_reason") is not None:
#|                raise ValueError(f"eligible sample {key} has an ineligible reason")
#|            for field, control, relation in (
#|                ("same_label_hard_mismatch", same, "same"),
#|                ("opposite_label_matched_warrant", opposite, "opposite"),
#|            ):
#|                donor_key = str(control.get("donor_id"))
#|                donor = by_id.get(donor_key)
#|                if donor is None or donor_key == key:
#|                    raise ValueError(f"sample {key} has invalid {field} donor")
#|                if donor.get("partition") != partition:
#|                    raise ValueError(f"sample {key} {field} crosses partitions")
#|                donor_span = donor.get("silver_warrant")
#|                if not isinstance(donor_span, Mapping):
#|                    raise ValueError(f"sample {key} {field} donor lacks a span")
#|                if control.get("text") != donor_span.get("text"):
#|                    raise ValueError(f"sample {key} {field} is not donor-exact")
#|                donor_label = int(donor["label"])
#|                if int(control.get("donor_label")) != donor_label:
#|                    raise ValueError(f"sample {key} {field} donor label mismatch")
#|                if relation == "same" and donor_label != int(record["label"]):
#|                    raise ValueError(f"sample {key} same-label donor has wrong label")
#|                if relation == "opposite" and donor_label == int(record["label"]):
#|                    raise ValueError(f"sample {key} opposite donor has wrong label")
#|                if (
#|                    control.get("rule_family") != donor_span.get("rule_family")
#|                    or donor_span.get("rule_family") != silver.get("rule_family")
#|                ):
#|                    raise ValueError(f"sample {key} {field} violates family matching")
#|                if control.get("relaxation_level") != 0:
#|                    raise ValueError(f"sample {key} {field} uses a relaxed fallback")
#|                source_tokens = content_tokens(str(silver["text"]))
#|                donor_tokens = content_tokens(str(donor_span["text"]))
#|                expected_ratio = min(len(source_tokens), len(donor_tokens)) / max(
#|                    1, max(len(source_tokens), len(donor_tokens))
#|                )
#|                try:
#|                    ratio = float(control.get("length_ratio"))
#|                    semantic = float(control.get("semantic_similarity"))
#|                except (TypeError, ValueError) as error:
#|                    raise ValueError(f"sample {key} {field} has invalid metrics") from error
#|                if not math.isfinite(semantic) or not -1.00001 <= semantic <= 1.00001:
#|                    raise ValueError(f"sample {key} {field} similarity is invalid")
#|                if not math.isclose(ratio, expected_ratio, abs_tol=1e-12):
#|                    raise ValueError(f"sample {key} {field} length ratio mismatch")
#|                if ratio < MIN_DONOR_LENGTH_RATIO:
#|                    raise ValueError(f"sample {key} {field} donor is length-unmatched")
#|                if relation == "same":
#|                    surface = _surface_similarity(
#|                        str(silver["text"]), str(donor_span["text"])
#|                    )
#|                    if (
#|                        donor_span.get("text") == silver.get("text")
#|                        or surface > MAX_MISMATCH_SURFACE_SIMILARITY
#|                    ):
#|                        raise ValueError(
#|                            f"sample {key} same-label donor is not a hard mismatch"
#|                        )
#|        else:
#|            if same is not None or opposite is not None:
#|                raise ValueError(f"ineligible sample {key} contains partial controls")
#|            if not record.get("ineligible_reason"):
#|                raise ValueError(f"ineligible sample {key} lacks an audit reason")
#|    if expected_ids is not None:
#|        expected = {str(value) for value in expected_ids}
#|        if seen != expected:
#|            raise ValueError(
#|                f"CWCT cache id mismatch: missing={sorted(expected-seen)[:5]} "
#|                f"extra={sorted(seen-expected)[:5]}"
#|            )
#|
#|
#|def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
#|    output = []
#|    with Path(path).open("r", encoding="utf-8") as handle:
#|        for line_number, line in enumerate(handle, 1):
#|            if not line.strip():
#|                continue
#|            try:
#|                output.append(json.loads(line))
#|            except json.JSONDecodeError as error:
#|                raise ValueError(f"invalid JSONL at {path}:{line_number}") from error
#|    return output
#|
#|
#|def load_warrant_map(path: str | Path) -> dict[str, dict[str, Any]]:
#|    records = read_jsonl(path)
#|    validate_warrant_records(records)
#|    return {str(record["id"]): record for record in records}
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: dome_ft_data.py ===
#|"""Training-only data construction for DOME-FT.
#|
#|DOME-FT mines fluent mistakes sampled from the current policy.  This module
#|does not read concept-graph caches or test annotations.  It pairs one
#|same-verdict, near-gold policy explanation with either the gold explanation or
#|an optional, independently audited minimal repair.
#|"""
#|
#|from __future__ import annotations
#|
#|import argparse
#|import copy
#|import json
#|import math
#|import re
#|from collections import Counter
#|from difflib import SequenceMatcher
#|from pathlib import Path
#|from typing import Any, Iterable
#|
#|
#|LABEL_RE = re.compile(
#|    r"^\s*(entailment|entails?|entailed|contradiction|contradicts?|contradicted|[01])\b[\s:;,.!?-]*",
#|    re.IGNORECASE,
#|)
#|WORD_RE = re.compile(r"[a-z0-9][a-z0-9'-]*", re.IGNORECASE)
#|STOPWORDS = {
#|    "a", "an", "and", "are", "as", "at", "be", "because", "by", "for",
#|    "from", "has", "have", "he", "her", "here", "his", "in", "is", "it",
#|    "its", "of", "on", "or", "she", "that", "the", "their", "there", "they",
#|    "this", "to", "was", "were", "which", "while", "with", "would",
#|}
#|
#|
#|def clean_text(value: Any) -> str:
#|    return " ".join(str(value or "").strip().split())
#|
#|
#|def parse_label(value: Any) -> int | None:
#|    match = LABEL_RE.match(clean_text(value))
#|    if not match:
#|        return None
#|    token = match.group(1).lower()
#|    return int(token.startswith("entail") or token == "1")
#|
#|
#|def strip_label(value: Any) -> str:
#|    return clean_text(LABEL_RE.sub("", clean_text(value), count=1))
#|
#|
#|def answer_from_sample(sample: dict[str, Any]) -> str:
#|    for message in reversed(sample.get("conversations") or []):
#|        if not isinstance(message, dict):
#|            continue
#|        speaker = clean_text(message.get("from")).lower()
#|        if speaker in {"gpt", "assistant", "model"}:
#|            return clean_text(message.get("value"))
#|    return ""
#|
#|
#|def replace_answer(sample: dict[str, Any], answer: str) -> dict[str, Any]:
#|    output = copy.deepcopy(sample)
#|    for message in reversed(output.get("conversations") or []):
#|        if not isinstance(message, dict):
#|            continue
#|        speaker = clean_text(message.get("from")).lower()
#|        if speaker in {"gpt", "assistant", "model"}:
#|            message["value"] = clean_text(answer)
#|            return output
#|    raise ValueError(f"sample {sample.get('id')} has no assistant answer")
#|
#|
#|def label_word(label: int) -> str:
#|    return "entailment" if int(label) == 1 else "contradiction"
#|
#|
#|def normalized_tokens(value: Any) -> list[str]:
#|    return [
#|        token.lower()
#|        for token in WORD_RE.findall(clean_text(value))
#|        if token.lower() not in STOPWORDS
#|    ]
#|
#|
#|def token_f1(left: Any, right: Any) -> float:
#|    left_counts = Counter(normalized_tokens(left))
#|    right_counts = Counter(normalized_tokens(right))
#|    if not left_counts or not right_counts:
#|        return 0.0
#|    overlap = sum((left_counts & right_counts).values())
#|    precision = overlap / sum(left_counts.values())
#|    recall = overlap / sum(right_counts.values())
#|    return 2.0 * precision * recall / max(1e-12, precision + recall)
#|
#|
#|def sequence_similarity(left: Any, right: Any) -> float:
#|    left_norm = " ".join(normalized_tokens(left))
#|    right_norm = " ".join(normalized_tokens(right))
#|    if not left_norm or not right_norm:
#|        return 0.0
#|    return SequenceMatcher(None, left_norm, right_norm).ratio()
#|
#|
#|def candidate_statistics(candidate: str, gold: str) -> dict[str, float]:
#|    candidate_words = max(1, len(WORD_RE.findall(candidate)))
#|    gold_words = max(1, len(WORD_RE.findall(gold)))
#|    lexical = token_f1(candidate, gold)
#|    sequence = sequence_similarity(candidate, gold)
#|    similarity = 0.75 * lexical + 0.25 * sequence
#|    return {
#|        "token_f1": lexical,
#|        "sequence_similarity": sequence,
#|        "similarity": similarity,
#|        "candidate_words": float(candidate_words),
#|        "gold_words": float(gold_words),
#|        "length_ratio": candidate_words / gold_words,
#|    }
#|
#|
#|def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
#|    records: list[dict[str, Any]] = []
#|    with Path(path).open("r", encoding="utf-8") as handle:
#|        for line_number, line in enumerate(handle, start=1):
#|            if not line.strip():
#|                continue
#|            try:
#|                row = json.loads(line)
#|            except json.JSONDecodeError as error:
#|                raise ValueError(f"invalid JSONL at {path}:{line_number}") from error
#|            if isinstance(row, dict):
#|                records.append(row)
#|    return records
#|
#|
#|def load_repairs(path: str | Path | None) -> dict[tuple[str, int], dict[str, Any]]:
#|    if path is None:
#|        return {}
#|    repairs: dict[tuple[str, int], dict[str, Any]] = {}
#|    for row in load_jsonl(path):
#|        if not bool(row.get("valid", False)):
#|            continue
#|        explanation = clean_text(row.get("repaired_explanation"))
#|        if not explanation:
#|            continue
#|        key = (str(row.get("id")), int(row.get("candidate_index", 0)))
#|        repairs[key] = row
#|    return repairs
#|
#|
#|def index_candidates(
#|    rows: Iterable[dict[str, Any]],
#|) -> dict[str, list[dict[str, Any]]]:
#|    output: dict[str, list[dict[str, Any]]] = {}
#|    seen: set[tuple[str, int]] = set()
#|    for row in rows:
#|        key = (str(row.get("id")), int(row.get("candidate_index", 0)))
#|        if key in seen:
#|            raise ValueError(f"duplicate DOME candidate key: {key}")
#|        seen.add(key)
#|        output.setdefault(key[0], []).append(row)
#|    return output
#|
#|
#|def select_policy_error(
#|    sample: dict[str, Any],
#|    candidates: Iterable[dict[str, Any]],
#|    *,
#|    minimum_words: int,
#|    minimum_similarity: float,
#|    maximum_similarity: float,
#|    minimum_length_ratio: float,
#|    maximum_length_ratio: float,
#|) -> tuple[dict[str, Any] | None, dict[str, int]]:
#|    gold_answer = answer_from_sample(sample)
#|    gold_label = parse_label(gold_answer)
#|    gold = strip_label(gold_answer)
#|    reasons: Counter[str] = Counter()
#|    eligible: list[dict[str, Any]] = []
#|    for row in candidates:
#|        if row.get("error"):
#|            reasons["generation_error"] += 1
#|            continue
#|        candidate_label = row.get("label")
#|        if candidate_label is None:
#|            candidate_label = parse_label(row.get("raw_response"))
#|        if candidate_label is None or int(candidate_label) != gold_label:
#|            reasons["verdict_mismatch"] += 1
#|            continue
#|        candidate = clean_text(
#|            row.get("explanation") or strip_label(row.get("raw_response"))
#|        )
#|        if len(WORD_RE.findall(candidate)) < minimum_words:
#|            reasons["too_short"] += 1
#|            continue
#|        stats = candidate_statistics(candidate, gold)
#|        if not minimum_length_ratio <= stats["length_ratio"] <= maximum_length_ratio:
#|            reasons["length_ratio"] += 1
#|            continue
#|        if stats["similarity"] < minimum_similarity:
#|            reasons["too_easy"] += 1
#|            continue
#|        if stats["similarity"] > maximum_similarity:
#|            reasons["possible_paraphrase"] += 1
#|            continue
#|        enriched = dict(row)
#|        enriched["explanation"] = candidate
#|        enriched["dome_stats"] = stats
#|        # Prefer the most gold-like error after excluding probable paraphrases.
#|        enriched["dome_hardness"] = (
#|            stats["similarity"] - 0.08 * abs(math.log(stats["length_ratio"]))
#|        )
#|        eligible.append(enriched)
#|    if not eligible:
#|        return None, dict(reasons)
#|    eligible.sort(
#|        key=lambda row: (
#|            float(row["dome_hardness"]),
#|            -int(row.get("candidate_index", 0)),
#|        ),
#|        reverse=True,
#|    )
#|    return eligible[0], dict(reasons)
#|
#|
#|def build_dome_pairs(
#|    train_json: str | Path,
#|    candidates_jsonl: str | Path,
#|    output_dir: str | Path,
#|    *,
#|    repairs_jsonl: str | Path | None = None,
#|    minimum_words: int = 12,
#|    minimum_similarity: float = 0.28,
#|    maximum_similarity: float = 0.78,
#|    minimum_length_ratio: float = 0.55,
#|    maximum_length_ratio: float = 1.65,
#|    minimum_pairs: int = 1,
#|    allowed_ids: set[str] | None = None,
#|    output_prefix: str = "dome_ft",
#|    method_name: str = "decision_locked_on_policy_mechanism_error_finetuning_v1",
#|) -> tuple[Path, Path, Path]:
#|    with Path(train_json).open("r", encoding="utf-8") as handle:
#|        samples = json.load(handle)
#|    if not isinstance(samples, list) or not samples:
#|        raise ValueError(f"empty or invalid train JSON: {train_json}")
#|    if allowed_ids is not None:
#|        allowed_ids = {str(value) for value in allowed_ids}
#|        samples = [
#|            sample for sample in samples if str(sample.get("id")) in allowed_ids
#|        ]
#|        found = {str(sample.get("id")) for sample in samples}
#|        missing = allowed_ids - found
#|        if missing:
#|            raise ValueError(f"pair builder is missing {len(missing)} allowed ids")
#|    candidates = index_candidates(load_jsonl(candidates_jsonl))
#|    repairs = load_repairs(repairs_jsonl)
#|    chosen_rows: list[dict[str, Any]] = []
#|    rejected_rows: list[dict[str, Any]] = []
#|    pair_records: list[dict[str, Any]] = []
#|    rejection_counts: Counter[str] = Counter()
#|    repair_count = 0
#|
#|    for sample in samples:
#|        selected, reasons = select_policy_error(
#|            sample,
#|            candidates.get(str(sample.get("id")), []),
#|            minimum_words=minimum_words,
#|            minimum_similarity=minimum_similarity,
#|            maximum_similarity=maximum_similarity,
#|            minimum_length_ratio=minimum_length_ratio,
#|            maximum_length_ratio=maximum_length_ratio,
#|        )
#|        rejection_counts.update(reasons)
#|        if selected is None:
#|            rejection_counts["sample_without_pair"] += 1
#|            continue
#|        gold_answer = answer_from_sample(sample)
#|        gold_label = parse_label(gold_answer)
#|        if gold_label is None:
#|            raise ValueError(f"unparseable gold verdict for id={sample.get('id')}")
#|        candidate_index = int(selected.get("candidate_index", 0))
#|        repair = repairs.get((str(sample.get("id")), candidate_index))
#|        if repair is not None:
#|            chosen_explanation = clean_text(repair["repaired_explanation"])
#|            chosen_source = "audited_minimal_repair"
#|            repair_count += 1
#|        else:
#|            chosen_explanation = strip_label(gold_answer)
#|            chosen_source = "gold_rationale"
#|        rejected_explanation = clean_text(selected["explanation"])
#|        chosen_answer = f"{label_word(gold_label)}. {chosen_explanation}"
#|        rejected_answer = f"{label_word(gold_label)}. {rejected_explanation}"
#|        if clean_text(chosen_answer).lower() == clean_text(rejected_answer).lower():
#|            rejection_counts["identical_pair"] += 1
#|            continue
#|        chosen_rows.append(replace_answer(sample, chosen_answer))
#|        rejected_rows.append(replace_answer(sample, rejected_answer))
#|        pair_records.append(
#|            {
#|                "id": sample.get("id"),
#|                "candidate_index": candidate_index,
#|                "chosen_source": chosen_source,
#|                "similarity": selected["dome_stats"]["similarity"],
#|                "token_f1": selected["dome_stats"]["token_f1"],
#|                "length_ratio": selected["dome_stats"]["length_ratio"],
#|            }
#|        )
#|
#|    if len(chosen_rows) < int(minimum_pairs):
#|        raise RuntimeError(
#|            f"DOME valid pairs {len(chosen_rows)} below minimum {minimum_pairs}; "
#|            f"rejections={dict(rejection_counts)}"
#|        )
#|    output = Path(output_dir)
#|    output.mkdir(parents=True, exist_ok=True)
#|    chosen_path = output / f"{output_prefix}_chosen_train.json"
#|    rejected_path = output / f"{output_prefix}_rejected_train.json"
#|    audit_path = output / f"{output_prefix}_pair_audit.json"
#|    with chosen_path.open("w", encoding="utf-8") as handle:
#|        json.dump(chosen_rows, handle, ensure_ascii=False, indent=2)
#|    with rejected_path.open("w", encoding="utf-8") as handle:
#|        json.dump(rejected_rows, handle, ensure_ascii=False, indent=2)
#|    similarities = [float(row["similarity"]) for row in pair_records]
#|    length_ratios = [float(row["length_ratio"]) for row in pair_records]
#|    audit = {
#|        "method": method_name,
#|        "train_samples": len(samples),
#|        "candidate_records": sum(len(values) for values in candidates.values()),
#|        "candidate_sample_ids": len(candidates),
#|        "valid_pairs": len(pair_records),
#|        "coverage": len(pair_records) / len(samples),
#|        "audited_minimal_repairs": repair_count,
#|        "gold_rationale_fallbacks": len(pair_records) - repair_count,
#|        "mean_similarity": sum(similarities) / max(1, len(similarities)),
#|        "mean_length_ratio": sum(length_ratios) / max(1, len(length_ratios)),
#|        "rejections": dict(sorted(rejection_counts.items())),
#|        "thresholds": {
#|            "minimum_words": minimum_words,
#|            "minimum_similarity": minimum_similarity,
#|            "maximum_similarity": maximum_similarity,
#|            "minimum_length_ratio": minimum_length_ratio,
#|            "maximum_length_ratio": maximum_length_ratio,
#|        },
#|        "pairs": pair_records,
#|        "test_annotations_accessed": False,
#|        "concept_graph_accessed_by_pair_builder": False,
#|        "allowed_id_filter": allowed_ids is not None,
#|    }
#|    with audit_path.open("w", encoding="utf-8") as handle:
#|        json.dump(audit, handle, ensure_ascii=False, indent=2)
#|    print(
#|        f"[dome-ft-data] pairs={len(pair_records)}/{len(samples)} "
#|        f"coverage={audit['coverage']:.2%} repairs={repair_count} "
#|        f"mean_similarity={audit['mean_similarity']:.3f}"
#|    )
#|    return chosen_path, rejected_path, audit_path
#|
#|
#|def parse_args() -> argparse.Namespace:
#|    parser = argparse.ArgumentParser()
#|    parser.add_argument("--train_json", required=True)
#|    parser.add_argument("--candidates_jsonl", required=True)
#|    parser.add_argument("--output_dir", required=True)
#|    parser.add_argument("--repairs_jsonl", default=None)
#|    parser.add_argument("--minimum_words", type=int, default=12)
#|    parser.add_argument("--minimum_similarity", type=float, default=0.28)
#|    parser.add_argument("--maximum_similarity", type=float, default=0.78)
#|    parser.add_argument("--minimum_length_ratio", type=float, default=0.55)
#|    parser.add_argument("--maximum_length_ratio", type=float, default=1.65)
#|    parser.add_argument("--minimum_pairs", type=int, default=1)
#|    return parser.parse_args()
#|
#|
#|def main() -> None:
#|    args = parse_args()
#|    build_dome_pairs(
#|        args.train_json,
#|        args.candidates_jsonl,
#|        args.output_dir,
#|        repairs_jsonl=args.repairs_jsonl,
#|        minimum_words=args.minimum_words,
#|        minimum_similarity=args.minimum_similarity,
#|        maximum_similarity=args.maximum_similarity,
#|        minimum_length_ratio=args.minimum_length_ratio,
#|        maximum_length_ratio=args.maximum_length_ratio,
#|        minimum_pairs=args.minimum_pairs,
#|    )
#|
#|
#|if __name__ == "__main__":
#|    main()
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: final_original_verifier.py ===
#|"""Standalone IESFD scorer; role width is explicit, no RIFT model is instantiated."""
#|def make_verifier(torch,hidden_size,role_size=1024):
#|    from iesfd_stage_10 import VERIFIER_DIM,VERIFIER_FEATURE_DIM,make_iesfd_v10_readout_classes
#|    _,Legacy=make_iesfd_v10_readout_classes(torch,torch.nn)
#|    nn=torch.nn
#|    class Verifier(nn.Module):
#|        score_evidence_candidates=Legacy.score_evidence_candidates
#|        def __init__(self):
#|            super().__init__()
#|            self.iesfd_v10_hidden=nn.Sequential(nn.LayerNorm(hidden_size),nn.Linear(hidden_size,VERIFIER_DIM),nn.GELU(),nn.Linear(VERIFIER_DIM,VERIFIER_DIM))
#|            self.iesfd_v10_role=nn.Sequential(nn.LayerNorm(role_size),nn.Linear(role_size,VERIFIER_DIM,bias=False))
#|            self.iesfd_v10_score=nn.Sequential(nn.LayerNorm(VERIFIER_FEATURE_DIM),nn.Linear(VERIFIER_FEATURE_DIM,32),nn.GELU(),nn.Linear(32,1))
#|            for layer in self.iesfd_v10_hidden.modules():
#|                if isinstance(layer,nn.Linear):
#|                    nn.init.normal_(layer.weight,std=1e-3)
#|                    if layer.bias is not None:nn.init.zeros_(layer.bias)
#|            nn.init.normal_(self.iesfd_v10_role[1].weight,std=1e-3)
#|            nn.init.normal_(self.iesfd_v10_score[-1].weight,std=1e-2);nn.init.zeros_(self.iesfd_v10_score[-1].bias)
#|            self._iesfd_v10_roles=None
#|    return Verifier()
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: g_mipo_loss.py ===
#|from __future__ import annotations
#|
#|
#|def mutual_information_preference_loss(
#|    chosen_logps,
#|    rejected_logps,
#|    *,
#|    beta: float = 0.08,
#|    margin: float = 0.0,
#|    reference_free: bool = True,
#|):
#|    """Reference-free preference loss that increases chosen mutual evidence."""
#|    if not reference_free:
#|        raise ValueError("G-MIPO v1 expects reference_free=True")
#|    advantage = beta * (chosen_logps - rejected_logps - margin)
#|    return chosen_logps.new_zeros(()) + __import__("torch").nn.functional.softplus(-advantage).mean()
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: gesv_stage_2_counterfactual.py ===
#|"""Local counterfactuals and span alignment for GESV-v2.
#|
#|GESV-v1 replaced visual and figurative clauses with text from another sample.
#|That made the negative answer topically unrelated and allowed the language
#|model to solve the ranking task without checking evidence sufficiency.
#|
#|GESV-v2 instead makes one minimal, within-sample semantic edit for each of the
#|visual, figurative, and claim-relation roles.  Training code scores only the
#|small token window changed by that edit.
#|"""
#|
#|from __future__ import annotations
#|
#|from collections import Counter
#|from difflib import SequenceMatcher
#|import re
#|from typing import Any, Iterable, Sequence
#|
#|
#|ROLE_NAMES = ("visual", "figurative", "relation")
#|
#|_LABEL_RE = re.compile(
#|    r"^\s*(?P<label>entailment|contradiction)\b[\s:;,.!?-]*",
#|    flags=re.IGNORECASE,
#|)
#|_SENTENCE_RE = re.compile(r"[^.!?]+(?:[.!?]+|$)")
#|
#|_VISUAL_CUES = (
#|    "image",
#|    "picture",
#|    "photo",
#|    "scene",
#|    "depict",
#|    "show",
#|    "display",
#|    "visible",
#|    "appears",
#|    "wearing",
#|    "holding",
#|    "standing",
#|    "sitting",
#|)
#|_FIGURATIVE_CUES = (
#|    "metaphor",
#|    "idiom",
#|    "simile",
#|    "figurative",
#|    "sarcas",
#|    "humor",
#|    "symbol",
#|    "represent",
#|    "means",
#|    "meaning",
#|    "suggest",
#|    "imply",
#|    "evoke",
#|    "comparison",
#|)
#|_RELATION_CUES = (
#|    "entail",
#|    "contradict",
#|    "support",
#|    "refute",
#|    "align",
#|    "consistent",
#|    "inconsistent",
#|    "claim",
#|    "therefore",
#|    "thus",
#|    "because",
#|)
#|
#|_VISUAL_SWAPS = (
#|    ("left", "right"),
#|    ("above", "below"),
#|    ("inside", "outside"),
#|    ("indoors", "outdoors"),
#|    ("open", "closed"),
#|    ("empty", "full"),
#|    ("standing", "sitting"),
#|    ("sitting", "standing"),
#|    ("up", "down"),
#|    ("black", "white"),
#|    ("white", "black"),
#|    ("day", "night"),
#|    ("night", "day"),
#|    ("man", "woman"),
#|    ("woman", "man"),
#|    ("boy", "girl"),
#|    ("girl", "boy"),
#|    ("dog", "cat"),
#|    ("cat", "dog"),
#|    ("one", "two"),
#|    ("two", "one"),
#|)
#|_FIGURATIVE_SWAPS = (
#|    ("hope", "despair"),
#|    ("despair", "hope"),
#|    ("success", "failure"),
#|    ("failure", "success"),
#|    ("strength", "weakness"),
#|    ("weakness", "strength"),
#|    ("freedom", "control"),
#|    ("control", "freedom"),
#|    ("positive", "negative"),
#|    ("negative", "positive"),
#|    ("unity", "division"),
#|    ("division", "unity"),
#|    ("calm", "chaos"),
#|    ("chaos", "calm"),
#|)
#|
#|_PREDICATE_TOGGLES = (
#|    (re.compile(r"\bdoes\s+not\s+show\b", re.I), "shows"),
#|    (re.compile(r"\bshows\b", re.I), "does not show"),
#|    (re.compile(r"\bdoes\s+not\s+depict\b", re.I), "depicts"),
#|    (re.compile(r"\bdepicts\b", re.I), "does not depict"),
#|    (re.compile(r"\bdoes\s+not\s+display\b", re.I), "displays"),
#|    (re.compile(r"\bdisplays\b", re.I), "does not display"),
#|    (re.compile(r"\bdoes\s+not\s+feature\b", re.I), "features"),
#|    (re.compile(r"\bfeatures\b", re.I), "does not feature"),
#|    (re.compile(r"\bdoes\s+not\s+contain\b", re.I), "contains"),
#|    (re.compile(r"\bcontains\b", re.I), "does not contain"),
#|    (re.compile(r"\bis\s+not\b", re.I), "is"),
#|    (re.compile(r"\bare\s+not\b", re.I), "are"),
#|    (re.compile(r"\bis\b", re.I), "is not"),
#|    (re.compile(r"\bare\b", re.I), "are not"),
#|)
#|_BRIDGE_TOGGLES = (
#|    (re.compile(r"\bdoes\s+not\s+represent\b", re.I), "represents"),
#|    (re.compile(r"\brepresents\b", re.I), "does not represent"),
#|    (re.compile(r"\bdoes\s+not\s+symbolize\b", re.I), "symbolizes"),
#|    (re.compile(r"\bsymbolizes\b", re.I), "does not symbolize"),
#|    (re.compile(r"\bdoes\s+not\s+mean\b", re.I), "means"),
#|    (re.compile(r"\bmeans\b", re.I), "does not mean"),
#|    (re.compile(r"\bdoes\s+not\s+suggest\b", re.I), "suggests"),
#|    (re.compile(r"\bsuggests\b", re.I), "does not suggest"),
#|    (re.compile(r"\bdoes\s+not\s+imply\b", re.I), "implies"),
#|    (re.compile(r"\bimplies\b", re.I), "does not imply"),
#|    (re.compile(r"\bdoes\s+not\s+evoke\b", re.I), "evokes"),
#|    (re.compile(r"\bevokes\b", re.I), "does not evoke"),
#|)
#|
#|_RELATION_INVERSION = {
#|    "entails": "contradicts",
#|    "entailed": "contradicted",
#|    "entailment": "contradiction",
#|    "supports": "contradicts",
#|    "supported": "contradicted",
#|    "support": "contradict",
#|    "contradicts": "supports",
#|    "contradicted": "supported",
#|    "contradiction": "entailment",
#|    "contradict": "support",
#|    "refutes": "supports",
#|    "refuted": "supported",
#|    "refute": "support",
#|    "aligns": "conflicts",
#|    "aligned": "conflicted",
#|    "consistent": "inconsistent",
#|    "inconsistent": "consistent",
#|}
#|_RELATION_RE = re.compile(
#|    r"\b(" + "|".join(sorted(map(re.escape, _RELATION_INVERSION), key=len, reverse=True)) + r")\b",
#|    flags=re.IGNORECASE,
#|)
#|
#|
#|def _clean(value: Any) -> str:
#|    return " ".join(str(value or "").split())
#|
#|
#|def answer_from_sample(sample: dict[str, Any]) -> str:
#|    for message in reversed(sample.get("conversations") or []):
#|        if str(message.get("from", "")).lower() in {"gpt", "assistant"}:
#|            return _clean(message.get("value"))
#|    return ""
#|
#|
#|def parse_answer_label(answer: Any) -> int:
#|    match = _LABEL_RE.match(str(answer or ""))
#|    if not match:
#|        raise ValueError("GESV-v2 requires a leading entailment label")
#|    return int(match.group("label").lower() == "entailment")
#|
#|
#|def split_label_and_rationale(answer: Any) -> tuple[str, str]:
#|    text = _clean(answer)
#|    match = _LABEL_RE.match(text)
#|    if not match:
#|        return "", text
#|    return _clean(text[: match.end()]), _clean(text[match.end() :])
#|
#|
#|def _sentences(rationale: str) -> list[str]:
#|    values = [match.group(0).strip() for match in _SENTENCE_RE.finditer(rationale)]
#|    return [value for value in values if value]
#|
#|
#|def _cue_score(text: str, cues: Iterable[str]) -> int:
#|    lowered = text.lower()
#|    return sum(int(cue in lowered) for cue in cues)
#|
#|
#|def select_evidence_role_spans(answer: Any) -> tuple[str, str, str]:
#|    """Select existing, order-preserving sentence spans for the three roles."""
#|
#|    _, rationale = split_label_and_rationale(answer)
#|    sentences = _sentences(rationale)
#|    if not sentences:
#|        return rationale, rationale, rationale
#|    if len(sentences) == 1:
#|        return sentences[0], sentences[0], sentences[0]
#|
#|    count = len(sentences)
#|    available = set(range(count))
#|
#|    visual_index = max(
#|        available,
#|        key=lambda index: (
#|            _cue_score(sentences[index], _VISUAL_CUES),
#|            -index,
#|        ),
#|    )
#|    available.remove(visual_index)
#|
#|    relation_index = max(
#|        available,
#|        key=lambda index: (
#|            _cue_score(sentences[index], _RELATION_CUES),
#|            index,
#|        ),
#|    )
#|    if len(sentences) == 2:
#|        figurative_index = relation_index
#|    else:
#|        available.remove(relation_index)
#|        figurative_index = max(
#|            available,
#|            key=lambda index: (
#|                _cue_score(sentences[index], _FIGURATIVE_CUES),
#|                -abs(index - (count - 1) / 2.0),
#|            ),
#|        )
#|    return (
#|        sentences[visual_index],
#|        sentences[figurative_index],
#|        sentences[relation_index],
#|    )
#|
#|
#|def _restore_case(source: str, target: str) -> str:
#|    if source.isupper():
#|        return target.upper()
#|    if source[:1].isupper():
#|        return target[:1].upper() + target[1:]
#|    return target
#|
#|
#|def _swap_first(text: str, swaps: Sequence[tuple[str, str]]) -> tuple[str, str] | None:
#|    for source, target in swaps:
#|        pattern = re.compile(rf"\b{re.escape(source)}\b", flags=re.IGNORECASE)
#|        match = pattern.search(text)
#|        if match:
#|            replacement = _restore_case(match.group(0), target)
#|            return pattern.sub(replacement, text, count=1), f"{source}->{target}"
#|    return None
#|
#|
#|def _toggle_first(
#|    text: str,
#|    toggles: Sequence[tuple[re.Pattern[str], str]],
#|    *,
#|    operator_prefix: str,
#|) -> tuple[str, str] | None:
#|    for pattern, target in toggles:
#|        match = pattern.search(text)
#|        if match:
#|            replacement = _restore_case(match.group(0), target)
#|            return (
#|                pattern.sub(replacement, text, count=1),
#|                f"{operator_prefix}:{match.group(0).lower()}->{target}",
#|            )
#|    return None
#|
#|
#|def corrupt_visual_span(span: str) -> tuple[str, str]:
#|    swapped = _swap_first(span, _VISUAL_SWAPS)
#|    if swapped is not None:
#|        return swapped
#|    toggled = _toggle_first(span, _PREDICATE_TOGGLES, operator_prefix="visual-polarity")
#|    if toggled is not None:
#|        return toggled
#|    return f"It is false that {span[:1].lower() + span[1:]}", "visual-fallback"
#|
#|
#|def corrupt_figurative_span(span: str) -> tuple[str, str]:
#|    swapped = _swap_first(span, _FIGURATIVE_SWAPS)
#|    if swapped is not None:
#|        return swapped
#|    toggled = _toggle_first(span, _BRIDGE_TOGGLES, operator_prefix="bridge-polarity")
#|    if toggled is not None:
#|        return toggled
#|    toggled = _toggle_first(span, _PREDICATE_TOGGLES, operator_prefix="bridge-copula")
#|    if toggled is not None:
#|        return toggled
#|    return (
#|        f"This does not convey that {span[:1].lower() + span[1:]}",
#|        "figurative-fallback",
#|    )
#|
#|
#|def invert_relation_span(span: str, label: int) -> tuple[str, str]:
#|    replaced = False
#|
#|    def invert(match: re.Match[str]) -> str:
#|        nonlocal replaced
#|        replaced = True
#|        source = match.group(0)
#|        return _restore_case(source, _RELATION_INVERSION[source.lower()])
#|
#|    output = _RELATION_RE.sub(invert, span)
#|    if replaced:
#|        return output, "relation-inversion"
#|    if label == 1:
#|        return (
#|            f"{span} However, it contradicts rather than supports the claim.",
#|            "relation-fallback-entailment",
#|        )
#|    return (
#|        f"{span} However, it supports rather than contradicts the claim.",
#|        "relation-fallback-contradiction",
#|    )
#|
#|
#|def _replace_span(answer: str, span: str, replacement: str) -> str:
#|    index = answer.find(span)
#|    if index < 0:
#|        raise RuntimeError(f"role span is not an exact substring: {span!r}")
#|    return _clean(answer[:index] + replacement + answer[index + len(span) :])
#|
#|
#|def _forced_distinct_corruption(span: str, role: str, label: int) -> tuple[str, str]:
#|    lowered = span[:1].lower() + span[1:]
#|    if role == "visual":
#|        return (
#|            f"Contrary to what is visible, it is false that {lowered}",
#|            "visual-forced-distinct",
#|        )
#|    if role == "figurative":
#|        return (
#|            f"This does not figuratively convey that {lowered}",
#|            "figurative-forced-distinct",
#|        )
#|    if label == 1:
#|        return (
#|            f"{span} This contradicts rather than supports the claim.",
#|            "relation-forced-entailment",
#|        )
#|    return (
#|        f"{span} This supports rather than contradicts the claim.",
#|        "relation-forced-contradiction",
#|    )
#|
#|
#|def build_local_counterfactual_answer_map(
#|    samples: Iterable[dict[str, Any]],
#|) -> tuple[dict[Any, tuple[str, str, str]], dict[str, Any]]:
#|    """Build three minimal within-sample negatives without donor text."""
#|
#|    output: dict[Any, tuple[str, str, str]] = {}
#|    distinct = [0, 0, 0]
#|    operators: Counter[str] = Counter()
#|    length_deltas: list[int] = []
#|    overlap_ratios: list[float] = []
#|    entailment = 0
#|    contradiction = 0
#|
#|    for sample in samples:
#|        answer = answer_from_sample(sample)
#|        if not answer:
#|            continue
#|        label = parse_answer_label(answer)
#|        entailment += label
#|        contradiction += 1 - label
#|        spans = select_evidence_role_spans(answer)
#|        visual, visual_op = corrupt_visual_span(spans[0])
#|        figurative, figurative_op = corrupt_figurative_span(spans[1])
#|        relation, relation_op = invert_relation_span(spans[2], label)
#|        replacements = [visual, figurative, relation]
#|        role_operators = [visual_op, figurative_op, relation_op]
#|        negatives = []
#|        seen = set()
#|        for index, (span, replacement) in enumerate(zip(spans, replacements)):
#|            negative = _replace_span(answer, span, replacement)
#|            if negative == answer or negative in seen:
#|                replacement, operator = _forced_distinct_corruption(
#|                    span,
#|                    ROLE_NAMES[index],
#|                    label,
#|                )
#|                role_operators[index] = operator
#|                negative = _replace_span(answer, span, replacement)
#|            negatives.append(negative)
#|            seen.add(negative)
#|        negatives = tuple(negatives)
#|        if any(parse_answer_label(negative) != label for negative in negatives):
#|            raise RuntimeError(f"GESV-v2 changed the leading label for id={sample.get('id')}")
#|        if len(set(negatives)) != len(ROLE_NAMES):
#|            raise RuntimeError(f"GESV-v2 produced duplicate negatives for id={sample.get('id')}")
#|        output[sample["id"]] = negatives
#|
#|        answer_words = answer.split()
#|        for index, (negative, operator) in enumerate(zip(negatives, role_operators)):
#|            distinct[index] += int(negative != answer)
#|            operators[f"{ROLE_NAMES[index]}:{operator}"] += 1
#|            negative_words = negative.split()
#|            length_deltas.append(len(negative_words) - len(answer_words))
#|            overlap_ratios.append(
#|                SequenceMatcher(None, answer_words, negative_words).ratio()
#|            )
#|
#|    stats: dict[str, Any] = {
#|        "records": len(output),
#|        "entailment": entailment,
#|        "contradiction": contradiction,
#|        "visual_distinct": distinct[0],
#|        "figurative_distinct": distinct[1],
#|        "relation_distinct": distinct[2],
#|        "max_abs_length_delta": max(map(abs, length_deltas), default=0),
#|        "mean_overlap": (
#|            sum(overlap_ratios) / len(overlap_ratios) if overlap_ratios else 0.0
#|        ),
#|        "min_overlap": min(overlap_ratios, default=0.0),
#|        "operators": dict(sorted(operators.items())),
#|    }
#|    return output, stats
#|
#|
#|def sources_with_counterfactual_answer(
#|    sample: dict[str, Any], negative_answer: str
#|) -> list[list[dict[str, Any]]]:
#|    import copy
#|
#|    conversations = copy.deepcopy(sample.get("conversations") or [])
#|    for message in reversed(conversations):
#|        if str(message.get("from", "")).lower() in {"gpt", "assistant"}:
#|            message["value"] = negative_answer
#|            return [conversations]
#|    raise ValueError(f"sample {sample.get('id')} has no assistant answer")
#|
#|
#|def local_difference_windows(
#|    positive_tokens: Sequence[int],
#|    negative_tokens: Sequence[int],
#|    *,
#|    context: int = 2,
#|) -> tuple[tuple[int, int], tuple[int, int]]:
#|    """Return expanded changed windows in supervised-token coordinates."""
#|
#|    if context < 0:
#|        raise ValueError("local context must be non-negative")
#|    positive = list(positive_tokens)
#|    negative = list(negative_tokens)
#|    prefix = 0
#|    limit = min(len(positive), len(negative))
#|    while prefix < limit and positive[prefix] == negative[prefix]:
#|        prefix += 1
#|
#|    suffix = 0
#|    remaining_positive = len(positive) - prefix
#|    remaining_negative = len(negative) - prefix
#|    while (
#|        suffix < remaining_positive
#|        and suffix < remaining_negative
#|        and positive[len(positive) - 1 - suffix]
#|        == negative[len(negative) - 1 - suffix]
#|    ):
#|        suffix += 1
#|
#|    positive_stop = len(positive) - suffix
#|    negative_stop = len(negative) - suffix
#|    positive_window = (
#|        max(0, prefix - context),
#|        min(len(positive), max(prefix + 1, positive_stop) + context),
#|    )
#|    negative_window = (
#|        max(0, prefix - context),
#|        min(len(negative), max(prefix + 1, negative_stop) + context),
#|    )
#|    if positive_window[0] >= positive_window[1]:
#|        raise RuntimeError("empty positive local supervision window")
#|    if negative_window[0] >= negative_window[1]:
#|        raise RuntimeError("empty negative local supervision window")
#|    return positive_window, negative_window
#|
#|
#|def smooth_sufficiency_ranking_loss(
#|    positive_nll,
#|    negative_nll,
#|    *,
#|    margin: float,
#|    temperature: float,
#|):
#|    if margin < 0.0:
#|        raise ValueError("GESV-v2 margin must be non-negative")
#|    if temperature <= 0.0:
#|        raise ValueError("GESV-v2 temperature must be positive")
#|    import torch.nn.functional as F
#|
#|    gap = negative_nll.float() - positive_nll.float()
#|    loss = temperature * F.softplus((margin - gap) / temperature)
#|    return loss, gap
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: iesfd_stage_10.py ===
#|"""Endogenous evidence verification for generate-then-rerank IESFD-v10.
#|
#|The clean innovation-point-1 generator is left unchanged.  A graph-free
#|verifier reads a complete candidate explanation and checks whether its token
#|states jointly cover the endogenous image, claim and image-description roles.
#|The verifier is trained on gold versus same-label evidence-replacement pairs
#|and is used only to rerank beam candidates at inference.
#|"""
#|
#|from __future__ import annotations
#|
#|import math
#|
#|from rgc_semantic_readout_stage_8 import make_v8_readout_classes
#|
#|
#|VERIFIER_DIM = 128
#|VERIFIER_FEATURE_DIM = 10
#|
#|
#|def explanation_state_mask(torch, labels, *, ignore_index, label_token_count):
#|    if labels.dim() != 2:
#|        raise ValueError("IESFD-v10 labels must have shape [B,T]")
#|    shifted = labels[:, 1:]
#|    valid = shifted.ne(int(ignore_index))
#|    order = valid.long().cumsum(dim=1)
#|    prediction_mask = valid & order.gt(int(label_token_count))
#|    mask = torch.zeros_like(labels, dtype=torch.bool)
#|    mask[:, :-1] = prediction_mask
#|    return mask
#|
#|
#|def candidate_explanation_mask(
#|    torch,
#|    candidate_ids,
#|    *,
#|    pad_token_id,
#|    eos_token_id,
#|    label_token_count,
#|):
#|    """Return candidate-token positions belonging to the explanation body."""
#|
#|    if candidate_ids.dim() != 2:
#|        raise ValueError("IESFD-v10 candidate IDs must have shape [K,T]")
#|    valid = candidate_ids.ne(int(pad_token_id))
#|    if eos_token_id is not None:
#|        eos = candidate_ids.eq(int(eos_token_id))
#|        ended_before = eos.long().cumsum(dim=1).sub(eos.long()).gt(0)
#|        valid = valid & ~ended_before & ~eos
#|    order = valid.long().cumsum(dim=1)
#|    return valid & order.gt(int(label_token_count))
#|
#|
#|def evidence_verifier_ranking_loss(
#|    torch,
#|    positive_score,
#|    negative_score,
#|    *,
#|    margin,
#|    temperature,
#|    anchor_weight,
#|):
#|    if positive_score.shape != negative_score.shape:
#|        raise ValueError("IESFD-v10 positive/negative score shapes differ")
#|    if min(float(margin), float(temperature)) <= 0.0:
#|        raise ValueError("IESFD-v10 margin/temperature must be positive")
#|    gap = positive_score.float() - negative_score.float()
#|    ranking = float(temperature) * torch.nn.functional.softplus(
#|        (float(margin) - gap) / float(temperature)
#|    ).mean()
#|    anchor = 0.5 * (
#|        torch.nn.functional.softplus(-positive_score.float()).mean()
#|        + torch.nn.functional.softplus(negative_score.float()).mean()
#|    )
#|    return ranking + float(anchor_weight) * anchor, gap.mean(), anchor
#|
#|
#|def select_verified_candidate(
#|    torch,
#|    *,
#|    verifier_scores,
#|    generation_scores,
#|    parsed_labels,
#|    verifier_weight,
#|    generation_weight,
#|    override_margin,
#|):
#|    """Conservatively replace beam-0 only with a same-verdict candidate."""
#|
#|    if verifier_scores.dim() != 1 or generation_scores.dim() != 1:
#|        raise ValueError("IESFD-v10 candidate scores must be vectors")
#|    if verifier_scores.shape != generation_scores.shape:
#|        raise ValueError("IESFD-v10 verifier/generation score shapes differ")
#|    if len(parsed_labels) != int(verifier_scores.numel()):
#|        raise ValueError("IESFD-v10 parsed-label count differs from candidates")
#|    baseline_label = parsed_labels[0]
#|    eligible = torch.tensor(
#|        [label == baseline_label for label in parsed_labels],
#|        device=verifier_scores.device,
#|        dtype=torch.bool,
#|    )
#|    relative_verifier = verifier_scores.float() - verifier_scores[0].float()
#|    relative_generation = generation_scores.float() - generation_scores[0].float()
#|    utility = (
#|        float(verifier_weight) * relative_verifier
#|        + float(generation_weight) * relative_generation
#|    )
#|    utility = utility.masked_fill(~eligible, float("-inf"))
#|    best = int(utility.argmax().item())
#|    if best != 0 and float(utility[best].item()) < float(override_margin):
#|        best = 0
#|    return best, utility.detach(), eligible
#|
#|
#|def make_iesfd_v10_readout_classes(torch, nn):
#|    Readout, V8Controller = make_v8_readout_classes(torch, nn)
#|
#|    class EndogenousEvidenceVerifierController(V8Controller):
#|        def __init__(self, *args, **kwargs):
#|            super().__init__(*args, **kwargs)
#|            condition_dim = int(self.config.condition_dim)
#|            hidden_size = int(self.hidden_size)
#|            self.iesfd_v10_hidden = nn.Sequential(
#|                nn.LayerNorm(hidden_size),
#|                nn.Linear(hidden_size, VERIFIER_DIM),
#|                nn.GELU(),
#|                nn.Linear(VERIFIER_DIM, VERIFIER_DIM),
#|            )
#|            self.iesfd_v10_role = nn.Sequential(
#|                nn.LayerNorm(condition_dim),
#|                nn.Linear(condition_dim, VERIFIER_DIM, bias=False),
#|            )
#|            self.iesfd_v10_score = nn.Sequential(
#|                nn.LayerNorm(VERIFIER_FEATURE_DIM),
#|                nn.Linear(VERIFIER_FEATURE_DIM, 32),
#|                nn.GELU(),
#|                nn.Linear(32, 1),
#|            )
#|            for module in self.iesfd_v10_hidden.modules():
#|                if isinstance(module, nn.Linear):
#|                    nn.init.normal_(module.weight, std=1.0e-3)
#|                    if module.bias is not None:
#|                        nn.init.zeros_(module.bias)
#|            nn.init.normal_(self.iesfd_v10_role[1].weight, std=1.0e-3)
#|            nn.init.normal_(self.iesfd_v10_score[-1].weight, std=1.0e-2)
#|            nn.init.zeros_(self.iesfd_v10_score[-1].bias)
#|            self._iesfd_v10_roles = None
#|            self.last_iesfd_v10_coverage = torch.zeros(3)
#|            self.last_iesfd_v10_score = torch.tensor(0.0)
#|
#|        def encode_condition(
#|            self,
#|            e_img,
#|            e_txt,
#|            e_desc,
#|            graph_feature,
#|            semantic_token_embeddings,
#|            semantic_mask,
#|            *,
#|            activate,
#|        ):
#|            # Compute these roles independently of the concept-graph branch.
#|            p_img = self.img_norm(self.img_proj(e_img.float()))
#|            p_txt = self.txt_norm(self.txt_proj(e_txt.float()))
#|            p_desc = self.desc_norm(self.desc_proj(e_desc.float()))
#|            condition = super().encode_condition(
#|                e_img,
#|                e_txt,
#|                e_desc,
#|                graph_feature,
#|                semantic_token_embeddings,
#|                semantic_mask,
#|                activate=activate,
#|            )
#|            if activate:
#|                self._iesfd_v10_roles = torch.stack(
#|                    (p_img, p_txt, p_desc), dim=1
#|                ).detach()
#|            return condition
#|
#|        def score_evidence_candidates(self, hidden, explanation_mask):
#|            if hidden.dim() != 3 or explanation_mask.dim() != 2:
#|                raise ValueError("IESFD-v10 hidden/mask ranks are invalid")
#|            if hidden.shape[:2] != explanation_mask.shape:
#|                raise ValueError("IESFD-v10 hidden/mask shapes differ")
#|            roles = self._iesfd_v10_roles
#|            if roles is None:
#|                raise RuntimeError("IESFD-v10 roles were not encoded")
#|            if roles.size(0) != hidden.size(0):
#|                if hidden.size(0) % roles.size(0) != 0:
#|                    raise ValueError("IESFD-v10 role/candidate batches differ")
#|                roles = roles.repeat_interleave(
#|                    hidden.size(0) // roles.size(0), dim=0
#|                )
#|            token_codes = torch.nn.functional.normalize(
#|                self.iesfd_v10_hidden(hidden.detach().float()), dim=-1
#|            )
#|            role_codes = torch.nn.functional.normalize(
#|                self.iesfd_v10_role(roles.to(hidden.device).float()), dim=-1
#|            )
#|            similarity = torch.bmm(token_codes, role_codes.transpose(1, 2))
#|            mask = explanation_mask.bool()
#|            if not bool(mask.any(dim=1).all().item()):
#|                raise RuntimeError("IESFD-v10 candidate has no explanation tokens")
#|            masked = similarity.masked_fill(~mask.unsqueeze(-1), -1.0e4)
#|            temperature = 0.10
#|            counts = mask.float().sum(dim=1, keepdim=True).clamp_min(1.0)
#|            coverage = temperature * (
#|                torch.logsumexp(masked / temperature, dim=1)
#|                - counts.log()
#|            )
#|            weights = mask.unsqueeze(-1).to(token_codes.dtype)
#|            pooled = (token_codes * weights).sum(dim=1) / counts
#|            pooled = torch.nn.functional.normalize(pooled, dim=-1)
#|            pooled_similarity = (
#|                pooled.unsqueeze(1) * role_codes
#|            ).sum(dim=-1)
#|            token_support = masked.max(dim=-1).values
#|            token_support = (
#|                token_support * mask.to(token_support.dtype)
#|            ).sum(dim=1) / counts.squeeze(1)
#|            features = torch.cat(
#|                (
#|                    coverage,
#|                    pooled_similarity,
#|                    coverage.min(dim=-1, keepdim=True).values,
#|                    coverage.mean(dim=-1, keepdim=True),
#|                    coverage.std(dim=-1, keepdim=True, unbiased=False),
#|                    token_support.unsqueeze(-1),
#|                ),
#|                dim=-1,
#|            )
#|            score = self.iesfd_v10_score(features).squeeze(-1)
#|            self.last_iesfd_v10_coverage = coverage.detach().mean(dim=0)
#|            self.last_iesfd_v10_score = score.detach().mean()
#|            return score, coverage
#|
#|    return Readout, EndogenousEvidenceVerifierController
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: iesfd_stage_11.py ===
#|"""Train-only candidate quality distillation for endogenous evidence reranking.
#|
#|The frozen v10 encoder supplies token/role codes, NOT ranking decisions.
#|All v11 training and test codes are extracted by the same inference function.
#|No reference explanation, dataset identity or test metric is an input feature.
#|"""
#|from __future__ import annotations
#|
#|import hashlib
#|import json
#|from pathlib import Path
#|
#|SCHEMA = "iesfd_v11_candidates_v1"
#|THRESHOLDS = (0.53, 0.60)
#|
#|
#|def sha256(path):
#|    digest = hashlib.sha256()
#|    with Path(path).open("rb") as handle:
#|        for block in iter(lambda: handle.read(1024 * 1024), b""):
#|            digest.update(block)
#|    return digest.hexdigest()
#|
#|
#|def read_manifest(directory, required_split=None, complete=True):
#|    path = Path(directory) / "manifest.json"
#|    manifest = json.loads(path.read_text(encoding="utf-8"))
#|    if manifest.get("schema") != SCHEMA:
#|        raise ValueError("incompatible v11 cache schema")
#|    if required_split is not None and manifest["split"] != required_split:
#|        raise ValueError("v11 train/test split violation")
#|    if complete:
#|        marker = json.loads((Path(directory) / "complete.json").read_text(encoding="utf-8"))
#|        if marker["manifest_sha256"] != sha256(path):
#|            raise ValueError("candidate completion marker does not match manifest")
#|        if marker["records"] != manifest["records"]:
#|            raise ValueError("candidate cache is incomplete")
#|        if len(list(Path(directory).glob('item_*.pt'))) != manifest['records']:
#|            raise ValueError('completed candidate cache has missing/extra item files')
#|    return manifest
#|
#|
#|def explanation(text):
#|    return text.partition(".")[2].strip()
#|
#|
#|def explanation_token_mask(torch, ids, tokenizer):
#|    """Mask post-token states, excluding special tokens and verdict prefix.
#|
#|    Find the decoded first period instead of assuming the verdict is exactly
#|    two tokens. Used identically on generated TRAIN and TEST candidates.
#|    """
#|    mask = torch.zeros_like(ids, dtype=torch.bool)
#|    special = set(tokenizer.all_special_ids)
#|    prefix = []
#|    in_body = False
#|    for index, token in enumerate(ids.tolist()):
#|        if token in special:
#|            if token == tokenizer.eos_token_id:
#|                break
#|            continue
#|        if in_body:
#|            mask[index] = True
#|        else:
#|            prefix.append(token)
#|            in_body = "." in tokenizer.decode(prefix, skip_special_tokens=True)
#|    if not bool(mask.any()):
#|        raise ValueError("candidate has no explanation body")
#|    return mask
#|
#|
#|def make_ranker(torch):
#|    nn = torch.nn
#|
#|    class EvidenceCandidateRanker(nn.Module):
#|        def __init__(self):
#|            super().__init__()
#|            self.token = nn.Sequential(nn.LayerNorm(128), nn.Linear(128, 64), nn.GELU())
#|            self.role = nn.Sequential(nn.LayerNorm(128), nn.Linear(128, 64), nn.GELU())
#|            self.head = nn.Sequential(
#|                nn.LayerNorm(3 * 64 * 4 + 64 + 2),
#|                nn.Linear(3 * 64 * 4 + 64 + 2, 128), nn.GELU(),
#|                nn.Dropout(0.10), nn.Linear(128, 3),
#|            )
#|
#|        def forward(self, tokens, roles, mask, extras):
#|            if not bool(mask.any(dim=1).all()):
#|                raise ValueError("empty explanation in v11 ranker")
#|            token = self.token(tokens.float())
#|            role = self.role(roles.float())
#|            affinity = torch.bmm(role, token.transpose(1, 2)) / 8.0
#|            affinity = affinity.masked_fill(~mask[:, None, :], float("-inf"))
#|            attended = torch.bmm(affinity.softmax(dim=-1), token)
#|            interaction = torch.cat((role, attended, role * attended, role - attended), dim=-1)
#|            pooled = (token * mask[:, :, None]).sum(1) / mask.sum(1, keepdim=True)
#|            logits = self.head(torch.cat((interaction.flatten(1), pooled, extras.float()), dim=-1))
#|            quality = logits[:, 0].sigmoid()
#|            p53 = logits[:, 1].sigmoid()
#|            p60 = p53 * logits[:, 2].sigmoid()  # enforce P(q>.60) <= P(q>.53)
#|            return quality, torch.stack((p53, p60), dim=-1)
#|
#|    return EvidenceCandidateRanker
#|
#|
#|def candidate_loss(torch, quality, passes, targets, group_sizes):
#|    soft_passes = torch.sigmoid((targets[:, None] - targets.new_tensor(THRESHOLDS)) / 0.025)
#|    regression = torch.nn.functional.smooth_l1_loss(quality, targets, beta=0.05)
#|    boundary = torch.nn.functional.binary_cross_entropy(passes.clamp(1e-6, 1-1e-6), soft_passes)
#|    pairs = []
#|    offset = 0
#|    for count in group_sizes:
#|        prediction = quality[offset:offset+count]
#|        target = targets[offset:offset+count]
#|        gap = target[:, None] - target[None, :]
#|        keep = gap > 0.01  # ignore near-ties in the training reference teacher
#|        if bool(keep.any()):
#|            predicted_gap = prediction[:, None] - prediction[None, :]
#|            pairs.append(((gap[keep].clamp(max=0.2) / 0.05) *
#|                          torch.nn.functional.softplus(-predicted_gap[keep] / 0.05)).mean())
#|        offset += count
#|    ranking = torch.stack(pairs).mean() if pairs else quality.sum() * 0.0
#|    return regression + 0.25 * boundary + 0.10 * ranking
#|
#|
#|def pack_groups(torch, groups, device):
#|    candidates = [c for group in groups for c in group["candidates"]]
#|    lengths = [c["tokens"].size(0) for c in candidates]
#|    tokens = torch.nn.utils.rnn.pad_sequence([c["tokens"].float() for c in candidates], batch_first=True)
#|    mask = torch.arange(tokens.size(1))[None, :] < torch.tensor(lengths)[:, None]
#|    roles = torch.stack([group["roles"].float() for group in groups for _ in group["candidates"]])
#|    extras = torch.tensor([[c["v10_score"], min(c["tokens"].size(0), 256) / 256.0] for c in candidates])
#|    return tuple(value.to(device) for value in (tokens, roles, mask, extras))
#|
#|
#|def select_candidate(torch, qualities, passes, labels, margin=0.04, uncertainty=1.0):
#|    """Paired ensemble disagreement is a conservative heuristic, not a CI."""
#|    utilities = passes.sum(-1) + 0.10 * qualities
#|    difference = utilities - utilities[:, :1]
#|    mean = difference.mean(0)
#|    spread = difference.std(0, unbiased=False)
#|    gains = mean - float(uncertainty) * spread
#|    eligible = torch.tensor([label == labels[0] for label in labels], device=gains.device)
#|    if labels[0] not in (0, 1):
#|        return 0, gains, spread
#|    gains = gains.masked_fill(~eligible, float("-inf"))
#|    selected = int(gains.argmax())
#|    if selected and float(gains[selected]) < margin:
#|        selected = 0
#|    return selected, gains, spread
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: iesfd_stage_13_repair.py ===
#|"""Error-localized repair and source-likelihood retention for IESFD-v13.
#|
#|No new network. Token edits are alignment proxies, not annotated causal spans.
#|All masks are applied AFTER a full-label model forward.
#|"""
#|from __future__ import annotations
#|
#|import hashlib
#|import json
#|from contextlib import contextmanager
#|from difflib import SequenceMatcher
#|from pathlib import Path
#|
#|
#|def digest(path):
#|    h = hashlib.sha256()
#|    with Path(path).open('rb') as f:
#|        for block in iter(lambda: f.read(1024*1024), b''):
#|            h.update(block)
#|    return h.hexdigest()
#|
#|
#|def write_json(path, value):
#|    path = Path(path)
#|    path.parent.mkdir(parents=True, exist_ok=True)
#|    temp = path.with_suffix('.tmp')
#|    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
#|    temp.replace(path)
#|
#|
#|def edited_positions(positive, negative):
#|    """Changed tokens plus one boundary token for pure insertions/deletions."""
#|    pos, neg = set(), set()
#|    for tag, a, b, c, d in SequenceMatcher(a=list(positive), b=list(negative), autojunk=False).get_opcodes():
#|        if tag == 'equal':
#|            continue
#|        pos.update(range(a, b))
#|        neg.update(range(c, d))
#|        if a == b and positive:
#|            pos.add(min(a, len(positive)-1))
#|        if c == d and negative:
#|            neg.add(min(c, len(negative)-1))
#|    return sorted(pos), sorted(neg)
#|
#|
#|def answer_regions(tokenizer, ids):
#|    """Indices in the supervised answer sequence; delimiter found by decoding."""
#|    special = set(tokenizer.all_special_ids)
#|    prefix, decision, body, found = [], [], [], False
#|    for i, token in enumerate(ids):
#|        if token in special:
#|            continue
#|        if found:
#|            body.append(i)
#|        else:
#|            decision.append(i)
#|            prefix.append(token)
#|            found = '.' in tokenizer.decode(prefix, skip_special_tokens=True)
#|    if not found or not decision or not body:
#|        raise ValueError('missing decision delimiter or explanation tokens')
#|    return decision, body
#|
#|
#|def loss_terms(torch, gold_nll, rejected_nll, anchor_nll, reference, masks, meta,
#|               *, preference_weight=.10, anchor_weight=1., gold_weight=.10,
#|               decision_weight=1., temperature=.10, margin=.05, rejection_cap=.10,
#|               anchor_tolerance=.01, ablation='full'):
#|    """Positive repair cannot be replaced by unlimited negative suppression.
#|
#|    reference contains source per-token NLL vectors, not a second 7B model.
#|    Mean masked token losses are surrogates, not sequence log-likelihoods.
#|    """
#|    if ablation not in ('full', 'no_anchor', 'global_repair'):
#|        raise ValueError('unknown ablation')
#|    decision, body, edit_pos, edit_neg, anchor_body, negative_body = masks
#|    zero = gold_nll.sum()*0
#|    decision_loss = gold_nll[decision].mean() * (1+meta['wrong_rate'])
#|    # Include EOS/turn terminator in low-weight continuation supervision.
#|    # Local edit alignment still excludes special tokens.
#|    continuation = list(range(max(decision)+1, len(gold_nll)))
#|    positive = gold_nll[continuation].mean()
#|    local, preference, positive_floor = zero, zero, zero
#|    if meta['pair_active'] and edit_pos and edit_neg:
#|        if ablation == 'global_repair':
#|            edit_pos, edit_neg = body, negative_body
#|        local = gold_nll[edit_pos].mean()
#|        ap = reference['gold'][edit_pos].mean()-local
#|        an = reference['rejected'][edit_neg].mean()-rejected_nll[edit_neg].mean()
#|        advantage = ap-an.clamp(min=-rejection_cap)
#|        preference = torch.nn.functional.softplus((margin-advantage)/temperature)*temperature
#|        positive_floor = torch.relu(-ap).square()
#|    elif meta['wrong_rate'] > 0:
#|        local = positive
#|    anchor = zero
#|    if anchor_nll is not None and anchor_body and ablation != 'no_anchor':
#|        # Tokenwise retention catches erosion hidden by a whole-answer average.
#|        drift = anchor_nll[anchor_body]-reference['anchor'][anchor_body]-anchor_tolerance
#|        anchor = torch.relu(drift).square().mean()*meta['anchor_quality']**4
#|    total = (decision_weight*decision_loss+gold_weight*positive
#|             +meta['repair_weight']*(local+preference_weight*preference+positive_floor)
#|             +anchor_weight*anchor)
#|    return total, dict(decision=decision_loss, gold=positive, local=local,
#|                       preference=preference, positive_floor=positive_floor, anchor=anchor)
#|
#|
#|@contextmanager
#|def source_parameters(model, torch):
#|    """Swap only selected LoRA tensors, before building any student graph."""
#|    parameters = dict(model.llm.named_parameters())
#|    current = {n: parameters[n].detach().clone() for n in model.dome_source_parameters}
#|    try:
#|        with torch.no_grad():
#|            for name, source in model.dome_source_parameters.items():
#|                parameters[name].copy_(source)
#|        yield
#|    finally:
#|        with torch.no_grad():
#|            for name, value in current.items():
#|                parameters[name].copy_(value)
#|
#|
#|def full_label_nll(model, module, batch, device):
#|    """Capture logits after multimodal expansion, retaining full-label timing."""
#|    from train_llava_claim_dome_ft import move_images
#|    torch = module.torch
#|    captures = []
#|    def capture(_module, _args, kwargs, output):
#|        labels = kwargs.get('labels')
#|        if labels is None or labels.size(0) != 1:
#|            raise RuntimeError('v13 requires one full-label sequence per forward')
#|        targets = labels[:, 1:]
#|        keep = targets.ne(module.IGNORE_INDEX)
#|        # Select answer logits before FP32 conversion to avoid copying all
#|        # prompt logits; cross_entropy supplies its own log normalization.
#|        logits = output.logits[:, :-1][keep].float()
#|        ids = targets[keep]
#|        nll = torch.nn.functional.cross_entropy(logits, ids, reduction='none')
#|        if not bool(torch.isfinite(nll).all()):
#|            raise FloatingPointError('nonfinite model token loss')
#|        captures.append((nll, ids.detach().cpu().tolist()))
#|    hook = model.llm.register_forward_hook(capture, with_kwargs=True)
#|    try:
#|        output = model(move_images(batch['images'], device, torch), batch['image_sizes'],
#|            batch['e_img'].to(device), batch['e_txt'].to(device), batch['e_desc'].to(device),
#|            batch['graph_feature'].to(device), batch['ids'].to(device), batch['mask'].to(device),
#|            batch['labels'].to(device), batch['cf'].to(device),
#|            graph_semantic_ids=batch['graph_semantic_ids'].to(device),
#|            graph_semantic_mask=batch['graph_semantic_mask'].to(device),
#|            phenomenon_group=batch['phenomenon_group'].to(device))
#|        del output
#|    finally:
#|        hook.remove()
#|    if len(captures) != 1:
#|        raise RuntimeError('unexpected auxiliary LM forward; v13 capture contract failed')
#|    return captures[0]
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: iesfd_stage_14.py ===
#|"""Factorized decision/explanation policies on one frozen LLaVA backbone."""
#|from __future__ import annotations
#|
#|import math
#|
#|from iesfd_stage_13_repair import answer_regions
#|
#|
#|def consensus_pair(records, min_gain=.01):
#|    """Require agreement of TWO train-only teachers; disagreement is not error.
#|
#|    Input records must already have the correct verdict. Returns indices.
#|    """
#|    if not math.isfinite(min_gain) or min_gain <= 0:
#|        raise ValueError('min_gain must be positive')
#|    pairs = []
#|    for i, winner in enumerate(records):
#|        for j, loser in enumerate(records):
#|            if i == j or winner['text'] == loser['text']:
#|                continue
#|            gains = [winner[k]-loser[k] for k in ('bert', 'bleurt')]
#|            if min(gains) >= min_gain:
#|                pairs.append((min(gains), sum(gains), i, j))
#|    if not pairs:
#|        return None
#|    _, _, i, j = max(pairs)
#|    return i, j
#|
#|
#|def set_policy(model, state, torch):
#|    """Copy only declared existing LoRA-B weights; never add an adapter module."""
#|    parameters = dict(model.named_parameters())
#|    if not state:
#|        raise ValueError('empty policy state')
#|    for name, value in state.items():
#|        if 'lora_B' not in name or name not in parameters or parameters[name].shape != value.shape:
#|            raise ValueError(f'incompatible policy tensor: {name}')
#|    with torch.no_grad():
#|        for name, value in state.items():
#|            parameters[name].copy_(value.to(parameters[name].device, dtype=parameters[name].dtype))
#|
#|
#|def coarse_probabilities(torch, logits, top_ids):
#|    """Top-k named events plus an aggregated other event, FP32 normalization."""
#|    logp = logits.float().log_softmax(-1)
#|    selected = logp.gather(-1, top_ids).exp()
#|    other = (1-selected.sum(-1, keepdim=True)).clamp_min(1e-8)
#|    probabilities = torch.cat((selected, other), -1).clamp_min(1e-8)
#|    return probabilities/probabilities.sum(-1, keepdim=True)
#|
#|
#|def coarse_kl(torch, logits, top_ids, teacher_probabilities):
#|    current = coarse_probabilities(torch, logits, top_ids)
#|    teacher = teacher_probabilities.float().clamp_min(1e-8)
#|    teacher = teacher/teacher.sum(-1, keepdim=True)
#|    return (teacher*(teacher.log()-current.log())).sum(-1)
#|
#|
#|def decision_loss(torch, true_score, false_score, source_true, source_false, *, margin=2., balance=1.):
#|    logits = torch.stack((true_score, false_score))
#|    source = torch.stack((source_true, source_false)).detach()
#|    p = source.softmax(0)
#|    kl = (p*(source.log_softmax(0)-logits.log_softmax(0))).sum()
#|    # True/false here denote training correctness, not fixed label 0/1 order.
#|    return balance*torch.nn.functional.softplus(margin-(true_score-false_score)) + .1*kl*(source_true>source_false)
#|
#|
#|def forward_stats(model, module, batch, device, *, reference=None, top_k=32):
#|    """Full labels control readout timing; token objectives are applied later."""
#|    import train_llava_claim_dome_ft as dome
#|    torch = module.torch
#|    captured = []
#|    def hook(_m, _args, kwargs, output):
#|        labels = kwargs.get('labels')
#|        if labels is None or labels.size(0) != 1:
#|            raise RuntimeError('requires full-label, single-record forward')
#|        targets = labels[:, 1:]
#|        valid = targets.ne(module.IGNORE_INDEX)
#|        logits = output.logits[:, :-1][valid].float()
#|        ids = targets[valid]
#|        nll = torch.nn.functional.cross_entropy(logits, ids, reduction='none')
#|        if not bool(torch.isfinite(nll).all()):
#|            raise FloatingPointError('nonfinite token likelihood')
#|        ids_list = ids.detach().cpu().tolist()
#|        decision, _ = answer_regions(model.tokenizer, ids_list)
#|        continuation = list(range(max(decision)+1, len(ids_list)))
#|        result = dict(ids=ids_list, decision=-nll[decision].sum(), continuation=nll[continuation].mean())
#|        if reference is None:
#|            top_ids = logits[continuation].topk(min(top_k, logits.size(-1)), -1).indices
#|            result['reference'] = dict(ids=ids_list, top_ids=top_ids.detach().cpu(),
#|                probabilities=coarse_probabilities(torch, logits[continuation], top_ids).detach().cpu(),
#|                decision=result['decision'].detach().cpu())
#|        else:
#|            if reference['ids'] != ids_list:
#|                raise ValueError('source/current tokenization mismatch')
#|            result['kl'] = coarse_kl(torch, logits[continuation], reference['top_ids'].to(device),
#|                                    reference['probabilities'].to(device)).mean()
#|        captured.append(result)
#|    handle = model.llm.register_forward_hook(hook, with_kwargs=True)
#|    try:
#|        dome.forward_loss(model, batch, 'labels', device, torch)
#|    finally:
#|        handle.remove()
#|    if len(captured) != 1:
#|        raise RuntimeError('unexpected auxiliary LM calls')
#|    return captured[0]
#|
#|
#|def label_constraint(prefix_ids, vocabulary_size):
#|    """Constrain only the verdict; accommodate HF input-embedding dummy IDs."""
#|    if not prefix_ids or any(i < 0 or i >= vocabulary_size for i in prefix_ids):
#|        raise ValueError('invalid verdict token prefix')
#|    initial_length = [None]
#|    vocabulary = list(range(vocabulary_size))
#|    def allowed(_batch, input_ids):
#|        if initial_length[0] is None:
#|            initial_length[0] = len(input_ids)
#|        index = len(input_ids)-initial_length[0]
#|        if index < 0:
#|            raise RuntimeError('generation prefix length regressed')
#|        return [prefix_ids[index]] if index < len(prefix_ids) else vocabulary
#|    return allowed
#|
#|
#|def verdict_scores(torch, tokenizer, model, projector, embeds, mask):
#|    """Exact complete-prefix log probability; no explanation/lookahead input."""
#|    scores = []
#|    for label in ('contradiction.', 'entailment.'):
#|        ids = tokenizer(label, add_special_tokens=False, return_tensors='pt').input_ids.to(embeds.device)
#|        answer = model.get_input_embeddings()(ids)
#|        joint = torch.cat((embeds.to(answer.dtype), answer), 1)
#|        joint_mask = torch.cat((mask, torch.ones_like(ids)), 1)
#|        scale = torch.ones((*joint.shape[:2], 1), device=joint.device)
#|        scale[:, :embeds.size(1)+max(0, projector.config.label_token_count-1)] = projector.config.label_readout_scale
#|        readout = projector.semantic_readout
#|        readout.reset_generation()
#|        readout.set_token_scale(scale)
#|        try:
#|            out = model(inputs_embeds=joint, attention_mask=joint_mask, use_cache=False, return_dict=True)
#|            start = embeds.size(1)-1
#|            logits = out.logits[0, start:start+ids.size(1)].float()
#|            score = logits.log_softmax(-1).gather(1, ids[0, :, None]).sum()
#|            scores.append(float(score))
#|            del out
#|        finally:
#|            readout.reset_generation()
#|    return scores
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: iesfd_stage_16.py ===
#|"""Frozen conditional generation with an explicit keep-original action."""
#|import math
#|
#|
#|def select_candidate(records, margin=.05, likelihood_slack=.1):
#|    if not records or margin <= 0 or likelihood_slack < 0:
#|        raise ValueError('invalid selection configuration')
#|    if not all(math.isfinite(x) for x in (margin,likelihood_slack)):
#|        raise ValueError('nonfinite configuration')
#|    base=records[0]
#|    valid=lambda r: r.get('scorable',False) and all(math.isfinite(r[k]) for k in ('evidence','likelihood'))
#|    if not valid(base):return 0
#|    eligible=[i for i,r in enumerate(records) if i and valid(r)
#|              and r['label']==base['label'] and r['text']!=base['text']
#|              and r['evidence']>base['evidence']+margin
#|              and r['likelihood']>=base['likelihood']-likelihood_slack]
#|    return max(eligible,key=lambda i:(records[i]['evidence'],records[i]['likelihood'],-i)) if eligible else 0
#|
#|
#|def score_candidates(module,tokenizer,model,projector,verifier,embeds,mask,texts):
#|    from dome_ft_data import parse_label
#|    from iesfd_stage_11 import explanation_token_mask
#|    from rgc_semantic_readout import find_final_decoder_norm
#|    torch=module.torch
#|    _,norm=find_final_decoder_norm(model)
#|    result=[]
#|    for text in texts:
#|        ids=tokenizer(text,add_special_tokens=False,return_tensors='pt').input_ids.to(embeds.device)
#|        try:body=explanation_token_mask(torch,ids[0],tokenizer)
#|        except ValueError:
#|            result.append(dict(text=text,label=parse_label(text),scorable=False));continue
#|        tokens=model.get_input_embeddings()(ids)
#|        joint=torch.cat((embeds.to(tokens.dtype),tokens),1)
#|        joint_mask=torch.cat((mask,torch.ones_like(ids)),1)
#|        scale=torch.ones((*joint.shape[:2],1),device=joint.device)
#|        scale[:,:embeds.size(1)+max(0,projector.config.label_token_count-1)]=projector.config.label_readout_scale
#|        captured=[]
#|        handle=norm.register_forward_hook(lambda _m,_i,out:captured.append(out))
#|        readout=projector.semantic_readout
#|        readout.reset_generation();readout.set_token_scale(scale)
#|        try:
#|            output=model(inputs_embeds=joint,attention_mask=joint_mask,use_cache=False,return_dict=True)
#|            hidden=captured[-1][:,-ids.size(1):,:]
#|            evidence,coverage=verifier.score_evidence_candidates(hidden,body[None,:])
#|            start=embeds.size(1)-1
#|            logits=output.logits[0,start:start+ids.size(1)][body].float()
#|            ll=-torch.nn.functional.cross_entropy(logits,ids[0,body],reduction='mean')
#|            result.append(dict(text=text,label=parse_label(text),scorable=True,
#|                evidence=float(evidence.item()),likelihood=float(ll.item()),coverage=coverage[0].float().cpu().tolist()))
#|            del output,hidden,logits
#|        finally:
#|            handle.remove();readout.reset_generation()
#|    return result
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: infer_llava_final.py ===
#|"""Inference from one final model.pt, with v16 decision/selection for innovation2."""
#|import argparse,csv,json,pickle
#|from pathlib import Path
#|from types import SimpleNamespace
#|from iesfd_stage_13_repair import digest,write_json
#|from llava_final_runtime import load_payload,graph_inputs,context,prompt
#|from llava_legacy_inference import load_legacy_runtime as load_runtime,original_source_response,prediction_row
#|
#|class NoReadout:
#|    def reset_generation(self):pass
#|    def set_token_scale(self,scale):pass
#|
#|
#|def infer_record(rt,row,features,graphs,texts):
#|    from iesfd_stage_14 import verdict_scores,label_constraint
#|    from iesfd_stage_16 import select_candidate,score_candidates
#|    from iesfd_stage_11 import explanation_token_mask
#|    from dome_ft_data import parse_label,strip_label,label_word
#|    torch=rt.torch
#|    proxy=rt.controller or SimpleNamespace(config=SimpleNamespace(label_token_count=4,label_readout_scale=.1),semantic_readout=NoReadout())
#|    context(rt,row,features,graphs,texts)
#|    source=original_source_response(rt,row)
#|    if rt.verifier is None:
#|        return dict(id=row['id'],source=source,routed_source=source,final=source,selected=0,candidates=[])
#|    # Original v16 builds this prompt after obtaining the ordinary source response.
#|    embeds,mask,stop=prompt(rt,row)
#|    def generate(label=None,count=1):
#|        proxy.semantic_readout.reset_generation();extra={}
#|        if label is not None:extra['prefix_allowed_tokens_fn']=label_constraint(rt.tokenizer(label_word(label)+'.',add_special_tokens=False)['input_ids'],rt.model.config.vocab_size)
#|        ids=rt.module.GenerationMixin.generate(rt.model,inputs_embeds=embeds,attention_mask=mask,
#|            do_sample=False,num_beams=3,num_return_sequences=count,max_new_tokens=256,use_cache=True,
#|            pad_token_id=rt.tokenizer.pad_token_id,repetition_penalty=1.02,early_stopping=True,**extra)
#|        texts=[t.strip() for t in rt.tokenizer.batch_decode(ids,skip_special_tokens=True)]
#|        return [t[:-len(stop)].strip() if stop and t.endswith(stop) else t for t in texts]
#|    selected=0;candidates=[]
#|    if rt.verifier is None:final=source;routed=source
#|    else:
#|        scores=verdict_scores(torch,rt.tokenizer,rt.model,proxy,embeds,mask);label=int(scores[1]>scores[0])
#|        beam0=generate(label)[0];routed=beam0;beams=generate(label,3)
#|        if beams[0]!=beam0:raise RuntimeError('beam-0 differs with return count')
#|        candidate_texts=list(dict.fromkeys([beam0]+beams))
#|        for text in candidate_texts:
#|            if parse_label(text)!=label or not strip_label(text):raise ValueError('invalid fixed-label explanation')
#|        # Use the verified v16 scorer itself, not a separately maintained copy.
#|        candidates=score_candidates(rt.module,rt.tokenizer,rt.model,proxy,rt.verifier,embeds,mask,candidate_texts)
#|        selected=select_candidate(candidates,.05,.1);final=candidates[selected]['text']
#|    if parse_label(final) not in (0,1) or not strip_label(final):raise ValueError('malformed final output')
#|    if rt.verifier is not None and parse_label(final)!=parse_label(routed):raise RuntimeError('verifier selection changed verdict')
#|    return dict(id=row['id'],source=source,routed_source=routed,final=final,selected=selected,candidates=candidates)
#|
#|
#|
#|def main():
#|    p=argparse.ArgumentParser();p.add_argument('--checkpoint',required=True);p.add_argument('--output',required=True)
#|    p.add_argument('--test-graph');p.add_argument('--device',default='cuda:0');a=p.parse_args()
#|    import torch
#|    from paths_paper2 import Paper2Paths
#|    from iesfd_stage_14 import verdict_scores,label_constraint
#|    from iesfd_stage_16 import select_candidate
#|    from iesfd_stage_11 import explanation_token_mask
#|    from dome_ft_data import parse_label,strip_label,label_word
#|    paths=Paper2Paths.from_env();payload=load_payload(torch,a.checkpoint);variant=payload['variant']
#|    if paths.llm_path!=payload['metadata']['contract']['base_model']:raise ValueError('base model path differs from training')
#|    out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
#|    contract=dict(checkpoint_sha256=digest(a.checkpoint),test_input_sha256=digest(paths.test_json),
#|        feature_sha256=digest(paths.test_features),graph_sha256=digest(a.test_graph) if variant!='innovation2' else None,
#|        variant=variant,reference_used=False,inference='historical_loader_and_source_v1',
#|        original_io_sha256=digest(paths.orig_root/'test_moe_创新点1.py'),
#|        code={n:digest(Path(__file__).with_name(n)) for n in ('infer_llava_final.py','llava_legacy_inference.py','llava_final_runtime.py','iesfd_stage_14.py','iesfd_stage_16.py','cache_iesfd_stage_11_candidates.py')})
#|    cp=out/'contract.json'
#|    if cp.exists() and json.loads(cp.read_text(encoding='utf-8'))!=contract:raise ValueError('changed evaluation; use new output directory')
#|    write_json(cp,contract)
#|    rows=[dict(id=r['id'],image=r['image'],conversations=[r['conversations'][0]]) for r in json.loads(paths.test_json.read_text(encoding='utf-8'))]
#|    if len({str(r['id']) for r in rows})!=len(rows):raise ValueError('duplicate TEST IDs')
#|    with paths.test_features.open('rb') as f:features=pickle.load(f)
#|    rt=load_runtime(paths,variant,a.device,payload['config'],payload['lora_config'],payload)
#|    for obj in (rt.model,rt.controller,rt.verifier,rt.roles):
#|        if obj is not None:
#|            obj.eval()
#|            for q in obj.parameters():q.requires_grad_(False)
#|    graphs,texts=graph_inputs(rt,a.test_graph,'test');results=[]
#|    proxy=rt.controller or SimpleNamespace(config=SimpleNamespace(label_token_count=4,label_readout_scale=.1),semantic_readout=NoReadout())
#|    # clean-v8 uses no_grad; the historical v16 runner uses inference_mode.
#|    with (torch.no_grad() if variant=='innovation1' else torch.inference_mode()):
#|        for index,row in enumerate(rows):
#|            item_path=out/f'item_{index:05d}.json'
#|            if item_path.exists():
#|                item=json.loads(item_path.read_text(encoding='utf-8'))
#|                if str(item['id'])!=str(row['id']):raise ValueError('cached ID mismatch')
#|                results.append(item);continue
#|            item=infer_record(rt,row,features,graphs,texts)
#|            selected=item['selected']
#|            write_json(item_path,item);results.append(item)
#|            print(f'[final infer] variant={variant} records={index+1}/{len(rows)} selected={selected}',flush=True)
#|    with (out/'result.tmp').open('w',encoding='utf-8',newline='') as f:
#|        writer=csv.DictWriter(f,fieldnames=('id','label','explanation'));writer.writeheader()
#|        writer.writerows(prediction_row(rt,r) for r in results)
#|    (out/'result.tmp').replace(out/'result.csv')
#|    for mode in ('source','routed_source'):
#|        folder=out/mode;folder.mkdir(exist_ok=True)
#|        with (folder/'result.tmp').open('w',encoding='utf-8',newline='') as f:
#|            writer=csv.DictWriter(f,fieldnames=('id','label','explanation'));writer.writeheader()
#|            writer.writerows(prediction_row(rt,r,mode) for r in results)
#|        (folder/'result.tmp').replace(folder/'result.csv')
#|    write_json(out/'complete.json',dict(records=len(results),variant=variant,reference_used=False,
#|        selected_nonbaseline=sum(r['selected']!=0 for r in results),
#|        selection_label_changes=sum(parse_label(r['final'])!=parse_label(r['routed_source']) for r in results)))
#|
#|if __name__=='__main__':main()
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: lces_stage_4_polarity.py ===
#|"""Binary verdict-margin objective for LCES-v4."""
#|
#|from __future__ import annotations
#|
#|from dataclasses import dataclass
#|
#|
#|@dataclass(frozen=True)
#|class PolarityDiagnostics:
#|    loss: object
#|    cross_entropy: object
#|    margin_loss: object
#|    mean_margin: object
#|    accuracy: object
#|    count: int
#|
#|
#|def first_supervised_polarity_loss(
#|    logits,
#|    labels,
#|    *,
#|    contradiction_token_id: int,
#|    entailment_token_id: int,
#|    ignore_index: int,
#|    margin: float,
#|    margin_weight: float,
#|) -> PolarityDiagnostics:
#|    """Contrast the two verdict tokens at the first supervised position."""
#|
#|    import torch
#|    import torch.nn.functional as F
#|
#|    if logits.ndim != 3 or labels.ndim != 2:
#|        raise ValueError("LCES-v4 expects [B,T,V] logits and [B,T] labels")
#|    if logits.shape[:2] != labels.shape:
#|        raise ValueError("LCES-v4 logits/labels sequence shapes differ")
#|    if logits.size(1) < 2:
#|        raise ValueError("LCES-v4 sequence is too short")
#|    if contradiction_token_id == entailment_token_id:
#|        raise ValueError("LCES-v4 polarity tokens must differ")
#|    if margin < 0.0 or margin_weight < 0.0:
#|        raise ValueError("LCES-v4 margin settings must be non-negative")
#|
#|    shift_logits = logits[:, :-1, :].float()
#|    shift_labels = labels[:, 1:].long()
#|    valid = shift_labels.ne(int(ignore_index))
#|    has_target = valid.any(dim=1)
#|    if not bool(has_target.all()):
#|        raise RuntimeError("LCES-v4 found a sample without supervised tokens")
#|    first_positions = valid.float().argmax(dim=1)
#|    batch_indices = torch.arange(
#|        shift_labels.size(0),
#|        device=shift_labels.device,
#|    )
#|    gold_tokens = shift_labels[batch_indices, first_positions]
#|    pair_ids = gold_tokens.new_tensor(
#|        [int(contradiction_token_id), int(entailment_token_id)]
#|    )
#|    token_matches = gold_tokens.unsqueeze(1).eq(pair_ids.unsqueeze(0))
#|    if not bool(token_matches.any(dim=1).all()):
#|        unexpected = gold_tokens[~token_matches.any(dim=1)].detach().cpu().tolist()
#|        raise RuntimeError(
#|            "LCES-v4 first supervised tokens are not verdict tokens: "
#|            f"{unexpected[:8]}"
#|        )
#|    targets = token_matches.float().argmax(dim=1).long()
#|    selected = shift_logits[batch_indices, first_positions][:, pair_ids]
#|    cross_entropy = F.cross_entropy(selected, targets)
#|    correct = selected.gather(1, targets.unsqueeze(1)).squeeze(1)
#|    wrong = selected.gather(1, (1 - targets).unsqueeze(1)).squeeze(1)
#|    signed_margin = correct - wrong
#|    margin_loss = torch.relu(float(margin) - signed_margin).mean()
#|    loss = cross_entropy + float(margin_weight) * margin_loss
#|    accuracy = selected.argmax(dim=1).eq(targets).float().mean()
#|    return PolarityDiagnostics(
#|        loss=loss,
#|        cross_entropy=cross_entropy,
#|        margin_loss=margin_loss,
#|        mean_margin=signed_margin.mean(),
#|        accuracy=accuracy,
#|        count=int(targets.numel()),
#|    )
#|
#|
#|def encode_verdict_first_tokens(tokenizer) -> tuple[int, int]:
#|    """Return distinct first token ids for contradiction and entailment."""
#|
#|    output = []
#|    for text in ("contradiction.", "entailment."):
#|        encoded = tokenizer(text, add_special_tokens=False)
#|        ids = encoded["input_ids"] if isinstance(encoded, dict) else encoded.input_ids
#|        if not ids:
#|            raise ValueError(f"tokenizer produced no verdict ids for {text!r}")
#|        output.append(int(ids[0]))
#|    if output[0] == output[1]:
#|        raise ValueError("verdict strings share a first token")
#|    return output[0], output[1]
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: llava_final_runtime.py ===
#|"""Shared LLaVA-only initialization and single-file model format.
#|
#|No RIFT checkpoint, v6/v8 checkpoint, FLUTE bank, or legacy adapter is loaded.
#|"""
#|import importlib.util,json,sys
#|from pathlib import Path
#|from types import SimpleNamespace
#|
#|VARIANTS=('innovation1','innovation2','combined')
#|
#|
#|def final_controller_config():
#|    """Pin the effective clean-v8 runner configuration, not inherited class defaults."""
#|    from dataclasses import asdict
#|    from rgc_semantic_readout_stage_8 import ReliabilityTrustReadoutConfig
#|    return asdict(ReliabilityTrustReadoutConfig(graph_dropout=0.,gate_init=.04,gate_cap=.12,
#|        rank_modulation_cap=.35,residual_norm_ratio=.06,alignment_nce_weight=0.,
#|        alignment_decay_start=.50,alignment_final_nce_weight=0.,same_group_negative_scale=1.,
#|        decoder_alignment_weight=.015))
#|
#|
#|def fresh_lora_settings(layers):
#|    targets=[]
#|    for i in range(layers):
#|        targets.extend(f'model.layers.{i}.self_attn.{n}' for n in ('q_proj','k_proj','v_proj','o_proj'))
#|        targets.extend(f'model.layers.{i}.mlp.{n}' for n in ('gate_proj','up_proj','down_proj'))
#|    return dict(r=128,lora_alpha=256,lora_dropout=.05,bias='none',task_type='CAUSAL_LM',target_modules=targets)
#|
#|
#|def set_stage_seed(torch,seed,stage):
#|    import random
#|    effective=seed+{'foundation':0,'consolidation':10000,'verifier':20000}[stage]
#|    random.seed(effective);torch.manual_seed(effective)
#|    return effective
#|
#|
#|def configure_stage(rt,stage):
#|    """One explicit parameter/mode contract for every variant."""
#|    is_verifier=stage=='verifier';consolidate=stage=='consolidation' and rt.controller is not None
#|    rt.model.train(not is_verifier and not consolidate)
#|    for name,param in rt.model.named_parameters():param.requires_grad_('lora_' in name and not is_verifier and not consolidate)
#|    if rt.controller is not None:
#|        rt.controller.train(not is_verifier)
#|        for name,param in rt.controller.named_parameters():
#|            param.requires_grad_(not is_verifier and (not consolidate or name.startswith(('semantic_readout.','decoder_alignment_projection.','graph_alignment_projection.','target_alignment_projection.'))))
#|        if consolidate:rt.controller.set_trust_reference()
#|    if rt.verifier is not None:
#|        for obj in (rt.verifier,rt.roles):
#|            obj.train(is_verifier)
#|            for param in obj.parameters():param.requires_grad_(is_verifier)
#|        if is_verifier and rt.controller is not None:
#|            for k,prefix in (('E_image','img'),('E_text','txt'),('E_desc','desc')):
#|                rt.roles[k][0].load_state_dict(getattr(rt.controller,prefix+'_proj').state_dict())
#|                rt.roles[k][1].load_state_dict(getattr(rt.controller,prefix+'_norm').state_dict())
#|            for param in rt.roles.parameters():param.requires_grad_(False)
#|    if is_verifier:
#|        rt.model.gradient_checkpointing_disable()
#|        if rt.verifier is None:raise ValueError('innovation1 has no verifier stage')
#|        for obj in (rt.model,rt.controller):
#|            if obj is not None and any(p.requires_grad for p in obj.parameters()):raise RuntimeError('verifier stage must freeze generator')
#|    return is_verifier,consolidate
#|
#|
#|def generator_versions(rt):
#|    return {prefix+'.'+n:p._version for prefix,obj in (('model',rt.model),('controller',rt.controller))
#|        if obj is not None for n,p in obj.named_parameters()}
#|
#|
#|def assert_frozen_generator(rt,versions):
#|    if generator_versions(rt)!=versions:raise RuntimeError('generator parameter version changed during verifier training')
#|    for obj in (rt.model,rt.controller):
#|        if obj is not None and any(p.requires_grad or p.grad is not None for p in obj.parameters()):raise RuntimeError('generator has trainable parameters or gradients during verifier stage')
#|
#|
#|def enable_training_checkpointing(model):
#|    """Support old HF's no-argument API while retaining non-reentrant autograd.
#|
#|    Old LlamaModel forwards call torch.utils.checkpoint.checkpoint directly;
#|    changing only _gradient_checkpointing_func does not cover that API.
#|    The legacy override is process-local to this training invocation.
#|    """
#|    import inspect,functools
#|    import torch.utils.checkpoint as checkpoint_module
#|    enable=model.gradient_checkpointing_enable
#|    parameters=inspect.signature(enable).parameters
#|    if 'gradient_checkpointing_kwargs' in parameters or any(p.kind==inspect.Parameter.VAR_KEYWORD for p in parameters.values()):
#|        enable(gradient_checkpointing_kwargs={'use_reentrant':False})
#|        print('[final checkpoint] modern API; use_reentrant=False',flush=True)
#|        return 'modern'
#|    original=checkpoint_module.checkpoint
#|    if 'use_reentrant' not in inspect.signature(original).parameters:
#|        raise RuntimeError('This PyTorch checkpoint implementation lacks use_reentrant; non-reentrant support is required')
#|    if getattr(original,'_llava_final_nonreentrant',False):
#|        wrapper=original
#|    else:
#|        @functools.wraps(original)
#|        def wrapper(function,*args,**kwargs):
#|            kwargs['use_reentrant']=False
#|            return original(function,*args,**kwargs)
#|        wrapper._llava_final_nonreentrant=True
#|    enable()
#|    checkpoint_module.checkpoint=wrapper
#|    aliases=0
#|    for module in model.modules():
#|        if hasattr(module,'_gradient_checkpointing_func'):
#|            module._gradient_checkpointing_func=wrapper
#|        for cls in type(module).__mro__:
#|            forward=cls.__dict__.get('forward')
#|            namespace=getattr(forward,'__globals__',{})
#|            for name,value in list(namespace.items()):
#|                if value is original and value is not wrapper:
#|                    namespace[name]=wrapper;aliases+=1
#|    print(f'[final checkpoint] legacy HF API; use_reentrant=False; direct torch call and {aliases} imported aliases covered',flush=True)
#|    return 'legacy'
#|
#|
#|def build_modules(torch,hidden,variant,config):
#|    if variant not in VARIANTS:raise ValueError('unknown variant')
#|    controller=verifier=roles=None
#|    if variant!='innovation2':
#|        from rgc_semantic_readout_stage_8 import ReliabilityTrustReadoutConfig,make_v8_readout_classes
#|        _,Controller=make_v8_readout_classes(torch,torch.nn)
#|        controller=Controller(hidden,0,ReliabilityTrustReadoutConfig(**config),training_graph_dropout=False)
#|    if variant!='innovation1':
#|        from final_original_verifier import make_verifier
#|        verifier=make_verifier(torch,hidden,256)
#|        # A fresh evidence-role encoder belongs to innovation2, not a RIFT projector.
#|        roles=torch.nn.ModuleDict({k:torch.nn.Sequential(torch.nn.Linear(d,256),torch.nn.LayerNorm(256))
#|            for k,d in (('E_image',768),('E_text',1024),('E_desc',1024))})
#|        if controller is not None:
#|            for k,prefix in (('E_image','img'),('E_text','txt'),('E_desc','desc')):
#|                roles[k][0].load_state_dict(getattr(controller,prefix+'_proj').state_dict())
#|                roles[k][1].load_state_dict(getattr(controller,prefix+'_norm').state_dict())
#|    return controller,verifier,roles
#|
#|
#|def import_io(paths):
#|    # Import only original LLaVA image/prompt IO helpers; never load its hybrid model.
#|    root=paths.orig_root.resolve();sys.path.insert(0,str(root))
#|    spec=importlib.util.spec_from_file_location('llava_final_io',root/'test_v45_rag.py')
#|    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
#|    return module
#|
#|
#|def load_runtime(paths,variant,device,config,lora_config=None,payload=None):
#|    import torch
#|    from peft import LoraConfig,get_peft_model,set_peft_model_state_dict
#|    module=import_io(paths)
#|    tokenizer,model,processor,_=module.load_pretrained_model(paths.llm_path,None,module.get_model_name_from_path(paths.llm_path),device_map=device,torch_dtype=torch.bfloat16)
#|    model.to(device=device,dtype=torch.bfloat16)
#|    if tokenizer.pad_token is None:tokenizer.pad_token=tokenizer.unk_token
#|    lc=LoraConfig(**(lora_config if lora_config else fresh_lora_settings(model.config.num_hidden_layers)))
#|    model=get_peft_model(model,lc)
#|    controller,verifier,roles=build_modules(torch,model.config.hidden_size,variant,config)
#|    if payload:
#|        from peft import get_peft_model_state_dict
#|        expected=get_peft_model_state_dict(model)
#|        if set(expected)!=set(payload['lora']) or any(expected[k].shape!=payload['lora'][k].shape for k in expected):raise ValueError('saved LoRA structure mismatch')
#|        result=set_peft_model_state_dict(model,payload['lora'])
#|        if result.unexpected_keys:raise ValueError('unexpected saved LoRA tensors')
#|        restored=get_peft_model_state_dict(model)
#|        if any(not torch_equal_after_cast(torch,restored[k],payload['lora'][k]) for k in restored):raise ValueError('LoRA restore changed saved values beyond destination dtype conversion')
#|        for obj,key in ((controller,'controller'),(verifier,'verifier'),(roles,'roles')):
#|            if (obj is None)!=(payload[key] is None):raise ValueError('variant/module mismatch')
#|            if obj is not None:obj.load_state_dict(payload[key],strict=True)
#|        model=model.merge_and_unload().to(device=device,dtype=torch.bfloat16)
#|    for obj in (controller,verifier,roles):
#|        if obj is not None:obj.to(device)
#|    if controller is not None:
#|        from rgc_semantic_readout import attach_semantic_readout
#|        attach_semantic_readout(model,controller)
#|    return SimpleNamespace(torch=torch,module=module,model=model,tokenizer=tokenizer,processor=processor,
#|        controller=controller,verifier=verifier,roles=roles,paths=paths,device=device,variant=variant)
#|
#|
#|def torch_equal_after_cast(torch,loaded,saved):
#|    return torch.equal(loaded.detach().cpu(),saved.to(dtype=loaded.dtype,device='cpu'))
#|
#|
#|def graph_inputs(rt,path,split):
#|    if rt.controller is None:return None,None
#|    from concept_graph_integration import require_concept_graph_cache
#|    from rgc_semantic_readout import load_graph_semantic_text_map
#|    _,features,_=require_concept_graph_cache(Path(path),split=split,allow_phenomenon_fallback=split=='train')
#|    texts=load_graph_semantic_text_map(Path(path),allow_phenomenon_fallback=split=='train')
#|    return features,texts
#|
#|
#|def context(rt,row,features,graphs,texts,group=None):
#|    torch=rt.torch;f=features[row['id']];condition=None
#|    if rt.controller is not None:
#|        from rgc_semantic_readout import tokenize_graph_semantic_text,safe_token_embeddings
#|        c=rt.controller;c.semantic_readout.reset_generation()
#|        c.set_group_context(None if group is None else torch.tensor([group],device=rt.device))
#|        ids,mask=tokenize_graph_semantic_text(rt.tokenizer,texts.get(row['id'],''),c.config.semantic_max_length)
#|        with torch.no_grad():sem,mask=safe_token_embeddings(rt.model.get_input_embeddings(),ids[None].to(rt.device),mask[None].to(rt.device),vocab_size=rt.model.config.vocab_size)
#|        condition,_=c(*[f[k][None].to(rt.device) for k in ('E_image','E_text','E_desc')],graph_feature=graphs[row['id']][None].to(rt.device),semantic_token_embeddings=sem,semantic_mask=mask)
#|    if rt.verifier is not None:
#|        rt.verifier._iesfd_v10_roles=torch.stack([rt.roles[k](f[k][None].to(rt.device).float()) for k in ('E_image','E_text','E_desc')],1)
#|    return condition
#|
#|
#|def prompt(rt,row):
#|    from cache_iesfd_stage_11_candidates import prepare_prompt
#|    return prepare_prompt(rt.module,rt.tokenizer,rt.model,rt.processor,str(rt.paths.image_folder/row['image']),row['conversations'][0]['value'],rt.device)
#|
#|
#|def forward_answer(rt,embeds,mask,text,training=False):
#|    torch=rt.torch
#|    from rgc_semantic_readout import find_final_decoder_norm
#|    ids=rt.tokenizer(text,add_special_tokens=False,return_tensors='pt').input_ids.to(rt.device)
#|    if training and rt.tokenizer.eos_token_id is not None:ids=torch.cat((ids,ids.new_tensor([[rt.tokenizer.eos_token_id]])),1)
#|    tokens=rt.model.get_input_embeddings()(ids);joint=torch.cat((embeds.to(tokens.dtype),tokens),1)
#|    if joint.size(1)>getattr(rt.model.config,'max_position_embeddings',4096):raise ValueError('example exceeds model context; no silent truncation')
#|    labels=torch.cat((ids.new_full((1,embeds.size(1)),-100),ids),1)
#|    c=rt.controller
#|    if c is not None:
#|        c.semantic_readout.reset_generation()
#|        if training:c.prepare_readout_token_scale(labels,-100)
#|        else:
#|            scale=torch.ones((*joint.shape[:2],1),device=rt.device)
#|            scale[:,:embeds.size(1)+max(0,c.config.label_token_count-1)]=c.config.label_readout_scale
#|            c.semantic_readout.set_token_scale(scale)
#|    _,norm=find_final_decoder_norm(rt.model);captured=[]
#|    hook=norm.register_forward_hook(lambda m,args,out:captured.append(out))
#|    try:
#|        out=rt.model(inputs_embeds=joint,attention_mask=torch.cat((mask,torch.ones_like(ids)),1),labels=labels if training else None,use_cache=False,return_dict=True)
#|        hidden=captured[-1]
#|        return out,hidden,ids,labels
#|    finally:
#|        hook.remove()
#|        if c is not None:c.clear_readout_token_scale()
#|
#|
#|def export_payload(rt,config,metadata):
#|    from peft import get_peft_model_state_dict
#|    def state(obj):return None if obj is None else {k:v.detach().cpu().clone() for k,v in obj.state_dict().items()}
#|    lc=rt.model.peft_config['default'].to_dict()
#|    for k,v in lc.items():
#|        if isinstance(v,set):lc[k]=sorted(v)
#|    lc=json.loads(json.dumps(lc))
#|    return dict(schema='llava_final_single_v1',variant=rt.variant,config=config,metadata=metadata,
#|        lora_config=lc,lora={k:v.detach().cpu().clone() for k,v in get_peft_model_state_dict(rt.model).items()},
#|        controller=state(rt.controller),verifier=state(rt.verifier),roles=state(rt.roles))
#|
#|
#|def load_payload(torch,path):
#|    try:payload=torch.load(path,map_location='cpu',weights_only=True)
#|    except TypeError:payload=torch.load(path,map_location='cpu')
#|    if payload['schema']!='llava_final_single_v1' or payload['variant'] not in VARIANTS:raise ValueError('invalid final model')
#|    if bool(payload['controller'] is not None)!=(payload['variant']!='innovation2'):raise ValueError('wrong innovation1 state')
#|    if bool(payload['verifier'] is not None)!=(payload['variant']!='innovation1'):raise ValueError('wrong innovation2 state')
#|    if (payload['roles'] is None)!=(payload['verifier'] is None):raise ValueError('missing evidence role encoder')
#|    return payload
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: llava_legacy_inference.py ===
#|"""Restore the audited historical inference path from one final model.pt."""
#|import json
#|import tempfile
#|from pathlib import Path
#|from types import SimpleNamespace
#|
#|
#|def load_legacy_runtime(paths, variant, device, config, lora_config=None, payload=None):
#|    import torch
#|    from peft import PeftModel
#|    from test_llava_claim_graphprompt import load_original_test_module
#|    from llava_final_runtime import build_modules
#|    from rgc_semantic_readout import attach_semantic_readout
#|    if payload is None or payload['variant'] != variant:
#|        raise ValueError('Historical inference requires the final payload for this variant')
#|    module = load_original_test_module(paths)  # test_moe_创新点1.py, same as clean-v8
#|    tokenizer, backbone, processor, _ = module.load_pretrained_model(
#|        paths.llm_path, None, module.get_model_name_from_path(paths.llm_path),
#|        device_map=device, torch_dtype=torch.bfloat16)
#|    # Do not cast the base model or change tokenizer.pad_token before PEFT loads.
#|    # Match the successful audit's exact serialization and from_pretrained path.
#|    # This is a temporary read interface, not a new trained checkpoint.
#|    with tempfile.TemporaryDirectory(prefix='llava_legacy_adapter_') as directory:
#|        adapter = Path(directory)
#|        torch.save(payload['lora'], adapter / 'adapter_model.bin')
#|        (adapter / 'adapter_config.json').write_text(
#|            json.dumps(payload['lora_config'], ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
#|        if variant == 'innovation1':
#|            model = PeftModel.from_pretrained(backbone, str(adapter))
#|        else:
#|            model = PeftModel.from_pretrained(backbone, str(adapter), is_trainable=False)
#|        model = model.merge_and_unload()
#|    model = model.to(device=device, dtype=torch.bfloat16)
#|    model.eval()
#|    controller, verifier, roles = build_modules(torch, model.config.hidden_size, variant, config)
#|    for obj, key in ((controller, 'controller'), (verifier, 'verifier'), (roles, 'roles')):
#|        if (obj is None) != (payload[key] is None): raise ValueError('Payload module mismatch: ' + key)
#|        if obj is not None:
#|            obj.load_state_dict(payload[key], strict=True)
#|            obj.to(device).eval()
#|    if controller is not None: attach_semantic_readout(model, controller)
#|    print('[legacy inference] original test_moe IO; from_pretrained -> merge -> BF16; tokenizer unchanged', flush=True)
#|    return SimpleNamespace(torch=torch, module=module, model=model, tokenizer=tokenizer,
#|        processor=processor, controller=controller, verifier=verifier, roles=roles,
#|        paths=paths, device=device, variant=variant)
#|
#|
#|def original_source_response(rt, row):
#|    return rt.module.get_response(str(rt.paths.image_folder / row['image']),
#|        row['conversations'][0]['value'], rt.tokenizer, rt.model, rt.processor,
#|        rt.controller, None, rt.device)
#|
#|
#|def prediction_row(rt, item, key='final'):
#|    text = item[key]
#|    if rt.variant == 'innovation1':
#|        # Exact historical clean-v8 CSV extraction, including whitespace.
#|        label = rt.module.parse_label(text)
#|        explanation = '.'.join(text.split('.')[1:]).strip()
#|    else:
#|        # The original v16 runner uses these two functions for all its outputs.
#|        from dome_ft_data import parse_label, strip_label
#|        label, explanation = parse_label(text), strip_label(text)
#|    return dict(id=item['id'], label=label, explanation=explanation)
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: llava_replay_memory.py ===
#|"""CPU-only inter-stage snapshots; never write intermediate weights."""
#|from dataclasses import dataclass
#|
#|
#|@dataclass
#|class MemorySource:
#|    lora: dict
#|    projector: dict
#|    adapter_config: object = None
#|
#|    @classmethod
#|    def capture(cls, model):
#|        import copy
#|        from peft import get_peft_model_state_dict
#|        def cpu(state):
#|            return {k: v.detach().cpu().clone() for k, v in state.items()}
#|        return cls(cpu(get_peft_model_state_dict(model.llm)), cpu(model.projector.state_dict()),
#|                   copy.deepcopy(model.llm.peft_config['default']))
#|
#|    def restore_lora(self, llm):
#|        import copy
#|        import torch
#|        from peft import get_peft_model_state_dict, set_peft_model_state_dict
#|        if self.adapter_config is not None:
#|            # Follow the old PeftModel.from_pretrained constructor path, replacing
#|            # only its config/weight file reads with the in-memory snapshot.
#|            # Reusing the existing adapter would omit initialization RNG draws.
#|            from peft import get_peft_model
#|            config = copy.deepcopy(self.adapter_config)
#|            config.inference_mode = True
#|            base = llm.base_model.model if hasattr(llm, 'base_model') else llm
#|            llm = get_peft_model(base, config)
#|        current = get_peft_model_state_dict(llm)
#|        if current.keys() != self.lora.keys():
#|            raise ValueError('In-memory source LoRA keys differ from fresh original model')
#|        if any(current[k].shape != self.lora[k].shape for k in current):
#|            raise ValueError('In-memory source LoRA shapes differ')
#|        result = set_peft_model_state_dict(llm, self.lora)
#|        if result.unexpected_keys:
#|            raise ValueError('Unexpected LoRA source tensors')
#|        restored = get_peft_model_state_dict(llm)
#|        for key, value in restored.items():
#|            if not torch.equal(value.detach().cpu(), self.lora[key].to(dtype=value.dtype)):
#|                raise ValueError('In-memory LoRA restore failed: ' + key)
#|        return llm
#|
#|
#|def split_final_modules(torch, model, variant):
#|    """Translate the historical composite projector into the existing final format."""
#|    from dataclasses import asdict
#|    from llava_final_runtime import build_modules, final_controller_config
#|    if variant == 'innovation2':
#|        return None, model.projector.verifier, model.projector.roles, final_controller_config()
#|    config = asdict(model.projector.config)
#|    controller, verifier, roles = build_modules(torch, model.hidden_size, variant, config)
#|    state = model.projector.state_dict()
#|    controller.load_state_dict({k: v for k, v in state.items() if not k.startswith('iesfd_v10_')}, strict=True)
#|    if verifier is not None:
#|        verifier.load_state_dict({k: v for k, v in state.items() if k.startswith('iesfd_v10_')}, strict=True)
#|        for key, prefix in (('E_image', 'img'), ('E_text', 'txt'), ('E_desc', 'desc')):
#|            roles[key][0].load_state_dict(getattr(model.projector, prefix + '_proj').state_dict())
#|            roles[key][1].load_state_dict(getattr(model.projector, prefix + '_norm').state_dict())
#|    return controller, verifier, roles, config
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: llava_replay_standalone.py ===
#|"""LLaVA + IESFD ablation: original Dataset/loop, no innovation-1 controller."""
#|
#|
#|def prepare_plain_inputs(module, model, images, image_sizes, ids, mask, labels):
#|    """Match the historical semantic trainer's multimodal tail crop/pad/clamp."""
#|    torch = module.torch
#|    base = model.llm.base_model.model if hasattr(model.llm, 'base_model') else model.llm
#|    result = base.prepare_inputs_labels_for_multimodal(
#|        input_ids=ids, position_ids=None, attention_mask=mask,
#|        past_key_values=None, labels=labels, images=images, image_sizes=image_sizes)
#|    mask, embeds, labels = module.unpack_prepared(result, model.hidden_size)
#|    if isinstance(embeds, list): embeds = torch.cat(embeds, dim=0)
#|    if isinstance(mask, list): mask = torch.cat(mask, dim=0)
#|    if isinstance(labels, list): labels = torch.cat(labels, dim=0)
#|    if embeds is None:
#|        embeds = base.get_input_embeddings()(ids.clamp(0, model.vocab_size - 1))
#|    if embeds.dim() == 2: embeds = embeds.unsqueeze(0)
#|    shape = embeds.shape[:2]
#|    if mask is None: mask = torch.ones(shape, device=embeds.device, dtype=torch.long)
#|    else: mask = mask.reshape(-1)[:shape[0]*shape[1]].reshape(shape)
#|    if labels is None: raise RuntimeError('Multimodal training lost supervised labels')
#|    labels = labels.reshape(-1)[:shape[0]*shape[1]].reshape(shape)
#|    limit = model.max_seq_len - 8
#|    embeds, mask, labels = embeds[:, -limit:], mask[:, -limit:], labels[:, -limit:]
#|    remainder = embeds.size(1) % 8
#|    if remainder:
#|        pad = 8 - remainder
#|        embeds = torch.nn.functional.pad(embeds, (0, 0, 0, pad))
#|        mask = torch.nn.functional.pad(mask, (0, pad), value=0)
#|        labels = torch.nn.functional.pad(labels, (0, pad), value=module.IGNORE_INDEX)
#|    embeds = torch.nan_to_num(embeds.to(torch.bfloat16), nan=0., posinf=100., neginf=-100.).clamp(-100., 100.)
#|    return embeds.contiguous(), (mask > 0).long().contiguous(), labels.long().contiguous()
#|
#|
#|def install_standalone(module, graph_path, args, verifier_stage):
#|    torch = module.torch
#|    nn = torch.nn
#|    BaseModel, BaseDataset, collate = module.Hybrid_MoE_LLaVA, module.HybridDataset, module.collate_fn
#|
#|    class Projector(nn.Module):
#|        def __init__(self, hidden_size, num_tokens=0):
#|            super().__init__()
#|            if num_tokens != 0: raise ValueError('Standalone IESFD has no prompt tokens')
#|            if verifier_stage:
#|                from final_original_verifier import make_verifier
#|                self.verifier = make_verifier(torch, hidden_size, 256)
#|                self.roles = nn.ModuleDict({key: nn.Sequential(nn.Linear(dim, 256), nn.LayerNorm(256))
#|                    for key, dim in (('E_image', 768), ('E_text', 1024), ('E_desc', 1024))})
#|
#|    class Dataset(BaseDataset):
#|        def __getitem__(self, index):
#|            item = super().__getitem__(index)
#|            item['graph_feature'] = torch.zeros(1)  # shared loop signature only
#|            return item
#|
#|    def plain_collate(batch):
#|        result = collate(batch)
#|        result['graph_feature'] = torch.stack([item['graph_feature'] for item in batch])
#|        return result
#|
#|    class Model(BaseModel):
#|        def train(self, mode=True):
#|            super().train(mode)
#|            if verifier_stage: self.llm.eval()
#|            return self
#|
#|        def forward(self, images, image_sizes, e_img, e_txt, e_desc, graph_feature,
#|                    input_ids, attention_mask, labels, cf_labels, **extra):
#|            del graph_feature, cf_labels
#|            from rgc_semantic_readout import find_final_decoder_norm
#|            def run(ids, mask, target):
#|                embeds, prepared_mask, prepared_labels = prepare_plain_inputs(
#|                    module, self, images, image_sizes, ids, mask, target)
#|                captured = []
#|                handle = None
#|                if verifier_stage:
#|                    _, norm = find_final_decoder_norm(self.llm)
#|                    handle = norm.register_forward_hook(lambda _m, _a, out: captured.append(out))
#|                try:
#|                    out = self.llm(inputs_embeds=embeds, attention_mask=prepared_mask,
#|                                   labels=prepared_labels, use_cache=False, return_dict=True)
#|                finally:
#|                    if handle is not None: handle.remove()
#|                return out.loss, (captured[-1] if captured else None), prepared_labels
#|            if not verifier_stage:
#|                loss, _, _ = run(input_ids, attention_mask, labels)
#|                return loss, loss, loss.new_zeros(())
#|            from iesfd_stage_10 import explanation_state_mask, evidence_verifier_ranking_loss
#|            with torch.no_grad():
#|                lm, positive, positive_labels = run(input_ids, attention_mask, labels)
#|                eligible = bool(extra['oiec_eligible'].all())
#|                if eligible:
#|                    _, negative, negative_labels = run(extra['oiec_negative_ids'],
#|                        extra['oiec_negative_mask'], extra['oiec_negative_labels'])
#|            scorer = self.projector.verifier
#|            roles = self.projector.roles
#|            scorer._iesfd_v10_roles = torch.stack([roles[k](x.float()) for k, x in
#|                (('E_image', e_img), ('E_text', e_txt), ('E_desc', e_desc))], dim=1)
#|            # Preserve zero-gradient optimizer steps for ineligible records.
#|            auxiliary = sum((p.reshape(-1)[0] * 0. for p in self.projector.parameters()), lm.new_zeros(()))
#|            if eligible:
#|                scores = [scorer.score_evidence_candidates(hidden.detach(), explanation_state_mask(
#|                    torch, target, ignore_index=module.IGNORE_INDEX, label_token_count=4))[0]
#|                    for hidden, target in ((positive, positive_labels), (negative, negative_labels))]
#|                rank_loss, _, _ = evidence_verifier_ranking_loss(torch, *scores,
#|                    margin=args.verifier_margin, temperature=args.verifier_temperature,
#|                    anchor_weight=args.verifier_anchor_weight)
#|                auxiliary = auxiliary + args.verifier_weight * rank_loss
#|            return lm + auxiliary, lm, lm.new_zeros(())
#|
#|    module.MoE_LLM_Projector = Projector
#|    module.Hybrid_MoE_LLaVA = Model
#|    module.HybridDataset = Dataset
#|    module.collate_fn = plain_collate
#|    if verifier_stage:
#|        from train_llava_claim_oiec_stage_1 import install_oiec_training
#|        module, _ = install_oiec_training(module, graph_path, args=args, dataset_only=True)
#|    return module
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: oiec_completion.py ===
#|"""Pure helpers for order-invariant evidence-completion training.
#|
#|OIEC deliberately uses a same-label warrant replacement.  The label and the
#|rest of the explanation stay fixed, so the auxiliary task cannot be solved by
#|reading the verdict token.  Completion is scored from a mean over all answer
#|states; no fixed premise/warrant/relation order is assumed.
#|"""
#|
#|from __future__ import annotations
#|
#|import hashlib
#|from pathlib import Path
#|from typing import Any
#|
#|
#|def file_sha256(path: str | Path) -> str:
#|    digest = hashlib.sha256()
#|    with Path(path).open("rb") as handle:
#|        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
#|            digest.update(chunk)
#|    return digest.hexdigest()
#|
#|
#|def replace_exact_warrant(answer: str, record: dict[str, Any]) -> str:
#|    """Replace the audited silver span with its same-label hard mismatch."""
#|
#|    silver = record.get("silver_warrant")
#|    mismatch = record.get("same_label_hard_mismatch")
#|    if not isinstance(silver, dict) or not isinstance(mismatch, dict):
#|        raise ValueError("OIEC eligible record lacks an audited warrant pair")
#|    start, end = silver.get("char_start"), silver.get("char_end")
#|    if not isinstance(start, int) or not isinstance(end, int):
#|        raise ValueError("OIEC warrant offsets must be integers")
#|    if start < 0 or end <= start or end > len(answer):
#|        raise ValueError("OIEC warrant offsets are out of range")
#|    source_text = str(silver.get("text", ""))
#|    replacement = str(mismatch.get("text", ""))
#|    if answer[start:end] != source_text:
#|        raise ValueError("OIEC silver warrant is not source-exact")
#|    if not replacement.strip() or replacement == source_text:
#|        raise ValueError("OIEC same-label replacement is empty or unchanged")
#|    return answer[:start] + replacement + answer[end:]
#|
#|
#|def mean_answer_state(torch, hidden, labels, ignore_index: int, eos_token_id: int):
#|    """Mean-pool supervised answer states while excluding EOS.
#|
#|    ``labels`` must be the final labels passed into the language model after
#|    multimodal expansion and alignment padding.  Selecting by the supervised
#|    mask avoids every assumption about prompt length, image-token expansion,
#|    warrant position, or right-padding length.
#|    """
#|
#|    if hidden.dim() != 3 or hidden.size(0) != 1:
#|        raise ValueError("OIEC state pooling requires hidden shape [1, T, D]")
#|    if labels.dim() != 2 or labels.size(0) != 1:
#|        raise ValueError("OIEC state pooling requires labels shape [1, T]")
#|    if labels.size(1) != hidden.size(1):
#|        raise ValueError("OIEC captured labels and hidden states are misaligned")
#|    supervised = labels[0].ne(int(ignore_index))
#|    supervised_ids = labels[0][supervised]
#|    if supervised_ids.numel() < 2:
#|        raise ValueError("OIEC answer has fewer than two supervised tokens")
#|    if int(supervised_ids[-1].item()) != int(eos_token_id):
#|        raise ValueError("OIEC answer does not end in EOS")
#|    positions = supervised.nonzero(as_tuple=False).reshape(-1)
#|    content_positions = positions[:-1]
#|    if content_positions.numel() <= 0:
#|        raise ValueError("OIEC answer has no non-EOS supervised state")
#|    # The last supervised vector corresponds to the EOS input token.  Exclude
#|    # it and pool every answer token before it.
#|    return hidden[0].index_select(0, content_positions).float().mean(dim=0)
#|
#|
#|def completion_pair_loss(
#|    torch,
#|    positive_score,
#|    negative_score,
#|    *,
#|    margin: float,
#|    temperature: float,
#|    anchor_weight: float,
#|):
#|    """Smooth pairwise completion ranking with an anchored score direction."""
#|
#|    if margin <= 0.0 or temperature <= 0.0:
#|        raise ValueError("OIEC margin and temperature must be positive")
#|    if not 0.0 <= anchor_weight <= 1.0:
#|        raise ValueError("OIEC anchor_weight must be in [0, 1]")
#|    gap = positive_score.float() - negative_score.float()
#|    ranking = temperature * torch.nn.functional.softplus(
#|        (float(margin) - gap) / float(temperature)
#|    ).mean()
#|    anchor = 0.5 * (
#|        torch.nn.functional.softplus(-positive_score.float()).mean()
#|        + torch.nn.functional.softplus(negative_score.float()).mean()
#|    )
#|    return ranking + float(anchor_weight) * anchor, gap.mean()
#|
#|
#|def configure_oiec_training_modes(torch, llm, projector, completion_head, mode: bool):
#|    """Keep v7 capture active while disabling stochastic dropout.
#|
#|    The inherited v7 semantic readout stores its decoder state only when the
#|    projector/readout is in training mode.  The frozen LLM can remain in eval
#|    mode (gradients still flow to selected LoRA tensors), and individual
#|    dropout modules in the projector are put in eval mode to make the paired
#|    positive/negative comparison deterministic.
#|    """
#|
#|    llm.eval()
#|    projector.train(bool(mode))
#|    completion_head.train(bool(mode))
#|    for child in projector.modules():
#|        if isinstance(child, torch.nn.Dropout):
#|            child.eval()
#|    if hasattr(projector, "training_graph_dropout"):
#|        projector.training_graph_dropout = False
#|    if mode:
#|        semantic = getattr(projector, "semantic_readout", None)
#|        if not projector.training or semantic is None or not semantic.training:
#|            raise RuntimeError("OIEC requires the v7 semantic readout capture in train mode")
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: paths_paper2.py ===
#|"""Path configuration supplied by the user at runtime."""
#|
#|from __future__ import annotations
#|
#|import os
#|from dataclasses import dataclass
#|from pathlib import Path
#|
#|
#|PAPER2_DIR = Path(__file__).resolve().parent
#|def _norm_path(value: str | os.PathLike[str]) -> Path:
#|    return Path(os.path.normpath(os.fspath(value)))
#|
#|
#|@dataclass(frozen=True)
#|class Paper2Paths:
#|    orig_root: Path
#|    output_root: Path
#|    llm_path: str
#|
#|    @classmethod
#|    def from_env(cls) -> "Paper2Paths":
#|        original = os.environ.get("RIFT_ORIG_ROOT")
#|        model = os.environ.get("LLAVA_MODEL_PATH")
#|        if not original or not model:
#|            raise RuntimeError("Set RIFT_ORIG_ROOT and LLAVA_MODEL_PATH before running")
#|        orig_root = _norm_path(original)
#|        output_root = _norm_path(os.environ.get("PAPER2_OUTPUT_ROOT", PAPER2_DIR))
#|        llm_path = model
#|        return cls(orig_root=orig_root, output_root=output_root, llm_path=llm_path)
#|
#|    @property
#|    def train_json(self) -> Path:
#|        return self.orig_root / "data" / "train_ac2_v1.6_cot_merged.json"
#|
#|    @property
#|    def test_json(self) -> Path:
#|        return self.orig_root / "data" / "test_ac2_v1.6_cot_merged.json"
#|
#|    @property
#|    def train_features(self) -> Path:
#|        return self.orig_root / "data" / "train_ac2_v1.6_cot_merged_features.pkl"
#|
#|    @property
#|    def test_features(self) -> Path:
#|        return self.orig_root / "data" / "test_ac2_v1.6_cot_merged_features.pkl"
#|
#|    @property
#|    def flute_bank(self) -> Path:
#|        return self.orig_root / "flute" / "figurative_relation_rag_bank.pt"
#|
#|    @property
#|    def train_relation_queries(self) -> Path:
#|        return self.orig_root / "flute" / "FLUTE" / "vflute_relation_queries.pt"
#|
#|    @property
#|    def test_relation_queries(self) -> Path:
#|        return self.orig_root / "flute" / "FLUTE" / "vflute_relation_queries_test.pt"
#|
#|    @property
#|    def image_folder(self) -> Path:
#|        return self.orig_root
#|
#|    @property
#|    def original_train_script(self) -> Path:
#|        return self.orig_root / "train_v45_rag.py"
#|
#|    @property
#|    def original_test_script(self) -> Path:
#|        return self.orig_root / "test_v45_rag.py"
#|
#|    @property
#|    def original_metrics_script(self) -> Path:
#|        return self.orig_root / "compute_metrics_bscore_bleurt.py"
#|
#|    @property
#|    def default_true_csv(self) -> Path:
#|        return self.orig_root / "data" / "test_ground_truth_v1.6.csv"
#|
#|    @property
#|    def cache_dir(self) -> Path:
#|        return self.output_root / "cache"
#|
#|    @property
#|    def checkpoint_dir(self) -> Path:
#|        ckpt_name = os.environ.get("PAPER2_CKPT_NAME", "checkpoints_paper2_innov1_graphprompt")
#|        return self.output_root / ckpt_name
#|
#|    @property
#|    def result_dir(self) -> Path:
#|        return self.output_root / "result"
#|
#|    @property
#|    def pred_dir(self) -> Path:
#|        return self.output_root / "pred"
#|
#|    @property
#|    def train_concept_graph_cache(self) -> Path:
#|        return self.cache_dir / "concept_graph_train.jsonl"
#|
#|    @property
#|    def test_concept_graph_cache(self) -> Path:
#|        return self.cache_dir / "concept_graph_test.jsonl"
#|
#|    @property
#|    def train_adaptive_retrieval_cache(self) -> Path:
#|        return self.cache_dir / "adaptive_retrieval_train.pt"
#|
#|    @property
#|    def test_adaptive_retrieval_cache(self) -> Path:
#|        return self.cache_dir / "adaptive_retrieval_test.pt"
#|
#|    def resolve_output_path(self, value: str | os.PathLike[str]) -> Path:
#|        path = _norm_path(value)
#|        if path.is_absolute():
#|            return path
#|        return _norm_path(self.output_root / path)
#|
#|    def ensure_output_dirs(self) -> None:
#|        for path in [self.output_root, self.cache_dir, self.checkpoint_dir, self.result_dir, self.pred_dir]:
#|            path.mkdir(parents=True, exist_ok=True)
#|
#|    def require_original_inputs(self, split: str = "train") -> None:
#|        common = [self.flute_bank]
#|        if split == "train":
#|            required = [self.train_json, self.train_features, self.train_relation_queries, *common]
#|        elif split == "test":
#|            required = [self.test_json, self.test_features, self.test_relation_queries, *common]
#|        else:
#|            required = [
#|                self.train_json,
#|                self.test_json,
#|                self.train_features,
#|                self.test_features,
#|                self.train_relation_queries,
#|                self.test_relation_queries,
#|                *common,
#|            ]
#|        missing = [str(path) for path in required if not path.exists()]
#|        if missing:
#|            raise FileNotFoundError("Missing required original resources:\n" + "\n".join(missing))
#|
#|
#|def describe_paths(paths: Paper2Paths | None = None) -> str:
#|    paths = paths or Paper2Paths.from_env()
#|    rows = {
#|        "orig_root": paths.orig_root,
#|        "output_root": paths.output_root,
#|        "llm_path": paths.llm_path,
#|        "train_json": paths.train_json,
#|        "test_json": paths.test_json,
#|        "train_features": paths.train_features,
#|        "test_features": paths.test_features,
#|        "flute_bank": paths.flute_bank,
#|        "train_relation_queries": paths.train_relation_queries,
#|        "test_relation_queries": paths.test_relation_queries,
#|    }
#|    return "\n".join(f"{key}: {value}" for key, value in rows.items())
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: rgc_hyperlora.py ===
#|"""Reliability-gated concept-conditioned low-rank weight modulation.
#|
#|The concept graph is used in parameter space. It never becomes an input,
#|prefix, or soft-prompt token. Each selected decoder layer receives a bounded
#|sample-conditioned low-rank residual:
#|
#|    h' = h + gate(c) * B[SiLU(A LN(h)) * (1 + scale(c))]
#|
#|where ``c`` is computed from multimodal relation features and the filtered
#|concept-graph feature.
#|"""
#|
#|from __future__ import annotations
#|
#|import math
#|from typing import Any, Iterable
#|
#|
#|DATASET_FEATURE_INDEX = 5
#|
#|
#|def validate_hyperlora_config(
#|    *,
#|    hidden_size: int,
#|    condition_dim: int,
#|    rank: int,
#|    layer_indices: Iterable[int],
#|    gate_init: float,
#|    gate_cap: float,
#|    modulation_cap: float,
#|    residual_norm_ratio: float,
#|) -> tuple[int, ...]:
#|    layers = tuple(int(index) for index in layer_indices)
#|    if hidden_size <= 0 or condition_dim <= 0 or rank <= 0:
#|        raise ValueError("RGC-HyperLoRA dimensions must be positive")
#|    if not layers or len(layers) != len(set(layers)) or min(layers) < 0:
#|        raise ValueError("RGC-HyperLoRA layer indices must be unique and non-negative")
#|    if not 0.0 < gate_init < gate_cap <= 1.0:
#|        raise ValueError("RGC-HyperLoRA requires 0 < gate_init < gate_cap <= 1")
#|    if not 0.0 < modulation_cap <= 1.0:
#|        raise ValueError("RGC-HyperLoRA modulation_cap must be in (0, 1]")
#|    if not 0.0 < residual_norm_ratio <= 0.25:
#|        raise ValueError(
#|            "RGC-HyperLoRA residual_norm_ratio must be in (0, 0.25]"
#|        )
#|    return layers
#|
#|
#|def sanitize_graph_feature(graph_feature):
#|    """Remove the dataset/source coordinate before graph conditioning."""
#|
#|    if graph_feature.size(-1) <= DATASET_FEATURE_INDEX:
#|        raise ValueError(
#|            "RGC-HyperLoRA graph feature is too short to remove source identity"
#|        )
#|    clean = graph_feature.clone()
#|    clean[..., DATASET_FEATURE_INDEX] = 0
#|    return clean
#|
#|
#|def _maybe_getattr(root: Any, path: str) -> Any | None:
#|    current = root
#|    for part in path.split("."):
#|        if not hasattr(current, part):
#|            return None
#|        current = getattr(current, part)
#|    return current
#|
#|
#|def find_decoder_layers(model: Any) -> list[Any]:
#|    """Find decoder layers before or after PEFT wrapping/merging."""
#|
#|    candidates = (
#|        "model.layers",
#|        "base_model.model.model.layers",
#|        "language_model.model.layers",
#|        "model.language_model.model.layers",
#|        "model.model.layers",
#|    )
#|    for path in candidates:
#|        layers = _maybe_getattr(model, path)
#|        if layers is not None and len(layers):
#|            return list(layers)
#|    if hasattr(model, "get_model"):
#|        inner = model.get_model()
#|        if inner is not model:
#|            layers = find_decoder_layers(inner)
#|            if layers:
#|                return layers
#|    raise RuntimeError("RGC-HyperLoRA could not locate decoder layers")
#|
#|
#|def make_hyperlora_classes(torch, nn):
#|    class ConditionalLowRankResidual(nn.Module):
#|        """A static low-rank basis with graph-conditioned rank coefficients."""
#|
#|        def __init__(
#|            self,
#|            hidden_size: int,
#|            condition_dim: int,
#|            rank: int,
#|            *,
#|            gate_init: float,
#|            gate_cap: float,
#|            modulation_cap: float,
#|            residual_norm_ratio: float,
#|        ) -> None:
#|            super().__init__()
#|            self.hidden_size = int(hidden_size)
#|            self.rank = int(rank)
#|            self.gate_cap = float(gate_cap)
#|            self.modulation_cap = float(modulation_cap)
#|            self.residual_norm_ratio = float(residual_norm_ratio)
#|
#|            self.input_norm = nn.LayerNorm(hidden_size)
#|            self.down = nn.Linear(hidden_size, rank, bias=False)
#|            self.up = nn.Linear(rank, hidden_size, bias=False)
#|            self.rank_controller = nn.Linear(condition_dim, rank)
#|            self.gate_controller = nn.Linear(condition_dim, 1)
#|
#|            nn.init.kaiming_uniform_(self.down.weight, a=math.sqrt(5))
#|            # A small non-zero branch gives the reliability controller a
#|            # gradient from the first step while the gate keeps it conservative.
#|            nn.init.normal_(self.up.weight, mean=0.0, std=1e-2)
#|            nn.init.zeros_(self.rank_controller.weight)
#|            nn.init.zeros_(self.rank_controller.bias)
#|            nn.init.zeros_(self.gate_controller.weight)
#|            nn.init.constant_(
#|                self.gate_controller.bias,
#|                math.log(gate_init / (gate_cap - gate_init)),
#|            )
#|
#|            self._condition = None
#|            self.last_gate = torch.tensor(gate_init)
#|            self.last_rank_scale = torch.tensor(0.0)
#|            self.last_residual_ratio = torch.tensor(0.0)
#|
#|        def set_condition(self, condition) -> None:
#|            if condition is None or condition.dim() != 2:
#|                raise ValueError(
#|                    "RGC-HyperLoRA condition must have shape [batch, dim]"
#|                )
#|            self._condition = condition
#|
#|        def _match_batch(self, condition, batch_size: int):
#|            if condition.size(0) == batch_size:
#|                return condition
#|            if condition.size(0) == 1:
#|                return condition.expand(batch_size, -1)
#|            if batch_size % condition.size(0) == 0:
#|                repeats = batch_size // condition.size(0)
#|                return condition.repeat_interleave(repeats, dim=0)
#|            raise RuntimeError(
#|                "RGC-HyperLoRA condition batch does not match hidden-state batch: "
#|                f"{condition.size(0)} vs {batch_size}"
#|            )
#|
#|        def forward(self, hidden):
#|            if self._condition is None:
#|                return hidden
#|            condition = self._match_batch(self._condition, hidden.size(0))
#|            target_device = hidden.device
#|            condition = condition.to(
#|                device=target_device,
#|                dtype=self.rank_controller.weight.dtype,
#|            )
#|            hidden_float = hidden.to(dtype=self.down.weight.dtype)
#|            low_rank = self.down(self.input_norm(hidden_float))
#|            rank_delta = self.modulation_cap * torch.tanh(
#|                self.rank_controller(condition)
#|            )
#|            modulated = torch.nn.functional.silu(low_rank) * (
#|                1.0 + rank_delta.unsqueeze(1)
#|            )
#|            residual = self.up(modulated)
#|            gate = self.gate_cap * torch.sigmoid(
#|                self.gate_controller(condition)
#|            )
#|            delta = residual * gate.unsqueeze(1)
#|
#|            hidden_norm = hidden_float.detach().norm(dim=-1, keepdim=True)
#|            delta_norm = delta.norm(dim=-1, keepdim=True).clamp_min(1e-6)
#|            max_norm = self.residual_norm_ratio * hidden_norm.clamp_min(1e-6)
#|            delta = delta * (max_norm / delta_norm).clamp(max=1.0)
#|
#|            self.last_gate = gate.detach().float().mean()
#|            self.last_rank_scale = rank_delta.detach().float().abs().mean()
#|            self.last_residual_ratio = (
#|                delta.detach().float().norm(dim=-1)
#|                / hidden.detach().float().norm(dim=-1).clamp_min(1e-6)
#|            ).mean()
#|            return hidden + delta.to(dtype=hidden.dtype)
#|
#|    class LayerwiseConceptHyperLoRA(nn.Module):
#|        """Container for all selected layer adapters."""
#|
#|        def __init__(
#|            self,
#|            hidden_size: int,
#|            condition_dim: int,
#|            rank: int,
#|            layer_indices: Iterable[int],
#|            *,
#|            gate_init: float,
#|            gate_cap: float,
#|            modulation_cap: float,
#|            residual_norm_ratio: float,
#|        ) -> None:
#|            super().__init__()
#|            layers = validate_hyperlora_config(
#|                hidden_size=hidden_size,
#|                condition_dim=condition_dim,
#|                rank=rank,
#|                layer_indices=layer_indices,
#|                gate_init=gate_init,
#|                gate_cap=gate_cap,
#|                modulation_cap=modulation_cap,
#|                residual_norm_ratio=residual_norm_ratio,
#|            )
#|            self.layer_indices = layers
#|            self.adapters = nn.ModuleDict(
#|                {
#|                    str(index): ConditionalLowRankResidual(
#|                        hidden_size,
#|                        condition_dim,
#|                        rank,
#|                        gate_init=gate_init,
#|                        gate_cap=gate_cap,
#|                        modulation_cap=modulation_cap,
#|                        residual_norm_ratio=residual_norm_ratio,
#|                    )
#|                    for index in layers
#|                }
#|            )
#|            self._hook_handles = []
#|
#|        def set_condition(self, condition) -> None:
#|            for adapter in self.adapters.values():
#|                adapter.set_condition(condition)
#|
#|        def attach(self, model) -> None:
#|            if self._hook_handles:
#|                return
#|            layers = find_decoder_layers(model)
#|            if max(self.layer_indices) >= len(layers):
#|                raise ValueError(
#|                    "RGC-HyperLoRA requested decoder layer "
#|                    f"{max(self.layer_indices)}, but model has {len(layers)} layers"
#|                )
#|            for index in self.layer_indices:
#|                adapter = self.adapters[str(index)]
#|
#|                def hook(_module, _inputs, output, layer_adapter=adapter):
#|                    hidden = output[0] if isinstance(output, tuple) else output
#|                    updated = layer_adapter(hidden)
#|                    if isinstance(output, tuple):
#|                        return (updated, *output[1:])
#|                    return updated
#|
#|                self._hook_handles.append(
#|                    layers[index].register_forward_hook(hook)
#|                )
#|                print(f"[rgc-hyperlora] attached decoder layer {index}")
#|
#|        def diagnostics(self):
#|            values = list(self.adapters.values())
#|            if not values:
#|                zero = torch.tensor(0.0)
#|                return zero, zero, zero
#|            device = values[0].last_gate.device
#|            gate = torch.stack(
#|                [item.last_gate.to(device) for item in values]
#|            ).mean()
#|            scale = torch.stack(
#|                [item.last_rank_scale.to(device) for item in values]
#|            ).mean()
#|            ratio = torch.stack(
#|                [item.last_residual_ratio.to(device) for item in values]
#|            ).mean()
#|            return gate, scale, ratio
#|
#|    return ConditionalLowRankResidual, LayerwiseConceptHyperLoRA
#|
#|
#|def attach_hyperlora(model, projector) -> None:
#|    if not hasattr(projector, "concept_hyperlora"):
#|        raise AttributeError("Projector has no concept_hyperlora module")
#|    projector.concept_hyperlora.attach(model)
#|
#|
#|def collect_hyperlora_metrics(model, torch) -> dict[str, str]:
#|    del torch
#|    controller = getattr(model.projector, "concept_hyperlora", None)
#|    if controller is None:
#|        return {}
#|    gate, rank_scale, residual_ratio = controller.diagnostics()
#|    return {
#|        "HL_G": f"{gate.item():.4f}",
#|        "HL_S": f"{rank_scale.item():.4f}",
#|        "HL_R": f"{residual_ratio.item():.4e}",
#|    }
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: rgc_semantic_readout.py ===
#|"""Token-free graph-semantic conditioning at the LLaVA language readout.
#|
#|Concept-graph text is encoded as a pooled side-channel representation. It is
#|never appended to the language-model input sequence. A bounded low-rank
#|adapter modifies the final decoder normalization output, where the ordinary
#|language-model loss can train the graph controller without crossing the
#|per-layer gradient-checkpoint boundaries more than once.
#|"""
#|
#|from __future__ import annotations
#|
#|import json
#|import math
#|from dataclasses import dataclass
#|from pathlib import Path
#|from typing import Any
#|
#|from concept_graph_integration import (
#|    GRAPH_FEATURE_DIM,
#|    extract_trusted_mapping_text,
#|)
#|from rgc_hyperlora import sanitize_graph_feature
#|
#|
#|@dataclass(frozen=True)
#|class SemanticReadoutConfig:
#|    relation_dim: int = 256
#|    condition_dim: int = 256
#|    readout_rank: int = 32
#|    controller_dropout: float = 0.10
#|    graph_dropout: float = 0.10
#|    gate_init: float = 0.08
#|    gate_cap: float = 0.25
#|    rank_modulation_cap: float = 0.50
#|    residual_norm_ratio: float = 0.08
#|    semantic_max_length: int = 96
#|
#|
#|def validate_semantic_readout_config(config: SemanticReadoutConfig) -> None:
#|    if min(
#|        config.relation_dim,
#|        config.condition_dim,
#|        config.readout_rank,
#|        config.semantic_max_length,
#|    ) <= 0:
#|        raise ValueError("SemanticReadout dimensions and lengths must be positive")
#|    if not 0.0 <= config.graph_dropout <= 1.0:
#|        raise ValueError("graph_dropout must be in [0, 1]")
#|    if not 0.0 < config.gate_init < config.gate_cap <= 1.0:
#|        raise ValueError("gate_init must satisfy 0 < init < cap <= 1")
#|    if not 0.0 < config.rank_modulation_cap <= 1.0:
#|        raise ValueError("rank_modulation_cap must be in (0, 1]")
#|    if not 0.0 < config.residual_norm_ratio <= 0.25:
#|        raise ValueError("residual_norm_ratio must be in (0, 0.25]")
#|
#|
#|def _clean(value: Any) -> str:
#|    return " ".join(str(value or "").strip().split())
#|
#|
#|def _unique_texts(value: Any, limit: int) -> list[str]:
#|    if not isinstance(value, list):
#|        return []
#|    output = []
#|    seen = set()
#|    for item in value:
#|        text = _clean(item)
#|        key = text.lower()
#|        if not text or key in seen:
#|            continue
#|        seen.add(key)
#|        output.append(text)
#|        if len(output) >= limit:
#|            break
#|    return output
#|
#|
#|def build_graph_semantic_text(
#|    record: dict[str, Any],
#|    *,
#|    allow_phenomenon_fallback: bool = True,
#|) -> str:
#|    """Serialize inference-safe concept fields into a compact side channel."""
#|
#|    inferred = _clean(record.get("inferred_phenomenon", ""))
#|    phenomenon = (
#|        inferred
#|        if inferred or not allow_phenomenon_fallback
#|        else _clean(record.get("phenomenon", ""))
#|    )
#|    anchors = _unique_texts(record.get("figurative_anchors", []), 8)
#|    visual_nodes = _unique_texts(record.get("visual_nodes", []), 12)
#|    claim_nodes = _unique_texts(record.get("claim_nodes", []), 10)
#|    trusted_mapping = _clean(
#|        extract_trusted_mapping_text(
#|            record,
#|            allow_phenomenon_fallback=allow_phenomenon_fallback,
#|        )
#|    )
#|
#|    fields = []
#|    if phenomenon:
#|        fields.append(f"phenomenon: {phenomenon}")
#|    if anchors:
#|        fields.append("figurative anchors: " + "; ".join(anchors))
#|    if visual_nodes:
#|        fields.append("visual concepts: " + "; ".join(visual_nodes))
#|    if claim_nodes:
#|        fields.append("claim concepts: " + "; ".join(claim_nodes))
#|    if trusted_mapping:
#|        fields.append("grounded mappings: " + trusted_mapping)
#|    return ". ".join(fields)
#|
#|
#|def load_graph_semantic_text_map(
#|    cache_path: str | Path | None,
#|    *,
#|    allow_phenomenon_fallback: bool = True,
#|) -> dict[Any, str]:
#|    if cache_path is None:
#|        return {}
#|    path = Path(cache_path)
#|    if not path.is_file():
#|        return {}
#|    output = {}
#|    with path.open("r", encoding="utf-8") as handle:
#|        for line in handle:
#|            if not line.strip():
#|                continue
#|            record = json.loads(line)
#|            output[record["id"]] = build_graph_semantic_text(
#|                record,
#|                allow_phenomenon_fallback=allow_phenomenon_fallback,
#|            )
#|    return output
#|
#|
#|def tokenize_graph_semantic_text(tokenizer, text: str, max_length: int):
#|    """Return fixed-size CPU tensors suitable for the original collator."""
#|
#|    import torch
#|
#|    if not text:
#|        return (
#|            torch.zeros(max_length, dtype=torch.long),
#|            torch.zeros(max_length, dtype=torch.long),
#|        )
#|    encoded = tokenizer(
#|        text,
#|        add_special_tokens=False,
#|        truncation=True,
#|        max_length=max_length,
#|        padding="max_length",
#|        return_tensors="pt",
#|    )
#|    return encoded["input_ids"][0].long(), encoded["attention_mask"][0].long()
#|
#|
#|def safe_token_embeddings(
#|    embed_layer,
#|    token_ids,
#|    token_mask,
#|    *,
#|    vocab_size: int,
#|):
#|    """Embed side-channel tokens without exposing them to the decoder."""
#|
#|    safe_ids = token_ids.long().clone()
#|    valid_ids = (safe_ids >= 0) & (safe_ids < int(vocab_size))
#|    safe_ids[~valid_ids] = 0
#|    mask = token_mask.to(safe_ids.device).bool() & valid_ids
#|    embeddings = embed_layer(safe_ids).float()
#|    return embeddings, mask
#|
#|
#|def masked_mean_token_embeddings(
#|    embed_layer,
#|    token_ids,
#|    token_mask,
#|    *,
#|    vocab_size: int,
#|):
#|    """Pool frozen token embeddings for a training-only semantic target."""
#|
#|    embeddings, mask = safe_token_embeddings(
#|        embed_layer,
#|        token_ids,
#|        token_mask,
#|        vocab_size=vocab_size,
#|    )
#|    weights = mask.unsqueeze(-1).to(embeddings.dtype)
#|    pooled = (embeddings * weights).sum(dim=1)
#|    pooled = pooled / weights.sum(dim=1).clamp_min(1.0)
#|    return pooled, mask.any(dim=1)
#|
#|
#|def _get_by_path(root: Any, path: str) -> Any | None:
#|    value = root
#|    for part in path.split("."):
#|        if not hasattr(value, part):
#|            return None
#|        value = getattr(value, part)
#|    return value
#|
#|
#|def find_final_decoder_norm(model: Any) -> tuple[str, Any]:
#|    candidates = (
#|        "base_model.model.model.norm",
#|        "base_model.model.model.model.norm",
#|        "model.model.norm",
#|        "model.norm",
#|        "base_model.model.norm",
#|    )
#|    for path in candidates:
#|        module = _get_by_path(model, path)
#|        if module is not None and hasattr(module, "register_forward_hook"):
#|            return path, module
#|
#|    matches = []
#|    for name, module in model.named_modules():
#|        if (
#|            (name == "norm" or name.endswith(".model.norm"))
#|            and hasattr(module, "register_forward_hook")
#|            and hasattr(module, "weight")
#|        ):
#|            matches.append((name, module))
#|    if not matches:
#|        raise RuntimeError("Could not locate the final decoder normalization layer")
#|    matches.sort(key=lambda item: (item[0].count("."), len(item[0])))
#|    return matches[0]
#|
#|
#|def make_semantic_readout_classes(torch, nn):
#|    class GraphSemanticReadout(nn.Module):
#|        def __init__(
#|            self,
#|            hidden_size: int,
#|            condition_dim: int,
#|            rank: int,
#|            *,
#|            gate_init: float,
#|            gate_cap: float,
#|            rank_modulation_cap: float,
#|            residual_norm_ratio: float,
#|        ):
#|            super().__init__()
#|            self.hidden_size = int(hidden_size)
#|            self.condition_dim = int(condition_dim)
#|            self.rank = int(rank)
#|            self.gate_cap = float(gate_cap)
#|            self.rank_modulation_cap = float(rank_modulation_cap)
#|            self.residual_norm_ratio = float(residual_norm_ratio)
#|
#|            self.down = nn.Linear(hidden_size, rank, bias=False)
#|            self.up = nn.Linear(rank, hidden_size, bias=False)
#|            self.rank_controller = nn.Linear(condition_dim, rank)
#|            self.condition_gate = nn.Linear(condition_dim, 1, bias=False)
#|            self.token_gate = nn.Linear(hidden_size, 1, bias=False)
#|            init_logit = math.log(gate_init / (gate_cap - gate_init))
#|            self.gate_bias = nn.Parameter(torch.tensor(init_logit))
#|
#|            nn.init.xavier_uniform_(self.down.weight)
#|            nn.init.xavier_uniform_(self.up.weight)
#|            nn.init.zeros_(self.rank_controller.weight)
#|            nn.init.zeros_(self.rank_controller.bias)
#|            nn.init.zeros_(self.condition_gate.weight)
#|            nn.init.zeros_(self.token_gate.weight)
#|
#|            self._condition = None
#|            self._hook_handle = None
#|            self.last_gate = torch.tensor(gate_init)
#|            self.last_rank_scale = torch.tensor(1.0)
#|            self.last_residual_ratio = torch.tensor(0.0)
#|
#|        def set_condition(self, condition) -> None:
#|            if condition is None or condition.dim() != 2:
#|                raise ValueError("readout condition must have shape [batch, dim]")
#|            self._condition = condition
#|
#|        def _match_condition(self, batch_size: int):
#|            condition = self._condition
#|            if condition is None:
#|                return None
#|            if condition.size(0) == batch_size:
#|                return condition
#|            if batch_size % condition.size(0) == 0:
#|                return condition.repeat_interleave(
#|                    batch_size // condition.size(0),
#|                    dim=0,
#|                )
#|            raise ValueError(
#|                "readout condition batch mismatch: "
#|                f"condition={condition.size(0)}, hidden={batch_size}"
#|            )
#|
#|        def forward(self, hidden):
#|            condition = self._match_condition(hidden.size(0))
#|            if condition is None:
#|                return hidden
#|
#|            original_dtype = hidden.dtype
#|            hidden_float = hidden.float()
#|            condition_float = condition.float()
#|            rank_scale = 1.0 + self.rank_modulation_cap * torch.tanh(
#|                self.rank_controller(condition_float)
#|            )
#|            low_rank = torch.nn.functional.silu(self.down(hidden_float))
#|            raw_delta = self.up(low_rank * rank_scale.unsqueeze(1))
#|
#|            hidden_norm = hidden_float.norm(dim=-1, keepdim=True).clamp_min(1e-6)
#|            delta_norm = raw_delta.norm(dim=-1, keepdim=True).clamp_min(1e-6)
#|            norm_scale = torch.clamp(
#|                self.residual_norm_ratio * hidden_norm / delta_norm,
#|                max=1.0,
#|            )
#|            bounded_delta = raw_delta * norm_scale
#|            gate = self.gate_cap * torch.sigmoid(
#|                self.gate_bias
#|                + self.condition_gate(condition_float).unsqueeze(1)
#|                + self.token_gate(hidden_float)
#|            )
#|            delta = bounded_delta * gate
#|            output = hidden_float + delta
#|
#|            self.last_gate = gate.detach().mean()
#|            self.last_rank_scale = rank_scale.detach().abs().mean()
#|            self.last_residual_ratio = (
#|                delta.detach().norm(dim=-1)
#|                / hidden_float.detach().norm(dim=-1).clamp_min(1e-6)
#|            ).mean()
#|            return output.to(original_dtype)
#|
#|        def attach(self, model) -> str:
#|            if self._hook_handle is not None:
#|                return getattr(self, "_attached_norm_name", "already-attached")
#|            name, norm = find_final_decoder_norm(model)
#|
#|            def hook(_module, _inputs, output):
#|                if isinstance(output, tuple):
#|                    return (self(output[0]), *output[1:])
#|                return self(output)
#|
#|            self._hook_handle = norm.register_forward_hook(hook)
#|            self._attached_norm_name = name
#|            return name
#|
#|    class GraphSemanticController(nn.Module):
#|        def __init__(
#|            self,
#|            hidden_size: int,
#|            num_tokens: int,
#|            config: SemanticReadoutConfig,
#|            *,
#|            training_graph_dropout: bool,
#|        ):
#|            super().__init__()
#|            validate_semantic_readout_config(config)
#|            if int(num_tokens) != 0:
#|                raise ValueError(
#|                    "RGC-SemanticReadout is token-free and requires num_tokens=0"
#|                )
#|            self.hidden_size = int(hidden_size)
#|            self.num_tokens = 0
#|            self.config = config
#|            self.training_graph_dropout = bool(training_graph_dropout)
#|
#|            relation_dim = config.relation_dim
#|            condition_dim = config.condition_dim
#|            self.img_proj = nn.Linear(768, relation_dim)
#|            self.txt_proj = nn.Linear(1024, relation_dim)
#|            self.desc_proj = nn.Linear(1024, relation_dim)
#|            self.img_norm = nn.LayerNorm(relation_dim)
#|            self.txt_norm = nn.LayerNorm(relation_dim)
#|            self.desc_norm = nn.LayerNorm(relation_dim)
#|            self.relation_encoder = nn.Sequential(
#|                nn.LayerNorm(relation_dim * 5),
#|                nn.Linear(relation_dim * 5, condition_dim),
#|                nn.GELU(),
#|            )
#|            self.graph_encoder = nn.Sequential(
#|                nn.LayerNorm(GRAPH_FEATURE_DIM),
#|                nn.Linear(GRAPH_FEATURE_DIM, condition_dim),
#|                nn.GELU(),
#|                nn.Linear(condition_dim, condition_dim),
#|                nn.GELU(),
#|            )
#|            self.semantic_encoder = nn.Sequential(
#|                nn.LayerNorm(hidden_size),
#|                nn.Linear(hidden_size, condition_dim),
#|                nn.GELU(),
#|                nn.Dropout(config.controller_dropout),
#|            )
#|            self.semantic_query = nn.Linear(condition_dim * 2, condition_dim)
#|            self.semantic_norm = nn.LayerNorm(condition_dim)
#|            self.reliability_router = nn.Linear(
#|                condition_dim * 3 + GRAPH_FEATURE_DIM,
#|                3,
#|            )
#|            self.condition_encoder = nn.Sequential(
#|                nn.LayerNorm(condition_dim * 6),
#|                nn.Linear(condition_dim * 6, condition_dim * 2),
#|                nn.GELU(),
#|                nn.Dropout(config.controller_dropout),
#|                nn.Linear(condition_dim * 2, condition_dim),
#|                nn.LayerNorm(condition_dim),
#|            )
#|            self.alignment_head = nn.Linear(condition_dim, hidden_size)
#|            self.semantic_readout = GraphSemanticReadout(
#|                hidden_size,
#|                condition_dim,
#|                config.readout_rank,
#|                gate_init=config.gate_init,
#|                gate_cap=config.gate_cap,
#|                rank_modulation_cap=config.rank_modulation_cap,
#|                residual_norm_ratio=config.residual_norm_ratio,
#|            )
#|
#|            for module in self.modules():
#|                if isinstance(module, nn.Linear) and module not in (
#|                    self.semantic_readout.rank_controller,
#|                    self.semantic_readout.condition_gate,
#|                    self.semantic_readout.token_gate,
#|                ):
#|                    if module is not self.semantic_readout.down and module is not self.semantic_readout.up:
#|                        nn.init.xavier_uniform_(module.weight)
#|                        if module.bias is not None:
#|                            nn.init.zeros_(module.bias)
#|            nn.init.zeros_(self.reliability_router.weight)
#|            nn.init.zeros_(self.reliability_router.bias)
#|
#|            self.last_graph_prompt_norm = torch.tensor(0.0)
#|            self.last_graph_gate = torch.tensor(config.gate_init)
#|            self.last_graph_drop_fraction = torch.tensor(0.0)
#|            self.last_semantic_alignment = torch.tensor(0.0)
#|            self.last_router_weights = torch.full((3,), 1.0 / 3.0)
#|
#|        def _drop_graph_evidence(
#|            self,
#|            graph_feature,
#|            semantic_token_embeddings,
#|            semantic_mask,
#|        ):
#|            if (
#|                not self.training
#|                or not self.training_graph_dropout
#|                or self.config.graph_dropout == 0.0
#|            ):
#|                self.last_graph_drop_fraction = graph_feature.new_zeros(())
#|                return (
#|                    graph_feature,
#|                    semantic_token_embeddings,
#|                    semantic_mask,
#|                )
#|            keep = (
#|                torch.rand(
#|                    (graph_feature.size(0), 1),
#|                    device=graph_feature.device,
#|                )
#|                >= self.config.graph_dropout
#|            )
#|            self.last_graph_drop_fraction = (~keep).float().mean().detach()
#|            return (
#|                graph_feature * keep.to(graph_feature.dtype),
#|                semantic_token_embeddings
#|                * keep.unsqueeze(-1).to(semantic_token_embeddings.dtype),
#|                semantic_mask & keep.bool(),
#|            )
#|
#|        def encode_condition(
#|            self,
#|            e_img,
#|            e_txt,
#|            e_desc,
#|            graph_feature,
#|            semantic_token_embeddings,
#|            semantic_mask,
#|            *,
#|            activate: bool,
#|        ):
#|            p_img = self.img_norm(self.img_proj(e_img.float()))
#|            p_txt = self.txt_norm(self.txt_proj(e_txt.float()))
#|            p_desc = self.desc_norm(self.desc_proj(e_desc.float()))
#|            relation = torch.cat(
#|                [
#|                    p_img,
#|                    p_desc,
#|                    p_txt,
#|                    torch.abs(p_desc - p_txt),
#|                    p_desc * p_txt,
#|                ],
#|                dim=-1,
#|            )
#|            if graph_feature is None:
#|                graph_feature = relation.new_zeros(
#|                    (relation.size(0), GRAPH_FEATURE_DIM)
#|                )
#|            if graph_feature.dim() == 1:
#|                graph_feature = graph_feature.unsqueeze(0)
#|            graph_feature = sanitize_graph_feature(
#|                graph_feature.to(relation.device).float()
#|            )
#|            if semantic_token_embeddings is None:
#|                semantic_token_embeddings = relation.new_zeros(
#|                    (relation.size(0), 1, self.hidden_size)
#|                )
#|            if semantic_token_embeddings.dim() == 2:
#|                semantic_token_embeddings = semantic_token_embeddings.unsqueeze(1)
#|            semantic_token_embeddings = semantic_token_embeddings.to(
#|                relation.device
#|            ).float()
#|            if semantic_mask is None:
#|                semantic_mask = torch.ones(
#|                    semantic_token_embeddings.shape[:2],
#|                    device=relation.device,
#|                    dtype=torch.bool,
#|                )
#|            else:
#|                semantic_mask = semantic_mask.to(relation.device).bool()
#|            (
#|                graph_feature,
#|                semantic_token_embeddings,
#|                semantic_mask,
#|            ) = self._drop_graph_evidence(
#|                graph_feature,
#|                semantic_token_embeddings,
#|                semantic_mask,
#|            )
#|
#|            relation_state = self.relation_encoder(relation)
#|            graph_state = self.graph_encoder(graph_feature)
#|            semantic_tokens = self.semantic_encoder(
#|                semantic_token_embeddings
#|            )
#|            semantic_query = self.semantic_query(
#|                torch.cat([relation_state, graph_state], dim=-1)
#|            )
#|            semantic_logits = (
#|                semantic_tokens * semantic_query.unsqueeze(1)
#|            ).sum(dim=-1) / math.sqrt(self.config.condition_dim)
#|            semantic_logits = semantic_logits.masked_fill(
#|                ~semantic_mask,
#|                -1e4,
#|            )
#|            semantic_weights = torch.softmax(semantic_logits, dim=-1)
#|            semantic_present = semantic_mask.any(dim=-1, keepdim=True)
#|            semantic_weights = (
#|                semantic_weights
#|                * semantic_mask.to(semantic_weights.dtype)
#|            )
#|            semantic_weights = semantic_weights / semantic_weights.sum(
#|                dim=-1,
#|                keepdim=True,
#|            ).clamp_min(1e-6)
#|            semantic_state = self.semantic_norm(
#|                (semantic_tokens * semantic_weights.unsqueeze(-1)).sum(dim=1)
#|            )
#|            semantic_state = (
#|                semantic_state
#|                * semantic_present.to(semantic_state.dtype)
#|            )
#|            route_input = torch.cat(
#|                [
#|                    relation_state,
#|                    graph_state,
#|                    semantic_state,
#|                    graph_feature,
#|                ],
#|                dim=-1,
#|            )
#|            route_weights = torch.softmax(
#|                self.reliability_router(route_input),
#|                dim=-1,
#|            )
#|            states = torch.stack(
#|                [relation_state, graph_state, semantic_state],
#|                dim=1,
#|            )
#|            routed = (states * route_weights.unsqueeze(-1)).sum(dim=1)
#|            condition = self.condition_encoder(
#|                torch.cat(
#|                    [
#|                        relation_state,
#|                        graph_state,
#|                        semantic_state,
#|                        routed,
#|                        torch.abs(graph_state - semantic_state),
#|                        graph_state * semantic_state,
#|                    ],
#|                    dim=-1,
#|                )
#|            )
#|            self.last_graph_prompt_norm = (
#|                condition.detach().float().norm(dim=-1).mean()
#|            )
#|            self.last_router_weights = route_weights.detach().mean(dim=0)
#|            if activate:
#|                self.semantic_readout.set_condition(condition)
#|            return condition
#|
#|        def forward(
#|            self,
#|            e_img,
#|            e_txt,
#|            e_desc,
#|            graph_feature=None,
#|            semantic_token_embeddings=None,
#|            semantic_mask=None,
#|        ):
#|            condition = self.encode_condition(
#|                e_img,
#|                e_txt,
#|                e_desc,
#|                graph_feature,
#|                semantic_token_embeddings,
#|                semantic_mask,
#|                activate=True,
#|            )
#|            return condition, condition.new_zeros(())
#|
#|        def semantic_alignment_loss(self, condition, target, target_present):
#|            prediction = self.alignment_head(condition.float())
#|            cosine = torch.nn.functional.cosine_similarity(
#|                prediction,
#|                target.detach().float(),
#|                dim=-1,
#|            )
#|            present = target_present.to(cosine.device).float()
#|            loss = ((1.0 - cosine) * present).sum() / present.sum().clamp_min(1.0)
#|            self.last_semantic_alignment = loss.detach()
#|            return loss
#|
#|    return GraphSemanticReadout, GraphSemanticController
#|
#|
#|def attach_semantic_readout(model, projector) -> str:
#|    if not hasattr(projector, "semantic_readout"):
#|        raise TypeError("projector has no semantic_readout adapter")
#|    return projector.semantic_readout.attach(model)
#|
#|
#|def collect_semantic_readout_metrics(model, torch) -> dict[str, str]:
#|    projector = model.projector
#|    adapter = projector.semantic_readout
#|    projector.last_graph_gate = adapter.last_gate.detach()
#|    weights = projector.last_router_weights
#|    return {
#|        "SR_G": f"{adapter.last_gate.item():.4f}",
#|        "SR_RS": f"{adapter.last_rank_scale.item():.4f}",
#|        "SR_R": f"{adapter.last_residual_ratio.item():.5f}",
#|        "SR_SEM": f"{projector.last_semantic_alignment.item():.4f}",
#|        "SR_W": "/".join(f"{value.item():.2f}" for value in weights),
#|    }
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: rgc_semantic_readout_stage_3.py ===
#|"""Classification-preserving graph-semantic readout (RGC-SR v3).
#|
#|The relation representation is the permanent backbone. Structural and textual
#|concept-graph states enter as independently gated residuals, so a softmax
#|router cannot discard both graph branches. During the first label tokens the
#|language readout residual is attenuated; it is fully enabled for explanation
#|generation.
#|"""
#|
#|from __future__ import annotations
#|
#|import math
#|from dataclasses import dataclass
#|
#|from concept_graph_integration import GRAPH_FEATURE_DIM
#|from rgc_hyperlora import sanitize_graph_feature
#|from rgc_semantic_readout import (
#|    SemanticReadoutConfig,
#|    make_semantic_readout_classes,
#|    validate_semantic_readout_config,
#|)
#|
#|
#|@dataclass(frozen=True)
#|class ClassificationPreservingReadoutConfig(SemanticReadoutConfig):
#|    graph_gate_floor: float = 0.03
#|    graph_gate_cap: float = 0.35
#|    graph_gate_init: float = 0.12
#|    semantic_gate_floor: float = 0.03
#|    semantic_gate_cap: float = 0.35
#|    semantic_gate_init: float = 0.12
#|    label_token_count: int = 4
#|    label_readout_scale: float = 0.10
#|    label_loss_weight: float = 0.40
#|
#|
#|def validate_v3_config(config: ClassificationPreservingReadoutConfig) -> None:
#|    validate_semantic_readout_config(config)
#|    for name, floor, initial, cap in (
#|        (
#|            "graph",
#|            config.graph_gate_floor,
#|            config.graph_gate_init,
#|            config.graph_gate_cap,
#|        ),
#|        (
#|            "semantic",
#|            config.semantic_gate_floor,
#|            config.semantic_gate_init,
#|            config.semantic_gate_cap,
#|        ),
#|    ):
#|        if not 0.0 <= floor < initial < cap <= 1.0:
#|            raise ValueError(
#|                f"{name} residual gate must satisfy "
#|                "0 <= floor < init < cap <= 1"
#|            )
#|    if config.label_token_count <= 0:
#|        raise ValueError("label_token_count must be positive")
#|    if not 0.0 <= config.label_readout_scale <= 1.0:
#|        raise ValueError("label_readout_scale must be in [0, 1]")
#|    if config.label_loss_weight < 0.0:
#|        raise ValueError("label_loss_weight must be non-negative")
#|
#|
#|def _bounded_gate(torch, logits, floor: float, cap: float):
#|    return floor + (cap - floor) * torch.sigmoid(logits)
#|
#|
#|def _gate_bias(initial: float, floor: float, cap: float) -> float:
#|    fraction = (initial - floor) / (cap - floor)
#|    return math.log(fraction / (1.0 - fraction))
#|
#|
#|def make_v3_readout_classes(torch, nn):
#|    BaseReadout, _ = make_semantic_readout_classes(torch, nn)
#|
#|    class ClassificationPreservingReadout(BaseReadout):
#|        def __init__(
#|            self,
#|            hidden_size: int,
#|            condition_dim: int,
#|            rank: int,
#|            *,
#|            gate_init: float,
#|            gate_cap: float,
#|            rank_modulation_cap: float,
#|            residual_norm_ratio: float,
#|            label_token_count: int,
#|            label_readout_scale: float,
#|        ):
#|            super().__init__(
#|                hidden_size,
#|                condition_dim,
#|                rank,
#|                gate_init=gate_init,
#|                gate_cap=gate_cap,
#|                rank_modulation_cap=rank_modulation_cap,
#|                residual_norm_ratio=residual_norm_ratio,
#|            )
#|            self.label_token_count = int(label_token_count)
#|            self.label_readout_scale = float(label_readout_scale)
#|            self._token_scale = None
#|            self._generation_call_index = 0
#|
#|            # A tiny non-zero initialization lets the first LM backward pass
#|            # reach the graph condition while keeping the initial perturbation
#|            # effectively identical to the configured gate.
#|            nn.init.normal_(self.rank_controller.weight, mean=0.0, std=1e-3)
#|            nn.init.normal_(self.condition_gate.weight, mean=0.0, std=1e-3)
#|
#|        def set_token_scale(self, token_scale) -> None:
#|            if token_scale is None or token_scale.dim() != 3:
#|                raise ValueError(
#|                    "readout token scale must have shape [batch, seq, 1]"
#|                )
#|            self._token_scale = token_scale
#|
#|        def clear_token_scale(self) -> None:
#|            self._token_scale = None
#|
#|        def reset_generation(self) -> None:
#|            self._token_scale = None
#|            self._generation_call_index = 0
#|
#|        def _match_external_scale(self, hidden):
#|            scale = self._token_scale
#|            if scale is None:
#|                return None
#|            if scale.size(0) != hidden.size(0):
#|                if hidden.size(0) % scale.size(0) != 0:
#|                    raise ValueError(
#|                        "readout token-scale batch does not match hidden batch"
#|                    )
#|                scale = scale.repeat_interleave(
#|                    hidden.size(0) // scale.size(0),
#|                    dim=0,
#|                )
#|            if scale.size(1) != hidden.size(1):
#|                raise ValueError(
#|                    "readout token-scale sequence does not match hidden sequence"
#|                )
#|            return scale.to(hidden.device).float()
#|
#|        def _resolve_scale(self, hidden):
#|            external = self._match_external_scale(hidden)
#|            if external is not None:
#|                return external
#|            if self.training:
#|                return hidden.new_ones(
#|                    (hidden.size(0), hidden.size(1), 1),
#|                    dtype=torch.float32,
#|                )
#|            scale_value = (
#|                self.label_readout_scale
#|                if self._generation_call_index < self.label_token_count
#|                else 1.0
#|            )
#|            self._generation_call_index += 1
#|            return hidden.new_full(
#|                (hidden.size(0), hidden.size(1), 1),
#|                scale_value,
#|                dtype=torch.float32,
#|            )
#|
#|        def forward(self, hidden):
#|            base_hidden = hidden
#|            adapted = super().forward(hidden)
#|            token_scale = self._resolve_scale(hidden)
#|            delta = (adapted.float() - base_hidden.float()) * token_scale
#|            output = base_hidden.float() + delta
#|            self.last_residual_ratio = (
#|                delta.detach().norm(dim=-1)
#|                / base_hidden.detach().float().norm(dim=-1).clamp_min(1e-6)
#|            ).mean()
#|            return output.to(base_hidden.dtype)
#|
#|    class ClassificationPreservingController(nn.Module):
#|        def __init__(
#|            self,
#|            hidden_size: int,
#|            num_tokens: int,
#|            config: ClassificationPreservingReadoutConfig,
#|            *,
#|            training_graph_dropout: bool,
#|        ):
#|            super().__init__()
#|            validate_v3_config(config)
#|            if int(num_tokens) != 0:
#|                raise ValueError(
#|                    "RGC-SemanticReadout-v3 requires num_tokens=0"
#|                )
#|            self.hidden_size = int(hidden_size)
#|            self.num_tokens = 0
#|            self.config = config
#|            self.training_graph_dropout = bool(training_graph_dropout)
#|
#|            relation_dim = config.relation_dim
#|            condition_dim = config.condition_dim
#|            self.img_proj = nn.Linear(768, relation_dim)
#|            self.txt_proj = nn.Linear(1024, relation_dim)
#|            self.desc_proj = nn.Linear(1024, relation_dim)
#|            self.img_norm = nn.LayerNorm(relation_dim)
#|            self.txt_norm = nn.LayerNorm(relation_dim)
#|            self.desc_norm = nn.LayerNorm(relation_dim)
#|            self.relation_encoder = nn.Sequential(
#|                nn.LayerNorm(relation_dim * 5),
#|                nn.Linear(relation_dim * 5, condition_dim),
#|                nn.GELU(),
#|            )
#|            self.graph_encoder = nn.Sequential(
#|                nn.LayerNorm(GRAPH_FEATURE_DIM),
#|                nn.Linear(GRAPH_FEATURE_DIM, condition_dim),
#|                nn.GELU(),
#|                nn.Linear(condition_dim, condition_dim),
#|                nn.GELU(),
#|            )
#|            self.semantic_encoder = nn.Sequential(
#|                nn.LayerNorm(hidden_size),
#|                nn.Linear(hidden_size, condition_dim),
#|                nn.GELU(),
#|                nn.Dropout(config.controller_dropout),
#|            )
#|            self.semantic_query = nn.Linear(condition_dim * 2, condition_dim)
#|            self.semantic_norm = nn.LayerNorm(condition_dim)
#|
#|            gate_input_dim = condition_dim * 3 + GRAPH_FEATURE_DIM
#|            self.graph_reliability = nn.Linear(gate_input_dim, 1)
#|            self.semantic_reliability = nn.Linear(gate_input_dim, 1)
#|            self.graph_residual = nn.Sequential(
#|                nn.Linear(condition_dim, condition_dim),
#|                nn.GELU(),
#|                nn.LayerNorm(condition_dim),
#|            )
#|            self.semantic_residual = nn.Sequential(
#|                nn.Linear(condition_dim, condition_dim),
#|                nn.GELU(),
#|                nn.LayerNorm(condition_dim),
#|            )
#|            self.fused_norm = nn.LayerNorm(condition_dim)
#|            self.condition_encoder = nn.Sequential(
#|                nn.LayerNorm(condition_dim * 6),
#|                nn.Linear(condition_dim * 6, condition_dim * 2),
#|                nn.GELU(),
#|                nn.Dropout(config.controller_dropout),
#|                nn.Linear(condition_dim * 2, condition_dim),
#|                nn.LayerNorm(condition_dim),
#|            )
#|            self.alignment_head = nn.Linear(condition_dim, hidden_size)
#|            self.semantic_readout = ClassificationPreservingReadout(
#|                hidden_size,
#|                condition_dim,
#|                config.readout_rank,
#|                gate_init=config.gate_init,
#|                gate_cap=config.gate_cap,
#|                rank_modulation_cap=config.rank_modulation_cap,
#|                residual_norm_ratio=config.residual_norm_ratio,
#|                label_token_count=config.label_token_count,
#|                label_readout_scale=config.label_readout_scale,
#|            )
#|
#|            for module in self.modules():
#|                if not isinstance(module, nn.Linear):
#|                    continue
#|                if module in (
#|                    self.semantic_readout.down,
#|                    self.semantic_readout.up,
#|                    self.semantic_readout.rank_controller,
#|                    self.semantic_readout.condition_gate,
#|                    self.semantic_readout.token_gate,
#|                ):
#|                    continue
#|                nn.init.xavier_uniform_(module.weight)
#|                if module.bias is not None:
#|                    nn.init.zeros_(module.bias)
#|            nn.init.zeros_(self.graph_reliability.weight)
#|            nn.init.constant_(
#|                self.graph_reliability.bias,
#|                _gate_bias(
#|                    config.graph_gate_init,
#|                    config.graph_gate_floor,
#|                    config.graph_gate_cap,
#|                ),
#|            )
#|            nn.init.zeros_(self.semantic_reliability.weight)
#|            nn.init.constant_(
#|                self.semantic_reliability.bias,
#|                _gate_bias(
#|                    config.semantic_gate_init,
#|                    config.semantic_gate_floor,
#|                    config.semantic_gate_cap,
#|                ),
#|            )
#|
#|            self.last_graph_prompt_norm = torch.tensor(0.0)
#|            self.last_graph_gate = torch.tensor(config.gate_init)
#|            self.last_graph_drop_fraction = torch.tensor(0.0)
#|            self.last_semantic_alignment = torch.tensor(0.0)
#|            self.last_router_weights = torch.tensor(
#|                [1.0, config.graph_gate_init, config.semantic_gate_init]
#|            )
#|            self.last_label_loss = torch.tensor(0.0)
#|            self.last_weighted_label_loss = torch.tensor(0.0)
#|            self.last_label_token_count = torch.tensor(0.0)
#|
#|        def _drop_graph_evidence(
#|            self,
#|            graph_feature,
#|            semantic_token_embeddings,
#|            semantic_mask,
#|        ):
#|            if (
#|                not self.training
#|                or not self.training_graph_dropout
#|                or self.config.graph_dropout == 0.0
#|            ):
#|                self.last_graph_drop_fraction = graph_feature.new_zeros(())
#|                return (
#|                    graph_feature,
#|                    semantic_token_embeddings,
#|                    semantic_mask,
#|                )
#|            keep = (
#|                torch.rand(
#|                    (graph_feature.size(0), 1),
#|                    device=graph_feature.device,
#|                )
#|                >= self.config.graph_dropout
#|            )
#|            self.last_graph_drop_fraction = (~keep).float().mean().detach()
#|            return (
#|                graph_feature * keep.to(graph_feature.dtype),
#|                semantic_token_embeddings
#|                * keep.unsqueeze(-1).to(semantic_token_embeddings.dtype),
#|                semantic_mask & keep.bool(),
#|            )
#|
#|        def _pool_semantics(
#|            self,
#|            semantic_token_embeddings,
#|            semantic_mask,
#|            relation_state,
#|            graph_state,
#|        ):
#|            semantic_tokens = self.semantic_encoder(
#|                semantic_token_embeddings
#|            )
#|            query = self.semantic_query(
#|                torch.cat([relation_state, graph_state], dim=-1)
#|            )
#|            logits = (
#|                semantic_tokens * query.unsqueeze(1)
#|            ).sum(dim=-1) / math.sqrt(self.config.condition_dim)
#|            logits = logits.masked_fill(~semantic_mask, -1e4)
#|            weights = torch.softmax(logits, dim=-1)
#|            weights = weights * semantic_mask.to(weights.dtype)
#|            weights = weights / weights.sum(
#|                dim=-1,
#|                keepdim=True,
#|            ).clamp_min(1e-6)
#|            state = self.semantic_norm(
#|                (semantic_tokens * weights.unsqueeze(-1)).sum(dim=1)
#|            )
#|            present = semantic_mask.any(dim=-1, keepdim=True)
#|            return state * present.to(state.dtype)
#|
#|        def encode_condition(
#|            self,
#|            e_img,
#|            e_txt,
#|            e_desc,
#|            graph_feature,
#|            semantic_token_embeddings,
#|            semantic_mask,
#|            *,
#|            activate: bool,
#|        ):
#|            p_img = self.img_norm(self.img_proj(e_img.float()))
#|            p_txt = self.txt_norm(self.txt_proj(e_txt.float()))
#|            p_desc = self.desc_norm(self.desc_proj(e_desc.float()))
#|            relation = torch.cat(
#|                [
#|                    p_img,
#|                    p_desc,
#|                    p_txt,
#|                    torch.abs(p_desc - p_txt),
#|                    p_desc * p_txt,
#|                ],
#|                dim=-1,
#|            )
#|            if graph_feature is None:
#|                graph_feature = relation.new_zeros(
#|                    (relation.size(0), GRAPH_FEATURE_DIM)
#|                )
#|            if graph_feature.dim() == 1:
#|                graph_feature = graph_feature.unsqueeze(0)
#|            graph_feature = sanitize_graph_feature(
#|                graph_feature.to(relation.device).float()
#|            )
#|            if semantic_token_embeddings is None:
#|                semantic_token_embeddings = relation.new_zeros(
#|                    (relation.size(0), 1, self.hidden_size)
#|                )
#|            if semantic_token_embeddings.dim() == 2:
#|                semantic_token_embeddings = semantic_token_embeddings.unsqueeze(1)
#|            semantic_token_embeddings = semantic_token_embeddings.to(
#|                relation.device
#|            ).float()
#|            if semantic_mask is None:
#|                semantic_mask = torch.ones(
#|                    semantic_token_embeddings.shape[:2],
#|                    device=relation.device,
#|                    dtype=torch.bool,
#|                )
#|            else:
#|                semantic_mask = semantic_mask.to(relation.device).bool()
#|            (
#|                graph_feature,
#|                semantic_token_embeddings,
#|                semantic_mask,
#|            ) = self._drop_graph_evidence(
#|                graph_feature,
#|                semantic_token_embeddings,
#|                semantic_mask,
#|            )
#|
#|            relation_state = self.relation_encoder(relation)
#|            graph_state = self.graph_encoder(graph_feature)
#|            semantic_state = self._pool_semantics(
#|                semantic_token_embeddings,
#|                semantic_mask,
#|                relation_state,
#|                graph_state,
#|            )
#|            gate_input = torch.cat(
#|                [
#|                    relation_state,
#|                    graph_state,
#|                    semantic_state,
#|                    graph_feature,
#|                ],
#|                dim=-1,
#|            )
#|            graph_gate = _bounded_gate(
#|                torch,
#|                self.graph_reliability(gate_input),
#|                self.config.graph_gate_floor,
#|                self.config.graph_gate_cap,
#|            )
#|            semantic_gate = _bounded_gate(
#|                torch,
#|                self.semantic_reliability(gate_input),
#|                self.config.semantic_gate_floor,
#|                self.config.semantic_gate_cap,
#|            )
#|            graph_delta = graph_gate * self.graph_residual(graph_state)
#|            semantic_delta = (
#|                semantic_gate * self.semantic_residual(semantic_state)
#|            )
#|            fused = self.fused_norm(
#|                relation_state + graph_delta + semantic_delta
#|            )
#|            condition = self.condition_encoder(
#|                torch.cat(
#|                    [
#|                        relation_state,
#|                        fused,
#|                        graph_delta,
#|                        semantic_delta,
#|                        torch.abs(relation_state - fused),
#|                        relation_state * fused,
#|                    ],
#|                    dim=-1,
#|                )
#|            )
#|            self.last_graph_prompt_norm = (
#|                condition.detach().float().norm(dim=-1).mean()
#|            )
#|            self.last_router_weights = torch.stack(
#|                [
#|                    graph_gate.new_ones(()),
#|                    graph_gate.detach().mean(),
#|                    semantic_gate.detach().mean(),
#|                ]
#|            )
#|            if activate:
#|                self.semantic_readout.set_condition(condition)
#|                if not self.training:
#|                    self.semantic_readout.reset_generation()
#|            return condition
#|
#|        def forward(
#|            self,
#|            e_img,
#|            e_txt,
#|            e_desc,
#|            graph_feature=None,
#|            semantic_token_embeddings=None,
#|            semantic_mask=None,
#|        ):
#|            condition = self.encode_condition(
#|                e_img,
#|                e_txt,
#|                e_desc,
#|                graph_feature,
#|                semantic_token_embeddings,
#|                semantic_mask,
#|                activate=True,
#|            )
#|            return condition, condition.new_zeros(())
#|
#|        def semantic_alignment_loss(self, condition, target, target_present):
#|            prediction = self.alignment_head(condition.float())
#|            cosine = torch.nn.functional.cosine_similarity(
#|                prediction,
#|                target.detach().float(),
#|                dim=-1,
#|            )
#|            present = target_present.to(cosine.device).float()
#|            loss = ((1.0 - cosine) * present).sum()
#|            loss = loss / present.sum().clamp_min(1.0)
#|            self.last_semantic_alignment = loss.detach()
#|            return loss
#|
#|        def _label_prediction_mask(self, labels, ignore_index: int):
#|            shifted_labels = labels[:, 1:]
#|            valid = shifted_labels.ne(ignore_index)
#|            order = valid.long().cumsum(dim=1)
#|            return valid & order.le(self.config.label_token_count)
#|
#|        def prepare_readout_token_scale(
#|            self,
#|            labels,
#|            ignore_index: int,
#|        ) -> None:
#|            label_mask = self._label_prediction_mask(labels, ignore_index)
#|            token_scale = labels.new_ones(
#|                (labels.size(0), labels.size(1), 1),
#|                dtype=torch.float32,
#|            )
#|            leading_scale = torch.where(
#|                label_mask.unsqueeze(-1),
#|                token_scale[:, :-1].new_full(
#|                    token_scale[:, :-1].shape,
#|                    self.config.label_readout_scale,
#|                ),
#|                token_scale[:, :-1],
#|            )
#|            token_scale[:, :-1] = leading_scale
#|            self.semantic_readout.set_token_scale(token_scale)
#|
#|        def clear_readout_token_scale(self) -> None:
#|            self.semantic_readout.clear_token_scale()
#|
#|        def extra_language_loss(
#|            self,
#|            logits,
#|            labels,
#|            ignore_index: int,
#|        ):
#|            shift_logits = logits[:, :-1, :].float().contiguous()
#|            shift_labels = labels[:, 1:].long().contiguous()
#|            label_mask = self._label_prediction_mask(labels, ignore_index)
#|            per_token = torch.nn.functional.cross_entropy(
#|                shift_logits.view(-1, shift_logits.size(-1)),
#|                shift_labels.view(-1),
#|                ignore_index=ignore_index,
#|                reduction="none",
#|            ).view_as(shift_labels)
#|            mask_float = label_mask.to(per_token.dtype)
#|            label_loss = (per_token * mask_float).sum()
#|            label_loss = label_loss / mask_float.sum().clamp_min(1.0)
#|            weighted = self.config.label_loss_weight * label_loss
#|            self.last_label_loss = label_loss.detach()
#|            self.last_weighted_label_loss = weighted.detach()
#|            self.last_label_token_count = mask_float.sum().detach()
#|            return weighted
#|
#|    return ClassificationPreservingReadout, ClassificationPreservingController
#|
#|
#|def collect_v3_metrics(model, torch) -> dict[str, str]:
#|    projector = model.projector
#|    adapter = projector.semantic_readout
#|    projector.last_graph_gate = adapter.last_gate.detach()
#|    weights = projector.last_router_weights
#|    return {
#|        "CP_G": f"{adapter.last_gate.item():.4f}",
#|        "CP_RS": f"{adapter.last_rank_scale.item():.4f}",
#|        "CP_R": f"{adapter.last_residual_ratio.item():.5f}",
#|        "CP_SEM": f"{projector.last_semantic_alignment.item():.4f}",
#|        "CP_Y": f"{projector.last_label_loss.item():.4f}",
#|        "CP_YW": f"{projector.last_weighted_label_loss.item():.4f}",
#|        "CP_YN": f"{projector.last_label_token_count.item():.0f}",
#|        "CP_W": "/".join(f"{value.item():.2f}" for value in weights),
#|    }
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: rgc_semantic_readout_stage_4.py ===
#|"""Phenomenon-balanced graph-semantic readout (RGC-SR v4).
#|
#|V4 keeps the token-free classification-preserving v3 architecture. Training
#|uses loss-driven GroupDRO with uniform initialization, so no phenomenon gets a
#|manually assigned weight. A small target queue supplies negatives for
#|graph-to-explanation alignment when the physical batch size is one.
#|"""
#|
#|from __future__ import annotations
#|
#|import math
#|from dataclasses import dataclass
#|
#|from rgc_semantic_readout_stage_3 import (
#|    ClassificationPreservingReadoutConfig,
#|    make_v3_readout_classes,
#|    validate_v3_config,
#|)
#|
#|
#|PHENOMENON_GROUPS = (
#|    "humor",
#|    "sarcasm",
#|    "metaphor",
#|    "simile",
#|    "idiom",
#|    "hyperbole",
#|    "pun",
#|    "other",
#|)
#|PHENOMENON_TO_ID = {
#|    name: index for index, name in enumerate(PHENOMENON_GROUPS)
#|}
#|
#|
#|def canonicalize_phenomenon(value) -> str:
#|    text = str(value or "").strip().lower().replace("-", "_")
#|    aliases = {
#|        "irony": "sarcasm",
#|        "ironic": "sarcasm",
#|        "sarcastic": "sarcasm",
#|        "metaphorical": "metaphor",
#|        "visual_metaphor": "metaphor",
#|        "metaphor_simile": "metaphor",
#|        "idiomatic": "idiom",
#|        "humorous": "humor",
#|        "comedy": "humor",
#|        "wordplay": "pun",
#|    }
#|    text = aliases.get(text, text)
#|    return text if text in PHENOMENON_TO_ID else "other"
#|
#|
#|def select_phenomenon(record) -> str:
#|    """Prefer inferred_phenomenon, falling back only when it is empty."""
#|    inferred = str(record.get("inferred_phenomenon") or "").strip()
#|    source = inferred if inferred else record.get("phenomenon")
#|    return canonicalize_phenomenon(source)
#|
#|
#|@dataclass(frozen=True)
#|class PhenomenonBalancedReadoutConfig(
#|    ClassificationPreservingReadoutConfig
#|):
#|    dro_eta: float = 0.05
#|    dro_ema: float = 0.90
#|    dro_entropy_reg: float = 0.01
#|    dro_logit_cap: float = math.log(2.5)
#|    dro_prior_floor: float = 0.01
#|    dro_sample_weight_cap: float = 3.0
#|    dro_warmup_steps: int = 16
#|    alignment_queue_size: int = 128
#|    alignment_temperature: float = 0.10
#|    alignment_nce_weight: float = 0.20
#|
#|
#|def validate_v4_config(config: PhenomenonBalancedReadoutConfig) -> None:
#|    validate_v3_config(config)
#|    if config.dro_eta <= 0.0:
#|        raise ValueError("dro_eta must be positive")
#|    if not 0.0 <= config.dro_ema < 1.0:
#|        raise ValueError("dro_ema must be in [0, 1)")
#|    if not 0.0 <= config.dro_entropy_reg < 1.0:
#|        raise ValueError("dro_entropy_reg must be in [0, 1)")
#|    if config.dro_logit_cap <= 0.0:
#|        raise ValueError("dro_logit_cap must be positive")
#|    if not 0.0 <= config.dro_prior_floor < 1.0:
#|        raise ValueError("dro_prior_floor must be in [0, 1)")
#|    if config.dro_sample_weight_cap < 1.0:
#|        raise ValueError("dro_sample_weight_cap must be at least 1")
#|    if config.dro_warmup_steps < 0:
#|        raise ValueError("dro_warmup_steps must be non-negative")
#|    if config.alignment_queue_size < 0:
#|        raise ValueError("alignment_queue_size must be non-negative")
#|    if config.alignment_temperature <= 0.0:
#|        raise ValueError("alignment_temperature must be positive")
#|    if config.alignment_nce_weight < 0.0:
#|        raise ValueError("alignment_nce_weight must be non-negative")
#|
#|
#|def make_v4_readout_classes(torch, nn):
#|    Readout, V3Controller = make_v3_readout_classes(torch, nn)
#|
#|    class PhenomenonBalancedController(V3Controller):
#|        def __init__(
#|            self,
#|            hidden_size: int,
#|            num_tokens: int,
#|            config: PhenomenonBalancedReadoutConfig,
#|            *,
#|            training_graph_dropout: bool,
#|        ):
#|            validate_v4_config(config)
#|            super().__init__(
#|                hidden_size,
#|                num_tokens,
#|                config,
#|                training_graph_dropout=training_graph_dropout,
#|            )
#|            self.num_phenomenon_groups = len(PHENOMENON_GROUPS)
#|            self.register_buffer(
#|                "dro_log_weights",
#|                torch.zeros(self.num_phenomenon_groups),
#|            )
#|            self.register_buffer(
#|                "dro_loss_ema",
#|                torch.zeros(self.num_phenomenon_groups),
#|            )
#|            self.register_buffer(
#|                "dro_group_seen",
#|                torch.zeros(self.num_phenomenon_groups, dtype=torch.bool),
#|            )
#|            self.register_buffer(
#|                "dro_group_prior",
#|                torch.full(
#|                    (self.num_phenomenon_groups,),
#|                    1.0 / self.num_phenomenon_groups,
#|                ),
#|            )
#|            self.register_buffer(
#|                "dro_step",
#|                torch.zeros((), dtype=torch.long),
#|            )
#|            self.register_buffer(
#|                "_dro_pending_loss",
#|                torch.zeros(self.num_phenomenon_groups),
#|                persistent=False,
#|            )
#|            self.register_buffer(
#|                "_dro_pending_count",
#|                torch.zeros(self.num_phenomenon_groups),
#|                persistent=False,
#|            )
#|            queue_size = int(config.alignment_queue_size)
#|            self.register_buffer(
#|                "_alignment_queue",
#|                torch.zeros(queue_size, hidden_size),
#|                persistent=False,
#|            )
#|            self.register_buffer(
#|                "_alignment_queue_ptr",
#|                torch.zeros((), dtype=torch.long),
#|                persistent=False,
#|            )
#|            self.register_buffer(
#|                "_alignment_queue_count",
#|                torch.zeros((), dtype=torch.long),
#|                persistent=False,
#|            )
#|            self._current_group_ids = None
#|            self.last_dro_base_loss = torch.tensor(0.0)
#|            self.last_dro_weighted_loss = torch.tensor(0.0)
#|            self.last_dro_sample_weight = torch.tensor(1.0)
#|            self.last_dro_group_weights = torch.ones(
#|                self.num_phenomenon_groups
#|            )
#|            self.last_alignment_nce = torch.tensor(0.0)
#|
#|        def set_group_context(self, group_ids) -> None:
#|            if group_ids is None:
#|                self._current_group_ids = None
#|                return
#|            self._current_group_ids = group_ids.detach().long().reshape(-1)
#|
#|        def clear_group_context(self) -> None:
#|            self._current_group_ids = None
#|
#|        def set_group_priors(self, counts) -> None:
#|            values = torch.as_tensor(
#|                counts,
#|                device=self.dro_group_prior.device,
#|                dtype=torch.float32,
#|            ).reshape(-1)
#|            if values.numel() != self.num_phenomenon_groups:
#|                raise ValueError("phenomenon prior count has wrong length")
#|            if not bool(values.sum() > 0):
#|                raise ValueError("phenomenon prior counts are empty")
#|            values = values.clamp_min(0.0)
#|            self.dro_group_prior.copy_(values / values.sum())
#|
#|        def _relative_group_weights(self, extra_group_ids=None):
#|            active = self.dro_group_seen.clone()
#|            if extra_group_ids is not None and extra_group_ids.numel() > 0:
#|                ids = extra_group_ids.to(active.device).long().reshape(-1)
#|                ids = ids.clamp(0, self.num_phenomenon_groups - 1)
#|                active[ids.unique()] = True
#|            if not bool(active.any()):
#|                return self.dro_log_weights.new_ones(
#|                    self.num_phenomenon_groups
#|                )
#|            masked_logits = self.dro_log_weights.masked_fill(~active, -1e4)
#|            probabilities = torch.softmax(masked_logits, dim=0)
#|            active_prior = self.dro_group_prior * active.to(
#|                self.dro_group_prior.dtype
#|            )
#|            active_prior = active_prior / active_prior.sum().clamp_min(1e-8)
#|            effective_prior = torch.where(
#|                active,
#|                active_prior.clamp_min(float(self.config.dro_prior_floor)),
#|                active_prior,
#|            )
#|            effective_prior = (
#|                effective_prior
#|                / effective_prior.sum().clamp_min(1e-8)
#|            )
#|            raw_relative = probabilities / effective_prior.clamp_min(1e-8)
#|            raw_relative = raw_relative / (
#|                raw_relative * active_prior
#|            ).sum().clamp_min(1e-8)
#|            cap = float(self.config.dro_sample_weight_cap)
#|            interpolation = torch.clamp(
#|                (cap - 1.0)
#|                / (raw_relative.max() - 1.0).clamp_min(1e-8),
#|                max=1.0,
#|            )
#|            # Interpolation toward one preserves E_p[w] = 1 exactly while
#|            # bounding the largest inverse-frequency correction by `cap`.
#|            relative = 1.0 + interpolation * (raw_relative - 1.0)
#|            return relative * active.to(relative.dtype)
#|
#|        def _record_group_losses(self, group_ids, sample_losses) -> None:
#|            with torch.no_grad():
#|                ids = group_ids.to(self._dro_pending_loss.device).long()
#|                ids = ids.clamp(0, self.num_phenomenon_groups - 1)
#|                values = sample_losses.detach().float().to(
#|                    self._dro_pending_loss.device
#|                )
#|                ones = torch.ones_like(values)
#|                self._dro_pending_loss.index_add_(0, ids, values)
#|                self._dro_pending_count.index_add_(0, ids, ones)
#|
#|        def on_optimizer_step(self) -> None:
#|            with torch.no_grad():
#|                observed = self._dro_pending_count > 0
#|                if bool(observed.any()):
#|                    means = self._dro_pending_loss / (
#|                        self._dro_pending_count.clamp_min(1.0)
#|                    )
#|                    old_seen = self.dro_group_seen.clone()
#|                    beta = float(self.config.dro_ema)
#|                    updated = (
#|                        beta * self.dro_loss_ema
#|                        + (1.0 - beta) * means
#|                    )
#|                    first_values = torch.where(old_seen, updated, means)
#|                    self.dro_loss_ema.copy_(
#|                        torch.where(
#|                            observed,
#|                            first_values,
#|                            self.dro_loss_ema,
#|                        )
#|                    )
#|                    self.dro_group_seen.logical_or_(observed)
#|                    if (
#|                        int(self.dro_step.item())
#|                        >= int(self.config.dro_warmup_steps)
#|                    ):
#|                        active_losses = self.dro_loss_ema[
#|                            self.dro_group_seen
#|                        ]
#|                        center = active_losses.mean()
#|                        difficulty = self.dro_loss_ema - center
#|                        self.dro_log_weights.add_(
#|                            float(self.config.dro_eta)
#|                            * difficulty
#|                            * observed.to(difficulty.dtype)
#|                        )
#|                        self.dro_log_weights.mul_(
#|                            1.0 - float(self.config.dro_entropy_reg)
#|                        )
#|                        self.dro_log_weights.clamp_(
#|                            -float(self.config.dro_logit_cap),
#|                            float(self.config.dro_logit_cap),
#|                        )
#|                self.dro_step.add_(1)
#|                self._dro_pending_loss.zero_()
#|                self._dro_pending_count.zero_()
#|                self.last_dro_group_weights = (
#|                    self._relative_group_weights().detach()
#|                )
#|
#|        def _enqueue_alignment_targets(self, targets) -> None:
#|            if self._alignment_queue.size(0) == 0 or targets.numel() == 0:
#|                return
#|            with torch.no_grad():
#|                values = targets.detach().float().to(
#|                    self._alignment_queue.device
#|                )
#|                capacity = self._alignment_queue.size(0)
#|                for value in values:
#|                    pointer = int(self._alignment_queue_ptr.item())
#|                    self._alignment_queue[pointer].copy_(value)
#|                    self._alignment_queue_ptr.fill_(
#|                        (pointer + 1) % capacity
#|                    )
#|                    self._alignment_queue_count.copy_(
#|                        torch.minimum(
#|                            self._alignment_queue_count + 1,
#|                            self._alignment_queue_count.new_tensor(capacity),
#|                        )
#|                    )
#|
#|        def semantic_alignment_loss(
#|            self,
#|            condition,
#|            target,
#|            target_present,
#|        ):
#|            prediction = torch.nn.functional.normalize(
#|                self.alignment_head(condition.float()),
#|                dim=-1,
#|            )
#|            normalized_target = torch.nn.functional.normalize(
#|                target.detach().float(),
#|                dim=-1,
#|            )
#|            present = target_present.to(prediction.device).bool().reshape(-1)
#|            if not bool(present.any()):
#|                zero = prediction.sum() * 0.0
#|                self.last_semantic_alignment = zero.detach()
#|                self.last_alignment_nce = zero.detach()
#|                return zero
#|
#|            prediction = prediction[present]
#|            normalized_target = normalized_target[present]
#|            cosine_loss = (
#|                1.0 - (prediction * normalized_target).sum(dim=-1)
#|            ).mean()
#|
#|            queue_count = int(self._alignment_queue_count.item())
#|            nce_loss = cosine_loss.new_zeros(())
#|            if (
#|                queue_count > 0
#|                and float(self.config.alignment_nce_weight) > 0.0
#|            ):
#|                negatives = self._alignment_queue[:queue_count].to(
#|                    prediction.device
#|                )
#|                negatives = torch.nn.functional.normalize(
#|                    negatives.float(),
#|                    dim=-1,
#|                )
#|                positive_logits = (
#|                    prediction * normalized_target
#|                ).sum(dim=-1, keepdim=True)
#|                negative_logits = prediction @ negatives.transpose(0, 1)
#|                logits = torch.cat(
#|                    [positive_logits, negative_logits],
#|                    dim=1,
#|                ) / float(self.config.alignment_temperature)
#|                targets = torch.zeros(
#|                    logits.size(0),
#|                    device=logits.device,
#|                    dtype=torch.long,
#|                )
#|                nce_loss = torch.nn.functional.cross_entropy(
#|                    logits,
#|                    targets,
#|                )
#|
#|            total = (
#|                cosine_loss
#|                + float(self.config.alignment_nce_weight) * nce_loss
#|            )
#|            self.last_semantic_alignment = cosine_loss.detach()
#|            self.last_alignment_nce = nce_loss.detach()
#|            self._enqueue_alignment_targets(normalized_target)
#|            return total
#|
#|        def extra_language_loss(
#|            self,
#|            logits,
#|            labels,
#|            ignore_index: int,
#|        ):
#|            label_auxiliary = super().extra_language_loss(
#|                logits,
#|                labels,
#|                ignore_index,
#|            )
#|            group_ids = self._current_group_ids
#|            if group_ids is None:
#|                return label_auxiliary
#|
#|            shift_logits = logits[:, :-1, :].float().contiguous()
#|            shift_labels = labels[:, 1:].long().contiguous()
#|            per_token = torch.nn.functional.cross_entropy(
#|                shift_logits.view(-1, shift_logits.size(-1)),
#|                shift_labels.view(-1),
#|                ignore_index=ignore_index,
#|                reduction="none",
#|            ).view_as(shift_labels)
#|            valid = shift_labels.ne(ignore_index)
#|            token_counts = valid.float().sum(dim=1)
#|            valid_samples = token_counts > 0
#|            sample_losses = (
#|                (per_token * valid.float()).sum(dim=1)
#|                / token_counts.clamp_min(1.0)
#|            )
#|            if not bool(valid_samples.any()):
#|                return label_auxiliary
#|
#|            group_ids = group_ids.to(logits.device).long()
#|            if group_ids.numel() != sample_losses.numel():
#|                raise ValueError(
#|                    "phenomenon group batch does not match language batch"
#|                )
#|            group_ids = group_ids.clamp(
#|                0,
#|                self.num_phenomenon_groups - 1,
#|            )
#|            relative_weights = self._relative_group_weights(group_ids).to(
#|                logits.device
#|            )
#|            sample_weights = relative_weights[group_ids]
#|            weighted_lm = (
#|                sample_losses[valid_samples]
#|                * sample_weights[valid_samples]
#|            ).mean()
#|            base_lm = (
#|                per_token[valid].sum()
#|                / valid.float().sum().clamp_min(1.0)
#|            )
#|            self._record_group_losses(
#|                group_ids[valid_samples],
#|                sample_losses[valid_samples],
#|            )
#|            self.last_dro_base_loss = base_lm.detach()
#|            self.last_dro_weighted_loss = weighted_lm.detach()
#|            self.last_dro_sample_weight = (
#|                sample_weights[valid_samples].mean().detach()
#|            )
#|            self.last_dro_group_weights = (
#|                relative_weights.detach()
#|            )
#|            # The caller already adds the unweighted LM loss. This difference
#|            # replaces it with the GroupDRO-weighted per-sample objective.
#|            return weighted_lm - base_lm + label_auxiliary
#|
#|    return Readout, PhenomenonBalancedController
#|
#|
#|def collect_v4_metrics(model, torch) -> dict[str, str]:
#|    from rgc_semantic_readout_stage_3 import collect_v3_metrics
#|
#|    metrics = collect_v3_metrics(model, torch)
#|    projector = model.projector
#|    weights = projector.last_dro_group_weights
#|    if weights.device.type != "cpu":
#|        weights = weights.detach().cpu()
#|    active = projector.dro_group_seen.detach().cpu()
#|    if bool(active.any()):
#|        active_indices = active.nonzero(as_tuple=False).reshape(-1)
#|        max_index = int(
#|            active_indices[weights[active_indices].argmax()].item()
#|        )
#|        max_name = PHENOMENON_GROUPS[max_index]
#|    else:
#|        max_name = "warmup"
#|    metrics.update(
#|        {
#|            "DRO_B": f"{projector.last_dro_base_loss.item():.4f}",
#|            "DRO_L": f"{projector.last_dro_weighted_loss.item():.4f}",
#|            "DRO_SW": f"{projector.last_dro_sample_weight.item():.3f}",
#|            "DRO_MAX": max_name,
#|            "DRO_W": "/".join(f"{value.item():.2f}" for value in weights),
#|            "GA_NCE": f"{projector.last_alignment_nce.item():.4f}",
#|        }
#|    )
#|    return metrics
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: rgc_semantic_readout_stage_5.py ===
#|"""False-negative-aware phenomenon-balanced semantic readout (v5).
#|
#|V5 preserves v4 GroupDRO and the token-free v3 backbone. It prevents the
#|alignment queue from treating explanations from the same figurative
#|phenomenon as negatives, then smoothly reduces NCE pressure during the final
#|training stage to preserve medium-threshold semantic quality.
#|"""
#|
#|from __future__ import annotations
#|
#|import math
#|from dataclasses import dataclass
#|
#|from rgc_semantic_readout_stage_4 import (
#|    PhenomenonBalancedReadoutConfig,
#|    collect_v4_metrics,
#|    make_v4_readout_classes,
#|    validate_v4_config,
#|)
#|
#|
#|@dataclass(frozen=True)
#|class FalseNegativeAwareReadoutConfig(PhenomenonBalancedReadoutConfig):
#|    alignment_decay_start: float = 0.67
#|    alignment_final_nce_weight: float = 0.05
#|    same_group_negative_scale: float = 0.0
#|
#|
#|def validate_v5_config(config: FalseNegativeAwareReadoutConfig) -> None:
#|    validate_v4_config(config)
#|    if not 0.0 <= config.alignment_decay_start < 1.0:
#|        raise ValueError("alignment_decay_start must be in [0, 1)")
#|    if not 0.0 <= config.alignment_final_nce_weight <= (
#|        config.alignment_nce_weight
#|    ):
#|        raise ValueError(
#|            "final NCE weight must be between zero and the initial weight"
#|        )
#|    if not 0.0 <= config.same_group_negative_scale <= 1.0:
#|        raise ValueError("same_group_negative_scale must be in [0, 1]")
#|
#|
#|def make_v5_readout_classes(torch, nn):
#|    Readout, V4Controller = make_v4_readout_classes(torch, nn)
#|
#|    class FalseNegativeAwareController(V4Controller):
#|        def __init__(
#|            self,
#|            hidden_size: int,
#|            num_tokens: int,
#|            config: FalseNegativeAwareReadoutConfig,
#|            *,
#|            training_graph_dropout: bool,
#|        ):
#|            validate_v5_config(config)
#|            super().__init__(
#|                hidden_size,
#|                num_tokens,
#|                config,
#|                training_graph_dropout=training_graph_dropout,
#|            )
#|            self.register_buffer(
#|                "_alignment_queue_groups",
#|                torch.full(
#|                    (int(config.alignment_queue_size),),
#|                    -1,
#|                    dtype=torch.long,
#|                ),
#|                persistent=False,
#|            )
#|            self.training_progress = 0.0
#|            self.last_alignment_nce_weight = torch.tensor(
#|                float(config.alignment_nce_weight)
#|            )
#|            self.last_alignment_valid_negatives = torch.tensor(0.0)
#|            self.last_alignment_masked_fraction = torch.tensor(0.0)
#|
#|        def set_training_progress(self, progress: float) -> None:
#|            self.training_progress = min(1.0, max(0.0, float(progress)))
#|
#|        def _scheduled_nce_weight(self) -> float:
#|            initial = float(self.config.alignment_nce_weight)
#|            final = float(self.config.alignment_final_nce_weight)
#|            start = float(self.config.alignment_decay_start)
#|            if self.training_progress <= start:
#|                return initial
#|            phase = (self.training_progress - start) / max(1e-8, 1.0 - start)
#|            cosine = 0.5 * (1.0 + math.cos(math.pi * phase))
#|            return final + (initial - final) * cosine
#|
#|        def _current_alignment_groups(self, present, device):
#|            group_ids = self._current_group_ids
#|            if group_ids is None:
#|                return torch.full(
#|                    (int(present.sum().item()),),
#|                    -1,
#|                    device=device,
#|                    dtype=torch.long,
#|                )
#|            group_ids = group_ids.to(device).long().reshape(-1)
#|            if group_ids.numel() != present.numel():
#|                raise ValueError(
#|                    "phenomenon group batch does not match alignment batch"
#|                )
#|            return group_ids[present]
#|
#|        def _enqueue_targets_with_groups(self, targets, groups) -> None:
#|            if self._alignment_queue.size(0) == 0 or targets.numel() == 0:
#|                return
#|            with torch.no_grad():
#|                values = targets.detach().float().to(
#|                    self._alignment_queue.device
#|                )
#|                group_values = groups.detach().long().to(
#|                    self._alignment_queue_groups.device
#|                )
#|                capacity = self._alignment_queue.size(0)
#|                for value, group in zip(values, group_values):
#|                    pointer = int(self._alignment_queue_ptr.item())
#|                    self._alignment_queue[pointer].copy_(value)
#|                    self._alignment_queue_groups[pointer].copy_(group)
#|                    self._alignment_queue_ptr.fill_((pointer + 1) % capacity)
#|                    self._alignment_queue_count.copy_(
#|                        torch.minimum(
#|                            self._alignment_queue_count + 1,
#|                            self._alignment_queue_count.new_tensor(capacity),
#|                        )
#|                    )
#|
#|        def semantic_alignment_loss(
#|            self,
#|            condition,
#|            target,
#|            target_present,
#|        ):
#|            prediction = torch.nn.functional.normalize(
#|                self.alignment_head(condition.float()),
#|                dim=-1,
#|            )
#|            normalized_target = torch.nn.functional.normalize(
#|                target.detach().float(),
#|                dim=-1,
#|            )
#|            present = target_present.to(prediction.device).bool().reshape(-1)
#|            if not bool(present.any()):
#|                zero = prediction.sum() * 0.0
#|                self.last_semantic_alignment = zero.detach()
#|                self.last_alignment_nce = zero.detach()
#|                self.last_alignment_valid_negatives = zero.detach()
#|                self.last_alignment_masked_fraction = zero.detach()
#|                return zero
#|
#|            prediction = prediction[present]
#|            normalized_target = normalized_target[present]
#|            current_groups = self._current_alignment_groups(
#|                present,
#|                prediction.device,
#|            )
#|            cosine_loss = (
#|                1.0 - (prediction * normalized_target).sum(dim=-1)
#|            ).mean()
#|
#|            nce_loss = cosine_loss.new_zeros(())
#|            valid_negative_count = cosine_loss.new_zeros(())
#|            masked_fraction = cosine_loss.new_zeros(())
#|            queue_count = int(self._alignment_queue_count.item())
#|            scheduled_weight = self._scheduled_nce_weight()
#|            if queue_count > 0 and scheduled_weight > 0.0:
#|                negatives = self._alignment_queue[:queue_count].to(
#|                    prediction.device
#|                )
#|                negatives = torch.nn.functional.normalize(
#|                    negatives.float(),
#|                    dim=-1,
#|                )
#|                queue_groups = self._alignment_queue_groups[
#|                    :queue_count
#|                ].to(prediction.device)
#|                positive_logits = (
#|                    prediction * normalized_target
#|                ).sum(dim=-1, keepdim=True)
#|                negative_logits = prediction @ negatives.transpose(0, 1)
#|
#|                known_groups = current_groups.ge(0).unsqueeze(1) & (
#|                    queue_groups.ge(0).unsqueeze(0)
#|                )
#|                same_group = known_groups & current_groups.unsqueeze(1).eq(
#|                    queue_groups.unsqueeze(0)
#|                )
#|                same_scale = float(self.config.same_group_negative_scale)
#|                if same_scale == 0.0:
#|                    negative_logits = negative_logits.masked_fill(
#|                        same_group,
#|                        -1e4,
#|                    )
#|                    valid_negative_count = (
#|                        (~same_group).float().sum(dim=1).mean()
#|                    )
#|                else:
#|                    negative_logits = torch.where(
#|                        same_group,
#|                        negative_logits
#|                        + math.log(max(same_scale, 1e-8)),
#|                        negative_logits,
#|                    )
#|                    valid_negative_count = negative_logits.new_tensor(
#|                        float(queue_count)
#|                    )
#|                masked_fraction = same_group.float().mean()
#|                logits = torch.cat(
#|                    [positive_logits, negative_logits],
#|                    dim=1,
#|                ) / float(self.config.alignment_temperature)
#|                targets = torch.zeros(
#|                    logits.size(0),
#|                    device=logits.device,
#|                    dtype=torch.long,
#|                )
#|                nce_loss = torch.nn.functional.cross_entropy(logits, targets)
#|
#|            total = cosine_loss + scheduled_weight * nce_loss
#|            self.last_semantic_alignment = cosine_loss.detach()
#|            self.last_alignment_nce = nce_loss.detach()
#|            self.last_alignment_nce_weight = cosine_loss.new_tensor(
#|                scheduled_weight
#|            ).detach()
#|            self.last_alignment_valid_negatives = (
#|                valid_negative_count.detach()
#|            )
#|            self.last_alignment_masked_fraction = masked_fraction.detach()
#|            self._enqueue_targets_with_groups(
#|                normalized_target,
#|                current_groups,
#|            )
#|            return total
#|
#|    return Readout, FalseNegativeAwareController
#|
#|
#|def collect_v5_metrics(model, torch) -> dict[str, str]:
#|    metrics = collect_v4_metrics(model, torch)
#|    projector = model.projector
#|    metrics.update(
#|        {
#|            "FN_NW": f"{projector.last_alignment_nce_weight.item():.3f}",
#|            "FN_NEG": (
#|                f"{projector.last_alignment_valid_negatives.item():.1f}"
#|            ),
#|            "FN_MASK": (
#|                f"{projector.last_alignment_masked_fraction.item():.3f}"
#|            ),
#|        }
#|    )
#|    return metrics
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: rgc_semantic_readout_stage_6.py ===
#|"""Adaptive soft-negative and tail-risk semantic readout (PBFA-RGSR v6).
#|
#|V6 preserves the token-free v5 inference architecture.  Its changes are
#|training-only: queue negatives are weighted from their instance-level semantic
#|similarity, and an online robust error model emphasizes explanations whose
#|graph-to-text alignment remains unusually weak.  No phenomenon receives a
#|manual loss weight and no graph tokens are introduced.
#|"""
#|
#|from __future__ import annotations
#|
#|from dataclasses import dataclass
#|
#|from rgc_semantic_readout_stage_5 import (
#|    FalseNegativeAwareReadoutConfig,
#|    collect_v5_metrics,
#|    make_v5_readout_classes,
#|    validate_v5_config,
#|)
#|
#|
#|@dataclass(frozen=True)
#|class AdaptiveSoftNegativeReadoutConfig(FalseNegativeAwareReadoutConfig):
#|    soft_negative_mad_floor: float = 0.03
#|    soft_negative_min_weight: float = 1e-4
#|    tail_error_ema: float = 0.95
#|    tail_error_scale_floor: float = 0.02
#|    tail_weight_floor: float = 0.75
#|    tail_weight_cap: float = 1.25
#|
#|
#|def validate_v6_config(config: AdaptiveSoftNegativeReadoutConfig) -> None:
#|    validate_v5_config(config)
#|    if config.soft_negative_mad_floor <= 0.0:
#|        raise ValueError("soft_negative_mad_floor must be positive")
#|    if not 0.0 < config.soft_negative_min_weight < 1.0:
#|        raise ValueError("soft_negative_min_weight must be in (0, 1)")
#|    if not 0.0 <= config.tail_error_ema < 1.0:
#|        raise ValueError("tail_error_ema must be in [0, 1)")
#|    if config.tail_error_scale_floor <= 0.0:
#|        raise ValueError("tail_error_scale_floor must be positive")
#|    if not 0.0 < config.tail_weight_floor <= 1.0:
#|        raise ValueError("tail_weight_floor must be in (0, 1]")
#|    if not 1.0 <= config.tail_weight_cap <= 2.0:
#|        raise ValueError("tail_weight_cap must be in [1, 2]")
#|    if config.tail_weight_floor >= config.tail_weight_cap:
#|        raise ValueError("tail weight floor must be below its cap")
#|
#|
#|def robust_soft_negative_weights(
#|    torch,
#|    reference_similarity,
#|    *,
#|    mad_floor: float,
#|    minimum: float,
#|):
#|    """Return mass-preserving negative weights from target similarity.
#|
#|    The row-wise median and median absolute deviation are computed from the
#|    queue itself.  Highly similar target explanations receive less negative
#|    mass, while dissimilar explanations remain useful regardless of their
#|    coarse phenomenon label.  Mean normalization preserves the total NCE
#|    pressure of v5 instead of silently weakening the auxiliary objective.
#|    """
#|
#|    if reference_similarity.dim() != 2:
#|        raise ValueError("reference_similarity must be a matrix")
#|    if reference_similarity.size(1) == 0:
#|        return reference_similarity
#|    center = reference_similarity.median(dim=1, keepdim=True).values
#|    deviation = (reference_similarity - center).abs()
#|    mad = deviation.median(dim=1, keepdim=True).values
#|    robust_scale = (1.4826 * mad).clamp_min(float(mad_floor))
#|    raw = torch.sigmoid((center - reference_similarity) / robust_scale)
#|    raw = raw.clamp_min(float(minimum))
#|    return raw / raw.mean(dim=1, keepdim=True).clamp_min(float(minimum))
#|
#|
#|def adaptive_tail_weight(
#|    torch,
#|    error,
#|    *,
#|    center,
#|    deviation,
#|    scale_floor: float,
#|    weight_floor: float,
#|    weight_cap: float,
#|):
#|    """Map alignment error to a bounded online risk weight."""
#|
#|    scale = deviation.clamp_min(float(scale_floor))
#|    risk = torch.sigmoid((error.detach() - center) / scale)
#|    return float(weight_floor) + (
#|        float(weight_cap) - float(weight_floor)
#|    ) * risk
#|
#|
#|def make_v6_readout_classes(torch, nn):
#|    Readout, V5Controller = make_v5_readout_classes(torch, nn)
#|
#|    class AdaptiveSoftNegativeController(V5Controller):
#|        def __init__(
#|            self,
#|            hidden_size: int,
#|            num_tokens: int,
#|            config: AdaptiveSoftNegativeReadoutConfig,
#|            *,
#|            training_graph_dropout: bool,
#|        ):
#|            validate_v6_config(config)
#|            super().__init__(
#|                hidden_size,
#|                num_tokens,
#|                config,
#|                training_graph_dropout=training_graph_dropout,
#|            )
#|            self.register_buffer(
#|                "_tail_error_center",
#|                torch.zeros(()),
#|                persistent=False,
#|            )
#|            self.register_buffer(
#|                "_tail_error_deviation",
#|                torch.ones(()) * float(config.tail_error_scale_floor),
#|                persistent=False,
#|            )
#|            self.register_buffer(
#|                "_tail_error_seen",
#|                torch.zeros((), dtype=torch.bool),
#|                persistent=False,
#|            )
#|            self.last_soft_negative_min = torch.tensor(1.0)
#|            self.last_soft_negative_max = torch.tensor(1.0)
#|            self.last_soft_negative_ess = torch.tensor(0.0)
#|            self.last_same_group_keep = torch.tensor(0.0)
#|            self.last_cross_group_keep = torch.tensor(0.0)
#|            self.last_tail_weight = torch.tensor(1.0)
#|            self.last_tail_center = torch.tensor(0.0)
#|            self.last_tail_deviation = torch.tensor(
#|                float(config.tail_error_scale_floor)
#|            )
#|
#|        def _update_tail_statistics(self, error) -> None:
#|            with torch.no_grad():
#|                value = error.detach().float().mean().to(
#|                    self._tail_error_center.device
#|                )
#|                if not bool(self._tail_error_seen.item()):
#|                    self._tail_error_center.copy_(value)
#|                    self._tail_error_deviation.fill_(
#|                        float(self.config.tail_error_scale_floor)
#|                    )
#|                    self._tail_error_seen.fill_(True)
#|                    return
#|                beta = float(self.config.tail_error_ema)
#|                previous = self._tail_error_center.clone()
#|                self._tail_error_center.mul_(beta).add_(value * (1.0 - beta))
#|                absolute_error = (value - previous).abs()
#|                self._tail_error_deviation.mul_(beta).add_(
#|                    absolute_error * (1.0 - beta)
#|                )
#|
#|        def semantic_alignment_loss(
#|            self,
#|            condition,
#|            target,
#|            target_present,
#|        ):
#|            prediction = torch.nn.functional.normalize(
#|                self.alignment_head(condition.float()),
#|                dim=-1,
#|            )
#|            normalized_target = torch.nn.functional.normalize(
#|                target.detach().float(),
#|                dim=-1,
#|            )
#|            present = target_present.to(prediction.device).bool().reshape(-1)
#|            if not bool(present.any()):
#|                zero = prediction.sum() * 0.0
#|                self.last_semantic_alignment = zero.detach()
#|                self.last_alignment_nce = zero.detach()
#|                self.last_alignment_valid_negatives = zero.detach()
#|                self.last_alignment_masked_fraction = zero.detach()
#|                self.last_tail_weight = zero.detach()
#|                return zero
#|
#|            prediction = prediction[present]
#|            normalized_target = normalized_target[present]
#|            current_groups = self._current_alignment_groups(
#|                present,
#|                prediction.device,
#|            )
#|            per_sample_cosine = 1.0 - (
#|                prediction * normalized_target
#|            ).sum(dim=-1)
#|            base_cosine = per_sample_cosine.mean()
#|            tail_weight = adaptive_tail_weight(
#|                torch,
#|                base_cosine,
#|                center=self._tail_error_center.to(base_cosine.device),
#|                deviation=self._tail_error_deviation.to(base_cosine.device),
#|                scale_floor=float(self.config.tail_error_scale_floor),
#|                weight_floor=float(self.config.tail_weight_floor),
#|                weight_cap=float(self.config.tail_weight_cap),
#|            )
#|            cosine_loss = tail_weight * base_cosine
#|
#|            nce_loss = cosine_loss.new_zeros(())
#|            effective_negatives = cosine_loss.new_zeros(())
#|            masked_fraction = cosine_loss.new_zeros(())
#|            queue_count = int(self._alignment_queue_count.item())
#|            scheduled_weight = self._scheduled_nce_weight()
#|            if queue_count > 0 and scheduled_weight > 0.0:
#|                negatives = torch.nn.functional.normalize(
#|                    self._alignment_queue[:queue_count]
#|                    .to(prediction.device)
#|                    .float(),
#|                    dim=-1,
#|                )
#|                queue_groups = self._alignment_queue_groups[
#|                    :queue_count
#|                ].to(prediction.device)
#|                positive_logits = (
#|                    prediction * normalized_target
#|                ).sum(dim=-1, keepdim=True)
#|                negative_logits = prediction @ negatives.transpose(0, 1)
#|                reference_similarity = (
#|                    normalized_target @ negatives.transpose(0, 1)
#|                ).detach()
#|                weights = robust_soft_negative_weights(
#|                    torch,
#|                    reference_similarity,
#|                    mad_floor=float(self.config.soft_negative_mad_floor),
#|                    minimum=float(self.config.soft_negative_min_weight),
#|                )
#|                negative_logits = negative_logits + weights.log()
#|
#|                squared_mass = weights.square().sum(dim=1).clamp_min(1e-8)
#|                effective_negatives = (
#|                    weights.sum(dim=1).square() / squared_mass
#|                ).mean()
#|                masked_fraction = weights.lt(0.5).float().mean()
#|                known_groups = current_groups.ge(0).unsqueeze(1) & (
#|                    queue_groups.ge(0).unsqueeze(0)
#|                )
#|                same_group = known_groups & current_groups.unsqueeze(1).eq(
#|                    queue_groups.unsqueeze(0)
#|                )
#|                cross_group = known_groups & ~same_group
#|                self.last_same_group_keep = (
#|                    weights[same_group].mean().detach()
#|                    if bool(same_group.any())
#|                    else weights.new_zeros(())
#|                )
#|                self.last_cross_group_keep = (
#|                    weights[cross_group].mean().detach()
#|                    if bool(cross_group.any())
#|                    else weights.new_zeros(())
#|                )
#|                self.last_soft_negative_min = weights.min().detach()
#|                self.last_soft_negative_max = weights.max().detach()
#|                self.last_soft_negative_ess = effective_negatives.detach()
#|                logits = torch.cat(
#|                    [positive_logits, negative_logits],
#|                    dim=1,
#|                ) / float(self.config.alignment_temperature)
#|                targets = torch.zeros(
#|                    logits.size(0),
#|                    device=logits.device,
#|                    dtype=torch.long,
#|                )
#|                nce_loss = torch.nn.functional.cross_entropy(logits, targets)
#|
#|            total = cosine_loss + scheduled_weight * nce_loss
#|            self.last_semantic_alignment = base_cosine.detach()
#|            self.last_alignment_nce = nce_loss.detach()
#|            self.last_alignment_nce_weight = base_cosine.new_tensor(
#|                scheduled_weight
#|            ).detach()
#|            self.last_alignment_valid_negatives = effective_negatives.detach()
#|            self.last_alignment_masked_fraction = masked_fraction.detach()
#|            self.last_tail_weight = tail_weight.detach().mean()
#|            self.last_tail_center = self._tail_error_center.detach().clone()
#|            self.last_tail_deviation = (
#|                self._tail_error_deviation.detach().clone()
#|            )
#|            self._update_tail_statistics(base_cosine)
#|            self._enqueue_targets_with_groups(
#|                normalized_target,
#|                current_groups,
#|            )
#|            return total
#|
#|    return Readout, AdaptiveSoftNegativeController
#|
#|
#|def collect_v6_metrics(model, torch) -> dict[str, str]:
#|    metrics = collect_v5_metrics(model, torch)
#|    projector = model.projector
#|    metrics.update(
#|        {
#|            "SNEG_MIN": f"{projector.last_soft_negative_min.item():.3f}",
#|            "SNEG_MAX": f"{projector.last_soft_negative_max.item():.3f}",
#|            "SNEG_ESS": f"{projector.last_soft_negative_ess.item():.1f}",
#|            "SNEG_S": f"{projector.last_same_group_keep.item():.3f}",
#|            "SNEG_X": f"{projector.last_cross_group_keep.item():.3f}",
#|            "TAIL_W": f"{projector.last_tail_weight.item():.3f}",
#|            "TAIL_C": f"{projector.last_tail_center.item():.3f}",
#|            "TAIL_D": f"{projector.last_tail_deviation.item():.3f}",
#|        }
#|    )
#|    return metrics
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: rgc_semantic_readout_stage_7.py ===
#|"""Decoder-grounded multi-granular PBFA-RGSR v7.
#|
#|V7 keeps the v6 token-free inference path.  During training it captures the
#|actual explanation-region decoder states after graph-conditioned readout and
#|aligns them at two levels: a global target-explanation objective and a local
#|graph-token coverage objective.  The two losses are balanced from online loss
#|statistics instead of phenomenon-specific manual weights.
#|"""
#|
#|from __future__ import annotations
#|
#|import math
#|from dataclasses import dataclass
#|
#|from rgc_semantic_readout_stage_6 import (
#|    AdaptiveSoftNegativeReadoutConfig,
#|    collect_v6_metrics,
#|    make_v6_readout_classes,
#|    validate_v6_config,
#|)
#|
#|
#|@dataclass(frozen=True)
#|class DecoderGroundedReadoutConfig(AdaptiveSoftNegativeReadoutConfig):
#|    decoder_alignment_dim: int = 256
#|    decoder_alignment_weight: float = 0.02
#|    decoder_alignment_temperature: float = 0.08
#|    decoder_alignment_ema: float = 0.95
#|    decoder_min_explanation_tokens: int = 4
#|
#|
#|def validate_v7_config(config: DecoderGroundedReadoutConfig) -> None:
#|    validate_v6_config(config)
#|    if config.decoder_alignment_dim <= 0:
#|        raise ValueError("decoder_alignment_dim must be positive")
#|    if not 0.0 < config.decoder_alignment_weight <= 0.10:
#|        raise ValueError("decoder_alignment_weight must be in (0, 0.10]")
#|    if config.decoder_alignment_temperature <= 0.0:
#|        raise ValueError("decoder_alignment_temperature must be positive")
#|    if not 0.0 <= config.decoder_alignment_ema < 1.0:
#|        raise ValueError("decoder_alignment_ema must be in [0, 1)")
#|    if config.decoder_min_explanation_tokens <= 0:
#|        raise ValueError("decoder_min_explanation_tokens must be positive")
#|
#|
#|def explanation_prediction_mask(torch, labels, ignore_index: int, label_tokens: int):
#|    """Mask hidden positions that predict explanation rather than verdict."""
#|
#|    shifted = labels[:, 1:]
#|    valid = shifted.ne(int(ignore_index))
#|    order = valid.long().cumsum(dim=1)
#|    return valid & order.gt(int(label_tokens))
#|
#|
#|def masked_mean(torch, values, mask):
#|    weights = mask.unsqueeze(-1).to(values.dtype)
#|    pooled = (values * weights).sum(dim=1)
#|    return pooled / weights.sum(dim=1).clamp_min(1.0)
#|
#|
#|def smooth_graph_coverage(
#|    torch,
#|    graph_tokens,
#|    graph_mask,
#|    explanation_tokens,
#|    explanation_mask,
#|    *,
#|    temperature: float,
#|):
#|    """Measure whether each graph token is represented by an explanation span."""
#|
#|    similarity = torch.bmm(
#|        graph_tokens,
#|        explanation_tokens.transpose(1, 2),
#|    )
#|    similarity = similarity.masked_fill(
#|        ~explanation_mask.unsqueeze(1),
#|        -1e4,
#|    )
#|    attention = torch.softmax(similarity / float(temperature), dim=-1)
#|    matched = (attention * similarity).sum(dim=-1)
#|    weights = graph_mask.to(matched.dtype)
#|    coverage = (matched * weights).sum(dim=1)
#|    coverage = coverage / weights.sum(dim=1).clamp_min(1.0)
#|    present = graph_mask.any(dim=1) & explanation_mask.any(dim=1)
#|    loss = (1.0 - coverage) * present.to(coverage.dtype)
#|    return loss.sum() / present.float().sum().clamp_min(1.0), coverage
#|
#|
#|def automatic_two_loss_balance(torch, first, second, first_ema, second_ema):
#|    """Inverse-EMA balancing with unit average weight."""
#|
#|    inverse = torch.stack(
#|        [first_ema.clamp_min(1e-4).reciprocal(), second_ema.clamp_min(1e-4).reciprocal()]
#|    )
#|    weights = 2.0 * inverse / inverse.sum().clamp_min(1e-8)
#|    combined = 0.5 * (weights[0] * first + weights[1] * second)
#|    return combined, weights
#|
#|
#|def make_v7_readout_classes(torch, nn):
#|    V6Readout, V6Controller = make_v6_readout_classes(torch, nn)
#|
#|    class DecoderCapturingReadout(V6Readout):
#|        def __init__(self, *args, **kwargs):
#|            super().__init__(*args, **kwargs)
#|            self.decoder_alignment_hidden = None
#|
#|        def forward(self, hidden):
#|            output = super().forward(hidden)
#|            if self.training:
#|                self.decoder_alignment_hidden = output
#|            return output
#|
#|        def take_decoder_hidden(self):
#|            hidden = self.decoder_alignment_hidden
#|            self.decoder_alignment_hidden = None
#|            return hidden
#|
#|    class DecoderGroundedController(V6Controller):
#|        def __init__(
#|            self,
#|            hidden_size: int,
#|            num_tokens: int,
#|            config: DecoderGroundedReadoutConfig,
#|            *,
#|            training_graph_dropout: bool,
#|        ):
#|            validate_v7_config(config)
#|            super().__init__(
#|                hidden_size,
#|                num_tokens,
#|                config,
#|                training_graph_dropout=training_graph_dropout,
#|            )
#|            old_readout = self.semantic_readout
#|            self.semantic_readout = DecoderCapturingReadout(
#|                hidden_size,
#|                config.condition_dim,
#|                config.readout_rank,
#|                gate_init=config.gate_init,
#|                gate_cap=config.gate_cap,
#|                rank_modulation_cap=config.rank_modulation_cap,
#|                residual_norm_ratio=config.residual_norm_ratio,
#|                label_token_count=config.label_token_count,
#|                label_readout_scale=config.label_readout_scale,
#|            )
#|            # Loading a v6 source replaces this initialization before training.
#|            self.semantic_readout.load_state_dict(old_readout.state_dict())
#|
#|            dim = int(config.decoder_alignment_dim)
#|            self.decoder_alignment_projection = nn.Sequential(
#|                nn.LayerNorm(hidden_size),
#|                nn.Linear(hidden_size, dim, bias=False),
#|            )
#|            self.graph_alignment_projection = nn.Sequential(
#|                nn.LayerNorm(hidden_size),
#|                nn.Linear(hidden_size, dim, bias=False),
#|            )
#|            self.target_alignment_projection = nn.Sequential(
#|                nn.LayerNorm(hidden_size),
#|                nn.Linear(hidden_size, dim, bias=False),
#|            )
#|            for projection in (
#|                self.decoder_alignment_projection,
#|                self.graph_alignment_projection,
#|                self.target_alignment_projection,
#|            ):
#|                nn.init.xavier_uniform_(projection[1].weight)
#|
#|            self.register_buffer(
#|                "_decoder_global_ema",
#|                torch.ones(()),
#|                persistent=False,
#|            )
#|            self.register_buffer(
#|                "_decoder_local_ema",
#|                torch.ones(()),
#|                persistent=False,
#|            )
#|            self.register_buffer(
#|                "_decoder_ema_seen",
#|                torch.zeros((), dtype=torch.bool),
#|                persistent=False,
#|            )
#|            self._decoder_graph_tokens = None
#|            self._decoder_graph_mask = None
#|            self._decoder_target = None
#|            self._decoder_target_present = None
#|            self.last_decoder_global = torch.tensor(0.0)
#|            self.last_decoder_local = torch.tensor(0.0)
#|            self.last_decoder_weighted = torch.tensor(0.0)
#|            self.last_decoder_global_weight = torch.tensor(1.0)
#|            self.last_decoder_local_weight = torch.tensor(1.0)
#|            self.last_decoder_graph_coverage = torch.tensor(0.0)
#|            self.last_decoder_explanation_tokens = torch.tensor(0.0)
#|            self.last_decoder_graph_tokens = torch.tensor(0.0)
#|
#|        def _drop_graph_evidence(
#|            self,
#|            graph_feature,
#|            semantic_token_embeddings,
#|            semantic_mask,
#|        ):
#|            input_present = bool(semantic_mask.any())
#|            output = super()._drop_graph_evidence(
#|                graph_feature,
#|                semantic_token_embeddings,
#|                semantic_mask,
#|            )
#|            if input_present:
#|                self._decoder_graph_tokens = output[1].detach()
#|                self._decoder_graph_mask = output[2].detach()
#|            return output
#|
#|        def semantic_alignment_loss(self, condition, target, target_present):
#|            loss = super().semantic_alignment_loss(
#|                condition,
#|                target,
#|                target_present,
#|            )
#|            self._decoder_target = target.detach().float()
#|            self._decoder_target_present = target_present.detach().bool()
#|            return loss
#|
#|        def _update_decoder_ema(self, global_loss, local_loss) -> None:
#|            with torch.no_grad():
#|                first = global_loss.detach().float().to(
#|                    self._decoder_global_ema.device
#|                )
#|                second = local_loss.detach().float().to(
#|                    self._decoder_local_ema.device
#|                )
#|                if not bool(self._decoder_ema_seen.item()):
#|                    self._decoder_global_ema.copy_(first)
#|                    self._decoder_local_ema.copy_(second)
#|                    self._decoder_ema_seen.fill_(True)
#|                    return
#|                beta = float(self.config.decoder_alignment_ema)
#|                self._decoder_global_ema.mul_(beta).add_(first * (1.0 - beta))
#|                self._decoder_local_ema.mul_(beta).add_(second * (1.0 - beta))
#|
#|        def _local_decoder_alignment(
#|            self,
#|            graph_tokens,
#|            graph_mask,
#|            decoder_tokens,
#|            explanation_mask,
#|            projected_target,
#|            target_present,
#|        ):
#|            del projected_target, target_present
#|            return smooth_graph_coverage(
#|                torch,
#|                graph_tokens,
#|                graph_mask,
#|                decoder_tokens,
#|                explanation_mask,
#|                temperature=float(
#|                    self.config.decoder_alignment_temperature
#|                ),
#|            )
#|
#|        def decoder_alignment_loss(self, labels, ignore_index: int):
#|            hidden = self.semantic_readout.take_decoder_hidden()
#|            graph_tokens = self._decoder_graph_tokens
#|            graph_mask = self._decoder_graph_mask
#|            target = self._decoder_target
#|            target_present = self._decoder_target_present
#|            self._decoder_graph_tokens = None
#|            self._decoder_graph_mask = None
#|            self._decoder_target = None
#|            self._decoder_target_present = None
#|            if hidden is None:
#|                raise RuntimeError("v7 final decoder state was not captured")
#|            if hidden.size(1) != labels.size(1):
#|                raise RuntimeError(
#|                    "v7 decoder/label sequence mismatch: "
#|                    f"{hidden.size(1)} != {labels.size(1)}"
#|                )
#|
#|            explanation_mask = explanation_prediction_mask(
#|                torch,
#|                labels,
#|                ignore_index,
#|                self.config.label_token_count,
#|            )
#|            hidden = hidden[:, :-1, :].float()
#|            enough = explanation_mask.long().sum(dim=1).ge(
#|                int(self.config.decoder_min_explanation_tokens)
#|            )
#|            explanation_mask = explanation_mask & enough.unsqueeze(1)
#|            decoder_tokens = torch.nn.functional.normalize(
#|                self.decoder_alignment_projection(hidden),
#|                dim=-1,
#|            )
#|            pooled_decoder = torch.nn.functional.normalize(
#|                masked_mean(torch, decoder_tokens, explanation_mask),
#|                dim=-1,
#|            )
#|
#|            projected_target = None
#|            if target is None or target_present is None:
#|                global_loss = hidden.sum() * 0.0
#|            else:
#|                projected_target = torch.nn.functional.normalize(
#|                    self.target_alignment_projection(target.to(hidden.device)),
#|                    dim=-1,
#|                )
#|                present = target_present.to(hidden.device) & enough
#|                global_error = 1.0 - (
#|                    pooled_decoder * projected_target
#|                ).sum(dim=-1)
#|                global_loss = (
#|                    global_error * present.to(global_error.dtype)
#|                ).sum() / present.float().sum().clamp_min(1.0)
#|
#|            if graph_tokens is None or graph_mask is None:
#|                local_loss = hidden.sum() * 0.0
#|                coverage = hidden.new_zeros((hidden.size(0),))
#|                graph_mask = explanation_mask.new_zeros(
#|                    (hidden.size(0), 1)
#|                )
#|            else:
#|                graph_tokens = torch.nn.functional.normalize(
#|                    self.graph_alignment_projection(
#|                        graph_tokens.to(hidden.device).float()
#|                    ),
#|                    dim=-1,
#|                )
#|                graph_mask = graph_mask.to(hidden.device).bool()
#|                local_loss, coverage = self._local_decoder_alignment(
#|                    graph_tokens,
#|                    graph_mask,
#|                    decoder_tokens,
#|                    explanation_mask,
#|                    projected_target,
#|                    target_present,
#|                )
#|
#|            balanced, weights = automatic_two_loss_balance(
#|                torch,
#|                global_loss,
#|                local_loss,
#|                self._decoder_global_ema.to(hidden.device),
#|                self._decoder_local_ema.to(hidden.device),
#|            )
#|            weighted = float(self.config.decoder_alignment_weight) * balanced
#|            self.last_decoder_global = global_loss.detach()
#|            self.last_decoder_local = local_loss.detach()
#|            self.last_decoder_weighted = weighted.detach()
#|            self.last_decoder_global_weight = weights[0].detach()
#|            self.last_decoder_local_weight = weights[1].detach()
#|            self.last_decoder_graph_coverage = coverage.detach().mean()
#|            self.last_decoder_explanation_tokens = (
#|                explanation_mask.long().sum(dim=1).float().mean().detach()
#|            )
#|            self.last_decoder_graph_tokens = (
#|                graph_mask.long().sum(dim=1).float().mean().detach()
#|            )
#|            self._update_decoder_ema(global_loss, local_loss)
#|            return weighted
#|
#|    return DecoderCapturingReadout, DecoderGroundedController
#|
#|
#|def collect_v7_metrics(model, torch) -> dict[str, str]:
#|    metrics = collect_v6_metrics(model, torch)
#|    projector = model.projector
#|    metrics.update(
#|        {
#|            "DEC_G": f"{projector.last_decoder_global.item():.4f}",
#|            "DEC_L": f"{projector.last_decoder_local.item():.4f}",
#|            "DEC_W": f"{projector.last_decoder_weighted.item():.4f}",
#|            "DEC_GW": f"{projector.last_decoder_global_weight.item():.3f}",
#|            "DEC_LW": f"{projector.last_decoder_local_weight.item():.3f}",
#|            "DEC_C": f"{projector.last_decoder_graph_coverage.item():.3f}",
#|            "DEC_YN": f"{projector.last_decoder_explanation_tokens.item():.0f}",
#|            "DEC_GN": f"{projector.last_decoder_graph_tokens.item():.0f}",
#|        }
#|    )
#|    return metrics
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: rgc_semantic_readout_stage_8.py ===
#|"""Reliability-gated decoder grounding with a source trust region.
#|
#|V8 remains token-free. During training, graph semantic tokens receive
#|sample-specific reliability weights from their agreement with both the gold
#|semantic target and the frozen v6 graph condition. A primal-dual trust region
#|limits drift of the inference-active semantic readout from its v6 source.
#|Neither mechanism is used to read test labels during inference.
#|"""
#|
#|from __future__ import annotations
#|
#|from dataclasses import dataclass
#|
#|from rgc_semantic_readout_stage_7 import (
#|    DecoderGroundedReadoutConfig,
#|    collect_v7_metrics,
#|    make_v7_readout_classes,
#|    validate_v7_config,
#|)
#|
#|
#|@dataclass(frozen=True)
#|class ReliabilityTrustReadoutConfig(DecoderGroundedReadoutConfig):
#|    reliability_temperature: float = 1.0
#|    reliability_absolute_temperature: float = 0.10
#|    reliability_deviation_floor: float = 0.05
#|    trust_radius: float = 5e-4
#|    trust_dual_lr: float = 0.02
#|    trust_augmented_weight: float = 0.01
#|    trust_dual_cap: float = 0.10
#|
#|
#|def validate_v8_config(config: ReliabilityTrustReadoutConfig) -> None:
#|    validate_v7_config(config)
#|    if config.reliability_temperature <= 0.0:
#|        raise ValueError("reliability_temperature must be positive")
#|    if config.reliability_absolute_temperature <= 0.0:
#|        raise ValueError(
#|            "reliability_absolute_temperature must be positive"
#|        )
#|    if config.reliability_deviation_floor <= 0.0:
#|        raise ValueError("reliability_deviation_floor must be positive")
#|    if config.trust_radius <= 0.0:
#|        raise ValueError("trust_radius must be positive")
#|    if config.trust_dual_lr <= 0.0:
#|        raise ValueError("trust_dual_lr must be positive")
#|    if config.trust_augmented_weight <= 0.0:
#|        raise ValueError("trust_augmented_weight must be positive")
#|    if config.trust_dual_cap <= 0.0:
#|        raise ValueError("trust_dual_cap must be positive")
#|
#|
#|def automatic_concept_reliability(
#|    torch,
#|    graph_tokens,
#|    graph_mask,
#|    projected_target,
#|    projected_condition,
#|    *,
#|    relative_temperature: float,
#|    absolute_temperature: float,
#|    deviation_floor: float,
#|):
#|    """Estimate graph-token reliability without phenomenon weights."""
#|
#|    target_agreement = (
#|        graph_tokens * projected_target.unsqueeze(1)
#|    ).sum(dim=-1)
#|    condition_agreement = (
#|        graph_tokens * projected_condition.unsqueeze(1)
#|    ).sum(dim=-1)
#|    agreement = 0.5 * (target_agreement + condition_agreement)
#|    mask_float = graph_mask.to(agreement.dtype)
#|    counts = mask_float.sum(dim=1, keepdim=True).clamp_min(1.0)
#|    center = (agreement * mask_float).sum(dim=1, keepdim=True) / counts
#|    deviation = (
#|        (agreement - center).abs() * mask_float
#|    ).sum(dim=1, keepdim=True) / counts
#|    deviation = deviation.clamp_min(float(deviation_floor))
#|    standardized = (agreement - center) / deviation
#|    relative = torch.sigmoid(
#|        standardized / float(relative_temperature)
#|    )
#|    absolute = torch.sigmoid(
#|        agreement / float(absolute_temperature)
#|    )
#|    raw = relative * absolute * mask_float
#|    sample_confidence = raw.sum(dim=1) / counts.squeeze(1)
#|    mean_raw = raw.sum(dim=1, keepdim=True) / counts
#|    normalized = raw / mean_raw.clamp_min(1e-4)
#|    normalized = normalized * mask_float
#|    squared_mass = normalized.square().sum(dim=1).clamp_min(1e-8)
#|    effective_tokens = normalized.sum(dim=1).square() / squared_mass
#|    return (
#|        normalized.detach(),
#|        sample_confidence.detach(),
#|        agreement.detach(),
#|        effective_tokens.detach(),
#|    )
#|
#|
#|def reliability_weighted_graph_coverage(
#|    torch,
#|    graph_tokens,
#|    graph_mask,
#|    explanation_tokens,
#|    explanation_mask,
#|    reliability,
#|    sample_confidence,
#|    target_present,
#|    *,
#|    temperature: float,
#|):
#|    similarity = torch.bmm(
#|        graph_tokens,
#|        explanation_tokens.transpose(1, 2),
#|    )
#|    similarity = similarity.masked_fill(
#|        ~explanation_mask.unsqueeze(1),
#|        -1e4,
#|    )
#|    attention = torch.softmax(similarity / float(temperature), dim=-1)
#|    matched = (attention * similarity).sum(dim=-1)
#|    weights = reliability * graph_mask.to(reliability.dtype)
#|    coverage = (matched * weights).sum(dim=1)
#|    coverage = coverage / weights.sum(dim=1).clamp_min(1e-4)
#|    present = graph_mask.any(dim=1) & explanation_mask.any(dim=1)
#|    if target_present is not None:
#|        present = present & target_present.to(present.device).bool()
#|    errors = (1.0 - coverage) * sample_confidence.to(coverage.device)
#|    loss = (errors * present.to(errors.dtype)).sum()
#|    loss = loss / present.float().sum().clamp_min(1.0)
#|    return loss, coverage
#|
#|
#|def make_v8_readout_classes(torch, nn):
#|    Readout, V7Controller = make_v7_readout_classes(torch, nn)
#|
#|    class ReliabilityTrustController(V7Controller):
#|        def __init__(
#|            self,
#|            hidden_size: int,
#|            num_tokens: int,
#|            config: ReliabilityTrustReadoutConfig,
#|            *,
#|            training_graph_dropout: bool,
#|        ):
#|            validate_v8_config(config)
#|            super().__init__(
#|                hidden_size,
#|                num_tokens,
#|                config,
#|                training_graph_dropout=training_graph_dropout,
#|            )
#|            self._reliability_condition = None
#|            self._trust_reference = None
#|            self.register_buffer(
#|                "trust_dual",
#|                torch.zeros(()),
#|                persistent=False,
#|            )
#|            self.register_buffer(
#|                "_trust_pending_constraint",
#|                torch.zeros(()),
#|                persistent=False,
#|            )
#|            self.last_reliability_mean = torch.tensor(1.0)
#|            self.last_reliability_ess = torch.tensor(0.0)
#|            self.last_reliability_agreement = torch.tensor(0.0)
#|            self.last_trust_drift = torch.tensor(0.0)
#|            self.last_trust_ratio = torch.tensor(0.0)
#|            self.last_trust_loss = torch.tensor(0.0)
#|
#|        def semantic_alignment_loss(self, condition, target, target_present):
#|            self._reliability_condition = condition.detach().float()
#|            return super().semantic_alignment_loss(
#|                condition,
#|                target,
#|                target_present,
#|            )
#|
#|        def _local_decoder_alignment(
#|            self,
#|            graph_tokens,
#|            graph_mask,
#|            decoder_tokens,
#|            explanation_mask,
#|            projected_target,
#|            target_present,
#|        ):
#|            condition = self._reliability_condition
#|            self._reliability_condition = None
#|            if projected_target is None or condition is None:
#|                return super()._local_decoder_alignment(
#|                    graph_tokens,
#|                    graph_mask,
#|                    decoder_tokens,
#|                    explanation_mask,
#|                    projected_target,
#|                    target_present,
#|                )
#|            condition_hidden = self.alignment_head(
#|                condition.to(graph_tokens.device)
#|            )
#|            projected_condition = torch.nn.functional.normalize(
#|                self.target_alignment_projection(condition_hidden),
#|                dim=-1,
#|            )
#|            reliability, confidence, agreement, effective_tokens = (
#|                automatic_concept_reliability(
#|                    torch,
#|                    graph_tokens,
#|                    graph_mask,
#|                    projected_target.detach(),
#|                    projected_condition.detach(),
#|                    relative_temperature=float(
#|                        self.config.reliability_temperature
#|                    ),
#|                    absolute_temperature=float(
#|                        self.config.reliability_absolute_temperature
#|                    ),
#|                    deviation_floor=float(
#|                        self.config.reliability_deviation_floor
#|                    ),
#|                )
#|            )
#|            loss, coverage = reliability_weighted_graph_coverage(
#|                torch,
#|                graph_tokens,
#|                graph_mask,
#|                decoder_tokens,
#|                explanation_mask,
#|                reliability,
#|                confidence,
#|                target_present,
#|                temperature=float(
#|                    self.config.decoder_alignment_temperature
#|                ),
#|            )
#|            valid = graph_mask.any(dim=1)
#|            valid_float = valid.to(confidence.dtype)
#|            denominator = valid_float.sum().clamp_min(1.0)
#|            self.last_reliability_mean = (
#|                confidence * valid_float
#|            ).sum().detach() / denominator
#|            self.last_reliability_ess = (
#|                effective_tokens * valid_float
#|            ).sum().detach() / denominator
#|            agreement_mean = (
#|                agreement * graph_mask.to(agreement.dtype)
#|            ).sum(dim=1) / graph_mask.float().sum(dim=1).clamp_min(1.0)
#|            self.last_reliability_agreement = (
#|                agreement_mean * valid_float
#|            ).sum().detach() / denominator
#|            return loss, coverage
#|
#|        def set_trust_reference(self) -> None:
#|            self._trust_reference = {
#|                name: parameter.detach().float().clone()
#|                for name, parameter in self.semantic_readout.named_parameters()
#|            }
#|            if not self._trust_reference:
#|                raise RuntimeError("v8 semantic readout has no trust parameters")
#|
#|        def _semantic_readout_drift(self):
#|            if self._trust_reference is None:
#|                raise RuntimeError("v8 trust reference was not initialized")
#|            squared = None
#|            count = 0
#|            for name, parameter in self.semantic_readout.named_parameters():
#|                reference = self._trust_reference[name].to(parameter.device)
#|                value = (parameter.float() - reference).square().sum()
#|                squared = value if squared is None else squared + value
#|                count += parameter.numel()
#|            return torch.sqrt(squared / max(1, count) + 1e-12)
#|
#|        def parameter_trust_loss(self):
#|            drift = self._semantic_readout_drift()
#|            ratio = drift / float(self.config.trust_radius)
#|            constraint = ratio - 1.0
#|            violation = torch.relu(constraint)
#|            loss = (
#|                self.trust_dual.detach() * violation
#|                + 0.5
#|                * float(self.config.trust_augmented_weight)
#|                * violation.square()
#|            )
#|            with torch.no_grad():
#|                self._trust_pending_constraint.copy_(constraint.detach())
#|            self.last_trust_drift = drift.detach()
#|            self.last_trust_ratio = ratio.detach()
#|            self.last_trust_loss = loss.detach()
#|            return loss
#|
#|        def on_optimizer_step(self) -> None:
#|            super().on_optimizer_step()
#|            with torch.no_grad():
#|                self.trust_dual.add_(
#|                    float(self.config.trust_dual_lr)
#|                    * self._trust_pending_constraint
#|                )
#|                self.trust_dual.clamp_(
#|                    0.0,
#|                    float(self.config.trust_dual_cap),
#|                )
#|                self._trust_pending_constraint.zero_()
#|
#|    return Readout, ReliabilityTrustController
#|
#|
#|def collect_v8_metrics(model, torch) -> dict[str, str]:
#|    metrics = collect_v7_metrics(model, torch)
#|    projector = model.projector
#|    metrics.update(
#|        {
#|            "REL_M": f"{projector.last_reliability_mean.item():.3f}",
#|            "REL_E": f"{projector.last_reliability_ess.item():.1f}",
#|            "REL_A": f"{projector.last_reliability_agreement.item():.3f}",
#|            "TR_D": f"{projector.last_trust_drift.item():.2e}",
#|            "TR_R": f"{projector.last_trust_ratio.item():.2f}",
#|            "TR_U": f"{projector.trust_dual.item():.3f}",
#|            "TR_L": f"{projector.last_trust_loss.item():.4f}",
#|        }
#|    )
#|    return metrics
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: test_llava_claim_graphprompt.py ===
#|"""Inference for LLaVA+Claim plus paper-2 concept graph prompt.
#|
#|The output schema and result folder layout follow ``test_moe_创新点1.py`` so
#|the original metric script can be reused without changing evaluation logic.
#|"""
#|
#|from __future__ import annotations
#|
#|import argparse
#|import importlib.util
#|import math
#|import os
#|import sys
#|import traceback
#|from pathlib import Path
#|
#|from concept_graph_integration import (
#|    GRAPH_FEATURE_DIM,
#|    require_concept_graph_cache,
#|)
#|from paths_paper2 import Paper2Paths, describe_paths
#|from train_llava_claim_graphprompt import (
#|    DEFAULT_CKPT_NAME,
#|    PROJECTOR_SUFFIX,
#|)
#|
#|
#|BASE_TEST_SCRIPT = "test_moe_创新点1.py"
#|
#|
#|def load_original_test_module(paths: Paper2Paths):
#|    script_path = paths.orig_root / BASE_TEST_SCRIPT
#|    if not script_path.exists():
#|        raise FileNotFoundError(f"Missing original LLaVA+Claim test script: {script_path}")
#|    sys.path.insert(0, str(Path(__file__).resolve().parent))
#|    sys.path.insert(1, str(paths.orig_root))
#|    spec = importlib.util.spec_from_file_location("paper2_original_claim_test", script_path)
#|    if spec is None or spec.loader is None:
#|        raise ImportError(f"Could not import {script_path}")
#|    module = importlib.util.module_from_spec(spec)
#|    spec.loader.exec_module(module)
#|    return module
#|
#|
#|def install_claim_graphprompt_inference(
#|    module,
#|    concept_graph_path: str | Path | None,
#|    graph_gate_init: float = 0.25,
#|    graph_gate_cap: float = 0.75,
#|):
#|    import torch
#|    import torch.nn as nn
#|
#|    if not 0.0 < graph_gate_cap <= 1.0:
#|        raise ValueError(f"graph_gate_cap must be in (0, 1], got {graph_gate_cap}")
#|    if not 0.0 < graph_gate_init < graph_gate_cap:
#|        raise ValueError(
#|            f"graph_gate_init must be in (0, graph_gate_cap), "
#|            f"got init={graph_gate_init}, cap={graph_gate_cap}"
#|        )
#|
#|    BaseProjector = module.MoE_LLM_Projector
#|    _, graph_features, _ = require_concept_graph_cache(
#|        concept_graph_path,
#|        split="test",
#|    )
#|
#|    class ClaimGraphPromptProjector(BaseProjector):
#|        def __init__(self, *args, graph_dim: int = GRAPH_FEATURE_DIM, **kwargs):
#|            super().__init__(*args, **kwargs)
#|            self.graph_dim = graph_dim
#|            projected_dim = self.img_proj.out_features
#|            if hasattr(self, "experts"):
#|                del self.experts
#|            if hasattr(self, "gate"):
#|                del self.gate
#|            self.graph_prompt = nn.Sequential(
#|                nn.Linear(projected_dim * 5 + graph_dim, 2048),
#|                nn.LayerNorm(2048),
#|                nn.GELU(),
#|                nn.Linear(2048, self.hidden_size * self.num_tokens),
#|            )
#|            self.graph_gate_cap = graph_gate_cap
#|            self.graph_reliability_gate = nn.Linear(projected_dim * 5 + graph_dim, 1)
#|            nn.init.zeros_(self.graph_reliability_gate.weight)
#|            nn.init.constant_(
#|                self.graph_reliability_gate.bias,
#|                math.log(graph_gate_init / (graph_gate_cap - graph_gate_init)),
#|            )
#|            self._paper2_current_graph_feature = None
#|
#|        def forward(self, e_img, e_txt, e_desc):
#|            e_img = e_img.float()
#|            e_txt = e_txt.float()
#|            e_desc = e_desc.float()
#|
#|            p_img = self.img_norm(self.img_proj(e_img))
#|            p_txt = self.txt_norm(self.txt_proj(e_txt))
#|            p_desc = self.desc_norm(self.desc_proj(e_desc))
#|            x_relation = torch.cat(
#|                [p_img, p_desc, p_txt, torch.abs(p_desc - p_txt), p_desc * p_txt],
#|                dim=-1,
#|            )
#|
#|            graph_feature = self._paper2_current_graph_feature
#|            if graph_feature is None:
#|                graph_feature = torch.zeros((e_img.size(0), self.graph_dim), device=e_img.device)
#|            if graph_feature.dim() == 1:
#|                graph_feature = graph_feature.unsqueeze(0)
#|            graph_feature = graph_feature.to(e_img.device).float()
#|
#|            gate_input = torch.cat([x_relation, graph_feature], dim=-1)
#|            graph_gate_cap = self.graph_gate_cap
#|            graph_gate = graph_gate_cap * torch.sigmoid(
#|                self.graph_reliability_gate(gate_input)
#|            )
#|            gated_graph_feature = graph_feature * graph_gate
#|            graph_input = torch.cat([x_relation, gated_graph_feature], dim=-1)
#|            fused = self.graph_prompt(graph_input).view(-1, self.num_tokens, self.hidden_size)
#|            fused = self.output_norm(fused) * 0.01
#|            return fused
#|
#|    module.MoE_LLM_Projector = ClaimGraphPromptProjector
#|    return module, graph_features
#|
#|
#|def load_claim_graphprompt_model(module, paths: Paper2Paths, epoch: int, device: str, num_tokens: int):
#|    torch = module.torch
#|    lora_path = paths.checkpoint_dir / f"lora_epoch_{epoch}{PROJECTOR_SUFFIX}"
#|    proj_path = paths.checkpoint_dir / f"proj_epoch_{epoch}{PROJECTOR_SUFFIX}.pth"
#|    if not lora_path.exists():
#|        raise FileNotFoundError(f"Missing LoRA checkpoint: {lora_path}")
#|    if not proj_path.exists():
#|        raise FileNotFoundError(f"Missing projector checkpoint: {proj_path}")
#|
#|    print(f"[paper2-claim-graphprompt] base model: {paths.llm_path}")
#|    print(f"[paper2-claim-graphprompt] LoRA:       {lora_path}")
#|    print(f"[paper2-claim-graphprompt] Projector:  {proj_path}")
#|
#|    model_name = module.get_model_name_from_path(paths.llm_path)
#|    tokenizer, base_model, image_processor, _ = module.load_pretrained_model(
#|        paths.llm_path,
#|        None,
#|        model_name,
#|        device_map=device,
#|        torch_dtype=torch.bfloat16,
#|    )
#|    model = module.PeftModel.from_pretrained(base_model, str(lora_path))
#|    model = model.merge_and_unload()
#|    model = model.to(device, dtype=torch.bfloat16)
#|    model.eval()
#|
#|    projector = module.MoE_LLM_Projector(hidden_size=model.config.hidden_size, num_tokens=num_tokens)
#|    projector.load_state_dict(torch.load(proj_path, map_location=device))
#|    projector = projector.to(device)
#|    projector.eval()
#|    return tokenizer, model, image_processor, projector
#|
#|
#|def run_inference(
#|    args: argparse.Namespace,
#|    install_inference=install_claim_graphprompt_inference,
#|) -> None:
#|    os.environ.setdefault("PAPER2_CKPT_NAME", DEFAULT_CKPT_NAME)
#|    paths = Paper2Paths.from_env()
#|    paths.ensure_output_dirs()
#|    print(describe_paths(paths))
#|    concept_graph_path = paths.resolve_output_path(
#|        args.concept_graph_cache or paths.test_concept_graph_cache
#|    )
#|    require_concept_graph_cache(concept_graph_path, split="test")
#|
#|    module, graph_features = install_inference(
#|        load_original_test_module(paths),
#|        concept_graph_path,
#|        graph_gate_init=args.graph_gate_init,
#|        graph_gate_cap=args.graph_gate_cap,
#|    )
#|    tokenizer, model, image_processor, projector = load_claim_graphprompt_model(
#|        module,
#|        paths,
#|        args.epoch,
#|        args.device,
#|        args.num_tokens,
#|    )
#|
#|    with open(paths.test_json, "r", encoding="utf-8") as handle:
#|        data = module.json.load(handle)
#|    print(f"[paper2-claim-graphprompt] test samples: {len(data)}")
#|
#|    features_dict = {}
#|    if paths.test_features.exists():
#|        with open(paths.test_features, "rb") as handle:
#|            features_dict = module.pickle.load(handle)
#|        print(f"[paper2-claim-graphprompt] feature samples: {len(features_dict)}")
#|
#|    output_tag = args.output_tag or f"llava_claim_graphprompt_epoch{args.epoch}"
#|    output_dir = paths.result_dir / output_tag
#|    output_dir.mkdir(parents=True, exist_ok=True)
#|    result_path = output_dir / "_result.json"
#|    result = module.checkpoint_utils.load_checkpoint(str(result_path))
#|    skip_rows = len(result)
#|    print(f"[paper2-claim-graphprompt] completed rows: {skip_rows}; resume enabled")
#|
#|    for index, row in module.tqdm(enumerate(data), total=len(data)):
#|        if index < skip_rows:
#|            continue
#|
#|        image_path = paths.image_folder / row["image"]
#|        prompt = row["conversations"][0]["value"]
#|        sample_id = row["id"]
#|        feats = features_dict.get(sample_id, None)
#|        projector._paper2_current_graph_feature = graph_features.get(sample_id)
#|
#|        try:
#|            explanation = module.get_response(
#|                str(image_path),
#|                prompt,
#|                tokenizer,
#|                model,
#|                image_processor,
#|                projector,
#|                feats,
#|                args.device,
#|            )
#|            label = module.parse_label(explanation)
#|            explanation_final = ".".join(explanation.split(".")[1:]).strip()
#|        except Exception as exc:
#|            print(f"Error at index {index}: {exc}")
#|            traceback.print_exc()
#|            label, explanation_final = 0, ""
#|
#|        result.append({"id": sample_id, "label": label, "explanation": explanation_final})
#|        module.checkpoint_utils.save_checkpoint(result, str(result_path))
#|
#|    df = module.pd.DataFrame(result)
#|    csv_path = output_dir / "result.csv"
#|    df.to_csv(csv_path, index=False)
#|    print(f"\n[paper2-claim-graphprompt] saved result: {csv_path}")
#|
#|
#|def parse_args() -> argparse.Namespace:
#|    parser = argparse.ArgumentParser()
#|    parser.add_argument("--epoch", type=int, default=4)
#|    parser.add_argument("--device", type=str, default="cuda:0")
#|    parser.add_argument("--num_tokens", type=int, default=4)
#|    parser.add_argument("--graph_gate_init", type=float, default=0.25)
#|    parser.add_argument("--graph_gate_cap", type=float, default=0.75)
#|    parser.add_argument("--output_tag", type=str, default=None)
#|    parser.add_argument("--concept_graph_cache", type=str, default=None)
#|    return parser.parse_args()
#|
#|
#|if __name__ == "__main__":
#|    run_inference(parse_args())
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: test_llava_claim_rgc_semantic_readout.py ===
#|"""Inference for token-free graph-conditioned semantic readout (RGC-SR v2)."""
#|
#|from __future__ import annotations
#|
#|import argparse
#|import os
#|import traceback
#|
#|
#|DEFAULT_CKPT_NAME = "checkpoints_llava_claim_rgc_semantic_readout_v2"
#|PROJECTOR_SUFFIX = "_claim_rgc_semantic_readout_v2"
#|os.environ["PAPER2_CKPT_NAME"] = os.environ.get(
#|    "RGC_SR_CKPT_NAME",
#|    DEFAULT_CKPT_NAME,
#|)
#|os.environ["PAPER2_PROJECTOR_SUFFIX"] = os.environ.get(
#|    "RGC_SR_PROJECTOR_SUFFIX",
#|    PROJECTOR_SUFFIX,
#|)
#|
#|from concept_graph_integration import (  # noqa: E402
#|    GRAPH_FEATURE_DIM,
#|    require_concept_graph_cache,
#|)
#|from paths_paper2 import Paper2Paths, describe_paths  # noqa: E402
#|from rgc_semantic_readout import (  # noqa: E402
#|    attach_semantic_readout,
#|    load_graph_semantic_text_map,
#|    make_semantic_readout_classes,
#|    safe_token_embeddings,
#|    tokenize_graph_semantic_text,
#|)
#|from test_llava_claim_graphprompt import load_original_test_module  # noqa: E402
#|from train_llava_claim_rgc_semantic_readout import (  # noqa: E402
#|    config_from_args,
#|)
#|
#|
#|def install_semantic_readout_inference(module, args):
#|    import torch.nn as nn
#|
#|    config = config_from_args(args)
#|    _, GraphSemanticController = make_semantic_readout_classes(
#|        module.torch,
#|        nn,
#|    )
#|
#|    class InferenceSemanticController(GraphSemanticController):
#|        def __init__(self, hidden_size, num_tokens=0):
#|            super().__init__(
#|                hidden_size,
#|                num_tokens,
#|                config,
#|                training_graph_dropout=False,
#|            )
#|
#|    module.MoE_LLM_Projector = InferenceSemanticController
#|    return module
#|
#|
#|def load_model(module, paths: Paper2Paths, args):
#|    torch = module.torch
#|    lora_path = (
#|        paths.checkpoint_dir
#|        / f"lora_epoch_{args.epoch}{PROJECTOR_SUFFIX}"
#|    )
#|    projector_path = (
#|        paths.checkpoint_dir
#|        / f"proj_epoch_{args.epoch}{PROJECTOR_SUFFIX}.pth"
#|    )
#|    if not lora_path.exists():
#|        raise FileNotFoundError(f"Missing LoRA checkpoint: {lora_path}")
#|    if not projector_path.exists():
#|        raise FileNotFoundError(
#|            f"Missing RGC-SemanticReadout checkpoint: {projector_path}"
#|        )
#|    print(f"[rgc-semantic-readout] base model: {paths.llm_path}")
#|    print(f"[rgc-semantic-readout] LoRA: {lora_path}")
#|    print(f"[rgc-semantic-readout] controller: {projector_path}")
#|
#|    model_name = module.get_model_name_from_path(paths.llm_path)
#|    tokenizer, base_model, image_processor, _ = module.load_pretrained_model(
#|        paths.llm_path,
#|        None,
#|        model_name,
#|        device_map=args.device,
#|        torch_dtype=torch.bfloat16,
#|    )
#|    model = module.PeftModel.from_pretrained(base_model, str(lora_path))
#|    model = model.merge_and_unload()
#|    model = model.to(args.device, dtype=torch.bfloat16)
#|    model.eval()
#|
#|    projector = module.MoE_LLM_Projector(
#|        hidden_size=model.config.hidden_size,
#|        num_tokens=0,
#|    )
#|    state = torch.load(projector_path, map_location="cpu")
#|    projector.load_state_dict(state, strict=True)
#|    projector = projector.to(args.device)
#|    projector.eval()
#|    norm_name = attach_semantic_readout(model, projector)
#|    print(
#|        "[rgc-semantic-readout] graph_tokens=0; "
#|        f"final_norm={norm_name}; semantic side channel only"
#|    )
#|    return tokenizer, model, image_processor, projector
#|
#|
#|def run_inference(args) -> None:
#|    if args.num_tokens != 0:
#|        raise ValueError("RGC-SemanticReadout forbids latent prompt tokens")
#|    paths = Paper2Paths.from_env()
#|    paths.ensure_output_dirs()
#|    print(describe_paths(paths))
#|    graph_path = paths.resolve_output_path(
#|        args.concept_graph_cache or paths.test_concept_graph_cache
#|    )
#|    _, graph_features, _ = require_concept_graph_cache(
#|        graph_path,
#|        split="test",
#|        allow_phenomenon_fallback=False,
#|    )
#|    semantic_texts = load_graph_semantic_text_map(
#|        graph_path,
#|        allow_phenomenon_fallback=False,
#|    )
#|    print(
#|        "[rgc-semantic-readout] test phenomenon policy: "
#|        "inferred_phenomenon only; annotated phenomenon fallback disabled"
#|    )
#|    module = install_semantic_readout_inference(
#|        load_original_test_module(paths),
#|        args,
#|    )
#|    tokenizer, model, image_processor, projector = load_model(
#|        module,
#|        paths,
#|        args,
#|    )
#|    embed_layer = (
#|        model.get_input_embeddings()
#|        if hasattr(model, "get_input_embeddings")
#|        else model.get_model().embed_tokens
#|    )
#|
#|    with open(paths.test_json, "r", encoding="utf-8") as handle:
#|        data = module.json.load(handle)
#|    max_samples = getattr(args, "max_samples", None)
#|    if max_samples is not None:
#|        if max_samples <= 0:
#|            raise ValueError("max_samples must be positive")
#|        data = data[:max_samples]
#|    with open(paths.test_features, "rb") as handle:
#|        features = module.pickle.load(handle)
#|    output_tag = (
#|        args.output_tag
#|        or f"llava_claim_rgc_semantic_readout_v2_epoch{args.epoch}"
#|    )
#|    output_dir = paths.result_dir / output_tag
#|    output_dir.mkdir(parents=True, exist_ok=True)
#|    result_path = output_dir / "_result.json"
#|    result = module.checkpoint_utils.load_checkpoint(str(result_path))
#|    skip_rows = len(result)
#|    print(
#|        f"[rgc-semantic-readout] test={len(data)} completed={skip_rows}; "
#|        "resume enabled"
#|    )
#|
#|    for index, row in module.tqdm(enumerate(data), total=len(data)):
#|        if index < skip_rows:
#|            continue
#|        sample_id = row["id"]
#|        sample_features = features.get(sample_id)
#|        try:
#|            if sample_features is None:
#|                raise KeyError(f"missing feature row for sample {sample_id}")
#|            graph_feature = graph_features.get(
#|                sample_id,
#|                module.torch.zeros(
#|                    GRAPH_FEATURE_DIM,
#|                    dtype=module.torch.float32,
#|                ),
#|            )
#|            semantic_ids, semantic_mask = tokenize_graph_semantic_text(
#|                tokenizer,
#|                semantic_texts.get(sample_id, ""),
#|                args.semantic_max_length,
#|            )
#|            semantic_ids = semantic_ids.unsqueeze(0).to(args.device)
#|            semantic_mask = semantic_mask.unsqueeze(0).to(args.device)
#|            with module.torch.no_grad():
#|                semantic_token_embeddings, semantic_token_mask = (
#|                    safe_token_embeddings(
#|                        embed_layer,
#|                        semantic_ids,
#|                        semantic_mask,
#|                        vocab_size=model.config.vocab_size,
#|                    )
#|                )
#|                projector(
#|                    sample_features["E_image"].unsqueeze(0).to(args.device),
#|                    sample_features["E_text"].unsqueeze(0).to(args.device),
#|                    sample_features["E_desc"].unsqueeze(0).to(args.device),
#|                    graph_feature=graph_feature.unsqueeze(0).to(args.device),
#|                    semantic_token_embeddings=semantic_token_embeddings,
#|                    semantic_mask=semantic_token_mask,
#|                )
#|            explanation = module.get_response(
#|                str(paths.image_folder / row["image"]),
#|                row["conversations"][0]["value"],
#|                tokenizer,
#|                model,
#|                image_processor,
#|                projector,
#|                None,
#|                args.device,
#|            )
#|            label = module.parse_label(explanation)
#|            explanation_final = ".".join(
#|                explanation.split(".")[1:]
#|            ).strip()
#|        except Exception as exc:
#|            print(f"Error at index {index}: {exc}")
#|            traceback.print_exc()
#|            label, explanation_final = 0, ""
#|        result.append(
#|            {
#|                "id": sample_id,
#|                "label": label,
#|                "explanation": explanation_final,
#|            }
#|        )
#|        module.checkpoint_utils.save_checkpoint(result, str(result_path))
#|
#|    csv_path = output_dir / "result.csv"
#|    module.pd.DataFrame(result).to_csv(csv_path, index=False)
#|    print(f"[rgc-semantic-readout] saved result: {csv_path}")
#|
#|
#|def build_parser() -> argparse.ArgumentParser:
#|    parser = argparse.ArgumentParser()
#|    parser.add_argument("--epoch", type=int, default=3)
#|    parser.add_argument("--device", type=str, default="cuda:0")
#|    parser.add_argument("--num_tokens", type=int, default=0)
#|    parser.add_argument("--output_tag", type=str, default=None)
#|    parser.add_argument("--concept_graph_cache", type=str, default=None)
#|    parser.add_argument("--relation_dim", type=int, default=256)
#|    parser.add_argument("--condition_dim", type=int, default=256)
#|    parser.add_argument("--controller_dropout", type=float, default=0.10)
#|    parser.add_argument("--graph_dropout", type=float, default=0.10)
#|    parser.add_argument("--readout_rank", type=int, default=32)
#|    parser.add_argument("--readout_gate_init", type=float, default=0.08)
#|    parser.add_argument("--readout_gate_cap", type=float, default=0.25)
#|    parser.add_argument("--rank_modulation_cap", type=float, default=0.50)
#|    parser.add_argument("--readout_residual_ratio", type=float, default=0.08)
#|    parser.add_argument("--semantic_max_length", type=int, default=96)
#|    return parser
#|
#|
#|if __name__ == "__main__":
#|    run_inference(build_parser().parse_args())
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: test_llava_claim_rgc_semantic_readout_stage_4.py ===
#|"""Inference for phenomenon-balanced token-free semantic readout v4."""
#|
#|from __future__ import annotations
#|
#|import os
#|
#|
#|DEFAULT_CKPT_NAME = "checkpoints_llava_claim_rgc_semantic_readout_v4"
#|PROJECTOR_SUFFIX = "_claim_rgc_semantic_readout_v4"
#|os.environ["RGC_SR_CKPT_NAME"] = os.environ.get(
#|    "RGC_SR_V4_CKPT_NAME",
#|    DEFAULT_CKPT_NAME,
#|)
#|os.environ["RGC_SR_PROJECTOR_SUFFIX"] = os.environ.get(
#|    "RGC_SR_V4_PROJECTOR_SUFFIX",
#|    PROJECTOR_SUFFIX,
#|)
#|
#|import test_llava_claim_rgc_semantic_readout as base_test  # noqa: E402
#|from rgc_semantic_readout_stage_4 import make_v4_readout_classes  # noqa: E402
#|from train_llava_claim_rgc_semantic_readout_stage_4 import (  # noqa: E402
#|    config_from_args,
#|)
#|
#|
#|def build_parser():
#|    parser = base_test.build_parser()
#|    parser.set_defaults(
#|        readout_rank=32,
#|        readout_gate_init=0.04,
#|        readout_gate_cap=0.12,
#|        rank_modulation_cap=0.35,
#|        readout_residual_ratio=0.06,
#|        graph_dropout=0.10,
#|    )
#|    parser.add_argument("--graph_residual_gate_floor", type=float, default=0.03)
#|    parser.add_argument("--graph_residual_gate_init", type=float, default=0.12)
#|    parser.add_argument("--graph_residual_gate_cap", type=float, default=0.35)
#|    parser.add_argument(
#|        "--semantic_residual_gate_floor",
#|        type=float,
#|        default=0.03,
#|    )
#|    parser.add_argument(
#|        "--semantic_residual_gate_init",
#|        type=float,
#|        default=0.12,
#|    )
#|    parser.add_argument(
#|        "--semantic_residual_gate_cap",
#|        type=float,
#|        default=0.35,
#|    )
#|    parser.add_argument("--label_token_count", type=int, default=4)
#|    parser.add_argument("--label_readout_scale", type=float, default=0.10)
#|    parser.add_argument("--label_loss_weight", type=float, default=0.40)
#|    parser.add_argument("--dro_eta", type=float, default=0.05)
#|    parser.add_argument("--dro_ema", type=float, default=0.90)
#|    parser.add_argument("--dro_entropy_reg", type=float, default=0.01)
#|    parser.add_argument(
#|        "--dro_logit_cap",
#|        type=float,
#|        default=0.9162907318741551,
#|    )
#|    parser.add_argument("--dro_prior_floor", type=float, default=0.01)
#|    parser.add_argument("--dro_sample_weight_cap", type=float, default=3.0)
#|    parser.add_argument("--dro_warmup_steps", type=int, default=16)
#|    parser.add_argument("--alignment_queue_size", type=int, default=128)
#|    parser.add_argument("--alignment_temperature", type=float, default=0.10)
#|    parser.add_argument("--alignment_nce_weight", type=float, default=0.20)
#|    return parser
#|
#|
#|def main() -> None:
#|    args = build_parser().parse_args()
#|    if args.num_tokens != 0:
#|        raise ValueError("RGC-SemanticReadout-v4 forbids prompt tokens")
#|    if args.output_tag is None:
#|        args.output_tag = (
#|            f"llava_claim_rgc_semantic_readout_v4_epoch{args.epoch}"
#|        )
#|    base_test.make_semantic_readout_classes = make_v4_readout_classes
#|    base_test.config_from_args = config_from_args
#|    base_test.DEFAULT_CKPT_NAME = DEFAULT_CKPT_NAME
#|    base_test.PROJECTOR_SUFFIX = PROJECTOR_SUFFIX
#|    base_test.run_inference(args)
#|
#|
#|if __name__ == "__main__":
#|    main()
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: test_llava_claim_rgc_semantic_readout_stage_5.py ===
#|"""Inference for false-negative-aware semantic readout v5."""
#|
#|from __future__ import annotations
#|
#|import os
#|
#|
#|DEFAULT_CKPT_NAME = "checkpoints_llava_claim_rgc_semantic_readout_v5"
#|PROJECTOR_SUFFIX = "_claim_rgc_semantic_readout_v5"
#|os.environ["RGC_SR_V4_CKPT_NAME"] = os.environ.get(
#|    "RGC_SR_V5_CKPT_NAME",
#|    DEFAULT_CKPT_NAME,
#|)
#|os.environ["RGC_SR_V4_PROJECTOR_SUFFIX"] = os.environ.get(
#|    "RGC_SR_V5_PROJECTOR_SUFFIX",
#|    PROJECTOR_SUFFIX,
#|)
#|
#|import test_llava_claim_rgc_semantic_readout_stage_4 as base_v4_test  # noqa: E402
#|from rgc_semantic_readout_stage_5 import make_v5_readout_classes  # noqa: E402
#|from train_llava_claim_rgc_semantic_readout_stage_5 import (  # noqa: E402
#|    config_from_args,
#|)
#|
#|
#|def build_parser():
#|    parser = base_v4_test.build_parser()
#|    parser.add_argument("--alignment_decay_start", type=float, default=0.67)
#|    parser.add_argument(
#|        "--alignment_final_nce_weight",
#|        type=float,
#|        default=0.05,
#|    )
#|    parser.add_argument(
#|        "--same_group_negative_scale",
#|        type=float,
#|        default=0.0,
#|    )
#|    return parser
#|
#|
#|def main() -> None:
#|    args = build_parser().parse_args()
#|    if args.num_tokens != 0:
#|        raise ValueError("RGC-SemanticReadout-v5 forbids prompt tokens")
#|    if args.output_tag is None:
#|        args.output_tag = (
#|            f"llava_claim_rgc_semantic_readout_v5_epoch{args.epoch}"
#|        )
#|    base_v4_test.base_test.make_semantic_readout_classes = (
#|        make_v5_readout_classes
#|    )
#|    base_v4_test.base_test.config_from_args = config_from_args
#|    base_v4_test.base_test.DEFAULT_CKPT_NAME = DEFAULT_CKPT_NAME
#|    base_v4_test.base_test.PROJECTOR_SUFFIX = PROJECTOR_SUFFIX
#|    base_v4_test.base_test.run_inference(args)
#|
#|
#|if __name__ == "__main__":
#|    main()
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: test_llava_claim_rgc_semantic_readout_stage_6.py ===
#|"""Inference for adaptive soft-negative PBFA-RGSR v6."""
#|
#|from __future__ import annotations
#|
#|import os
#|
#|
#|DEFAULT_CKPT_NAME = "checkpoints_llava_claim_rgc_semantic_readout_v6"
#|PROJECTOR_SUFFIX = "_claim_rgc_semantic_readout_v6"
#|_TARGET_CKPT_NAME = os.environ.get("RGC_SR_V6_CKPT_NAME", DEFAULT_CKPT_NAME)
#|_TARGET_PROJECTOR_SUFFIX = os.environ.get(
#|    "RGC_SR_V6_PROJECTOR_SUFFIX", PROJECTOR_SUFFIX
#|)
#|for _name in (
#|    "RGC_SR_V5_CKPT_NAME",
#|    "RGC_SR_V4_CKPT_NAME",
#|    "RGC_SR_CKPT_NAME",
#|    "PAPER2_CKPT_NAME",
#|    "PAPER2_DEFAULT_CKPT_NAME",
#|):
#|    os.environ[_name] = _TARGET_CKPT_NAME
#|for _name in (
#|    "RGC_SR_V5_PROJECTOR_SUFFIX",
#|    "RGC_SR_V4_PROJECTOR_SUFFIX",
#|    "RGC_SR_PROJECTOR_SUFFIX",
#|    "PAPER2_PROJECTOR_SUFFIX",
#|):
#|    os.environ[_name] = _TARGET_PROJECTOR_SUFFIX
#|
#|import test_llava_claim_rgc_semantic_readout_stage_5 as base_v5_test  # noqa: E402
#|from rgc_semantic_readout_stage_6 import make_v6_readout_classes  # noqa: E402
#|from train_llava_claim_rgc_semantic_readout_stage_6 import (  # noqa: E402
#|    config_from_args,
#|)
#|
#|
#|def build_parser():
#|    parser = base_v5_test.build_parser()
#|    parser.add_argument("--soft_negative_mad_floor", type=float, default=0.03)
#|    parser.add_argument(
#|        "--soft_negative_min_weight", type=float, default=1e-4
#|    )
#|    parser.add_argument("--tail_error_ema", type=float, default=0.95)
#|    parser.add_argument(
#|        "--tail_error_scale_floor", type=float, default=0.02
#|    )
#|    parser.add_argument("--tail_weight_floor", type=float, default=0.75)
#|    parser.add_argument("--tail_weight_cap", type=float, default=1.25)
#|    return parser
#|
#|
#|def main() -> None:
#|    args = build_parser().parse_args()
#|    if args.num_tokens != 0:
#|        raise ValueError("PBFA-RGSR-v6 forbids graph prompt tokens")
#|    if args.output_tag is None:
#|        args.output_tag = f"llava_claim_rgc_semantic_readout_v6_epoch{args.epoch}"
#|    base_v5_test.base_v4_test.base_test.make_semantic_readout_classes = (
#|        make_v6_readout_classes
#|    )
#|    base_v5_test.base_v4_test.base_test.config_from_args = config_from_args
#|    base_v5_test.base_v4_test.base_test.DEFAULT_CKPT_NAME = _TARGET_CKPT_NAME
#|    base_v5_test.base_v4_test.base_test.PROJECTOR_SUFFIX = (
#|        _TARGET_PROJECTOR_SUFFIX
#|    )
#|    base_v5_test.base_v4_test.base_test.run_inference(args)
#|
#|
#|if __name__ == "__main__":
#|    main()
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: test_llava_claim_rgc_semantic_readout_stage_7.py ===
#|"""Inference for decoder-grounded PBFA-RGSR v7."""
#|
#|from __future__ import annotations
#|
#|import os
#|
#|
#|DEFAULT_CKPT_NAME = "checkpoints_llava_claim_rgc_semantic_readout_v7"
#|PROJECTOR_SUFFIX = "_claim_rgc_semantic_readout_v7"
#|_TARGET_CKPT_NAME = os.environ.get("RGC_SR_V7_CKPT_NAME", DEFAULT_CKPT_NAME)
#|_TARGET_PROJECTOR_SUFFIX = os.environ.get(
#|    "RGC_SR_V7_PROJECTOR_SUFFIX", PROJECTOR_SUFFIX
#|)
#|for _name in (
#|    "RGC_SR_V6_CKPT_NAME",
#|    "RGC_SR_V5_CKPT_NAME",
#|    "RGC_SR_V4_CKPT_NAME",
#|    "RGC_SR_CKPT_NAME",
#|    "PAPER2_CKPT_NAME",
#|    "PAPER2_DEFAULT_CKPT_NAME",
#|):
#|    os.environ[_name] = _TARGET_CKPT_NAME
#|for _name in (
#|    "RGC_SR_V6_PROJECTOR_SUFFIX",
#|    "RGC_SR_V5_PROJECTOR_SUFFIX",
#|    "RGC_SR_V4_PROJECTOR_SUFFIX",
#|    "RGC_SR_PROJECTOR_SUFFIX",
#|    "PAPER2_PROJECTOR_SUFFIX",
#|):
#|    os.environ[_name] = _TARGET_PROJECTOR_SUFFIX
#|
#|import test_llava_claim_rgc_semantic_readout_stage_6 as base_v6_test  # noqa: E402
#|from rgc_semantic_readout_stage_7 import make_v7_readout_classes  # noqa: E402
#|from train_llava_claim_rgc_semantic_readout_stage_7 import (  # noqa: E402
#|    config_from_args,
#|)
#|
#|
#|def build_parser():
#|    parser = base_v6_test.build_parser()
#|    parser.add_argument("--decoder_alignment_dim", type=int, default=256)
#|    parser.add_argument("--decoder_alignment_weight", type=float, default=0.02)
#|    parser.add_argument(
#|        "--decoder_alignment_temperature", type=float, default=0.08
#|    )
#|    parser.add_argument("--decoder_alignment_ema", type=float, default=0.95)
#|    parser.add_argument(
#|        "--decoder_min_explanation_tokens", type=int, default=4
#|    )
#|    return parser
#|
#|
#|def main() -> None:
#|    args = build_parser().parse_args()
#|    if args.num_tokens != 0:
#|        raise ValueError("PBFA-RGSR-v7 forbids graph prompt tokens")
#|    if args.output_tag is None:
#|        args.output_tag = f"llava_claim_rgc_semantic_readout_v7_epoch{args.epoch}"
#|    base_test = base_v6_test.base_v5_test.base_v4_test.base_test
#|    base_test.make_semantic_readout_classes = make_v7_readout_classes
#|    base_test.config_from_args = config_from_args
#|    base_test.DEFAULT_CKPT_NAME = _TARGET_CKPT_NAME
#|    base_test.PROJECTOR_SUFFIX = _TARGET_PROJECTOR_SUFFIX
#|    base_test.run_inference(args)
#|
#|
#|if __name__ == "__main__":
#|    main()
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: test_llava_claim_rgc_semantic_readout_stage_8.py ===
#|"""Inference for reliability-trust PBFA-RGSR v8."""
#|
#|from __future__ import annotations
#|
#|import os
#|
#|
#|DEFAULT_CKPT_NAME = "checkpoints_llava_claim_rgc_semantic_readout_v8"
#|PROJECTOR_SUFFIX = "_claim_rgc_semantic_readout_v8"
#|_TARGET_CKPT_NAME = os.environ.get("RGC_SR_V8_CKPT_NAME", DEFAULT_CKPT_NAME)
#|_TARGET_PROJECTOR_SUFFIX = os.environ.get(
#|    "RGC_SR_V8_PROJECTOR_SUFFIX", PROJECTOR_SUFFIX
#|)
#|for _name in (
#|    "RGC_SR_V7_CKPT_NAME",
#|    "RGC_SR_V6_CKPT_NAME",
#|    "RGC_SR_V5_CKPT_NAME",
#|    "RGC_SR_V4_CKPT_NAME",
#|    "RGC_SR_CKPT_NAME",
#|    "PAPER2_CKPT_NAME",
#|    "PAPER2_DEFAULT_CKPT_NAME",
#|):
#|    os.environ[_name] = _TARGET_CKPT_NAME
#|for _name in (
#|    "RGC_SR_V7_PROJECTOR_SUFFIX",
#|    "RGC_SR_V6_PROJECTOR_SUFFIX",
#|    "RGC_SR_V5_PROJECTOR_SUFFIX",
#|    "RGC_SR_V4_PROJECTOR_SUFFIX",
#|    "RGC_SR_PROJECTOR_SUFFIX",
#|    "PAPER2_PROJECTOR_SUFFIX",
#|):
#|    os.environ[_name] = _TARGET_PROJECTOR_SUFFIX
#|
#|import test_llava_claim_rgc_semantic_readout_stage_7 as base_v7_test  # noqa: E402
#|from rgc_semantic_readout_stage_8 import make_v8_readout_classes  # noqa: E402
#|from train_llava_claim_rgc_semantic_readout_stage_8 import (  # noqa: E402
#|    config_from_args,
#|)
#|
#|
#|def build_parser():
#|    parser = base_v7_test.build_parser()
#|    parser.set_defaults(decoder_alignment_weight=0.015)
#|    parser.add_argument("--reliability_temperature", type=float, default=1.0)
#|    parser.add_argument(
#|        "--reliability_absolute_temperature", type=float, default=0.10
#|    )
#|    parser.add_argument(
#|        "--reliability_deviation_floor", type=float, default=0.05
#|    )
#|    parser.add_argument("--trust_radius", type=float, default=5e-4)
#|    parser.add_argument("--trust_dual_lr", type=float, default=0.02)
#|    parser.add_argument(
#|        "--trust_augmented_weight", type=float, default=0.01
#|    )
#|    parser.add_argument("--trust_dual_cap", type=float, default=0.10)
#|    return parser
#|
#|
#|def main() -> None:
#|    args = build_parser().parse_args()
#|    if args.num_tokens != 0:
#|        raise ValueError("PBFA-RGSR-v8 forbids graph prompt tokens")
#|    if args.output_tag is None:
#|        args.output_tag = (
#|            "llava_claim_rgc_semantic_readout_v8_no_test_phenomenon_"
#|            f"epoch{args.epoch}"
#|        )
#|    base_test = (
#|        base_v7_test.base_v6_test.base_v5_test.base_v4_test.base_test
#|    )
#|    base_test.make_semantic_readout_classes = make_v8_readout_classes
#|    base_test.config_from_args = config_from_args
#|    base_test.DEFAULT_CKPT_NAME = _TARGET_CKPT_NAME
#|    base_test.PROJECTOR_SUFFIX = _TARGET_PROJECTOR_SUFFIX
#|    base_test.run_inference(args)
#|
#|
#|if __name__ == "__main__":
#|    main()
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: train_llava_claim_dome_ft.py ===
#|"""DOME-FT: decision-locked fine-tuning on on-policy mechanism errors.
#|
#|The inherited innovation-1 condition path is byte-frozen.  DOME itself reads
#|only raw training conversations, sampled policy explanations, and optional
#|audited repairs.  It updates a small, fixed subset of upper-layer LoRA-B
#|tensors and uses separate verdict-prefix and explanation-only objectives.
#|"""
#|
#|from __future__ import annotations
#|
#|import argparse
#|import json
#|import math
#|import os
#|import random
#|import re
#|from pathlib import Path
#|
#|
#|DEFAULT_CKPT_NAME = "checkpoints_llava_claim_dome_ft_v1"
#|PROJECTOR_SUFFIX = "_claim_dome_ft_v1"
#|SOURCE_CKPT_NAME = "checkpoints_llava_claim_rgc_semantic_readout_v8"
#|_TARGET_CKPT_NAME = os.environ.get("DOME_FT_CKPT_NAME", DEFAULT_CKPT_NAME)
#|_TARGET_PROJECTOR_SUFFIX = os.environ.get(
#|    "DOME_FT_PROJECTOR_SUFFIX", PROJECTOR_SUFFIX
#|)
#|for _name in (
#|    "RGC_SR_V8_CKPT_NAME", "RGC_SR_V7_CKPT_NAME", "RGC_SR_V6_CKPT_NAME",
#|    "RGC_SR_V5_CKPT_NAME", "RGC_SR_V4_CKPT_NAME", "RGC_SR_CKPT_NAME",
#|    "PAPER2_CKPT_NAME", "PAPER2_DEFAULT_CKPT_NAME",
#|):
#|    os.environ[_name] = _TARGET_CKPT_NAME
#|for _name in (
#|    "RGC_SR_V8_PROJECTOR_SUFFIX", "RGC_SR_V7_PROJECTOR_SUFFIX",
#|    "RGC_SR_V6_PROJECTOR_SUFFIX", "RGC_SR_V5_PROJECTOR_SUFFIX",
#|    "RGC_SR_V4_PROJECTOR_SUFFIX", "RGC_SR_PROJECTOR_SUFFIX",
#|    "PAPER2_PROJECTOR_SUFFIX",
#|):
#|    os.environ[_name] = _TARGET_PROJECTOR_SUFFIX
#|
#|from dome_ft_data import answer_from_sample, build_dome_pairs
#|from g_mipo_loss import mutual_information_preference_loss
#|from rgc_semantic_readout import attach_semantic_readout
#|from rgc_semantic_readout_stage_4 import PHENOMENON_GROUPS
#|import train_llava_claim_rgc_semantic_readout_stage_8 as v8
#|
#|
#|base_v4 = v8.base_v4
#|graph_train = base_v4.base_train.graph_train
#|
#|
#|LAYER_RE = re.compile(r"\.layers\.(\d+)\.")
#|
#|
#|def parse_int_set(value: str) -> set[int]:
#|    try:
#|        output = {int(item.strip()) for item in value.split(",") if item.strip()}
#|    except ValueError as error:
#|        raise ValueError("train_layer_indices must be comma-separated integers") from error
#|    if not output:
#|        raise ValueError("train_layer_indices cannot be empty")
#|    return output
#|
#|
#|def parse_modules(value: str) -> tuple[str, ...]:
#|    modules = tuple(item.strip() for item in value.split(",") if item.strip())
#|    if not modules:
#|        raise ValueError("train_modules cannot be empty")
#|    return modules
#|
#|
#|def install_dome_label_masks(module):
#|    """Add exact decision/explanation supervision masks to the inherited data."""
#|
#|    BaseDataset = module.HybridDataset
#|    original_collate = module.collate_fn
#|    torch = module.torch
#|    ignore_index = module.IGNORE_INDEX
#|
#|    class DOMEDataset(BaseDataset):
#|        def __getitem__(self, index):
#|            item = super().__getitem__(index)
#|            labels = item["labels"]
#|            supervised = labels.ne(ignore_index).nonzero(as_tuple=False).flatten()
#|            if supervised.numel() < 2:
#|                raise RuntimeError(
#|                    f"DOME recovered fewer than two answer tokens for id={self.samples[index].get('id')}"
#|                )
#|            answer = answer_from_sample(self.samples[index])
#|            prefix = answer.split(".", 1)[0].strip() + "."
#|            prefix_ids = self.tokenizer(
#|                prefix, add_special_tokens=False
#|            )["input_ids"]
#|            verdict_width = max(1, min(len(prefix_ids), int(supervised.numel()) - 1))
#|            verdict_positions = supervised[:verdict_width]
#|            decision = torch.full_like(labels, ignore_index)
#|            decision[verdict_positions] = labels[verdict_positions]
#|            explanation = labels.clone()
#|            explanation[verdict_positions] = ignore_index
#|            if not bool(explanation.ne(ignore_index).any()):
#|                raise RuntimeError(
#|                    f"DOME explanation mask is empty for id={self.samples[index].get('id')}"
#|                )
#|            item["decision_labels"] = decision
#|            item["explanation_labels"] = explanation
#|            item["dome_verdict_width"] = verdict_width
#|            return item
#|
#|    def dome_collate(batch):
#|        output = original_collate(batch)
#|        for name in ("decision_labels", "explanation_labels"):
#|            values = torch.nn.utils.rnn.pad_sequence(
#|                [item[name] for item in batch],
#|                batch_first=True,
#|                padding_value=ignore_index,
#|            )
#|            output[name] = values[:, :2048]
#|        output["dome_verdict_width"] = torch.tensor(
#|            [item["dome_verdict_width"] for item in batch], dtype=torch.long
#|        )
#|        return output
#|
#|    module.HybridDataset = DOMEDataset
#|    module.collate_fn = dome_collate
#|    return module
#|
#|
#|def initialize_from_innovation1(model, module, paths, args, counts) -> None:
#|    from peft import PeftModel
#|
#|    source_root = Path(args.source_ckpt_root)
#|    if not source_root.is_absolute():
#|        source_root = paths.output_root / source_root
#|    source_lora = source_root / (
#|        f"lora_epoch_{args.source_epoch}{args.source_projector_suffix}"
#|    )
#|    source_projector = source_root / (
#|        f"proj_epoch_{args.source_epoch}{args.source_projector_suffix}.pth"
#|    )
#|    if not source_lora.is_dir() or not source_projector.is_file():
#|        raise FileNotFoundError(
#|            f"missing innovation-1 source: {source_lora}, {source_projector}"
#|        )
#|    base_model = (
#|        model.llm.base_model.model if hasattr(model.llm, "base_model") else model.llm
#|    )
#|    model.llm = PeftModel.from_pretrained(
#|        base_model, str(source_lora), is_trainable=True
#|    )
#|    embedding_device = model.llm.get_input_embeddings().weight.device
#|    requested_device = module.torch.device(args.device)
#|    if requested_device.type == "cuda":
#|        requested_index = (
#|            module.torch.cuda.current_device()
#|            if requested_device.index is None
#|            else requested_device.index
#|        )
#|        if (
#|            embedding_device.type != "cuda"
#|            or embedding_device.index != requested_index
#|        ):
#|            raise RuntimeError(
#|                "DOME PEFT/device-map mismatch: "
#|                f"embedding={embedding_device}, requested={requested_device}"
#|            )
#|    elif embedding_device.type != requested_device.type:
#|        raise RuntimeError(
#|            "DOME PEFT/device mismatch: "
#|            f"embedding={embedding_device}, requested={requested_device}"
#|        )
#|    if hasattr(model.llm, "enable_input_require_grads"):
#|        model.llm.enable_input_require_grads()
#|    model.llm.config.use_cache = False
#|    state = module.torch.load(source_projector, map_location=args.device)
#|    incompatible = model.projector.load_state_dict(state, strict=True)
#|    if incompatible.missing_keys or incompatible.unexpected_keys:
#|        raise RuntimeError("innovation-1/DOME projector contract mismatch")
#|    for parameter in model.parameters():
#|        parameter.requires_grad = False
#|    layers = parse_int_set(args.train_layer_indices)
#|    modules = parse_modules(args.train_modules)
#|    available_layers: set[int] = set()
#|    trainable_names: list[str] = []
#|    with module.torch.no_grad():
#|        for name, parameter in model.llm.named_parameters():
#|            match = LAYER_RE.search(name)
#|            if match and "lora_" in name:
#|                available_layers.add(int(match.group(1)))
#|            selected = bool(
#|                match
#|                and int(match.group(1)) in layers
#|                and "lora_B" in name
#|                and any(f".{target}." in name for target in modules)
#|            )
#|            parameter.requires_grad = selected
#|            if selected:
#|                if parameter.dtype != module.torch.float32:
#|                    parameter.data = parameter.data.float()
#|                trainable_names.append(name)
#|    unavailable = layers - available_layers
#|    if unavailable or not trainable_names:
#|        raise RuntimeError(
#|            f"DOME unavailable layers={sorted(unavailable)} trainable={len(trainable_names)}"
#|        )
#|    for parameter in model.projector.parameters():
#|        parameter.requires_grad = False
#|    if hasattr(model.projector, "training_graph_dropout"):
#|        model.projector.training_graph_dropout = False
#|    if hasattr(model.projector, "set_training_progress"):
#|        model.projector.set_training_progress(1.0)
#|    model.projector.set_group_priors([counts[name] for name in PHENOMENON_GROUPS])
#|    norm_name = attach_semantic_readout(model.llm, model.projector)
#|    model.projector.set_trust_reference()
#|
#|    def clear_frozen_projector_pending_state():
#|        with module.torch.no_grad():
#|            for name in (
#|                "_dro_pending_loss", "_dro_pending_count", "_trust_pending_constraint"
#|            ):
#|                value = getattr(model.projector, name, None)
#|                if value is not None:
#|                    value.zero_()
#|
#|    model.projector.on_optimizer_step = clear_frozen_projector_pending_state
#|    model.dome_trainable_names = tuple(trainable_names)
#|    model.dome_source_parameters = {
#|        name: parameter.detach().clone()
#|        for name, parameter in model.llm.named_parameters()
#|        if parameter.requires_grad
#|    }
#|    model.dome_source_projector = {
#|        key: value.detach().cpu().clone()
#|        for key, value in model.projector.state_dict().items()
#|    }
#|    model.dome_source_paths = (source_lora, source_projector)
#|    print(f"[dome-ft] source LoRA:      {source_lora}")
#|    print(f"[dome-ft] source projector: {source_projector}")
#|    print(
#|        f"[dome-ft] layers={sorted(layers)} modules={modules} "
#|        f"trainable_groups={len(trainable_names)} "
#|        f"trainable={sum(p.numel() for p in model.parameters() if p.requires_grad):,} "
#|        f"final_norm={norm_name} inference_path=v8-one-pass"
#|    )
#|
#|
#|class PairedPreferenceSet:
#|    def __init__(self, chosen_set, rejected_set):
#|        if len(chosen_set) != len(rejected_set):
#|            raise ValueError("DOME chosen and rejected sets must have equal length")
#|        if len(chosen_set) <= 0:
#|            raise ValueError("DOME paired set is empty")
#|        self.chosen_set = chosen_set
#|        self.rejected_set = rejected_set
#|
#|    def __len__(self):
#|        return len(self.chosen_set)
#|
#|    def __getitem__(self, index):
#|        chosen = self.chosen_set[index]
#|        rejected = self.rejected_set[index]
#|        return {"chosen": chosen, "rejected": rejected}
#|
#|
#|def make_pair_collate(module):
#|    def collate(rows):
#|        return {
#|            "chosen": module.collate_fn([row["chosen"] for row in rows]),
#|            "rejected": module.collate_fn([row["rejected"] for row in rows]),
#|        }
#|    return collate
#|
#|
#|def move_images(images, device, torch):
#|    if isinstance(images, list):
#|        return [image.to(device, dtype=torch.bfloat16) for image in images]
#|    return images.to(device, dtype=torch.bfloat16)
#|
#|
#|def forward_loss(model, batch, labels_name, device, torch):
#|    _total, lm_loss, _contrastive = model(
#|        move_images(batch["images"], device, torch),
#|        batch["image_sizes"],
#|        batch["e_img"].to(device),
#|        batch["e_txt"].to(device),
#|        batch["e_desc"].to(device),
#|        batch["graph_feature"].to(device),
#|        batch["ids"].to(device),
#|        batch["mask"].to(device),
#|        batch[labels_name].to(device),
#|        batch["cf"].to(device),
#|        graph_semantic_ids=batch["graph_semantic_ids"].to(device),
#|        graph_semantic_mask=batch["graph_semantic_mask"].to(device),
#|        phenomenon_group=batch["phenomenon_group"].to(device),
#|    )
#|    return lm_loss
#|
#|
#|def proximal_loss(model, torch):
#|    values = []
#|    for name, parameter in model.llm.named_parameters():
#|        reference = model.dome_source_parameters.get(name)
#|        if reference is not None:
#|            values.append((parameter.float() - reference.float()).square().mean())
#|    if not values:
#|        raise RuntimeError("DOME proximal loss found no selected parameters")
#|    return torch.stack(values).mean()
#|
#|
#|def verify_projector_frozen(model) -> None:
#|    current = model.projector.state_dict()
#|    changed = [
#|        key
#|        for key, source in model.dome_source_projector.items()
#|        if key not in current or not current[key].detach().cpu().equal(source)
#|    ]
#|    if changed:
#|        raise RuntimeError(f"DOME inherited projector changed: {changed[:8]}")
#|
#|
#|def train(args: argparse.Namespace) -> None:
#|    paths = graph_train.Paper2Paths.from_env()
#|    paths.ensure_output_dirs()
#|    print(graph_train.describe_paths(paths))
#|    source_condition_cache = paths.resolve_output_path(args.source_condition_cache)
#|    graph_train.require_concept_graph_cache(source_condition_cache, split="train")
#|    candidate_path = paths.resolve_output_path(args.candidates_jsonl)
#|    if not candidate_path.is_file():
#|        raise FileNotFoundError(f"missing DOME candidates: {candidate_path}")
#|    repairs_path = (
#|        paths.resolve_output_path(args.repairs_jsonl)
#|        if args.repairs_jsonl
#|        else None
#|    )
#|    pair_dir = paths.resolve_output_path(args.pair_cache_dir)
#|    chosen_json, rejected_json, audit_path = build_dome_pairs(
#|        paths.train_json,
#|        candidate_path,
#|        pair_dir,
#|        repairs_jsonl=repairs_path,
#|        minimum_words=args.minimum_words,
#|        minimum_similarity=args.minimum_similarity,
#|        maximum_similarity=args.maximum_similarity,
#|        minimum_length_ratio=args.minimum_length_ratio,
#|        maximum_length_ratio=args.maximum_length_ratio,
#|        minimum_pairs=args.minimum_pairs,
#|    )
#|    with audit_path.open("r", encoding="utf-8") as handle:
#|        audit = json.load(handle)
#|    print(
#|        f"[dome-ft] pair audit: valid={audit['valid_pairs']} "
#|        f"coverage={audit['coverage']:.2%} path={audit_path}"
#|    )
#|
#|    os.chdir(paths.orig_root)
#|    base_v4.base_train.make_semantic_readout_classes = v8.make_v8_readout_classes
#|    base_v4.base_train.config_from_args = v8.config_from_args
#|    _, counts = base_v4.load_phenomenon_groups(source_condition_cache)
#|    module = base_v4.install_v4_training(
#|        graph_train.load_original_train_module(paths),
#|        source_condition_cache,
#|        args=args,
#|    )
#|    module = install_dome_label_masks(module)
#|    torch = module.torch
#|    random.seed(args.seed)
#|    torch.manual_seed(args.seed)
#|    if torch.cuda.is_available():
#|        torch.cuda.manual_seed_all(args.seed)
#|    model = module.Hybrid_MoE_LLaVA(
#|        paths.llm_path, num_tokens=args.num_tokens
#|    ).to(args.device)
#|    initialize_from_innovation1(model, module, paths, args, counts)
#|    chosen_set = module.HybridDataset(
#|        str(paths.train_features),
#|        str(chosen_json),
#|        model.tokenizer,
#|        model.image_processor,
#|        model_max_length=args.model_max_length,
#|    )
#|    rejected_set = module.HybridDataset(
#|        str(paths.train_features),
#|        str(rejected_json),
#|        model.tokenizer,
#|        model.image_processor,
#|        model_max_length=args.model_max_length,
#|    )
#|    paired_set = PairedPreferenceSet(chosen_set, rejected_set)
#|    trainable = [parameter for parameter in model.parameters() if parameter.requires_grad]
#|    optimizer = torch.optim.AdamW(
#|        trainable, lr=args.llm_lr, weight_decay=args.weight_decay
#|    )
#|    updates_per_epoch = math.ceil(len(paired_set) / max(1, args.accum_steps))
#|    total_updates = max(1, updates_per_epoch * args.epochs)
#|    scheduler = module.get_cosine_schedule_with_warmup(
#|        optimizer,
#|        num_warmup_steps=int(total_updates * args.warmup_ratio),
#|        num_training_steps=total_updates,
#|    )
#|    checkpoint_dir = paths.checkpoint_dir
#|    checkpoint_dir.mkdir(parents=True, exist_ok=True)
#|    optimizer.zero_grad(set_to_none=True)
#|    optimizer_updates = 0
#|    for epoch in range(args.epochs):
#|        generator = torch.Generator()
#|        generator.manual_seed(args.seed + epoch)
#|        loader = module.DataLoader(
#|            paired_set,
#|            batch_size=args.batch_size,
#|            shuffle=True,
#|            collate_fn=make_pair_collate(module),
#|            num_workers=args.num_workers,
#|            pin_memory=True,
#|            generator=generator,
#|        )
#|        model.train()
#|        model.projector.eval()
#|        # V7/V8 captures the final decoder hidden state only while the
#|        # semantic readout is in training mode.  Keep the frozen controller
#|        # deterministic/eval, but enable this state-capture hook; all of its
#|        # parameters remain requires_grad=False and DOME returns only lm_loss.
#|        model.projector.semantic_readout.train()
#|        progress = module.tqdm(loader, desc=f"DOME-FT Epoch {epoch + 1}/{args.epochs}")
#|        nan_count = 0
#|        for step, pair in enumerate(progress):
#|            chosen_explanation = forward_loss(
#|                model, pair["chosen"], "explanation_labels", args.device, torch
#|            )
#|            rejected_explanation = forward_loss(
#|                model, pair["rejected"], "explanation_labels", args.device, torch
#|            )
#|            decision = forward_loss(
#|                model, pair["chosen"], "decision_labels", args.device, torch
#|            )
#|            preference = mutual_information_preference_loss(
#|                -chosen_explanation,
#|                -rejected_explanation,
#|                beta=args.preference_beta,
#|                margin=args.preference_margin,
#|                reference_free=True,
#|            )
#|            proximal = proximal_loss(model, torch)
#|            loss = (
#|                args.explanation_sft_weight * chosen_explanation
#|                + args.preference_weight * preference
#|                + args.decision_weight * decision
#|                + args.proximal_weight * proximal
#|            )
#|            if not bool(torch.isfinite(loss)):
#|                nan_count += 1
#|                optimizer.zero_grad(set_to_none=True)
#|                continue
#|            (loss / args.accum_steps).backward()
#|            boundary = (step + 1) % args.accum_steps == 0 or step + 1 == len(loader)
#|            if boundary:
#|                finite = all(
#|                    parameter.grad is None or bool(torch.isfinite(parameter.grad).all())
#|                    for parameter in trainable
#|                )
#|                if not finite:
#|                    nan_count += 1
#|                    optimizer.zero_grad(set_to_none=True)
#|                    continue
#|                torch.nn.utils.clip_grad_norm_(trainable, args.grad_clip)
#|                optimizer.step()
#|                scheduler.step()
#|                optimizer.zero_grad(set_to_none=True)
#|                optimizer_updates += 1
#|            progress.set_postfix(
#|                {
#|                    "SFT": f"{chosen_explanation.item():.3f}",
#|                    "PREF": f"{preference.item():.3f}",
#|                    "GAP": f"{(rejected_explanation - chosen_explanation).item():+.3f}",
#|                    "Y": f"{decision.item():.3f}",
#|                    "L2": f"{proximal.item():.2e}",
#|                    "UPD": optimizer_updates,
#|                    "NaN": nan_count,
#|                }
#|            )
#|        verify_projector_frozen(model)
#|        lora_path = checkpoint_dir / (
#|            f"lora_epoch_{epoch + 1}{_TARGET_PROJECTOR_SUFFIX}"
#|        )
#|        projector_path = checkpoint_dir / (
#|            f"proj_epoch_{epoch + 1}{_TARGET_PROJECTOR_SUFFIX}.pth"
#|        )
#|        model.llm.save_pretrained(str(lora_path))
#|        torch.save(model.projector.state_dict(), projector_path)
#|        metadata = {
#|            "method": "DOME-FT-v1",
#|            "epoch": epoch + 1,
#|            "optimizer_updates": optimizer_updates,
#|            "valid_pairs": len(paired_set),
#|            "pair_audit": str(audit_path),
#|            "trainable_names": list(model.dome_trainable_names),
#|            "source_lora": str(model.dome_source_paths[0]),
#|            "source_projector": str(model.dome_source_paths[1]),
#|            "projector_frozen_verified": True,
#|            "test_annotations_accessed": False,
#|        }
#|        with (checkpoint_dir / f"dome_epoch_{epoch + 1}_metadata.json").open(
#|            "w", encoding="utf-8"
#|        ) as handle:
#|            json.dump(metadata, handle, ensure_ascii=False, indent=2)
#|        print(
#|            f"[dome-ft] epoch={epoch + 1} updates={optimizer_updates} "
#|            f"nan_count={nan_count} saved={lora_path}"
#|        )
#|
#|
#|def build_parser() -> argparse.ArgumentParser:
#|    parser = v8.build_parser()
#|    parser.set_defaults(
#|        source_ckpt_root=SOURCE_CKPT_NAME,
#|        source_epoch=1,
#|        source_projector_suffix="_claim_rgc_semantic_readout_v8",
#|        epochs=1,
#|        batch_size=1,
#|        accum_steps=16,
#|        num_tokens=0,
#|        warmup_ratio=0.03,
#|        projector_lr=0.0,
#|        llm_lr=5e-6,
#|        graph_dropout=0.0,
#|        semantic_loss_weight=0.0,
#|        cf_loss_weight=0.0,
#|        alignment_nce_weight=0.0,
#|        alignment_final_nce_weight=0.0,
#|        # Keep the inherited clean-v8 architecture contract valid.  DOME's
#|        # forward_loss returns only lm_loss, so this structural value does not
#|        # add the decoder-alignment auxiliary objective to DOME optimization.
#|        decoder_alignment_weight=0.015,
#|    )
#|    parser.add_argument("--source_condition_cache", required=True)
#|    parser.add_argument("--candidates_jsonl", required=True)
#|    parser.add_argument("--repairs_jsonl", default=None)
#|    parser.add_argument("--pair_cache_dir", default="cache/dome_ft_v1")
#|    parser.add_argument("--minimum_pairs", type=int, default=256)
#|    parser.add_argument("--minimum_words", type=int, default=12)
#|    parser.add_argument("--minimum_similarity", type=float, default=0.28)
#|    parser.add_argument("--maximum_similarity", type=float, default=0.78)
#|    parser.add_argument("--minimum_length_ratio", type=float, default=0.55)
#|    parser.add_argument("--maximum_length_ratio", type=float, default=1.65)
#|    parser.add_argument("--model_max_length", type=int, default=2048)
#|    parser.add_argument("--weight_decay", type=float, default=0.0)
#|    parser.add_argument("--train_layer_indices", default="20,24,28,31")
#|    parser.add_argument("--train_modules", default="o_proj,down_proj")
#|    parser.add_argument("--explanation_sft_weight", type=float, default=1.0)
#|    parser.add_argument("--preference_weight", type=float, default=0.05)
#|    parser.add_argument("--preference_beta", type=float, default=0.05)
#|    parser.add_argument("--preference_margin", type=float, default=0.0)
#|    parser.add_argument("--decision_weight", type=float, default=0.50)
#|    parser.add_argument("--proximal_weight", type=float, default=0.001)
#|    parser.add_argument("--grad_clip", type=float, default=1.0)
#|    return parser
#|
#|
#|if __name__ == "__main__":
#|    arguments = build_parser().parse_args()
#|    if arguments.num_tokens != 0:
#|        raise ValueError("DOME-FT requires the token-free v8 inference path")
#|    if arguments.batch_size != 1:
#|        raise ValueError("DOME-FT v1 requires batch_size=1 for paired objectives")
#|    train(arguments)
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: train_llava_claim_graphprompt.py ===
#|"""Train innovation-1 on the original LLaVA+Claim baseline.
#|
#|This script keeps the data flow from ``train_moe_创新点1.py``: image, claim
#|conversation, and precomputed claim/image/description features. It replaces
#|the original MoE projector with the paper-2 concept graph prompt projector and
#|does not use FLUTE/RAG resources.
#|"""
#|
#|from __future__ import annotations
#|
#|import argparse
#|import importlib.util
#|import math
#|import os
#|import random
#|import sys
#|from pathlib import Path
#|
#|from concept_graph_integration import (
#|    GRAPH_FEATURE_DIM,
#|    require_concept_graph_cache,
#|)
#|from paths_paper2 import Paper2Paths, describe_paths
#|
#|
#|def _missing_optional_loss(module_name: str, import_error: Exception):
#|    def missing(*args, **kwargs):
#|        del args, kwargs
#|        raise ModuleNotFoundError(
#|            f"{module_name} is required only when its optional loss is enabled"
#|        ) from import_error
#|
#|    return missing
#|
#|
#|try:
#|    from tspib_stage_6_losses import masked_teacher_kl
#|except ModuleNotFoundError as error:
#|    masked_teacher_kl = _missing_optional_loss("tspib_stage_6_losses", error)
#|
#|try:
#|    from tspib_v7_losses import (
#|        build_multigranular_semantic_targets,
#|        multigranular_semantic_loss,
#|    )
#|except ModuleNotFoundError as error:
#|    build_multigranular_semantic_targets = _missing_optional_loss(
#|        "tspib_v7_losses",
#|        error,
#|    )
#|    multigranular_semantic_loss = _missing_optional_loss(
#|        "tspib_v7_losses",
#|        error,
#|    )
#|
#|try:
#|    from tspib_v8_losses import masked_teacher_advantage_loss
#|except ModuleNotFoundError as error:
#|    masked_teacher_advantage_loss = _missing_optional_loss("tspib_v8_losses", error)
#|
#|
#|BASE_TRAIN_SCRIPT = "train_moe_创新点1.py"
#|DEFAULT_CKPT_NAME = os.environ.get(
#|    "PAPER2_DEFAULT_CKPT_NAME",
#|    "checkpoints_llava_claim_filtered_gptgraph_v10",
#|)
#|PROJECTOR_SUFFIX = os.environ.get("PAPER2_PROJECTOR_SUFFIX", "_claim_filtered_gptgraph_v10")
#|
#|
#|def apply_graph_feature_dropout(graph_feature, dropout: float, training: bool):
#|    """Drop complete graph evidence vectors without rescaling retained features."""
#|
#|    if not 0.0 <= dropout <= 1.0:
#|        raise ValueError(f"graph dropout must be in [0, 1], got {dropout}")
#|    if not training or dropout == 0.0:
#|        return graph_feature
#|    if dropout == 1.0:
#|        return graph_feature.new_zeros(graph_feature.shape)
#|
#|    import torch
#|
#|    keep_mask = torch.rand(
#|        (graph_feature.size(0), 1),
#|        device=graph_feature.device,
#|    ) >= dropout
#|    return graph_feature * keep_mask.to(graph_feature.dtype)
#|
#|
#|def load_original_train_module(paths: Paper2Paths):
#|    script_path = paths.orig_root / BASE_TRAIN_SCRIPT
#|    if not script_path.exists():
#|        raise FileNotFoundError(f"Missing original LLaVA+Claim baseline script: {script_path}")
#|    sys.path.insert(0, str(paths.orig_root))
#|    spec = importlib.util.spec_from_file_location("paper2_original_claim_train", script_path)
#|    if spec is None or spec.loader is None:
#|        raise ImportError(f"Could not import {script_path}")
#|    module = importlib.util.module_from_spec(spec)
#|    spec.loader.exec_module(module)
#|    return module
#|
#|
#|def install_claim_graphprompt_training(
#|    module,
#|    concept_graph_path: str | Path | None,
#|    graph_dropout: float = 0.15,
#|    graph_gate_init: float = 0.25,
#|    graph_gate_cap: float = 0.75,
#|):
#|    """Patch the original claim baseline module with graph-prompt components."""
#|
#|    import torch
#|    import torch.nn as nn
#|
#|    if not 0.0 <= graph_dropout <= 1.0:
#|        raise ValueError(f"graph_dropout must be in [0, 1], got {graph_dropout}")
#|    if not 0.0 < graph_gate_cap <= 1.0:
#|        raise ValueError(f"graph_gate_cap must be in (0, 1], got {graph_gate_cap}")
#|    if not 0.0 < graph_gate_init < graph_gate_cap:
#|        raise ValueError(
#|            f"graph_gate_init must be in (0, graph_gate_cap), "
#|            f"got init={graph_gate_init}, cap={graph_gate_cap}"
#|        )
#|
#|    _, graph_features, _ = require_concept_graph_cache(
#|        concept_graph_path,
#|        split="train",
#|    )
#|    BaseDataset = module.HybridDataset
#|    BaseProjector = module.MoE_LLM_Projector
#|    BaseModel = module.Hybrid_MoE_LLaVA
#|    original_collate = module.collate_fn
#|
#|    class ClaimGraphPromptProjector(BaseProjector):
#|        def __init__(self, *args, graph_dim: int = GRAPH_FEATURE_DIM, **kwargs):
#|            super().__init__(*args, **kwargs)
#|            self.graph_dim = graph_dim
#|            projected_dim = self.img_proj.out_features
#|            if hasattr(self, "experts"):
#|                del self.experts
#|            if hasattr(self, "gate"):
#|                del self.gate
#|            self.graph_prompt = nn.Sequential(
#|                nn.Linear(projected_dim * 5 + graph_dim, 2048),
#|                nn.LayerNorm(2048),
#|                nn.GELU(),
#|                nn.Linear(2048, self.hidden_size * self.num_tokens),
#|            )
#|            self.graph_dropout = graph_dropout
#|            self.graph_gate_cap = graph_gate_cap
#|            self.graph_reliability_gate = nn.Linear(projected_dim * 5 + graph_dim, 1)
#|            for layer in self.graph_prompt:
#|                if isinstance(layer, nn.Linear):
#|                    nn.init.xavier_uniform_(layer.weight)
#|                    nn.init.zeros_(layer.bias)
#|            nn.init.zeros_(self.graph_reliability_gate.weight)
#|            nn.init.constant_(
#|                self.graph_reliability_gate.bias,
#|                math.log(graph_gate_init / (graph_gate_cap - graph_gate_init)),
#|            )
#|            self.last_graph_prompt_norm = torch.tensor(0.0)
#|            self.last_graph_gate = torch.tensor(graph_gate_init)
#|            self.last_graph_drop_fraction = torch.tensor(0.0)
#|
#|        def forward(self, e_img, e_txt, e_desc, graph_feature=None):
#|            e_img = e_img.float()
#|            e_txt = e_txt.float()
#|            e_desc = e_desc.float()
#|
#|            p_img = self.img_norm(self.img_proj(e_img))
#|            p_txt = self.txt_norm(self.txt_proj(e_txt))
#|            p_desc = self.desc_norm(self.desc_proj(e_desc))
#|            x_relation = torch.cat(
#|                [p_img, p_desc, p_txt, torch.abs(p_desc - p_txt), p_desc * p_txt],
#|                dim=-1,
#|            )
#|
#|            if graph_feature is None:
#|                graph_feature = torch.zeros((e_img.size(0), self.graph_dim), device=e_img.device)
#|            if graph_feature.dim() == 1:
#|                graph_feature = graph_feature.unsqueeze(0)
#|            graph_feature = graph_feature.to(e_img.device).float()
#|
#|            graph_present = graph_feature.abs().sum(dim=-1) > 0
#|            graph_feature = apply_graph_feature_dropout(
#|                graph_feature,
#|                self.graph_dropout,
#|                self.training,
#|            )
#|            graph_retained = graph_feature.abs().sum(dim=-1) > 0
#|            present_count = graph_present.float().sum().clamp_min(1.0)
#|            self.last_graph_drop_fraction = (
#|                (graph_present & ~graph_retained).float().sum() / present_count
#|            ).detach()
#|
#|            gate_input = torch.cat([x_relation, graph_feature], dim=-1)
#|            graph_gate_cap = self.graph_gate_cap
#|            graph_gate = graph_gate_cap * torch.sigmoid(
#|                self.graph_reliability_gate(gate_input)
#|            )
#|            self.last_graph_gate = graph_gate.detach().float().mean()
#|            gated_graph_feature = graph_feature * graph_gate
#|
#|            graph_input = torch.cat([x_relation, gated_graph_feature], dim=-1)
#|            fused = self.graph_prompt(graph_input).view(-1, self.num_tokens, self.hidden_size)
#|            self.last_graph_prompt_norm = fused.detach().float().norm(dim=-1).mean()
#|            fused = self.output_norm(fused) * 0.01
#|
#|            balance_loss = torch.tensor(0.0, device=e_img.device)
#|            return fused, balance_loss
#|
#|    class ClaimGraphPromptDataset(BaseDataset):
#|        def __getitem__(self, idx):
#|            item = super().__getitem__(idx)
#|            sample_id = self.samples[idx]["id"]
#|            item["graph_feature"] = graph_features.get(
#|                sample_id,
#|                torch.zeros(GRAPH_FEATURE_DIM, dtype=torch.float32),
#|            )
#|            return item
#|
#|    def graph_collate_fn(batch):
#|        output = original_collate(batch)
#|        output["graph_feature"] = torch.stack([item["graph_feature"] for item in batch])
#|        return output
#|
#|    class ClaimGraphPromptLLaVA(BaseModel):
#|        def forward(
#|            self,
#|            images,
#|            image_sizes,
#|            e_img,
#|            e_txt,
#|            e_desc,
#|            graph_feature,
#|            input_ids,
#|            attention_mask,
#|            labels,
#|            cf_labels,
#|            alpha=0.05,
#|            gpsa_anchor_ids=None,
#|            gpsa_anchor_mask=None,
#|            gpsa_label_ids=None,
#|            gpsa_label_mask=None,
#|            gp_cca_positive_ids=None,
#|            gp_cca_positive_mask=None,
#|            gp_cca_counter_ids=None,
#|            gp_cca_counter_mask=None,
#|        ):
#|            base_model = self.llm.base_model.model if hasattr(self.llm, "base_model") else self.llm.model
#|            embed_layer = (
#|                base_model.get_input_embeddings()
#|                if hasattr(base_model, "get_input_embeddings")
#|                else base_model.get_model().embed_tokens
#|            )
#|
#|            prompt_embeds, balance_loss = self.projector(
#|                e_img,
#|                e_txt,
#|                e_desc,
#|                graph_feature=graph_feature,
#|            )
#|            main_graph_prompt_norm = self.projector.last_graph_prompt_norm
#|            main_graph_gate = self.projector.last_graph_gate
#|            main_graph_drop_fraction = self.projector.last_graph_drop_fraction
#|            main_cib_stats = {
#|                name: getattr(self.projector, name)
#|                for name in (
#|                    "last_cib_kl",
#|                    "last_cib_beta",
#|                    "last_cib_gamma",
#|                    "last_cib_scale",
#|                    "last_cib_residual_norm",
#|                    "last_cib_label_loss",
#|                    "last_cib_preserve_loss",
#|                    "last_cib_trust_loss",
#|                    "last_cib_amplitude_ratio",
#|                    "last_cib_trust_radius",
#|                    "last_cib_reliability",
#|                    "last_cib_weighted_kl",
#|                    "last_cib_weighted_label",
#|                    "last_cib_weighted_trust",
#|                    "last_cib_weighted_preserve",
#|                )
#|                if hasattr(self.projector, name)
#|            }
#|            teacher_prompt_embeds = getattr(
#|                self.projector,
#|                "last_teacher_prompt",
#|                None,
#|            )
#|            teacher_reliability = getattr(
#|                self.projector,
#|                "last_cib_reliability",
#|                None,
#|            )
#|            main_cib_posterior_mu = getattr(
#|                getattr(self.projector, "rccib", None),
#|                "current_posterior_mu",
#|                None,
#|            )
#|            prompt_embeds = prompt_embeds.to(dtype=torch.bfloat16)
#|            batch_size = e_img.size(0)
#|
#|            with torch.no_grad():
#|                zero_graph = torch.zeros_like(graph_feature)
#|                cf_embeds, _ = self.projector(
#|                    torch.zeros_like(e_img),
#|                    e_txt,
#|                    e_desc,
#|                    graph_feature=zero_graph,
#|                )
#|            self.projector.last_graph_prompt_norm = main_graph_prompt_norm
#|            self.projector.last_graph_gate = main_graph_gate
#|            self.projector.last_graph_drop_fraction = main_graph_drop_fraction
#|            for name, value in main_cib_stats.items():
#|                setattr(self.projector, name, value)
#|            if main_cib_posterior_mu is not None:
#|                self.projector.rccib.current_posterior_mu = main_cib_posterior_mu
#|            contrastive_loss = module.safe_contrastive_loss(
#|                prompt_embeds,
#|                cf_embeds.detach(),
#|                cf_labels,
#|            )
#|
#|            prepared_out = base_model.prepare_inputs_labels_for_multimodal(
#|                input_ids=input_ids,
#|                position_ids=None,
#|                attention_mask=attention_mask,
#|                past_key_values=None,
#|                labels=labels,
#|                images=images,
#|                image_sizes=image_sizes,
#|            )
#|            llava_mask, llava_embeds, llava_labels = module.unpack_prepared(prepared_out, self.hidden_size)
#|
#|            if isinstance(llava_embeds, list):
#|                llava_embeds = torch.cat(llava_embeds, dim=0)
#|            if isinstance(llava_mask, list):
#|                llava_mask = torch.cat(llava_mask, dim=0)
#|            if isinstance(llava_labels, list):
#|                llava_labels = torch.cat(llava_labels, dim=0)
#|
#|            if llava_embeds is None:
#|                embed_layer = (
#|                    base_model.get_input_embeddings()
#|                    if hasattr(base_model, "get_input_embeddings")
#|                    else base_model.get_model().embed_tokens
#|                )
#|                safe_ids = input_ids.clone()
#|                safe_ids[safe_ids < 0] = 0
#|                safe_ids[safe_ids >= self.vocab_size] = 0
#|                llava_embeds = embed_layer(safe_ids)
#|
#|            if llava_embeds.dim() == 2:
#|                llava_embeds = llava_embeds.unsqueeze(0)
#|            llava_seq = llava_embeds.size(1)
#|
#|            if llava_mask is None:
#|                llava_mask = torch.ones((batch_size, llava_seq), device=e_img.device, dtype=torch.long)
#|            else:
#|                llava_mask = llava_mask.reshape(-1)[: batch_size * llava_seq].reshape(batch_size, llava_seq)
#|
#|            if llava_labels is None:
#|                llava_labels = torch.full(
#|                    (batch_size, llava_seq),
#|                    module.IGNORE_INDEX,
#|                    device=e_img.device,
#|                    dtype=torch.long,
#|                )
#|            else:
#|                llava_labels = llava_labels.reshape(-1)[: batch_size * llava_seq].reshape(batch_size, llava_seq)
#|
#|            rectify_llava_context = getattr(
#|                self.projector,
#|                "rectify_llava_context",
#|                None,
#|            )
#|            if callable(rectify_llava_context):
#|                llava_embeds, rectification_auxiliary = rectify_llava_context(
#|                    llava_embeds,
#|                    llava_mask=llava_mask,
#|                    llava_labels=llava_labels,
#|                    input_ids=input_ids,
#|                    input_attention_mask=attention_mask,
#|                    image_token_index=module.IMAGE_TOKEN_INDEX,
#|                    ignore_index=module.IGNORE_INDEX,
#|                )
#|                if rectification_auxiliary is not None:
#|                    balance_loss = balance_loss + rectification_auxiliary / 0.01
#|
#|            augment_grounded_prompt = getattr(
#|                self.projector,
#|                "augment_grounded_prompt",
#|                None,
#|            )
#|            if callable(augment_grounded_prompt):
#|                prompt_embeds, grounding_auxiliary = augment_grounded_prompt(
#|                    prompt_embeds,
#|                    llava_embeds=llava_embeds,
#|                    llava_mask=llava_mask,
#|                    llava_labels=llava_labels,
#|                    input_ids=input_ids,
#|                    input_attention_mask=attention_mask,
#|                    image_token_index=module.IMAGE_TOKEN_INDEX,
#|                    ignore_index=module.IGNORE_INDEX,
#|                )
#|                if grounding_auxiliary is not None:
#|                    balance_loss = balance_loss + grounding_auxiliary / 0.01
#|
#|            inputs_embeds = torch.cat([prompt_embeds, llava_embeds.to(torch.bfloat16)], dim=1)
#|            inputs_embeds = torch.nan_to_num(inputs_embeds, nan=0.0, posinf=100.0, neginf=-100.0)
#|            inputs_embeds = torch.clamp(inputs_embeds, -100.0, 100.0)
#|
#|            prompt_len = prompt_embeds.size(1)
#|            prompt_mask = torch.ones((batch_size, prompt_len), device=e_img.device, dtype=torch.long)
#|            prompt_labels = torch.full(
#|                (batch_size, prompt_len),
#|                module.IGNORE_INDEX,
#|                device=e_img.device,
#|                dtype=torch.long,
#|            )
#|            final_mask = (torch.cat([prompt_mask, llava_mask.long()], dim=1) > 0).long()
#|            final_labels = torch.cat([prompt_labels, llava_labels.long()], dim=1)
#|
#|            limit = self.max_seq_len - 8
#|            if inputs_embeds.size(1) > limit:
#|                keep_back = limit - prompt_len
#|                inputs_embeds = torch.cat(
#|                    [inputs_embeds[:, :prompt_len, :], inputs_embeds[:, prompt_len:, :][:, -keep_back:, :]],
#|                    dim=1,
#|                )
#|                final_mask = torch.cat([final_mask[:, :prompt_len], final_mask[:, prompt_len:][:, -keep_back:]], dim=1)
#|                final_labels = torch.cat(
#|                    [final_labels[:, :prompt_len], final_labels[:, prompt_len:][:, -keep_back:]],
#|                    dim=1,
#|                )
#|
#|            rem = inputs_embeds.size(1) % 8
#|            if rem:
#|                pad = 8 - rem
#|                inputs_embeds = torch.nn.functional.pad(inputs_embeds, (0, 0, 0, pad))
#|                final_mask = torch.nn.functional.pad(final_mask, (0, pad), value=0)
#|                final_labels = torch.nn.functional.pad(final_labels, (0, pad), value=module.IGNORE_INDEX)
#|
#|            semantic_loss_weight = float(
#|                getattr(self.projector, "semantic_loss_weight", 0.0)
#|            )
#|            semantic_loss = inputs_embeds.sum() * 0.0
#|            semantic_global_loss = semantic_loss
#|            semantic_local_loss = semantic_loss
#|            if semantic_loss_weight > 0.0:
#|                if main_cib_posterior_mu is None:
#|                    raise RuntimeError(
#|                        "semantic TS-PIB requires the main posterior mean"
#|                    )
#|                semantic_predictions = self.projector.rccib.decode_semantics(
#|                    main_cib_posterior_mu
#|                )
#|                semantic_targets, semantic_valid = (
#|                    build_multigranular_semantic_targets(
#|                        final_labels,
#|                        embed_layer.weight,
#|                        ignore_index=module.IGNORE_INDEX,
#|                        num_chunks=self.projector.rccib.semantic_chunks,
#|                    )
#|                )
#|                (
#|                    semantic_loss,
#|                    semantic_global_loss,
#|                    semantic_local_loss,
#|                ) = multigranular_semantic_loss(
#|                    semantic_predictions,
#|                    semantic_targets,
#|                    semantic_valid,
#|                    local_weight=float(self.projector.semantic_local_weight),
#|                )
#|                if not bool(torch.isfinite(semantic_loss)):
#|                    semantic_loss = main_cib_posterior_mu.sum() * 0.0
#|                    semantic_global_loss = semantic_loss
#|                    semantic_local_loss = semantic_loss
#|
#|            outputs = self.llm(
#|                inputs_embeds=inputs_embeds.to(torch.bfloat16).contiguous(),
#|                attention_mask=final_mask.contiguous(),
#|                labels=final_labels.contiguous(),
#|            )
#|            if bool(getattr(self, "_capture_claim_polarity", False)):
#|                from lces_stage_4_polarity import first_supervised_polarity_loss
#|
#|                token_ids = getattr(self, "claim_polarity_token_ids", None)
#|                if token_ids is None or len(token_ids) != 2:
#|                    raise RuntimeError(
#|                        "claim polarity capture requires two verdict token ids"
#|                    )
#|                polarity = first_supervised_polarity_loss(
#|                    outputs.logits,
#|                    final_labels,
#|                    contradiction_token_id=int(token_ids[0]),
#|                    entailment_token_id=int(token_ids[1]),
#|                    ignore_index=module.IGNORE_INDEX,
#|                    margin=float(self.claim_polarity_margin),
#|                    margin_weight=float(self.claim_polarity_margin_weight),
#|                )
#|                self.claim_polarity_objective = polarity.loss.float()
#|                self.projector.last_lces_v4_polarity = polarity.loss.detach()
#|                self.projector.last_lces_v4_polarity_ce = (
#|                    polarity.cross_entropy.detach()
#|                )
#|                self.projector.last_lces_v4_polarity_margin_loss = (
#|                    polarity.margin_loss.detach()
#|                )
#|                self.projector.last_lces_v4_polarity_margin = (
#|                    polarity.mean_margin.detach()
#|                )
#|                self.projector.last_lces_v4_polarity_accuracy = (
#|                    polarity.accuracy.detach()
#|                )
#|                self._capture_claim_polarity = False
#|            lm_loss = outputs.loss
#|            gpsa_anchor_weight = float(getattr(self.projector, "gpsa_anchor_weight", 0.0))
#|            gpsa_label_weight = float(getattr(self.projector, "gpsa_label_weight", 0.0))
#|            gpsa_l2sp_weight = float(getattr(self.projector, "gpsa_l2sp_weight", 0.0))
#|            gp_cca_positive_weight = float(getattr(self.projector, "gp_cca_positive_weight", 0.0))
#|            gp_cca_counter_weight = float(getattr(self.projector, "gp_cca_counter_weight", 0.0))
#|            gp_cca_margin_weight = float(getattr(self.projector, "gp_cca_margin_weight", 0.0))
#|            gp_cca_l2sp_weight = float(getattr(self.projector, "gp_cca_l2sp_weight", 0.0))
#|            gpsa_anchor_loss = lm_loss.new_zeros(())
#|            gpsa_label_loss = lm_loss.new_zeros(())
#|            gpsa_l2sp_loss = lm_loss.new_zeros(())
#|            gpsa_anchor_count = lm_loss.new_zeros(())
#|            gpsa_label_count = lm_loss.new_zeros(())
#|            gp_cca_positive_loss = lm_loss.new_zeros(())
#|            gp_cca_counter_loss = lm_loss.new_zeros(())
#|            gp_cca_margin_loss = lm_loss.new_zeros(())
#|            gp_cca_l2sp_loss = lm_loss.new_zeros(())
#|            gp_cca_positive_count = lm_loss.new_zeros(())
#|            gp_cca_counter_count = lm_loss.new_zeros(())
#|            token_loss = None
#|            shift_logits = None
#|            shift_labels = None
#|            valid_labels = None
#|            if (
#|                gpsa_anchor_weight > 0.0
#|                and gpsa_anchor_ids is not None
#|                and gpsa_anchor_mask is not None
#|                and outputs.logits is not None
#|                and outputs.logits.size(1) > 1
#|            ):
#|                shift_logits = outputs.logits[:, :-1, :].contiguous()
#|                shift_labels = final_labels[:, 1:].contiguous()
#|                valid_labels = shift_labels.ne(module.IGNORE_INDEX)
#|                anchors = gpsa_anchor_ids.long()
#|                anchor_valid = gpsa_anchor_mask.bool()
#|                if anchors.dim() == 1:
#|                    anchors = anchors.unsqueeze(0)
#|                    anchor_valid = anchor_valid.unsqueeze(0)
#|                anchor_hits = (
#|                    shift_labels.unsqueeze(-1).eq(anchors.unsqueeze(1))
#|                    & anchor_valid.unsqueeze(1)
#|                    & valid_labels.unsqueeze(-1)
#|                ).any(dim=-1)
#|                gpsa_anchor_count = anchor_hits.float().sum()
#|                if bool(gpsa_anchor_count.item() > 0):
#|                    token_loss = torch.nn.functional.cross_entropy(
#|                        shift_logits.float().reshape(-1, shift_logits.size(-1)),
#|                        shift_labels.reshape(-1),
#|                        ignore_index=module.IGNORE_INDEX,
#|                        reduction="none",
#|                    ).reshape_as(shift_labels)
#|                    gpsa_anchor_loss = (
#|                        token_loss * anchor_hits.float()
#|                    ).sum() / gpsa_anchor_count.clamp_min(1.0)
#|            if (
#|                gpsa_label_weight > 0.0
#|                and gpsa_label_ids is not None
#|                and gpsa_label_mask is not None
#|                and outputs.logits is not None
#|                and outputs.logits.size(1) > 1
#|            ):
#|                if shift_logits is None:
#|                    shift_logits = outputs.logits[:, :-1, :].contiguous()
#|                    shift_labels = final_labels[:, 1:].contiguous()
#|                    valid_labels = shift_labels.ne(module.IGNORE_INDEX)
#|                label_ids = gpsa_label_ids.long()
#|                label_valid = gpsa_label_mask.bool()
#|                if label_ids.dim() == 1:
#|                    label_ids = label_ids.unsqueeze(0)
#|                    label_valid = label_valid.unsqueeze(0)
#|                label_hits = (
#|                    shift_labels.unsqueeze(-1).eq(label_ids.unsqueeze(1))
#|                    & label_valid.unsqueeze(1)
#|                    & valid_labels.unsqueeze(-1)
#|                ).any(dim=-1)
#|                gpsa_label_count = label_hits.float().sum()
#|                if bool(gpsa_label_count.item() > 0):
#|                    if token_loss is None:
#|                        token_loss = torch.nn.functional.cross_entropy(
#|                            shift_logits.float().reshape(-1, shift_logits.size(-1)),
#|                            shift_labels.reshape(-1),
#|                            ignore_index=module.IGNORE_INDEX,
#|                            reduction="none",
#|                        ).reshape_as(shift_labels)
#|                    gpsa_label_loss = (
#|                        token_loss * label_hits.float()
#|                    ).sum() / gpsa_label_count.clamp_min(1.0)
#|            if (
#|                gp_cca_positive_weight > 0.0
#|                and gp_cca_positive_ids is not None
#|                and gp_cca_positive_mask is not None
#|                and outputs.logits is not None
#|                and outputs.logits.size(1) > 1
#|            ):
#|                if shift_logits is None:
#|                    shift_logits = outputs.logits[:, :-1, :].contiguous()
#|                    shift_labels = final_labels[:, 1:].contiguous()
#|                    valid_labels = shift_labels.ne(module.IGNORE_INDEX)
#|                positive_ids = gp_cca_positive_ids.long()
#|                positive_valid = gp_cca_positive_mask.bool()
#|                if positive_ids.dim() == 1:
#|                    positive_ids = positive_ids.unsqueeze(0)
#|                    positive_valid = positive_valid.unsqueeze(0)
#|                positive_hits = (
#|                    shift_labels.unsqueeze(-1).eq(positive_ids.unsqueeze(1))
#|                    & positive_valid.unsqueeze(1)
#|                    & valid_labels.unsqueeze(-1)
#|                ).any(dim=-1)
#|                gp_cca_positive_count = positive_hits.float().sum()
#|                if bool(gp_cca_positive_count.item() > 0):
#|                    if token_loss is None:
#|                        token_loss = torch.nn.functional.cross_entropy(
#|                            shift_logits.float().reshape(-1, shift_logits.size(-1)),
#|                            shift_labels.reshape(-1),
#|                            ignore_index=module.IGNORE_INDEX,
#|                            reduction="none",
#|                        ).reshape_as(shift_labels)
#|                    gp_cca_positive_loss = (
#|                        token_loss * positive_hits.float()
#|                    ).sum() / gp_cca_positive_count.clamp_min(1.0)
#|            if (
#|                gp_cca_counter_weight > 0.0
#|                and gp_cca_counter_ids is not None
#|                and gp_cca_counter_mask is not None
#|                and outputs.logits is not None
#|                and outputs.logits.size(1) > 1
#|            ):
#|                if shift_logits is None:
#|                    shift_logits = outputs.logits[:, :-1, :].contiguous()
#|                    shift_labels = final_labels[:, 1:].contiguous()
#|                    valid_labels = shift_labels.ne(module.IGNORE_INDEX)
#|                counter_ids = gp_cca_counter_ids.long()
#|                counter_valid = gp_cca_counter_mask.bool()
#|                if counter_ids.dim() == 1:
#|                    counter_ids = counter_ids.unsqueeze(0)
#|                    counter_valid = counter_valid.unsqueeze(0)
#|                probs = torch.softmax(shift_logits.float(), dim=-1)
#|                safe_counter_ids = counter_ids.clamp_min(0).clamp_max(probs.size(-1) - 1)
#|                gathered = probs.gather(
#|                    -1,
#|                    safe_counter_ids.unsqueeze(1).expand(-1, probs.size(1), -1),
#|                )
#|                counter_prob = (
#|                    gathered * counter_valid.unsqueeze(1).to(gathered.dtype)
#|                ).sum(dim=-1)
#|                counter_prob = counter_prob.clamp(min=0.0, max=0.95)
#|                gp_cca_counter_count = valid_labels.float().sum()
#|                if bool(gp_cca_counter_count.item() > 0):
#|                    counter_unlikelihood = -torch.log1p(-counter_prob.clamp_max(0.95))
#|                    gp_cca_counter_loss = (
#|                        counter_unlikelihood * valid_labels.float()
#|                    ).sum() / gp_cca_counter_count.clamp_min(1.0)
#|                    if gp_cca_margin_weight > 0.0:
#|                        counter_nll = -torch.log(counter_prob.clamp_min(1e-8))
#|                        mean_counter_nll = (
#|                            counter_nll * valid_labels.float()
#|                        ).sum() / gp_cca_counter_count.clamp_min(1.0)
#|                        margin = float(getattr(self.projector, "gp_cca_margin", 0.35))
#|                        gp_cca_margin_loss = torch.relu(
#|                            gp_cca_positive_loss.detach() + margin - mean_counter_nll
#|                        )
#|            if gpsa_l2sp_weight > 0.0 and hasattr(self, "gpsa_l2sp_refs"):
#|                l2_terms = []
#|                for name, parameter in self.llm.named_parameters():
#|                    ref = self.gpsa_l2sp_refs.get(name)
#|                    if ref is None or not parameter.requires_grad:
#|                        continue
#|                    l2_terms.append(
#|                        (parameter.float() - ref.to(parameter.device).float()).pow(2).mean()
#|                    )
#|                if l2_terms:
#|                    gpsa_l2sp_loss = torch.stack(l2_terms).mean()
#|            if gp_cca_l2sp_weight > 0.0 and hasattr(self, "gp_cca_l2sp_refs"):
#|                l2_terms = []
#|                for name, parameter in self.llm.named_parameters():
#|                    ref = self.gp_cca_l2sp_refs.get(name)
#|                    if ref is None or not parameter.requires_grad:
#|                        continue
#|                    l2_terms.append(
#|                        (parameter.float() - ref.to(parameter.device).float()).pow(2).mean()
#|                    )
#|                if l2_terms:
#|                    gp_cca_l2sp_loss = torch.stack(l2_terms).mean()
#|            if hasattr(self.projector, "gpsa_anchor_weight"):
#|                self.projector.last_gpsa_anchor_loss = gpsa_anchor_loss.detach()
#|                self.projector.last_gpsa_anchor_count = gpsa_anchor_count.detach()
#|                self.projector.last_gpsa_weighted_anchor = (
#|                    gpsa_anchor_weight * gpsa_anchor_loss.detach()
#|                )
#|                self.projector.last_gpsa_label_loss = gpsa_label_loss.detach()
#|                self.projector.last_gpsa_label_count = gpsa_label_count.detach()
#|                self.projector.last_gpsa_weighted_label = (
#|                    gpsa_label_weight * gpsa_label_loss.detach()
#|                )
#|                self.projector.last_gpsa_l2sp_loss = gpsa_l2sp_loss.detach()
#|                self.projector.last_gpsa_weighted_l2sp = (
#|                    gpsa_l2sp_weight * gpsa_l2sp_loss.detach()
#|                )
#|            if hasattr(self.projector, "gp_cca_positive_weight"):
#|                self.projector.last_gp_cca_positive_loss = gp_cca_positive_loss.detach()
#|                self.projector.last_gp_cca_weighted_positive = (
#|                    gp_cca_positive_weight * gp_cca_positive_loss.detach()
#|                )
#|                self.projector.last_gp_cca_positive_count = gp_cca_positive_count.detach()
#|                self.projector.last_gp_cca_counter_loss = gp_cca_counter_loss.detach()
#|                self.projector.last_gp_cca_weighted_counter = (
#|                    gp_cca_counter_weight * gp_cca_counter_loss.detach()
#|                )
#|                self.projector.last_gp_cca_counter_count = gp_cca_counter_count.detach()
#|                self.projector.last_gp_cca_margin_loss = gp_cca_margin_loss.detach()
#|                self.projector.last_gp_cca_weighted_margin = (
#|                    gp_cca_margin_weight * gp_cca_margin_loss.detach()
#|                )
#|                self.projector.last_gp_cca_l2sp_loss = gp_cca_l2sp_loss.detach()
#|                self.projector.last_gp_cca_weighted_l2sp = (
#|                    gp_cca_l2sp_weight * gp_cca_l2sp_loss.detach()
#|                )
#|            teacher_consistency_weight = float(
#|                getattr(self.projector, "teacher_consistency_weight", 0.0)
#|            )
#|            teacher_advantage_weight = float(
#|                getattr(self.projector, "teacher_advantage_weight", 0.0)
#|            )
#|            teacher_loss = lm_loss.new_zeros(())
#|            advantage_loss = lm_loss.new_zeros(())
#|            effective_teacher_reliability = teacher_reliability
#|            teacher_enabled = (
#|                teacher_consistency_weight > 0.0 or teacher_advantage_weight > 0.0
#|            )
#|            if (
#|                teacher_enabled
#|                and teacher_prompt_embeds is not None
#|                and teacher_reliability is not None
#|            ):
#|                teacher_reliability_floor = float(
#|                    getattr(self.projector, "teacher_reliability_floor", 0.0)
#|                )
#|                effective_teacher_reliability = teacher_reliability_floor + (
#|                    1.0 - teacher_reliability_floor
#|                ) * teacher_reliability.detach().float().clamp(0.0, 1.0)
#|                if teacher_prompt_embeds.size(1) != prompt_len:
#|                    raise RuntimeError(
#|                        "v10 teacher prompt length does not match student prompt length"
#|                    )
#|                teacher_inputs_embeds = inputs_embeds.detach().clone()
#|                teacher_inputs_embeds[:, :prompt_len, :] = teacher_prompt_embeds.to(
#|                    device=teacher_inputs_embeds.device,
#|                    dtype=teacher_inputs_embeds.dtype,
#|                )
#|                with torch.no_grad():
#|                    teacher_outputs = self.llm(
#|                        inputs_embeds=teacher_inputs_embeds.to(
#|                            torch.bfloat16
#|                        ).contiguous(),
#|                        attention_mask=final_mask.contiguous(),
#|                        labels=final_labels.contiguous(),
#|                    )
#|                if teacher_consistency_weight > 0.0:
#|                    teacher_loss = masked_teacher_kl(
#|                        outputs.logits,
#|                        teacher_outputs.logits,
#|                        final_labels,
#|                        ignore_index=module.IGNORE_INDEX,
#|                        temperature=float(self.projector.teacher_temperature),
#|                        reliability=effective_teacher_reliability,
#|                    )
#|                if teacher_advantage_weight > 0.0:
#|                    advantage_loss = masked_teacher_advantage_loss(
#|                        outputs.logits,
#|                        teacher_outputs.logits,
#|                        final_labels,
#|                        ignore_index=module.IGNORE_INDEX,
#|                        margin=float(self.projector.teacher_advantage_margin),
#|                        smoothness=float(
#|                            self.projector.teacher_advantage_smoothness
#|                        ),
#|                        reliability=effective_teacher_reliability,
#|                    )
#|            if hasattr(self.projector, "teacher_consistency_weight"):
#|                self.projector.last_cib_teacher_loss = teacher_loss.detach()
#|                self.projector.last_cib_weighted_teacher = (
#|                    teacher_consistency_weight * teacher_loss.detach()
#|                )
#|                if effective_teacher_reliability is not None:
#|                    self.projector.last_cib_teacher_floor = (
#|                        effective_teacher_reliability.detach().mean()
#|                    )
#|            if hasattr(self.projector, "last_cib_advantage_loss"):
#|                self.projector.last_cib_advantage_loss = advantage_loss.detach()
#|                self.projector.last_cib_weighted_advantage = (
#|                    teacher_advantage_weight * advantage_loss.detach()
#|                )
#|            if hasattr(self.projector, "last_cib_semantic_loss"):
#|                self.projector.last_cib_semantic_global = (
#|                    semantic_global_loss.detach()
#|                )
#|                self.projector.last_cib_semantic_local = semantic_local_loss.detach()
#|                self.projector.last_cib_semantic_loss = semantic_loss.detach()
#|                self.projector.last_cib_weighted_semantic = (
#|                    semantic_loss_weight * semantic_loss.detach()
#|                )
#|            if torch.isnan(lm_loss) or torch.isinf(lm_loss):
#|                lm_loss = torch.tensor(0.0, device=e_img.device, requires_grad=True)
#|            if torch.isnan(contrastive_loss) or torch.isinf(contrastive_loss):
#|                contrastive_loss = torch.tensor(0.0, device=e_img.device)
#|
#|            core_loss = lm_loss + alpha * contrastive_loss
#|            compose_core_training_loss = getattr(
#|                self.projector,
#|                "compose_core_training_loss",
#|                None,
#|            )
#|            if callable(compose_core_training_loss):
#|                core_loss = compose_core_training_loss(
#|                    lm_loss=lm_loss,
#|                    contrastive_loss=contrastive_loss,
#|                    logits=outputs.logits,
#|                    labels=final_labels,
#|                    alpha=alpha,
#|                    ignore_index=module.IGNORE_INDEX,
#|                )
#|
#|            total = (
#|                core_loss
#|                + 0.01 * balance_loss.to(lm_loss.device)
#|                + teacher_consistency_weight * teacher_loss
#|                + teacher_advantage_weight * advantage_loss
#|                + semantic_loss_weight * semantic_loss
#|                + gpsa_anchor_weight * gpsa_anchor_loss
#|                + gpsa_label_weight * gpsa_label_loss
#|                + gpsa_l2sp_weight * gpsa_l2sp_loss
#|                + gp_cca_positive_weight * gp_cca_positive_loss
#|                + gp_cca_counter_weight * gp_cca_counter_loss
#|                + gp_cca_margin_weight * gp_cca_margin_loss
#|                + gp_cca_l2sp_weight * gp_cca_l2sp_loss
#|            )
#|            return total, lm_loss, contrastive_loss
#|
#|    module.MoE_LLM_Projector = ClaimGraphPromptProjector
#|    module.HybridDataset = ClaimGraphPromptDataset
#|    module.collate_fn = graph_collate_fn
#|    module.Hybrid_MoE_LLaVA = ClaimGraphPromptLLaVA
#|    return module
#|
#|
#|def train(
#|    args: argparse.Namespace,
#|    install_training=install_claim_graphprompt_training,
#|    initialize_model=None,
#|    build_optimizer=None,
#|    extra_batch_keys=(),
#|    collect_metrics=None,
#|    checkpoint_writer=None,
#|    prepare_model=None,
#|    expected_records=None,
#|):
#|    paths = Paper2Paths.from_env()
#|    os.environ.setdefault("PAPER2_CKPT_NAME", DEFAULT_CKPT_NAME)
#|    paths = Paper2Paths.from_env()
#|    paths.ensure_output_dirs()
#|    print(describe_paths(paths))
#|    concept_graph_path = paths.resolve_output_path(
#|        args.concept_graph_cache or paths.train_concept_graph_cache
#|    )
#|    require_concept_graph_cache(concept_graph_path, split="train")
#|    os.chdir(paths.orig_root)
#|
#|    module = install_training(
#|        load_original_train_module(paths),
#|        concept_graph_path,
#|        graph_dropout=args.graph_dropout,
#|        graph_gate_init=args.graph_gate_init,
#|        graph_gate_cap=args.graph_gate_cap,
#|    )
#|
#|    torch = module.torch
#|    DataLoader = module.DataLoader
#|    get_cosine_schedule_with_warmup = module.get_cosine_schedule_with_warmup
#|
#|    device = args.device
#|    random.seed(args.seed)
#|    torch.manual_seed(args.seed)
#|    if torch.cuda.is_available():
#|        torch.cuda.manual_seed_all(args.seed)
#|    ckpt_dir = paths.checkpoint_dir
#|    ckpt_dir.mkdir(parents=True, exist_ok=True)
#|
#|    model = module.Hybrid_MoE_LLaVA(paths.llm_path, num_tokens=args.num_tokens).to(device)
#|    if initialize_model is not None:
#|        initialize_model(model, module, paths, device)
#|    if prepare_model is not None:
#|        prepare_model(model, module)
#|    model.llm.print_trainable_parameters()
#|
#|    dataset = module.HybridDataset(
#|        str(paths.train_features),
#|        str(paths.train_json),
#|        model.tokenizer,
#|        model.image_processor,
#|        model_max_length=2048,
#|    )
#|    if expected_records is not None and len(dataset) != expected_records:
#|        raise ValueError(f'Expected {expected_records} usable TRAIN records; dataset has {len(dataset)}')
#|
#|    accum_steps = args.accum_steps
#|    total_steps = max(1, (len(dataset) * args.epochs) // accum_steps)
#|    warmup_steps = int(total_steps * args.warmup_ratio)
#|    if build_optimizer is None:
#|        optimizer = torch.optim.AdamW(
#|            [
#|                {"params": model.projector.parameters(), "lr": args.projector_lr},
#|                {"params": model.llm.parameters(), "lr": args.llm_lr},
#|            ],
#|            weight_decay=0.0,
#|        )
#|    else:
#|        optimizer = build_optimizer(model, torch, args)
#|    scheduler = get_cosine_schedule_with_warmup(
#|        optimizer,
#|        num_warmup_steps=warmup_steps,
#|        num_training_steps=total_steps,
#|    )
#|
#|    training_mode = getattr(args, "training_mode", "train from scratch")
#|    print(
#|        f"[paper2-claim-graphprompt] {training_mode}; "
#|        "only epoch-level LoRA/projector files will be saved"
#|    )
#|
#|    model.train()
#|    for epoch in range(args.epochs):
#|        generator = torch.Generator()
#|        generator.manual_seed(args.seed + epoch)
#|        dataloader = DataLoader(
#|            dataset,
#|            batch_size=args.batch_size,
#|            shuffle=True,
#|            collate_fn=module.collate_fn,
#|            num_workers=args.num_workers,
#|            pin_memory=True,
#|            generator=generator,
#|        )
#|        pbar = module.tqdm(dataloader, desc=f"Paper2 ClaimGraphPrompt Epoch {epoch + 1}/{args.epochs}")
#|        nan_count = 0
#|        ema_lm = None
#|        optimizer.zero_grad()
#|
#|        for step, batch in enumerate(pbar):
#|            training_progress = (
#|                epoch + step / max(1, len(dataloader))
#|            ) / max(1, args.epochs)
#|            if hasattr(model.projector, "set_training_progress"):
#|                model.projector.set_training_progress(training_progress)
#|
#|            images = batch["images"]
#|            if isinstance(images, list):
#|                images = [img.to(device, dtype=torch.bfloat16) for img in images]
#|            else:
#|                images = images.to(device, dtype=torch.bfloat16)
#|
#|            extra_forward_kwargs = {}
#|            for key in extra_batch_keys:
#|                if key not in batch:
#|                    continue
#|                value = batch[key]
#|                extra_forward_kwargs[key] = (
#|                    value.to(device) if hasattr(value, "to") else value
#|                )
#|
#|            loss, lm, cf = model(
#|                images,
#|                batch["image_sizes"],
#|                batch["e_img"].to(device),
#|                batch["e_txt"].to(device),
#|                batch["e_desc"].to(device),
#|                batch["graph_feature"].to(device),
#|                batch["ids"].to(device),
#|                batch["mask"].to(device),
#|                batch["labels"].to(device),
#|                batch["cf"].to(device),
#|                **(
#|                    {
#|                        **(
#|                            {
#|                                "gpsa_anchor_ids": batch["gpsa_anchor_ids"].to(device),
#|                                "gpsa_anchor_mask": batch["gpsa_anchor_mask"].to(device),
#|                            }
#|                            if "gpsa_anchor_ids" in batch
#|                            else {}
#|                        ),
#|                        **(
#|                            {
#|                                "gpsa_label_ids": batch["gpsa_label_ids"].to(device),
#|                                "gpsa_label_mask": batch["gpsa_label_mask"].to(device),
#|                            }
#|                            if "gpsa_label_ids" in batch
#|                            else {}
#|                        ),
#|                        **(
#|                            {
#|                                "gp_cca_positive_ids": batch["gp_cca_positive_ids"].to(device),
#|                                "gp_cca_positive_mask": batch["gp_cca_positive_mask"].to(device),
#|                                "gp_cca_counter_ids": batch["gp_cca_counter_ids"].to(device),
#|                                "gp_cca_counter_mask": batch["gp_cca_counter_mask"].to(device),
#|                            }
#|                            if "gp_cca_positive_ids" in batch
#|                            else {}
#|                        ),
#|                    }
#|                    if "gpsa_anchor_ids" in batch or "gp_cca_positive_ids" in batch
#|                    else {}
#|                ),
#|                **extra_forward_kwargs,
#|            )
#|
#|            if torch.isnan(loss) or torch.isinf(loss):
#|                nan_count += 1
#|                optimizer.zero_grad()
#|                continue
#|
#|            (loss / accum_steps).backward()
#|            has_nan = any(
#|                p.grad is not None and (torch.isnan(p.grad).any() or torch.isinf(p.grad).any())
#|                for p in model.parameters()
#|            )
#|            if has_nan:
#|                nan_count += 1
#|                optimizer.zero_grad()
#|                continue
#|
#|            if (step + 1) % accum_steps == 0:
#|                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
#|                optimizer.step()
#|                scheduler.step()
#|                on_optimizer_step = getattr(
#|                    model.projector,
#|                    "on_optimizer_step",
#|                    None,
#|                )
#|                if callable(on_optimizer_step):
#|                    on_optimizer_step()
#|                optimizer.zero_grad()
#|
#|            lm_val = lm.item()
#|            ema_lm = lm_val if ema_lm is None else 0.95 * ema_lm + 0.05 * lm_val
#|            graph_norm = getattr(model.projector, "last_graph_prompt_norm", torch.tensor(0.0)).item()
#|            graph_gate = getattr(model.projector, "last_graph_gate", torch.tensor(0.0)).item()
#|            graph_drop = getattr(
#|                model.projector,
#|                "last_graph_drop_fraction",
#|                torch.tensor(0.0),
#|            ).item()
#|            metrics = {
#|                "LM": f"{ema_lm:.3f}",
#|                "CF": f"{cf.item():.3f}",
#|                "GRAPH_N": f"{graph_norm:.3f}",
#|                "GRAPH_G": f"{graph_gate:.3f}",
#|                "DROP": f"{graph_drop:.2f}",
#|                "LR": f"{scheduler.get_last_lr()[0]:.2e}",
#|                "NaN": nan_count,
#|                "Step": f"{(step + 1) // accum_steps}",
#|            }
#|            if hasattr(model.projector, "last_cib_kl"):
#|                metrics.update(
#|                    {
#|                        "CIB_KL": f"{model.projector.last_cib_kl.item():.3f}",
#|                        "CIB_B": f"{model.projector.last_cib_beta.item():.2e}",
#|                        "CIB_G": f"{model.projector.last_cib_gamma.item():.3f}",
#|                        "CIB_S": f"{model.projector.last_cib_scale.item():.3f}",
#|                        "CIB_R": f"{model.projector.last_cib_residual_norm.item():.3f}",
#|                    }
#|                )
#|                if hasattr(model.projector, "last_cib_label_loss"):
#|                    metrics["CIB_Y"] = (
#|                        f"{model.projector.last_cib_label_loss.item():.3f}"
#|                    )
#|                if hasattr(model.projector, "last_cib_preserve_loss"):
#|                    metrics["CIB_P"] = (
#|                        f"{model.projector.last_cib_preserve_loss.item():.3e}"
#|                    )
#|                if hasattr(model.projector, "last_cib_trust_loss"):
#|                    metrics["CIB_TR"] = (
#|                        f"{model.projector.last_cib_trust_loss.item():.3e}"
#|                    )
#|                    metrics["CIB_A"] = (
#|                        f"{model.projector.last_cib_amplitude_ratio.item():.3e}"
#|                    )
#|                    metrics["CIB_TW"] = (
#|                        f"{model.projector.last_cib_weighted_trust.item():.3e}"
#|                    )
#|                if (
#|                    getattr(model.projector, "teacher_consistency_weight", 0.0)
#|                    > 0.0
#|                ):
#|                    metrics["CIB_KD"] = (
#|                        f"{model.projector.last_cib_teacher_loss.item():.3e}"
#|                    )
#|                    metrics["CIB_KDW"] = (
#|                        f"{model.projector.last_cib_weighted_teacher.item():.3e}"
#|                    )
#|                    metrics["CIB_KDF"] = (
#|                        f"{model.projector.last_cib_teacher_floor.item():.3f}"
#|                    )
#|                if getattr(model.projector, "semantic_loss_weight", 0.0) > 0.0:
#|                    metrics["CIB_SEMG"] = (
#|                        f"{model.projector.last_cib_semantic_global.item():.3e}"
#|                    )
#|                    metrics["CIB_SEML"] = (
#|                        f"{model.projector.last_cib_semantic_local.item():.3e}"
#|                    )
#|                    metrics["CIB_SEM"] = (
#|                        f"{model.projector.last_cib_semantic_loss.item():.3e}"
#|                    )
#|                    metrics["CIB_SEMW"] = (
#|                        f"{model.projector.last_cib_weighted_semantic.item():.3e}"
#|                    )
#|                if (
#|                    getattr(model.projector, "teacher_advantage_weight", 0.0)
#|                    > 0.0
#|                ):
#|                    metrics["CIB_ADV"] = (
#|                        f"{model.projector.last_cib_advantage_loss.item():.3e}"
#|                    )
#|                    metrics["CIB_ADVW"] = (
#|                        f"{model.projector.last_cib_weighted_advantage.item():.3e}"
#|                    )
#|                if hasattr(model.projector, "last_cib_weighted_kl"):
#|                    metrics["CIB_KLW"] = (
#|                        f"{model.projector.last_cib_weighted_kl.item():.3e}"
#|                    )
#|                    metrics["CIB_YW"] = (
#|                        f"{model.projector.last_cib_weighted_label.item():.3e}"
#|                    )
#|            if hasattr(model.projector, "last_gpsa_anchor_loss"):
#|                metrics["GPSA_A"] = (
#|                    f"{model.projector.last_gpsa_anchor_loss.item():.3e}"
#|                )
#|                metrics["GPSA_AW"] = (
#|                    f"{model.projector.last_gpsa_weighted_anchor.item():.3e}"
#|                )
#|                metrics["GPSA_N"] = (
#|                    f"{model.projector.last_gpsa_anchor_count.item():.0f}"
#|                )
#|                if hasattr(model.projector, "last_gpsa_label_loss"):
#|                    metrics["GPSA_Y"] = (
#|                        f"{model.projector.last_gpsa_label_loss.item():.3e}"
#|                    )
#|                    metrics["GPSA_YW"] = (
#|                        f"{model.projector.last_gpsa_weighted_label.item():.3e}"
#|                    )
#|                    metrics["GPSA_YN"] = (
#|                        f"{model.projector.last_gpsa_label_count.item():.0f}"
#|                    )
#|                metrics["GPSA_L2"] = (
#|                    f"{model.projector.last_gpsa_l2sp_loss.item():.3e}"
#|                )
#|            if hasattr(model.projector, "last_gp_cca_positive_loss"):
#|                metrics["CCA_P"] = (
#|                    f"{model.projector.last_gp_cca_positive_loss.item():.3e}"
#|                )
#|                metrics["CCA_PW"] = (
#|                    f"{model.projector.last_gp_cca_weighted_positive.item():.3e}"
#|                )
#|                metrics["CCA_PN"] = (
#|                    f"{model.projector.last_gp_cca_positive_count.item():.0f}"
#|                )
#|                metrics["CCA_C"] = (
#|                    f"{model.projector.last_gp_cca_counter_loss.item():.3e}"
#|                )
#|                metrics["CCA_CW"] = (
#|                    f"{model.projector.last_gp_cca_weighted_counter.item():.3e}"
#|                )
#|                metrics["CCA_CN"] = (
#|                    f"{model.projector.last_gp_cca_counter_count.item():.0f}"
#|                )
#|                metrics["CCA_M"] = (
#|                    f"{model.projector.last_gp_cca_margin_loss.item():.3e}"
#|                )
#|                metrics["CCA_L2"] = (
#|                    f"{model.projector.last_gp_cca_l2sp_loss.item():.3e}"
#|                )
#|            if collect_metrics is not None:
#|                metrics.update(collect_metrics(model, torch))
#|            pbar.set_postfix(metrics)
#|
#|        if checkpoint_writer is None:
#|            model.llm.save_pretrained(str(ckpt_dir / f"lora_epoch_{epoch + 1}{PROJECTOR_SUFFIX}"))
#|            torch.save(model.projector.state_dict(), ckpt_dir / f"proj_epoch_{epoch + 1}{PROJECTOR_SUFFIX}.pth")
#|        else:
#|            checkpoint_writer(model, epoch + 1, nan_count)
#|        print(f"\nPaper2 ClaimGraphPrompt epoch {epoch + 1} finished. nan_count={nan_count}")
#|
#|    return model
#|
#|
#|def parse_args() -> argparse.Namespace:
#|    parser = argparse.ArgumentParser()
#|    parser.add_argument("--epochs", type=int, default=4)
#|    parser.add_argument("--device", type=str, default="cuda:0")
#|    parser.add_argument("--batch_size", type=int, default=1)
#|    parser.add_argument("--accum_steps", type=int, default=16)
#|    parser.add_argument("--num_workers", type=int, default=2)
#|    parser.add_argument("--num_tokens", type=int, default=4)
#|    parser.add_argument("--warmup_ratio", type=float, default=0.03)
#|    parser.add_argument("--projector_lr", type=float, default=2e-5)
#|    parser.add_argument("--llm_lr", type=float, default=2e-4)
#|    parser.add_argument("--graph_dropout", type=float, default=0.15)
#|    parser.add_argument("--graph_gate_init", type=float, default=0.25)
#|    parser.add_argument("--graph_gate_cap", type=float, default=0.75)
#|    parser.add_argument("--concept_graph_cache", type=str, default=None)
#|    parser.add_argument("--seed", type=int, default=42)
#|    return parser.parse_args()
#|
#|
#|if __name__ == "__main__":
#|    train(parse_args())
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: train_llava_claim_iesfd_stage_10.py ===
#|"""Train graph-free explanation verifier for IESFD-v10 reranking."""
#|
#|from __future__ import annotations
#|
#|import json
#|import os
#|
#|
#|DEFAULT_CKPT_NAME = "checkpoints_llava_claim_iesfd_v10_fulltrain"
#|PROJECTOR_SUFFIX = "_claim_iesfd_v10_fulltrain"
#|os.environ["OIEC_V1_CKPT_NAME"] = os.environ.get(
#|    "IESFD_V10_CKPT_NAME", DEFAULT_CKPT_NAME
#|)
#|os.environ["OIEC_V1_PROJECTOR_SUFFIX"] = os.environ.get(
#|    "IESFD_V10_PROJECTOR_SUFFIX", PROJECTOR_SUFFIX
#|)
#|
#|import train_llava_claim_oiec_stage_1 as oiec  # noqa: E402
#|from iesfd_stage_10 import (  # noqa: E402
#|    evidence_verifier_ranking_loss,
#|    explanation_state_mask,
#|    make_iesfd_v10_readout_classes,
#|)
#|from oiec_completion import file_sha256  # noqa: E402
#|from rgc_semantic_readout import attach_semantic_readout  # noqa: E402
#|from rgc_semantic_readout_stage_4 import PHENOMENON_GROUPS  # noqa: E402
#|
#|
#|oiec.v8.make_v8_readout_classes = make_iesfd_v10_readout_classes
#|_BASE_BUILD_PARSER = oiec.build_parser
#|_BASE_INSTALL_OIEC_TRAINING = oiec.install_oiec_training
#|_BASE_COLLECT_METRICS = oiec.collect_metrics
#|
#|
#|def build_parser():
#|    parser = _BASE_BUILD_PARSER()
#|    parser.add_argument("--verifier_weight", type=float, default=0.20)
#|    parser.add_argument("--verifier_margin", type=float, default=0.30)
#|    parser.add_argument("--verifier_temperature", type=float, default=0.10)
#|    parser.add_argument("--verifier_anchor_weight", type=float, default=0.10)
#|    return parser
#|
#|
#|def install_iesfd_v10_training(module, concept_graph_path, *, args):
#|    # ``main`` replaces oiec.install_oiec_training with this wrapper.  Always
#|    # call the captured OIEC implementation, otherwise the wrapper recurses.
#|    installed, counts = _BASE_INSTALL_OIEC_TRAINING(
#|        module, concept_graph_path, args=args
#|    )
#|    BaseModel = installed.Hybrid_MoE_LLaVA
#|
#|    class EvidenceVerifierModel(BaseModel):
#|        def compute_oiec_causal_auxiliary(
#|            self,
#|            *,
#|            positive_hidden,
#|            positive_labels,
#|            positive_intervention,
#|            negative_hidden,
#|            negative_labels,
#|            negative_intervention,
#|        ):
#|            del positive_intervention, negative_intervention
#|            label_tokens = int(self.projector.config.label_token_count)
#|            positive_mask = explanation_state_mask(
#|                installed.torch,
#|                positive_labels,
#|                ignore_index=installed.IGNORE_INDEX,
#|                label_token_count=label_tokens,
#|            )
#|            negative_mask = explanation_state_mask(
#|                installed.torch,
#|                negative_labels,
#|                ignore_index=installed.IGNORE_INDEX,
#|                label_token_count=label_tokens,
#|            )
#|            positive_score, positive_coverage = (
#|                self.projector.score_evidence_candidates(
#|                    positive_hidden, positive_mask
#|                )
#|            )
#|            negative_score, negative_coverage = (
#|                self.projector.score_evidence_candidates(
#|                    negative_hidden, negative_mask
#|                )
#|            )
#|            loss, gap, anchor = evidence_verifier_ranking_loss(
#|                installed.torch,
#|                positive_score,
#|                negative_score,
#|                margin=float(args.verifier_margin),
#|                temperature=float(args.verifier_temperature),
#|                anchor_weight=float(args.verifier_anchor_weight),
#|            )
#|            weighted = float(args.verifier_weight) * loss
#|            projector = self.projector
#|            projector.last_iesfd_v10_positive = positive_score.mean().detach()
#|            projector.last_iesfd_v10_negative = negative_score.mean().detach()
#|            projector.last_iesfd_v10_gap = gap.detach()
#|            projector.last_iesfd_v10_loss = loss.detach()
#|            projector.last_iesfd_v10_anchor = anchor.detach()
#|            projector.last_iesfd_v10_weighted = weighted.detach()
#|            projector.last_iesfd_v10_positive_coverage = (
#|                positive_coverage.detach().mean(dim=0)
#|            )
#|            projector.last_iesfd_v10_negative_coverage = (
#|                negative_coverage.detach().mean(dim=0)
#|            )
#|            return weighted
#|
#|        def forward(self, *model_args, **model_kwargs):
#|            result = super().forward(*model_args, **model_kwargs)
#|            # Ineligible items contain no paired verifier loss.  Keep their
#|            # ordinary frozen-generator forward valid for the shared loop.
#|            dummy = result[0].new_zeros(())
#|            for name, parameter in self.projector.named_parameters():
#|                if name.startswith("iesfd_v10_") and parameter.requires_grad:
#|                    dummy = dummy + parameter.reshape(-1)[0] * 0.0
#|            return result[0] + dummy, result[1], result[2]
#|
#|    installed.Hybrid_MoE_LLaVA = EvidenceVerifierModel
#|    return installed, counts
#|
#|
#|def initialize_from_v8(model, module, paths, device, args, counts, memory_source=None):
#|    from peft import PeftModel
#|
#|    source_lora, source_projector = oiec._source_paths(paths, args) if memory_source is None else ('in-memory v8 LoRA', 'in-memory v8 controller')
#|    base_model = (
#|        model.llm.base_model.model
#|        if hasattr(model.llm, "base_model")
#|        else model.llm
#|    )
#|    model.llm = PeftModel.from_pretrained(
#|        base_model, str(source_lora), is_trainable=False
#|    ) if memory_source is None else memory_source.restore_lora(model.llm)
#|    model.llm.config.use_cache = False
#|    state = module.torch.load(source_projector, map_location=device) if memory_source is None else memory_source.projector
#|    incompatible = model.projector.load_state_dict(state, strict=False)
#|    invalid_missing = [
#|        key
#|        for key in incompatible.missing_keys
#|        if not key.startswith("iesfd_v10_")
#|    ]
#|    if incompatible.unexpected_keys or invalid_missing:
#|        raise RuntimeError(
#|            "clean-v8/IESFD-v10 projector mismatch: "
#|            f"unexpected={incompatible.unexpected_keys[:5]} "
#|            f"missing={invalid_missing[:5]}"
#|        )
#|
#|    for parameter in model.parameters():
#|        parameter.requires_grad = False
#|    verifier_names = []
#|    for name, parameter in model.projector.named_parameters():
#|        trainable = name.startswith("iesfd_v10_")
#|        parameter.requires_grad = trainable
#|        if trainable:
#|            parameter.data = parameter.data.float()
#|            verifier_names.append(name)
#|    if not verifier_names:
#|        raise RuntimeError("IESFD-v10 selected no verifier parameters")
#|
#|    class FrozenZeroCompletionHead(module.torch.nn.Module):
#|        def forward(self, state):
#|            return state.float().sum(dim=-1) * 0.0
#|
#|    model.oiec_completion_head = FrozenZeroCompletionHead().to(device)
#|    model.projector.training_graph_dropout = False
#|    model.projector.set_group_priors(
#|        [counts[name] for name in PHENOMENON_GROUPS]
#|    )
#|    semantic_norm = attach_semantic_readout(model.llm, model.projector)
#|    capture_norm = model.attach_oiec_capture()
#|    if semantic_norm != capture_norm:
#|        raise RuntimeError("IESFD-v10 capture/readout final norms differ")
#|    model.projector.set_trust_reference()
#|    model.oiec_l2sp_refs = {}
#|    model.oiec_trainable_names = tuple(verifier_names)
#|
#|    zero = module.torch.tensor(0.0, device=device)
#|    model.projector.last_iesfd_v10_positive_coverage = module.torch.zeros(
#|        3, device=device
#|    )
#|    model.projector.last_iesfd_v10_negative_coverage = module.torch.zeros(
#|        3, device=device
#|    )
#|    for name in (
#|        "last_iesfd_v10_positive",
#|        "last_iesfd_v10_negative",
#|        "last_iesfd_v10_gap",
#|        "last_iesfd_v10_loss",
#|        "last_iesfd_v10_anchor",
#|        "last_iesfd_v10_weighted",
#|    ):
#|        setattr(model.projector, name, zero)
#|    print(f"[iesfd-v10] source LoRA={source_lora}")
#|    print(f"[iesfd-v10] source projector={source_projector}")
#|    print(
#|        f"[iesfd-v10] final_norm={semantic_norm} generator_frozen=true "
#|        f"verifier_trainable={sum(p.numel() for p in model.projector.parameters() if p.requires_grad):,} "
#|        "negative=same-label_evidence-replacement graph_used_by_verifier=false "
#|        "inference=beam-generate_then_endogenous-verify"
#|    )
#|
#|
#|def build_optimizer(model, torch, args):
#|    verifier = [
#|        parameter
#|        for name, parameter in model.projector.named_parameters()
#|        if name.startswith("iesfd_v10_") and parameter.requires_grad
#|    ]
#|    if not verifier:
#|        raise RuntimeError("IESFD-v10 optimizer requires verifier parameters")
#|    if any(parameter.requires_grad for parameter in model.llm.parameters()):
#|        raise RuntimeError("IESFD-v10 must freeze the clean-v8 generator")
#|    return torch.optim.AdamW(
#|        [
#|            {
#|                "params": verifier,
#|                "lr": float(args.projector_lr),
#|                "weight_decay": float(args.projector_weight_decay),
#|            }
#|        ]
#|    )
#|
#|
#|def collect_metrics(model, torch):
#|    # This callback is monkey-patched onto ``oiec`` as well, so use the
#|    # pre-patch implementation for the base metrics.
#|    values = _BASE_COLLECT_METRICS(model, torch)
#|    projector = model.projector
#|    positive = projector.last_iesfd_v10_positive_coverage.detach().float().tolist()
#|    negative = projector.last_iesfd_v10_negative_coverage.detach().float().tolist()
#|    values.update(
#|        {
#|            "EV_P": f"{projector.last_iesfd_v10_positive.item():+.3f}",
#|            "EV_N": f"{projector.last_iesfd_v10_negative.item():+.3f}",
#|            "EV_G": f"{projector.last_iesfd_v10_gap.item():+.3f}",
#|            "EV_L": f"{projector.last_iesfd_v10_loss.item():.3f}",
#|            "EV_A": f"{projector.last_iesfd_v10_anchor.item():.3f}",
#|            "EV_W": f"{projector.last_iesfd_v10_weighted.item():.3e}",
#|            "EV_PC": "/".join(f"{value:+.2f}" for value in positive),
#|            "EV_NC": "/".join(f"{value:+.2f}" for value in negative),
#|        }
#|    )
#|    return values
#|
#|
#|def _write_proof(args):
#|    from paths_paper2 import Paper2Paths
#|
#|    paths = Paper2Paths.from_env()
#|    for epoch in range(1, args.epochs + 1):
#|        lora = paths.checkpoint_dir / (
#|            f"lora_epoch_{epoch}{oiec._TARGET_PROJECTOR_SUFFIX}"
#|        )
#|        if not lora.is_dir():
#|            continue
#|        proof = {
#|            "schema": "iesfd_v10_checkpoint_proof",
#|            "research_direction": "endogenous evidence-state modeling and faithful explanation decoding",
#|            "source": "clean_ra_rcgde_v8_innovation_point_1",
#|            "generator_frozen": True,
#|            "training_partition": "full_train",
#|            "training_records": 4578,
#|            "dev_split_used": False,
#|            "graph_used_by_innovation_point_2": False,
#|            "verifier_roles": ["image", "claim", "image_description"],
#|            "training_pair": "gold_vs_same_label_evidence_replacement",
#|            "inference": "beam_generate_then_endogenous_evidence_rerank",
#|            "baseline_candidate_retained": True,
#|            "warrant_manifest_sha256": file_sha256(args.warrant_manifest),
#|            "primary_metrics": ["F1@0", "F1@0.53", "F1@0.60"],
#|        }
#|        (lora / "iesfd_v10_proof.json").write_text(
#|            json.dumps(proof, ensure_ascii=False, indent=2) + "\n",
#|            encoding="utf-8",
#|        )
#|
#|
#|def main():
#|    args = build_parser().parse_args()
#|    for name in (
#|        "verifier_weight",
#|        "verifier_margin",
#|        "verifier_temperature",
#|        "verifier_anchor_weight",
#|        "projector_lr",
#|    ):
#|        if float(getattr(args, name)) <= 0.0:
#|            raise ValueError(f"IESFD-v10 requires positive --{name}")
#|    oiec.build_parser = build_parser
#|    oiec.install_oiec_training = install_iesfd_v10_training
#|    oiec.initialize_from_v8 = initialize_from_v8
#|    oiec.build_optimizer = build_optimizer
#|    oiec.collect_metrics = collect_metrics
#|    oiec.main()
#|    _write_proof(args)
#|
#|
#|if __name__ == "__main__":
#|    main()
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: train_llava_claim_oiec_stage_1.py ===
#|"""Train order-invariant evidence completion from the clean v8 checkpoint.
#|
#|The ordinary gold-answer objective remains primary.  On train-only tune
#|records with an audited silver warrant, a second teacher-forced pass replaces
#|that warrant with a partition-local, same-label hard mismatch.  A disposable
#|completion head ranks the mean-pooled complete answer state above its corrupted
#|counterpart.  Only selected upper-layer LoRA-B tensors are retained for
#|inference; the v8 projector stays byte-frozen and inference remains one pass.
#|"""
#|
#|from __future__ import annotations
#|
#|import hashlib
#|import json
#|import os
#|from pathlib import Path
#|import re
#|
#|
#|DEFAULT_CKPT_NAME = "checkpoints_llava_claim_oiec_v1"
#|PROJECTOR_SUFFIX = "_claim_oiec_v1"
#|_TARGET_CKPT_NAME = os.environ.get("OIEC_V1_CKPT_NAME", DEFAULT_CKPT_NAME)
#|_TARGET_PROJECTOR_SUFFIX = os.environ.get(
#|    "OIEC_V1_PROJECTOR_SUFFIX", PROJECTOR_SUFFIX
#|)
#|for _name in (
#|    "RGC_SR_V8_CKPT_NAME", "RGC_SR_V7_CKPT_NAME", "RGC_SR_V6_CKPT_NAME",
#|    "RGC_SR_V5_CKPT_NAME", "RGC_SR_V4_CKPT_NAME", "RGC_SR_CKPT_NAME",
#|    "PAPER2_CKPT_NAME", "PAPER2_DEFAULT_CKPT_NAME",
#|):
#|    os.environ[_name] = _TARGET_CKPT_NAME
#|for _name in (
#|    "RGC_SR_V8_PROJECTOR_SUFFIX", "RGC_SR_V7_PROJECTOR_SUFFIX",
#|    "RGC_SR_V6_PROJECTOR_SUFFIX", "RGC_SR_V5_PROJECTOR_SUFFIX",
#|    "RGC_SR_V4_PROJECTOR_SUFFIX", "RGC_SR_PROJECTOR_SUFFIX",
#|    "PAPER2_PROJECTOR_SUFFIX",
#|):
#|    os.environ[_name] = _TARGET_PROJECTOR_SUFFIX
#|
#|from cwct_warrant_data import load_warrant_map  # noqa: E402
#|from gesv_stage_2_counterfactual import sources_with_counterfactual_answer  # noqa: E402
#|from oiec_completion import (  # noqa: E402
#|    completion_pair_loss,
#|    configure_oiec_training_modes,
#|    file_sha256,
#|    mean_answer_state,
#|    replace_exact_warrant,
#|)
#|from rgc_semantic_readout import (  # noqa: E402
#|    attach_semantic_readout,
#|    find_final_decoder_norm,
#|)
#|from rgc_semantic_readout_stage_4 import PHENOMENON_GROUPS  # noqa: E402
#|from rgc_semantic_readout_stage_8 import collect_v8_metrics  # noqa: E402
#|import train_llava_claim_rgc_semantic_readout_stage_8 as v8  # noqa: E402
#|
#|
#|base_v4 = v8.base_v4
#|_LAYER_RE = re.compile(r"\.layers\.(\d+)\.")
#|
#|
#|def _answer_text(sample) -> str:
#|    for message in reversed(sample.get("conversations") or []):
#|        if str(message.get("from", "")).lower() in {"gpt", "assistant"}:
#|            value = str(message.get("value", ""))
#|            if value:
#|                return value
#|    raise ValueError(f"OIEC sample id={sample.get('id')} has no assistant answer")
#|
#|
#|def _parse_int_set(value: str) -> set[int]:
#|    try:
#|        output = {int(part.strip()) for part in value.split(",") if part.strip()}
#|    except ValueError as error:
#|        raise ValueError("OIEC layer indices must be comma-separated integers") from error
#|    if not output:
#|        raise ValueError("OIEC requires at least one train layer")
#|    return output
#|
#|
#|def _parse_modules(value: str) -> tuple[str, ...]:
#|    output = tuple(part.strip() for part in value.split(",") if part.strip())
#|    if not output:
#|        raise ValueError("OIEC requires at least one train module")
#|    return output
#|
#|
#|def build_parser():
#|    parser = v8.build_parser()
#|    parser.set_defaults(
#|        epochs=1,
#|        source_ckpt_root="checkpoints_llava_claim_rgc_semantic_readout_v8",
#|        source_epoch=1,
#|        source_projector_suffix="_claim_rgc_semantic_readout_v8",
#|        llm_lr=1e-7,
#|        projector_lr=0.0,
#|        graph_dropout=0.0,
#|        semantic_loss_weight=0.0,
#|        cf_loss_weight=0.0,
#|        alignment_nce_weight=0.0,
#|        alignment_final_nce_weight=0.0,
#|        decoder_alignment_weight=0.015,
#|        batch_size=1,
#|    )
#|    parser.add_argument("--warrant_cache", required=True)
#|    parser.add_argument("--warrant_manifest", required=True)
#|    parser.add_argument("--cache_source_json", required=True)
#|    parser.add_argument("--cache_partition_seed", type=int, default=2026)
#|    parser.add_argument("--completion_weight", type=float, default=0.05)
#|    parser.add_argument("--completion_margin", type=float, default=0.20)
#|    parser.add_argument("--completion_temperature", type=float, default=0.10)
#|    parser.add_argument("--completion_anchor_weight", type=float, default=0.25)
#|    parser.add_argument("--completion_head_lr", type=float, default=5e-5)
#|    parser.add_argument("--l2sp_weight", type=float, default=0.01)
#|    parser.add_argument("--minimum_donor_length_ratio", type=float, default=0.50)
#|    parser.add_argument("--train_layer_indices", default="20,24,28,31")
#|    parser.add_argument("--train_modules", default="o_proj,down_proj")
#|    parser.add_argument(
#|        "--use_full_train",
#|        action="store_true",
#|        help="Train on every audited training record instead of reserving its dev partition.",
#|    )
#|    return parser
#|
#|
#|def _source_paths(paths, args) -> tuple[Path, Path]:
#|    root = Path(args.source_ckpt_root)
#|    if not root.is_absolute():
#|        root = paths.output_root / root
#|    lora = root / f"lora_epoch_{args.source_epoch}{args.source_projector_suffix}"
#|    projector = root / f"proj_epoch_{args.source_epoch}{args.source_projector_suffix}.pth"
#|    if not lora.is_dir() or not projector.is_file():
#|        raise FileNotFoundError(f"missing clean-v8 source: {lora}, {projector}")
#|    if not ((lora / "adapter_model.safetensors").is_file() or (lora / "adapter_model.bin").is_file()):
#|        raise FileNotFoundError(f"missing source adapter weights under {lora}")
#|    return lora, projector
#|
#|
#|def _validate_manifest(args, paths) -> dict:
#|    cache = Path(args.warrant_cache).resolve()
#|    manifest_path = Path(args.warrant_manifest).resolve()
#|    source_json = Path(args.cache_source_json).resolve()
#|    if not cache.is_file() or not manifest_path.is_file() or not source_json.is_file():
#|        raise FileNotFoundError("OIEC warrant cache, manifest, or source JSON is missing")
#|    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
#|    if manifest.get("manifest_version") != "cwct_warrant_manifest_v2":
#|        raise RuntimeError("OIEC requires the audited CWCT warrant manifest v2")
#|    if manifest.get("test_accessed") is not False:
#|        raise RuntimeError("OIEC cache must assert test_accessed=false")
#|    if manifest.get("cache_sha256") != file_sha256(cache):
#|        raise RuntimeError("OIEC warrant cache hash mismatch")
#|    if manifest.get("input_sha256", {}).get("train_json") != file_sha256(source_json):
#|        raise RuntimeError("OIEC cache source JSON hash mismatch")
#|    graph = paths.resolve_output_path(args.concept_graph_cache or paths.train_concept_graph_cache)
#|    if manifest.get("input_sha256", {}).get("concept_graph") != file_sha256(graph):
#|        raise RuntimeError("OIEC train graph differs from warrant-cache source")
#|    if int(manifest.get("seed", -1)) != int(args.cache_partition_seed):
#|        raise RuntimeError("OIEC cache partition seed mismatch")
#|    eligible = int(manifest.get("quality_statistics", {}).get("eligible_by_partition", {}).get("tune", 0))
#|    if eligible <= 0:
#|        raise RuntimeError("OIEC cache has no eligible tune records")
#|    return manifest
#|
#|
#|def install_oiec_training(module, concept_graph_path, *, args, dataset_only=False):
#|    counts = {}
#|    if not dataset_only:
#|        _, counts = base_v4.load_phenomenon_groups(concept_graph_path)
#|        base_v4.base_train.make_semantic_readout_classes = v8.make_v8_readout_classes
#|        base_v4.base_train.config_from_args = v8.config_from_args
#|        module = base_v4.install_v4_training(module, concept_graph_path, args=args)
#|    torch = module.torch
#|    records = load_warrant_map(args.warrant_cache)
#|    BaseDataset = module.HybridDataset
#|    BaseModel = module.Hybrid_MoE_LLaVA
#|    original_collate = module.collate_fn
#|
#|    class OIECDataset(BaseDataset):
#|        def __init__(self, *dataset_args, **dataset_kwargs):
#|            super().__init__(*dataset_args, **dataset_kwargs)
#|            dataset_ids = {str(sample["id"]) for sample in self.samples}
#|            if dataset_ids != set(records):
#|                raise RuntimeError("OIEC dataset/cache ID sets differ")
#|            if not bool(args.use_full_train):
#|                self.samples = [
#|                    sample for sample in self.samples
#|                    if records[str(sample["id"])]["partition"] == "tune"
#|                ]
#|            eligible = sum(
#|                bool(records[str(sample["id"])]["auxiliary_eligible"])
#|                and float(records[str(sample["id"])]["same_label_hard_mismatch"]["length_ratio"])
#|                >= float(args.minimum_donor_length_ratio)
#|                for sample in self.samples
#|            )
#|            if not self.samples or eligible <= 0:
#|                raise RuntimeError("OIEC tune partition is empty or ineligible")
#|            print(
#|                f"[oiec-v1] partition={'full-train' if args.use_full_train else 'tune-only'} "
#|                f"records={len(self.samples)} eligible={eligible} "
#|                f"held_out={len(records)-len(self.samples)} order_filter=none"
#|            )
#|
#|        def __getitem__(self, index):
#|            item = super().__getitem__(index)
#|            sample = self.samples[index]
#|            record = records[str(sample["id"])]
#|            answer = _answer_text(sample)
#|            answer_hash = hashlib.sha256(answer.encode("utf-8")).hexdigest()
#|            if answer_hash != record.get("answer_sha256"):
#|                raise RuntimeError(f"OIEC answer/cache hash mismatch for {sample['id']}")
#|            eligible = bool(record["auxiliary_eligible"])
#|            if eligible:
#|                ratio = float(record["same_label_hard_mismatch"]["length_ratio"])
#|                eligible = ratio >= float(args.minimum_donor_length_ratio)
#|            else:
#|                ratio = 0.0
#|            negative_answer = replace_exact_warrant(answer, record) if eligible else answer
#|            sources = module.preprocess_multimodal(
#|                sources_with_counterfactual_answer(sample, negative_answer)
#|            )
#|            negative = self._preprocess_v1(sources)
#|            item["oiec_negative_ids"] = negative["input_ids"][0]
#|            item["oiec_negative_labels"] = negative["labels"][0]
#|            item["oiec_eligible"] = torch.tensor(eligible, dtype=torch.bool)
#|            item["oiec_length_ratio"] = torch.tensor(ratio, dtype=torch.float32)
#|            return item
#|
#|    def oiec_collate(batch):
#|        extras = (
#|            "oiec_negative_ids", "oiec_negative_labels", "oiec_eligible",
#|            "oiec_length_ratio",
#|        )
#|        stripped = []
#|        for item in batch:
#|            copied = dict(item)
#|            for key in extras:
#|                copied.pop(key)
#|            stripped.append(copied)
#|        output = original_collate(stripped)
#|        pad = torch.nn.utils.rnn.pad_sequence
#|        output["oiec_negative_ids"] = pad(
#|            [item["oiec_negative_ids"] for item in batch],
#|            batch_first=True, padding_value=0,
#|        )[:, :2048]
#|        output["oiec_negative_mask"] = output["oiec_negative_ids"].ne(0)
#|        output["oiec_negative_labels"] = pad(
#|            [item["oiec_negative_labels"] for item in batch],
#|            batch_first=True, padding_value=module.IGNORE_INDEX,
#|        )[:, :2048]
#|        output["oiec_eligible"] = torch.stack([item["oiec_eligible"] for item in batch])
#|        output["oiec_length_ratio"] = torch.stack([item["oiec_length_ratio"] for item in batch])
#|        return output
#|
#|    if dataset_only:
#|        module.HybridDataset = OIECDataset
#|        module.collate_fn = oiec_collate
#|        return module, counts
#|
#|    class OIECModel(BaseModel):
#|        def __init__(self, *model_args, **model_kwargs):
#|            super().__init__(*model_args, **model_kwargs)
#|            hidden_size = int(self.llm.config.hidden_size)
#|            self.oiec_completion_head = torch.nn.Sequential(
#|                torch.nn.LayerNorm(hidden_size),
#|                torch.nn.Linear(hidden_size, 1),
#|            )
#|            torch.nn.init.normal_(self.oiec_completion_head[-1].weight, std=0.01)
#|            torch.nn.init.zeros_(self.oiec_completion_head[-1].bias)
#|            self._oiec_hidden = None
#|            self._oiec_final_labels = None
#|            self._oiec_capture_handle = None
#|            self._oiec_input_handle = None
#|            self._oiec_secondary_total = None
#|            self._oiec_secondary_lm = None
#|
#|        def attach_oiec_capture(self):
#|            if self._oiec_capture_handle is not None or self._oiec_input_handle is not None:
#|                raise RuntimeError("OIEC final-norm capture is already attached")
#|            norm_name, norm = find_final_decoder_norm(self.llm)
#|
#|            def capture(_module, _inputs, output):
#|                self._oiec_hidden = output[0] if isinstance(output, tuple) else output
#|                return output
#|
#|            # Attached after the v8 semantic readout, so the completion loss
#|            # observes exactly the hidden states used by the decoder.
#|            self._oiec_capture_handle = norm.register_forward_hook(capture)
#|
#|            def capture_inputs(_module, _args, kwargs):
#|                self._oiec_final_labels = kwargs.get("labels")
#|
#|            self._oiec_input_handle = self.llm.register_forward_pre_hook(
#|                capture_inputs, with_kwargs=True
#|            )
#|            return norm_name
#|
#|        def forward(
#|            self, images, image_sizes, e_img, e_txt, e_desc, graph_feature,
#|            input_ids, attention_mask, labels, cf_labels, *,
#|            graph_semantic_ids, graph_semantic_mask, phenomenon_group,
#|            oiec_negative_ids, oiec_negative_mask, oiec_negative_labels,
#|            oiec_eligible, oiec_length_ratio,
#|        ):
#|            common = (images, image_sizes, e_img, e_txt, e_desc, graph_feature)
#|            semantic = dict(
#|                graph_semantic_ids=graph_semantic_ids,
#|                graph_semantic_mask=graph_semantic_mask,
#|                phenomenon_group=phenomenon_group,
#|            )
#|            self._oiec_hidden = None
#|            self._oiec_final_labels = None
#|            self._oiec_secondary_total = None
#|            self._oiec_secondary_lm = None
#|            full_total, full_lm, contrastive = super().forward(
#|                *common, input_ids, attention_mask, labels, cf_labels, **semantic
#|            )
#|            positive_hidden = self._oiec_hidden
#|            positive_labels = self._oiec_final_labels
#|            positive_intervention = getattr(
#|                self.projector.semantic_readout,
#|                "last_evidence_intervention",
#|                None,
#|            )
#|            zero = full_total.float() * 0.0
#|            auxiliary = zero
#|            causal_auxiliary = zero
#|            pair = zero.detach()
#|            gap = zero.detach()
#|            positive_score = zero.detach()
#|            negative_score = zero.detach()
#|            if bool(oiec_eligible.all().item()):
#|                if positive_hidden is None or positive_labels is None:
#|                    raise RuntimeError("OIEC captured no positive hidden state/labels")
#|                positive_state = mean_answer_state(
#|                    torch, positive_hidden, positive_labels, module.IGNORE_INDEX,
#|                    int(self.tokenizer.eos_token_id),
#|                )
#|                self._oiec_hidden = None
#|                self._oiec_final_labels = None
#|                secondary_ids = oiec_negative_ids
#|                secondary_mask = oiec_negative_mask
#|                secondary_labels = oiec_negative_labels
#|                prepare_secondary = getattr(
#|                    self,
#|                    "prepare_oiec_secondary_inputs",
#|                    None,
#|                )
#|                if callable(prepare_secondary):
#|                    prepared_secondary = prepare_secondary(
#|                        input_ids=input_ids,
#|                        attention_mask=attention_mask,
#|                        labels=labels,
#|                        positive_hidden=positive_hidden,
#|                        positive_labels=positive_labels,
#|                        fallback_ids=oiec_negative_ids,
#|                        fallback_mask=oiec_negative_mask,
#|                        fallback_labels=oiec_negative_labels,
#|                    )
#|                    if not isinstance(prepared_secondary, tuple) or len(prepared_secondary) != 3:
#|                        raise RuntimeError(
#|                            "OIEC secondary-input callback must return (ids, mask, labels)"
#|                        )
#|                    secondary_ids, secondary_mask, secondary_labels = prepared_secondary
#|                # The base OIEC path discards this LM loss and uses only the
#|                # hidden state.  Later revisions may expose the returned loss
#|                # through a causal auxiliary (for example, self-roll-in).
#|                secondary_total, secondary_lm, _secondary_contrastive = super().forward(
#|                    *common, secondary_ids, secondary_mask,
#|                    secondary_labels, cf_labels, **semantic
#|                )
#|                self._oiec_secondary_total = secondary_total
#|                self._oiec_secondary_lm = secondary_lm
#|                negative_hidden = self._oiec_hidden
#|                negative_labels = self._oiec_final_labels
#|                negative_intervention = getattr(
#|                    self.projector.semantic_readout,
#|                    "last_evidence_intervention",
#|                    None,
#|                )
#|                if negative_hidden is None or negative_labels is None:
#|                    raise RuntimeError("OIEC captured no negative hidden state/labels")
#|                negative_state = mean_answer_state(
#|                    torch, negative_hidden, negative_labels,
#|                    module.IGNORE_INDEX, int(self.tokenizer.eos_token_id),
#|                )
#|                causal_callback = getattr(
#|                    self, "compute_oiec_causal_auxiliary", None
#|                )
#|                if callable(causal_callback):
#|                    causal_auxiliary = causal_callback(
#|                        positive_hidden=positive_hidden,
#|                        positive_labels=positive_labels,
#|                        positive_intervention=positive_intervention,
#|                        negative_hidden=negative_hidden,
#|                        negative_labels=negative_labels,
#|                        negative_intervention=negative_intervention,
#|                    )
#|                    if causal_auxiliary.dim() != 0 or not bool(torch.isfinite(causal_auxiliary)):
#|                        raise RuntimeError("OIEC causal auxiliary must be a finite scalar")
#|                positive_score = self.oiec_completion_head(positive_state).reshape(())
#|                negative_score = self.oiec_completion_head(negative_state).reshape(())
#|                pair, gap = completion_pair_loss(
#|                    torch, positive_score, negative_score,
#|                    margin=float(args.completion_margin),
#|                    temperature=float(args.completion_temperature),
#|                    anchor_weight=float(args.completion_anchor_weight),
#|                )
#|                auxiliary = float(args.completion_weight) * pair + causal_auxiliary
#|            l2_terms = []
#|            for name, parameter in self.llm.named_parameters():
#|                reference = getattr(self, "oiec_l2sp_refs", {}).get(name)
#|                if reference is not None and parameter.requires_grad:
#|                    l2_terms.append(
#|                        (parameter.float() - reference.to(parameter.device)).pow(2).mean()
#|                    )
#|            l2sp = torch.stack(l2_terms).mean() if l2_terms else zero
#|            total = full_total + auxiliary + float(args.l2sp_weight) * l2sp
#|            self.projector.last_oiec_pair = pair.detach()
#|            self.projector.last_oiec_auxiliary = auxiliary.detach()
#|            self.projector.last_oiec_gap = gap.detach()
#|            self.projector.last_oiec_positive = positive_score.detach()
#|            self.projector.last_oiec_negative = negative_score.detach()
#|            self.projector.last_oiec_l2sp = l2sp.detach()
#|            self.projector.last_oiec_eligible = oiec_eligible.float().mean().detach()
#|            self.projector.last_oiec_length_ratio = oiec_length_ratio.float().mean().detach()
#|            return total, full_lm, contrastive
#|
#|        def train(self, mode: bool = True):
#|            super().train(mode)
#|            configure_oiec_training_modes(
#|                torch, self.llm, self.projector,
#|                self.oiec_completion_head, mode,
#|            )
#|            return self
#|
#|    module.HybridDataset = OIECDataset
#|    module.collate_fn = oiec_collate
#|    module.Hybrid_MoE_LLaVA = OIECModel
#|    return module, counts
#|
#|
#|def initialize_from_v8(model, module, paths, device, args, counts):
#|    from peft import PeftModel
#|
#|    source_lora, source_projector = _source_paths(paths, args)
#|    base_model = model.llm.base_model.model if hasattr(model.llm, "base_model") else model.llm
#|    model.llm = PeftModel.from_pretrained(base_model, str(source_lora), is_trainable=True)
#|    if hasattr(model.llm, "enable_input_require_grads"):
#|        model.llm.enable_input_require_grads()
#|    model.llm.config.use_cache = False
#|    state = module.torch.load(source_projector, map_location=device)
#|    incompatible = model.projector.load_state_dict(state, strict=True)
#|    if incompatible.missing_keys or incompatible.unexpected_keys:
#|        raise RuntimeError("clean-v8/OIEC projector contract mismatch")
#|
#|    for parameter in model.parameters():
#|        parameter.requires_grad = False
#|    layers = _parse_int_set(args.train_layer_indices)
#|    modules = _parse_modules(args.train_modules)
#|    selected = []
#|    available_layers = set()
#|    for name, parameter in model.llm.named_parameters():
#|        match = _LAYER_RE.search(name)
#|        if match and "lora_" in name:
#|            available_layers.add(int(match.group(1)))
#|        trainable = bool(
#|            match and int(match.group(1)) in layers and "lora_B" in name
#|            and any(f".{target}." in name for target in modules)
#|        )
#|        parameter.requires_grad = trainable
#|        if trainable:
#|            if parameter.dtype != module.torch.float32:
#|                parameter.data = parameter.data.float()
#|            selected.append(name)
#|    unknown = layers - available_layers
#|    if unknown or not selected:
#|        raise RuntimeError(f"OIEC unavailable layers={sorted(unknown)} trainable={len(selected)}")
#|    for parameter in model.oiec_completion_head.parameters():
#|        parameter.requires_grad = True
#|    for parameter in model.projector.parameters():
#|        parameter.requires_grad = False
#|    model.projector.training_graph_dropout = False
#|    model.projector.set_group_priors([counts[name] for name in PHENOMENON_GROUPS])
#|    semantic_norm = attach_semantic_readout(model.llm, model.projector)
#|    capture_norm = model.attach_oiec_capture()
#|    if semantic_norm != capture_norm:
#|        raise RuntimeError("OIEC capture and semantic readout use different norms")
#|    model.projector.set_trust_reference()
#|    model.oiec_l2sp_refs = {
#|        name: parameter.detach().float().clone()
#|        for name, parameter in model.llm.named_parameters()
#|        if parameter.requires_grad
#|    }
#|
#|    def clear_frozen_projector_pending_state():
#|        with module.torch.no_grad():
#|            for name in ("_dro_pending_loss", "_dro_pending_count", "_trust_pending_constraint"):
#|                value = getattr(model.projector, name, None)
#|                if value is not None:
#|                    value.zero_()
#|
#|    model.projector.on_optimizer_step = clear_frozen_projector_pending_state
#|    model.oiec_trainable_names = tuple(selected)
#|    print(f"[oiec-v1] source LoRA={source_lora}")
#|    print(f"[oiec-v1] source projector={source_projector}")
#|    print(
#|        f"[oiec-v1] final_norm={semantic_norm} layers={sorted(layers)} modules={modules} "
#|        f"lora_trainable={sum(p.numel() for p in model.llm.parameters() if p.requires_grad):,} "
#|        f"head_trainable={sum(p.numel() for p in model.oiec_completion_head.parameters()):,} "
#|        "projector_frozen=true order_filter=none inference_path=v8-one-pass"
#|    )
#|
#|
#|def build_optimizer(model, torch, args):
#|    lora = [parameter for parameter in model.llm.parameters() if parameter.requires_grad]
#|    head = [parameter for parameter in model.oiec_completion_head.parameters() if parameter.requires_grad]
#|    if not lora or not head:
#|        raise RuntimeError("OIEC requires both LoRA-B and completion-head parameters")
#|    return torch.optim.AdamW(
#|        [
#|            {"params": lora, "lr": float(args.llm_lr), "weight_decay": 0.0},
#|            {"params": head, "lr": float(args.completion_head_lr), "weight_decay": 1e-4},
#|        ]
#|    )
#|
#|
#|def collect_metrics(model, torch):
#|    del torch
#|    projector = model.projector
#|    return {
#|        "OI_P": f"{projector.last_oiec_pair.item():.3f}",
#|        "OI_A": f"{projector.last_oiec_auxiliary.item():.3e}",
#|        "OI_G": f"{projector.last_oiec_gap.item():+.3f}",
#|        "OI_POS": f"{projector.last_oiec_positive.item():+.3f}",
#|        "OI_NEG": f"{projector.last_oiec_negative.item():+.3f}",
#|        "OI_L2": f"{projector.last_oiec_l2sp.item():.3e}",
#|        "OI_ON": f"{projector.last_oiec_eligible.item():.0f}",
#|        "OI_LEN": f"{projector.last_oiec_length_ratio.item():.2f}",
#|    }
#|
#|
#|def main() -> None:
#|    args = build_parser().parse_args()
#|    if args.num_tokens != 0 or args.batch_size != 1:
#|        raise ValueError("OIEC v1 requires num_tokens=0 and batch_size=1")
#|    for name in ("completion_weight", "completion_margin", "completion_temperature", "completion_head_lr"):
#|        if float(getattr(args, name)) <= 0.0:
#|            raise ValueError(f"{name} must be positive")
#|    if not 0.0 <= args.completion_anchor_weight <= 1.0:
#|        raise ValueError("completion_anchor_weight must be in [0, 1]")
#|    if not 0.0 <= args.l2sp_weight <= 1.0:
#|        raise ValueError("l2sp_weight must be in [0, 1]")
#|    if not 0.5 <= args.minimum_donor_length_ratio <= 1.0:
#|        raise ValueError("minimum_donor_length_ratio must be in [0.5, 1.0]")
#|    args.warrant_cache = str(Path(args.warrant_cache).resolve())
#|    args.warrant_manifest = str(Path(args.warrant_manifest).resolve())
#|    args.cache_source_json = str(Path(args.cache_source_json).resolve())
#|    from paths_paper2 import Paper2Paths
#|    paths = Paper2Paths.from_env()
#|    manifest = _validate_manifest(args, paths)
#|    counts = {}
#|
#|    def installer(module, concept_graph_path, **_kwargs):
#|        installed, values = install_oiec_training(module, concept_graph_path, args=args)
#|        counts.update(values)
#|        return installed
#|
#|    def initializer(model, module, paths, device):
#|        initialize_from_v8(model, module, paths, device, args, counts)
#|        zero = module.torch.tensor(0.0, device=device)
#|        for name in (
#|            "last_oiec_pair", "last_oiec_auxiliary", "last_oiec_gap",
#|            "last_oiec_positive", "last_oiec_negative", "last_oiec_l2sp",
#|            "last_oiec_eligible", "last_oiec_length_ratio",
#|        ):
#|            setattr(model.projector, name, zero)
#|
#|    base_v4.base_train.graph_train.train(
#|        args,
#|        install_training=installer,
#|        initialize_model=initializer,
#|        build_optimizer=build_optimizer,
#|        extra_batch_keys=(
#|            "graph_semantic_ids", "graph_semantic_mask", "phenomenon_group",
#|            "oiec_negative_ids", "oiec_negative_mask", "oiec_negative_labels",
#|            "oiec_eligible", "oiec_length_ratio",
#|        ),
#|        collect_metrics=collect_metrics,
#|    )
#|
#|    for epoch in range(1, args.epochs + 1):
#|        lora = paths.checkpoint_dir / f"lora_epoch_{epoch}{_TARGET_PROJECTOR_SUFFIX}"
#|        if not lora.is_dir():
#|            raise FileNotFoundError(f"OIEC trainer did not save {lora}")
#|        proof = {
#|            "version": "oiec_checkpoint_proof_v1",
#|            "method": "order_invariant_same_label_evidence_completion",
#|            "warrant_cache_sha256": manifest["cache_sha256"],
#|            "warrant_manifest_sha256": file_sha256(args.warrant_manifest),
#|            "source_root": args.source_ckpt_root,
#|            "source_epoch": args.source_epoch,
#|            "source_suffix": args.source_projector_suffix,
#|            "training_partition": "full_train" if args.use_full_train else "tune",
#|            "dev_used_for_optimization": bool(args.use_full_train),
#|            "test_accessed": False,
#|            "completion_weight": args.completion_weight,
#|            "completion_margin": args.completion_margin,
#|            "completion_temperature": args.completion_temperature,
#|            "completion_anchor_weight": args.completion_anchor_weight,
#|            "minimum_donor_length_ratio": args.minimum_donor_length_ratio,
#|            "l2sp_weight": args.l2sp_weight,
#|            "train_layer_indices": sorted(_parse_int_set(args.train_layer_indices)),
#|            "train_modules": list(_parse_modules(args.train_modules)),
#|            "completion_head_saved": False,
#|            "inference": "single_model_single_generation_v8_path",
#|        }
#|        proof_path = lora / "oiec_proof.json"
#|        proof_path.write_text(
#|            json.dumps(proof, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
#|            encoding="utf-8",
#|        )
#|        print(f"[oiec-v1] saved proof={proof_path}")
#|
#|
#|if __name__ == "__main__":
#|    main()
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: train_llava_claim_rgc_semantic_readout.py ===
#|"""Train token-free graph-conditioned semantic readout (RGC-SR v2)."""
#|
#|from __future__ import annotations
#|
#|import argparse
#|import os
#|
#|
#|DEFAULT_CKPT_NAME = "checkpoints_llava_claim_rgc_semantic_readout_v2"
#|PROJECTOR_SUFFIX = "_claim_rgc_semantic_readout_v2"
#|os.environ["PAPER2_CKPT_NAME"] = os.environ.get(
#|    "RGC_SR_CKPT_NAME",
#|    DEFAULT_CKPT_NAME,
#|)
#|os.environ["PAPER2_PROJECTOR_SUFFIX"] = os.environ.get(
#|    "RGC_SR_PROJECTOR_SUFFIX",
#|    PROJECTOR_SUFFIX,
#|)
#|
#|from concept_graph_integration import (  # noqa: E402
#|    GRAPH_FEATURE_DIM,
#|    require_concept_graph_cache,
#|)
#|from rgc_semantic_readout import (  # noqa: E402
#|    SemanticReadoutConfig,
#|    attach_semantic_readout,
#|    collect_semantic_readout_metrics,
#|    load_graph_semantic_text_map,
#|    make_semantic_readout_classes,
#|    masked_mean_token_embeddings,
#|    safe_token_embeddings,
#|    tokenize_graph_semantic_text,
#|)
#|import train_llava_claim_graphprompt as graph_train  # noqa: E402
#|
#|
#|def config_from_args(args) -> SemanticReadoutConfig:
#|    return SemanticReadoutConfig(
#|        relation_dim=args.relation_dim,
#|        condition_dim=args.condition_dim,
#|        readout_rank=args.readout_rank,
#|        controller_dropout=args.controller_dropout,
#|        graph_dropout=args.graph_dropout,
#|        gate_init=args.readout_gate_init,
#|        gate_cap=args.readout_gate_cap,
#|        rank_modulation_cap=args.rank_modulation_cap,
#|        residual_norm_ratio=args.readout_residual_ratio,
#|        semantic_max_length=args.semantic_max_length,
#|    )
#|
#|
#|def install_semantic_readout_training(
#|    module,
#|    concept_graph_path,
#|    *,
#|    args,
#|    **_kwargs,
#|):
#|    import torch
#|    import torch.nn as nn
#|
#|    _, graph_features, _ = require_concept_graph_cache(
#|        concept_graph_path,
#|        split="train",
#|    )
#|    semantic_texts = load_graph_semantic_text_map(concept_graph_path)
#|    config = config_from_args(args)
#|    _, GraphSemanticController = make_semantic_readout_classes(
#|        torch,
#|        nn,
#|    )
#|    BaseDataset = module.HybridDataset
#|    BaseModel = module.Hybrid_MoE_LLaVA
#|    original_collate = module.collate_fn
#|
#|    class SemanticReadoutDataset(BaseDataset):
#|        def __getitem__(self, index):
#|            item = super().__getitem__(index)
#|            sample_id = self.samples[index]["id"]
#|            item["graph_feature"] = graph_features.get(
#|                sample_id,
#|                torch.zeros(GRAPH_FEATURE_DIM, dtype=torch.float32),
#|            )
#|            semantic_ids, semantic_mask = tokenize_graph_semantic_text(
#|                self.tokenizer,
#|                semantic_texts.get(sample_id, ""),
#|                config.semantic_max_length,
#|            )
#|            item["graph_semantic_ids"] = semantic_ids
#|            item["graph_semantic_mask"] = semantic_mask
#|            return item
#|
#|    def semantic_readout_collate(batch):
#|        output = original_collate(batch)
#|        output["graph_feature"] = torch.stack(
#|            [item["graph_feature"] for item in batch]
#|        )
#|        output["graph_semantic_ids"] = torch.stack(
#|            [item["graph_semantic_ids"] for item in batch]
#|        )
#|        output["graph_semantic_mask"] = torch.stack(
#|            [item["graph_semantic_mask"] for item in batch]
#|        )
#|        return output
#|
#|    class TrainingSemanticController(GraphSemanticController):
#|        def __init__(self, hidden_size, num_tokens=0):
#|            super().__init__(
#|                hidden_size,
#|                num_tokens,
#|                config,
#|                training_graph_dropout=True,
#|            )
#|
#|    class SemanticReadoutLLaVA(BaseModel):
#|        def forward(
#|            self,
#|            images,
#|            image_sizes,
#|            e_img,
#|            e_txt,
#|            e_desc,
#|            graph_feature,
#|            input_ids,
#|            attention_mask,
#|            labels,
#|            cf_labels,
#|            graph_semantic_ids=None,
#|            graph_semantic_mask=None,
#|            **_kwargs,
#|        ):
#|            base_model = (
#|                self.llm.base_model.model
#|                if hasattr(self.llm, "base_model")
#|                else self.llm.model
#|            )
#|            embed_layer = (
#|                base_model.get_input_embeddings()
#|                if hasattr(base_model, "get_input_embeddings")
#|                else base_model.get_model().embed_tokens
#|            )
#|            if graph_semantic_ids is None or graph_semantic_mask is None:
#|                semantic_token_embeddings = e_img.new_zeros(
#|                    (e_img.size(0), 1, self.hidden_size)
#|                )
#|                semantic_token_mask = torch.zeros(
#|                    (e_img.size(0), 1),
#|                    device=e_img.device,
#|                    dtype=torch.bool,
#|                )
#|            else:
#|                with torch.no_grad():
#|                    (
#|                        semantic_token_embeddings,
#|                        semantic_token_mask,
#|                    ) = safe_token_embeddings(
#|                        embed_layer,
#|                        graph_semantic_ids,
#|                        graph_semantic_mask,
#|                        vocab_size=self.vocab_size,
#|                    )
#|                semantic_token_embeddings = (
#|                    semantic_token_embeddings.detach()
#|                )
#|
#|            condition, balance_loss = self.projector(
#|                e_img,
#|                e_txt,
#|                e_desc,
#|                graph_feature=graph_feature,
#|                semantic_token_embeddings=semantic_token_embeddings,
#|                semantic_mask=semantic_token_mask,
#|            )
#|            main_drop_fraction = self.projector.last_graph_drop_fraction
#|            main_router_weights = self.projector.last_router_weights
#|            with torch.no_grad():
#|                counter_condition = self.projector.encode_condition(
#|                    torch.zeros_like(e_img),
#|                    e_txt,
#|                    e_desc,
#|                    torch.zeros_like(graph_feature),
#|                    torch.zeros_like(semantic_token_embeddings),
#|                    torch.zeros_like(semantic_token_mask),
#|                    activate=False,
#|                )
#|            # Restore the graph-connected condition for the final readout hook.
#|            self.projector.semantic_readout.set_condition(condition)
#|            self.projector.last_graph_prompt_norm = (
#|                condition.detach().float().norm(dim=-1).mean()
#|            )
#|            self.projector.last_graph_drop_fraction = main_drop_fraction
#|            self.projector.last_router_weights = main_router_weights
#|            contrastive_loss = module.safe_contrastive_loss(
#|                condition.unsqueeze(1),
#|                counter_condition.detach().unsqueeze(1),
#|                cf_labels,
#|            )
#|
#|            prepared_out = base_model.prepare_inputs_labels_for_multimodal(
#|                input_ids=input_ids,
#|                position_ids=None,
#|                attention_mask=attention_mask,
#|                past_key_values=None,
#|                labels=labels,
#|                images=images,
#|                image_sizes=image_sizes,
#|            )
#|            llava_mask, llava_embeds, llava_labels = module.unpack_prepared(
#|                prepared_out,
#|                self.hidden_size,
#|            )
#|            if isinstance(llava_embeds, list):
#|                llava_embeds = torch.cat(llava_embeds, dim=0)
#|            if isinstance(llava_mask, list):
#|                llava_mask = torch.cat(llava_mask, dim=0)
#|            if isinstance(llava_labels, list):
#|                llava_labels = torch.cat(llava_labels, dim=0)
#|
#|            batch_size = e_img.size(0)
#|            if llava_embeds is None:
#|                safe_ids = input_ids.clone()
#|                safe_ids[safe_ids < 0] = 0
#|                safe_ids[safe_ids >= self.vocab_size] = 0
#|                llava_embeds = embed_layer(safe_ids)
#|            if llava_embeds.dim() == 2:
#|                llava_embeds = llava_embeds.unsqueeze(0)
#|            llava_seq = llava_embeds.size(1)
#|            llava_mask = (
#|                llava_mask.reshape(-1)[: batch_size * llava_seq].reshape(
#|                    batch_size,
#|                    llava_seq,
#|                )
#|                if llava_mask is not None
#|                else torch.ones(
#|                    (batch_size, llava_seq),
#|                    device=e_img.device,
#|                    dtype=torch.long,
#|                )
#|            )
#|            llava_labels = (
#|                llava_labels.reshape(-1)[: batch_size * llava_seq].reshape(
#|                    batch_size,
#|                    llava_seq,
#|                )
#|                if llava_labels is not None
#|                else torch.full(
#|                    (batch_size, llava_seq),
#|                    module.IGNORE_INDEX,
#|                    device=e_img.device,
#|                    dtype=torch.long,
#|                )
#|            )
#|
#|            label_mask = llava_labels.ne(module.IGNORE_INDEX)
#|            with torch.no_grad():
#|                semantic_target, target_present = masked_mean_token_embeddings(
#|                    embed_layer,
#|                    llava_labels,
#|                    label_mask,
#|                    vocab_size=self.vocab_size,
#|                )
#|            semantic_loss = self.projector.semantic_alignment_loss(
#|                condition,
#|                semantic_target,
#|                target_present,
#|            )
#|
#|            # Concept-graph information is not concatenated as prompt tokens.
#|            inputs_embeds = llava_embeds.to(torch.bfloat16)
#|            final_mask = (llava_mask.long() > 0).long()
#|            final_labels = llava_labels.long()
#|            # Optional graph-free evidence plans used by later IESFD revisions.
#|            # Keeping this hook here makes the exact same plan tokens visible to
#|            # teacher-forced training and autoregressive inference without
#|            # changing the token-free RGC-SR/IESFD-v1-v8 default path.
#|            augment_evidence_plan = getattr(
#|                self.projector,
#|                "augment_evidence_plan",
#|                None,
#|            )
#|            if callable(augment_evidence_plan):
#|                inputs_embeds, final_mask, final_labels = augment_evidence_plan(
#|                    inputs_embeds,
#|                    final_mask,
#|                    final_labels,
#|                    ignore_index=module.IGNORE_INDEX,
#|                )
#|            limit = self.max_seq_len - 8
#|            if inputs_embeds.size(1) > limit:
#|                inputs_embeds = inputs_embeds[:, -limit:, :]
#|                final_mask = final_mask[:, -limit:]
#|                final_labels = final_labels[:, -limit:]
#|            remainder = inputs_embeds.size(1) % 8
#|            if remainder:
#|                pad = 8 - remainder
#|                inputs_embeds = torch.nn.functional.pad(
#|                    inputs_embeds,
#|                    (0, 0, 0, pad),
#|                )
#|                final_mask = torch.nn.functional.pad(
#|                    final_mask,
#|                    (0, pad),
#|                    value=0,
#|                )
#|                final_labels = torch.nn.functional.pad(
#|                    final_labels,
#|                    (0, pad),
#|                    value=module.IGNORE_INDEX,
#|                )
#|            inputs_embeds = torch.nan_to_num(
#|                inputs_embeds,
#|                nan=0.0,
#|                posinf=100.0,
#|                neginf=-100.0,
#|            ).clamp(-100.0, 100.0)
#|
#|            prepare_token_scale = getattr(
#|                self.projector,
#|                "prepare_readout_token_scale",
#|                None,
#|            )
#|            if callable(prepare_token_scale):
#|                prepare_token_scale(final_labels, module.IGNORE_INDEX)
#|            outputs = self.llm(
#|                inputs_embeds=inputs_embeds.contiguous(),
#|                attention_mask=final_mask.contiguous(),
#|                labels=final_labels.contiguous(),
#|            )
#|            counterfactual_language_loss = outputs.loss.new_zeros(())
#|            compute_counterfactual_language_loss = getattr(
#|                self.projector,
#|                "counterfactual_language_objective",
#|                None,
#|            )
#|            if callable(compute_counterfactual_language_loss):
#|                counterfactual_language_loss = (
#|                    compute_counterfactual_language_loss(
#|                        llm=self.llm,
#|                        embed_layer=embed_layer,
#|                        inputs_embeds=inputs_embeds,
#|                        attention_mask=final_mask,
#|                        labels=final_labels,
#|                        factual_logits=outputs.logits,
#|                        ignore_index=module.IGNORE_INDEX,
#|                    )
#|                )
#|                counterfactual_language_loss = torch.nan_to_num(
#|                    counterfactual_language_loss
#|                )
#|            clear_token_scale = getattr(
#|                self.projector,
#|                "clear_readout_token_scale",
#|                None,
#|            )
#|            if callable(clear_token_scale):
#|                clear_token_scale()
#|            lm_loss = outputs.loss
#|            if torch.isnan(lm_loss) or torch.isinf(lm_loss):
#|                lm_loss = torch.tensor(
#|                    0.0,
#|                    device=e_img.device,
#|                    requires_grad=True,
#|                )
#|            contrastive_loss = torch.nan_to_num(contrastive_loss)
#|            semantic_loss = torch.nan_to_num(semantic_loss)
#|            extra_language_loss = lm_loss.new_zeros(())
#|            compute_extra_language_loss = getattr(
#|                self.projector,
#|                "extra_language_loss",
#|                None,
#|            )
#|            if callable(compute_extra_language_loss):
#|                extra_language_loss = compute_extra_language_loss(
#|                    outputs.logits,
#|                    final_labels,
#|                    module.IGNORE_INDEX,
#|                )
#|                extra_language_loss = torch.nan_to_num(extra_language_loss)
#|            decoder_alignment_loss = lm_loss.new_zeros(())
#|            compute_decoder_alignment_loss = getattr(
#|                self.projector,
#|                "decoder_alignment_loss",
#|                None,
#|            )
#|            if callable(compute_decoder_alignment_loss):
#|                decoder_alignment_loss = compute_decoder_alignment_loss(
#|                    final_labels,
#|                    module.IGNORE_INDEX,
#|                )
#|                decoder_alignment_loss = torch.nan_to_num(
#|                    decoder_alignment_loss
#|                )
#|            parameter_trust_loss = lm_loss.new_zeros(())
#|            compute_parameter_trust_loss = getattr(
#|                self.projector,
#|                "parameter_trust_loss",
#|                None,
#|            )
#|            if callable(compute_parameter_trust_loss):
#|                parameter_trust_loss = compute_parameter_trust_loss()
#|                parameter_trust_loss = torch.nan_to_num(
#|                    parameter_trust_loss
#|                )
#|            total = (
#|                lm_loss
#|                + args.cf_loss_weight * contrastive_loss
#|                + args.semantic_loss_weight * semantic_loss
#|                + balance_loss
#|                + extra_language_loss
#|                + decoder_alignment_loss
#|                + parameter_trust_loss
#|                + counterfactual_language_loss
#|            )
#|            return total, lm_loss, contrastive_loss
#|
#|    module.MoE_LLM_Projector = TrainingSemanticController
#|    module.HybridDataset = SemanticReadoutDataset
#|    module.collate_fn = semantic_readout_collate
#|    module.Hybrid_MoE_LLaVA = SemanticReadoutLLaVA
#|    return module
#|
#|
#|def build_optimizer(model, torch, args):
#|    projector_parameters = [
#|        parameter
#|        for parameter in model.projector.parameters()
#|        if parameter.requires_grad
#|    ]
#|    llm_parameters = [
#|        parameter
#|        for parameter in model.llm.parameters()
#|        if parameter.requires_grad
#|    ]
#|    return torch.optim.AdamW(
#|        [
#|            {
#|                "params": projector_parameters,
#|                "lr": args.projector_lr,
#|                "weight_decay": args.projector_weight_decay,
#|            },
#|            {
#|                "params": llm_parameters,
#|                "lr": args.llm_lr,
#|                "weight_decay": 0.0,
#|            },
#|        ]
#|    )
#|
#|
#|def build_parser() -> argparse.ArgumentParser:
#|    parser = argparse.ArgumentParser()
#|    parser.add_argument("--epochs", type=int, default=4)
#|    parser.add_argument("--device", type=str, default="cuda:0")
#|    parser.add_argument("--batch_size", type=int, default=1)
#|    parser.add_argument("--accum_steps", type=int, default=16)
#|    parser.add_argument("--num_workers", type=int, default=2)
#|    parser.add_argument("--num_tokens", type=int, default=0)
#|    parser.add_argument("--warmup_ratio", type=float, default=0.05)
#|    parser.add_argument("--projector_lr", type=float, default=3e-4)
#|    parser.add_argument("--projector_weight_decay", type=float, default=0.01)
#|    parser.add_argument("--llm_lr", type=float, default=5e-5)
#|    parser.add_argument("--graph_dropout", type=float, default=0.10)
#|    parser.add_argument("--graph_gate_init", type=float, default=0.25)
#|    parser.add_argument("--graph_gate_cap", type=float, default=0.75)
#|    parser.add_argument("--concept_graph_cache", type=str, default=None)
#|    parser.add_argument("--seed", type=int, default=42)
#|    parser.add_argument("--relation_dim", type=int, default=256)
#|    parser.add_argument("--condition_dim", type=int, default=256)
#|    parser.add_argument("--controller_dropout", type=float, default=0.10)
#|    parser.add_argument("--readout_rank", type=int, default=32)
#|    parser.add_argument("--readout_gate_init", type=float, default=0.08)
#|    parser.add_argument("--readout_gate_cap", type=float, default=0.25)
#|    parser.add_argument("--rank_modulation_cap", type=float, default=0.50)
#|    parser.add_argument("--readout_residual_ratio", type=float, default=0.08)
#|    parser.add_argument("--semantic_max_length", type=int, default=96)
#|    parser.add_argument("--semantic_loss_weight", type=float, default=0.05)
#|    parser.add_argument("--cf_loss_weight", type=float, default=0.02)
#|    return parser
#|
#|
#|def main() -> None:
#|    args = build_parser().parse_args()
#|    if args.num_tokens != 0:
#|        raise ValueError("RGC-SemanticReadout forbids latent prompt tokens")
#|
#|    def installer(module, concept_graph_path, **kwargs):
#|        del kwargs
#|        return install_semantic_readout_training(
#|            module,
#|            concept_graph_path,
#|            args=args,
#|        )
#|
#|    def initialize_model(model, _module, _paths, _device):
#|        if model.num_tokens != 0 or model.projector.num_tokens != 0:
#|            raise RuntimeError("RGC-SemanticReadout token-free contract failed")
#|        norm_name = attach_semantic_readout(model.llm, model.projector)
#|        adapter_parameters = sum(
#|            parameter.numel()
#|            for parameter in model.projector.semantic_readout.parameters()
#|            if parameter.requires_grad
#|        )
#|        print(
#|            "[rgc-semantic-readout] graph_tokens=0; "
#|            f"final_norm={norm_name}; rank={args.readout_rank}; "
#|            f"adapter_params={adapter_parameters}; "
#|            "LM gradients train the graph controller directly"
#|        )
#|
#|    graph_train.train(
#|        args,
#|        install_training=installer,
#|        initialize_model=initialize_model,
#|        build_optimizer=build_optimizer,
#|        extra_batch_keys=("graph_semantic_ids", "graph_semantic_mask"),
#|        collect_metrics=collect_semantic_readout_metrics,
#|    )
#|
#|
#|if __name__ == "__main__":
#|    main()
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: train_llava_claim_rgc_semantic_readout_stage_4.py ===
#|"""Train token-free semantic readout v4 with automatic GroupDRO."""
#|
#|from __future__ import annotations
#|
#|import json
#|import os
#|from pathlib import Path
#|
#|
#|DEFAULT_CKPT_NAME = "checkpoints_llava_claim_rgc_semantic_readout_v4"
#|PROJECTOR_SUFFIX = "_claim_rgc_semantic_readout_v4"
#|os.environ["RGC_SR_CKPT_NAME"] = os.environ.get(
#|    "RGC_SR_V4_CKPT_NAME",
#|    DEFAULT_CKPT_NAME,
#|)
#|os.environ["RGC_SR_PROJECTOR_SUFFIX"] = os.environ.get(
#|    "RGC_SR_V4_PROJECTOR_SUFFIX",
#|    PROJECTOR_SUFFIX,
#|)
#|
#|import train_llava_claim_rgc_semantic_readout as base_train  # noqa: E402
#|from rgc_semantic_readout import attach_semantic_readout  # noqa: E402
#|from rgc_semantic_readout_stage_4 import (  # noqa: E402
#|    PHENOMENON_GROUPS,
#|    PHENOMENON_TO_ID,
#|    PhenomenonBalancedReadoutConfig,
#|    collect_v4_metrics,
#|    make_v4_readout_classes,
#|    select_phenomenon,
#|)
#|
#|
#|def config_from_args(args) -> PhenomenonBalancedReadoutConfig:
#|    return PhenomenonBalancedReadoutConfig(
#|        relation_dim=args.relation_dim,
#|        condition_dim=args.condition_dim,
#|        readout_rank=args.readout_rank,
#|        controller_dropout=args.controller_dropout,
#|        graph_dropout=args.graph_dropout,
#|        gate_init=args.readout_gate_init,
#|        gate_cap=args.readout_gate_cap,
#|        rank_modulation_cap=args.rank_modulation_cap,
#|        residual_norm_ratio=args.readout_residual_ratio,
#|        semantic_max_length=args.semantic_max_length,
#|        graph_gate_floor=args.graph_residual_gate_floor,
#|        graph_gate_cap=args.graph_residual_gate_cap,
#|        graph_gate_init=args.graph_residual_gate_init,
#|        semantic_gate_floor=args.semantic_residual_gate_floor,
#|        semantic_gate_cap=args.semantic_residual_gate_cap,
#|        semantic_gate_init=args.semantic_residual_gate_init,
#|        label_token_count=args.label_token_count,
#|        label_readout_scale=args.label_readout_scale,
#|        label_loss_weight=args.label_loss_weight,
#|        dro_eta=args.dro_eta,
#|        dro_ema=args.dro_ema,
#|        dro_entropy_reg=args.dro_entropy_reg,
#|        dro_logit_cap=args.dro_logit_cap,
#|        dro_prior_floor=args.dro_prior_floor,
#|        dro_sample_weight_cap=args.dro_sample_weight_cap,
#|        dro_warmup_steps=args.dro_warmup_steps,
#|        alignment_queue_size=args.alignment_queue_size,
#|        alignment_temperature=args.alignment_temperature,
#|        alignment_nce_weight=args.alignment_nce_weight,
#|    )
#|
#|
#|def build_parser():
#|    parser = base_train.build_parser()
#|    parser.set_defaults(
#|        epochs=3,
#|        llm_lr=2e-4,
#|        projector_lr=1e-4,
#|        projector_weight_decay=0.01,
#|        warmup_ratio=0.03,
#|        graph_dropout=0.10,
#|        readout_rank=32,
#|        readout_gate_init=0.04,
#|        readout_gate_cap=0.12,
#|        rank_modulation_cap=0.35,
#|        readout_residual_ratio=0.06,
#|        semantic_loss_weight=0.03,
#|        cf_loss_weight=0.02,
#|    )
#|    parser.add_argument("--graph_residual_gate_floor", type=float, default=0.03)
#|    parser.add_argument("--graph_residual_gate_init", type=float, default=0.12)
#|    parser.add_argument("--graph_residual_gate_cap", type=float, default=0.35)
#|    parser.add_argument(
#|        "--semantic_residual_gate_floor",
#|        type=float,
#|        default=0.03,
#|    )
#|    parser.add_argument(
#|        "--semantic_residual_gate_init",
#|        type=float,
#|        default=0.12,
#|    )
#|    parser.add_argument(
#|        "--semantic_residual_gate_cap",
#|        type=float,
#|        default=0.35,
#|    )
#|    parser.add_argument("--label_token_count", type=int, default=4)
#|    parser.add_argument("--label_readout_scale", type=float, default=0.10)
#|    parser.add_argument("--label_loss_weight", type=float, default=0.40)
#|    parser.add_argument("--dro_eta", type=float, default=0.05)
#|    parser.add_argument("--dro_ema", type=float, default=0.90)
#|    parser.add_argument("--dro_entropy_reg", type=float, default=0.01)
#|    parser.add_argument(
#|        "--dro_logit_cap",
#|        type=float,
#|        default=0.9162907318741551,
#|    )
#|    parser.add_argument("--dro_prior_floor", type=float, default=0.01)
#|    parser.add_argument("--dro_sample_weight_cap", type=float, default=3.0)
#|    parser.add_argument("--dro_warmup_steps", type=int, default=16)
#|    parser.add_argument("--alignment_queue_size", type=int, default=128)
#|    parser.add_argument("--alignment_temperature", type=float, default=0.10)
#|    parser.add_argument("--alignment_nce_weight", type=float, default=0.20)
#|    return parser
#|
#|
#|def load_phenomenon_groups(cache_path):
#|    group_by_id = {}
#|    counts = {name: 0 for name in PHENOMENON_GROUPS}
#|    path = Path(cache_path)
#|    with path.open("r", encoding="utf-8") as handle:
#|        for line_number, line in enumerate(handle, start=1):
#|            if not line.strip():
#|                continue
#|            try:
#|                record = json.loads(line)
#|            except json.JSONDecodeError as error:
#|                raise ValueError(
#|                    f"invalid concept graph JSON at {path}:{line_number}"
#|                ) from error
#|            phenomenon = select_phenomenon(record)
#|            group_by_id[str(record["id"])] = PHENOMENON_TO_ID[phenomenon]
#|            counts[phenomenon] += 1
#|    if not group_by_id:
#|        raise ValueError(f"empty concept graph cache: {path}")
#|    return group_by_id, counts
#|
#|
#|def install_v4_training(module, concept_graph_path, *, args):
#|    import torch
#|
#|    module = base_train.install_semantic_readout_training(
#|        module,
#|        concept_graph_path,
#|        args=args,
#|    )
#|    group_by_id, counts = load_phenomenon_groups(concept_graph_path)
#|    BaseDataset = module.HybridDataset
#|    BaseModel = module.Hybrid_MoE_LLaVA
#|    original_collate = module.collate_fn
#|
#|    class PhenomenonBalancedDataset(BaseDataset):
#|        def __getitem__(self, index):
#|            item = super().__getitem__(index)
#|            sample_id = str(self.samples[index]["id"])
#|            if sample_id not in group_by_id:
#|                raise KeyError(
#|                    f"sample {sample_id} is missing from phenomenon cache"
#|                )
#|            item["phenomenon_group"] = torch.tensor(
#|                group_by_id[sample_id],
#|                dtype=torch.long,
#|            )
#|            return item
#|
#|    def phenomenon_balanced_collate(batch):
#|        output = original_collate(batch)
#|        output["phenomenon_group"] = torch.stack(
#|            [item["phenomenon_group"] for item in batch]
#|        )
#|        return output
#|
#|    class PhenomenonBalancedLLaVA(BaseModel):
#|        def forward(
#|            self,
#|            *model_args,
#|            phenomenon_group=None,
#|            **model_kwargs,
#|        ):
#|            self.projector.set_group_context(phenomenon_group)
#|            try:
#|                return super().forward(*model_args, **model_kwargs)
#|            finally:
#|                self.projector.clear_group_context()
#|
#|    count_text = ", ".join(
#|        f"{name}={counts[name]}"
#|        for name in PHENOMENON_GROUPS
#|        if counts[name] > 0
#|    )
#|    print(
#|        "[rgc-semantic-readout-v4] phenomenon groups "
#|        f"(inferred first, fallback second): {count_text}"
#|    )
#|    module.HybridDataset = PhenomenonBalancedDataset
#|    module.collate_fn = phenomenon_balanced_collate
#|    module.Hybrid_MoE_LLaVA = PhenomenonBalancedLLaVA
#|    return module
#|
#|
#|def main() -> None:
#|    args = build_parser().parse_args()
#|    if args.num_tokens != 0:
#|        raise ValueError("RGC-SemanticReadout-v4 forbids prompt tokens")
#|
#|    base_train.make_semantic_readout_classes = make_v4_readout_classes
#|    base_train.config_from_args = config_from_args
#|    training_counts = {}
#|
#|    def installer(module, concept_graph_path, **kwargs):
#|        del kwargs
#|        _, counts = load_phenomenon_groups(concept_graph_path)
#|        training_counts.update(counts)
#|        return install_v4_training(
#|            module,
#|            concept_graph_path,
#|            args=args,
#|        )
#|
#|    def initialize_model(model, _module, _paths, _device):
#|        if model.num_tokens != 0 or model.projector.num_tokens != 0:
#|            raise RuntimeError("v4 token-free contract failed")
#|        if not training_counts:
#|            raise RuntimeError("v4 phenomenon priors were not initialized")
#|        model.projector.set_group_priors(
#|            [training_counts[name] for name in PHENOMENON_GROUPS]
#|        )
#|        norm_name = attach_semantic_readout(model.llm, model.projector)
#|        print(
#|            "[rgc-semantic-readout-v4] graph_tokens=0; "
#|            f"final_norm={norm_name}; automatic_groupdro=true; "
#|            f"dro_eta={args.dro_eta}; dro_ema={args.dro_ema}; "
#|            f"dro_warmup={args.dro_warmup_steps}; "
#|            f"dro_prior_floor={args.dro_prior_floor}; "
#|            f"dro_sample_cap={args.dro_sample_weight_cap}; "
#|            f"alignment_queue={args.alignment_queue_size}; "
#|            f"alignment_nce_weight={args.alignment_nce_weight}; "
#|            "manual_phenomenon_weights=false"
#|        )
#|
#|    base_train.graph_train.train(
#|        args,
#|        install_training=installer,
#|        initialize_model=initialize_model,
#|        build_optimizer=base_train.build_optimizer,
#|        extra_batch_keys=(
#|            "graph_semantic_ids",
#|            "graph_semantic_mask",
#|            "phenomenon_group",
#|        ),
#|        collect_metrics=collect_v4_metrics,
#|    )
#|
#|
#|if __name__ == "__main__":
#|    main()
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: train_llava_claim_rgc_semantic_readout_stage_5.py ===
#|"""Train false-negative-aware phenomenon-balanced semantic readout v5."""
#|
#|from __future__ import annotations
#|
#|import os
#|
#|
#|DEFAULT_CKPT_NAME = "checkpoints_llava_claim_rgc_semantic_readout_v5"
#|PROJECTOR_SUFFIX = "_claim_rgc_semantic_readout_v5"
#|os.environ["RGC_SR_V4_CKPT_NAME"] = os.environ.get(
#|    "RGC_SR_V5_CKPT_NAME",
#|    DEFAULT_CKPT_NAME,
#|)
#|os.environ["RGC_SR_V4_PROJECTOR_SUFFIX"] = os.environ.get(
#|    "RGC_SR_V5_PROJECTOR_SUFFIX",
#|    PROJECTOR_SUFFIX,
#|)
#|
#|import train_llava_claim_rgc_semantic_readout_stage_4 as base_v4  # noqa: E402
#|from rgc_semantic_readout import attach_semantic_readout  # noqa: E402
#|from rgc_semantic_readout_stage_4 import PHENOMENON_GROUPS  # noqa: E402
#|from rgc_semantic_readout_stage_5 import (  # noqa: E402
#|    FalseNegativeAwareReadoutConfig,
#|    collect_v5_metrics,
#|    make_v5_readout_classes,
#|)
#|
#|
#|def config_from_args(args) -> FalseNegativeAwareReadoutConfig:
#|    base = base_v4.config_from_args(args)
#|    values = dict(base.__dict__)
#|    values.update(
#|        alignment_decay_start=args.alignment_decay_start,
#|        alignment_final_nce_weight=args.alignment_final_nce_weight,
#|        same_group_negative_scale=args.same_group_negative_scale,
#|    )
#|    return FalseNegativeAwareReadoutConfig(**values)
#|
#|
#|def build_parser():
#|    parser = base_v4.build_parser()
#|    parser.add_argument("--alignment_decay_start", type=float, default=0.67)
#|    parser.add_argument(
#|        "--alignment_final_nce_weight",
#|        type=float,
#|        default=0.05,
#|    )
#|    parser.add_argument(
#|        "--same_group_negative_scale",
#|        type=float,
#|        default=0.0,
#|    )
#|    return parser
#|
#|
#|def main() -> None:
#|    args = build_parser().parse_args()
#|    if args.num_tokens != 0:
#|        raise ValueError("RGC-SemanticReadout-v5 forbids prompt tokens")
#|
#|    base_v4.base_train.make_semantic_readout_classes = make_v5_readout_classes
#|    base_v4.base_train.config_from_args = config_from_args
#|    training_counts = {}
#|
#|    def installer(module, concept_graph_path, **kwargs):
#|        del kwargs
#|        _, counts = base_v4.load_phenomenon_groups(concept_graph_path)
#|        training_counts.update(counts)
#|        return base_v4.install_v4_training(
#|            module,
#|            concept_graph_path,
#|            args=args,
#|        )
#|
#|    def initialize_model(model, _module, _paths, _device):
#|        if model.num_tokens != 0 or model.projector.num_tokens != 0:
#|            raise RuntimeError("v5 token-free contract failed")
#|        if not training_counts:
#|            raise RuntimeError("v5 phenomenon priors were not initialized")
#|        model.projector.set_group_priors(
#|            [training_counts[name] for name in PHENOMENON_GROUPS]
#|        )
#|        norm_name = attach_semantic_readout(model.llm, model.projector)
#|        print(
#|            "[rgc-semantic-readout-v5] graph_tokens=0; "
#|            f"final_norm={norm_name}; automatic_groupdro=true; "
#|            "false_negative_aware=true; "
#|            f"same_group_scale={args.same_group_negative_scale}; "
#|            f"nce_weight={args.alignment_nce_weight}; "
#|            f"nce_final={args.alignment_final_nce_weight}; "
#|            f"nce_decay_start={args.alignment_decay_start}; "
#|            "manual_phenomenon_weights=false"
#|        )
#|
#|    base_v4.base_train.graph_train.train(
#|        args,
#|        install_training=installer,
#|        initialize_model=initialize_model,
#|        build_optimizer=base_v4.base_train.build_optimizer,
#|        extra_batch_keys=(
#|            "graph_semantic_ids",
#|            "graph_semantic_mask",
#|            "phenomenon_group",
#|        ),
#|        collect_metrics=collect_v5_metrics,
#|    )
#|
#|
#|if __name__ == "__main__":
#|    main()
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: train_llava_claim_rgc_semantic_readout_stage_6.py ===
#|"""Continue PBFA-RGSR v5 with adaptive soft-negative training."""
#|
#|from __future__ import annotations
#|
#|import os
#|from pathlib import Path
#|
#|
#|DEFAULT_CKPT_NAME = "checkpoints_llava_claim_rgc_semantic_readout_v6"
#|PROJECTOR_SUFFIX = "_claim_rgc_semantic_readout_v6"
#|_TARGET_CKPT_NAME = os.environ.get("RGC_SR_V6_CKPT_NAME", DEFAULT_CKPT_NAME)
#|_TARGET_PROJECTOR_SUFFIX = os.environ.get(
#|    "RGC_SR_V6_PROJECTOR_SUFFIX", PROJECTOR_SUFFIX
#|)
#|
#|# Set the inherited output namespace before importing the v4/v5 entrypoints.
#|for _name in (
#|    "RGC_SR_V5_CKPT_NAME",
#|    "RGC_SR_V4_CKPT_NAME",
#|    "RGC_SR_CKPT_NAME",
#|    "PAPER2_CKPT_NAME",
#|    "PAPER2_DEFAULT_CKPT_NAME",
#|):
#|    os.environ[_name] = _TARGET_CKPT_NAME
#|for _name in (
#|    "RGC_SR_V5_PROJECTOR_SUFFIX",
#|    "RGC_SR_V4_PROJECTOR_SUFFIX",
#|    "RGC_SR_PROJECTOR_SUFFIX",
#|    "PAPER2_PROJECTOR_SUFFIX",
#|):
#|    os.environ[_name] = _TARGET_PROJECTOR_SUFFIX
#|
#|import train_llava_claim_rgc_semantic_readout_stage_4 as base_v4  # noqa: E402
#|import train_llava_claim_rgc_semantic_readout_stage_5 as pbfa_v5  # noqa: E402
#|from rgc_semantic_readout import attach_semantic_readout  # noqa: E402
#|from rgc_semantic_readout_stage_4 import PHENOMENON_GROUPS  # noqa: E402
#|from rgc_semantic_readout_stage_6 import (  # noqa: E402
#|    AdaptiveSoftNegativeReadoutConfig,
#|    collect_v6_metrics,
#|    make_v6_readout_classes,
#|)
#|
#|
#|def _verify_namespace_contract() -> None:
#|    graph_train = base_v4.base_train.graph_train
#|    if str(graph_train.DEFAULT_CKPT_NAME) != _TARGET_CKPT_NAME:
#|        raise RuntimeError("v6 checkpoint namespace leaked from an older entrypoint")
#|    if str(graph_train.PROJECTOR_SUFFIX) != _TARGET_PROJECTOR_SUFFIX:
#|        raise RuntimeError("v6 projector suffix leaked from an older entrypoint")
#|
#|
#|def config_from_args(args) -> AdaptiveSoftNegativeReadoutConfig:
#|    base = pbfa_v5.config_from_args(args)
#|    values = dict(base.__dict__)
#|    values.update(
#|        soft_negative_mad_floor=args.soft_negative_mad_floor,
#|        soft_negative_min_weight=args.soft_negative_min_weight,
#|        tail_error_ema=args.tail_error_ema,
#|        tail_error_scale_floor=args.tail_error_scale_floor,
#|        tail_weight_floor=args.tail_weight_floor,
#|        tail_weight_cap=args.tail_weight_cap,
#|    )
#|    return AdaptiveSoftNegativeReadoutConfig(**values)
#|
#|
#|def build_parser():
#|    parser = pbfa_v5.build_parser()
#|    parser.set_defaults(
#|        epochs=1,
#|        llm_lr=0.0,
#|        projector_lr=1e-5,
#|        projector_weight_decay=0.01,
#|        warmup_ratio=0.05,
#|        graph_dropout=0.05,
#|        alignment_nce_weight=0.10,
#|        alignment_final_nce_weight=0.03,
#|        alignment_decay_start=0.50,
#|        same_group_negative_scale=1.0,
#|    )
#|    parser.add_argument(
#|        "--source_ckpt_root",
#|        default="checkpoints_llava_claim_rgc_semantic_readout_v5",
#|    )
#|    parser.add_argument("--source_epoch", type=int, default=3)
#|    parser.add_argument(
#|        "--source_projector_suffix",
#|        default="_claim_rgc_semantic_readout_v5",
#|    )
#|    parser.add_argument("--soft_negative_mad_floor", type=float, default=0.03)
#|    parser.add_argument(
#|        "--soft_negative_min_weight", type=float, default=1e-4
#|    )
#|    parser.add_argument("--tail_error_ema", type=float, default=0.95)
#|    parser.add_argument(
#|        "--tail_error_scale_floor", type=float, default=0.02
#|    )
#|    parser.add_argument("--tail_weight_floor", type=float, default=0.75)
#|    parser.add_argument("--tail_weight_cap", type=float, default=1.25)
#|    return parser
#|
#|
#|def _source_paths(paths, args) -> tuple[Path, Path]:
#|    root = Path(args.source_ckpt_root)
#|    if not root.is_absolute():
#|        root = paths.output_root / root
#|    lora = root / f"lora_epoch_{args.source_epoch}{args.source_projector_suffix}"
#|    projector = root / (
#|        f"proj_epoch_{args.source_epoch}{args.source_projector_suffix}.pth"
#|    )
#|    if not lora.is_dir():
#|        raise FileNotFoundError(f"missing PBFA-v5 source LoRA: {lora}")
#|    if not projector.is_file():
#|        raise FileNotFoundError(f"missing PBFA-v5 source projector: {projector}")
#|    if not (
#|        (lora / "adapter_model.safetensors").is_file()
#|        or (lora / "adapter_model.bin").is_file()
#|    ):
#|        raise FileNotFoundError(f"missing source adapter weights under {lora}")
#|    return lora, projector
#|
#|
#|def install_v6_training(module, concept_graph_path, *, args, **_kwargs):
#|    base_v4.base_train.make_semantic_readout_classes = make_v6_readout_classes
#|    base_v4.base_train.config_from_args = config_from_args
#|    module = base_v4.install_v4_training(
#|        module,
#|        concept_graph_path,
#|        args=args,
#|    )
#|    BaseModel = module.Hybrid_MoE_LLaVA
#|
#|    class FrozenLoRAV6(BaseModel):
#|        def train(self, mode: bool = True):
#|            super().train(mode)
#|            self.llm.eval()
#|            self.projector.train(mode)
#|            return self
#|
#|    module.Hybrid_MoE_LLaVA = FrozenLoRAV6
#|    return module
#|
#|
#|def initialize_from_v5(model, module, paths, device, args, training_counts, memory_source=None):
#|    from peft import PeftModel
#|
#|    lora_path, projector_path = _source_paths(paths, args) if memory_source is None else ('in-memory v5 LoRA', 'in-memory v5 controller')
#|    base_model = (
#|        model.llm.base_model.model
#|        if hasattr(model.llm, "base_model")
#|        else model.llm
#|    )
#|    model.llm = PeftModel.from_pretrained(
#|        base_model,
#|        str(lora_path),
#|        is_trainable=False,
#|    ).to(device) if memory_source is None else memory_source.restore_lora(model.llm)
#|    if hasattr(model.llm, "config"):
#|        model.llm.config.use_cache = False
#|
#|    source_state = module.torch.load(projector_path, map_location=device) if memory_source is None else memory_source.projector
#|    incompatible = model.projector.load_state_dict(source_state, strict=False)
#|    if incompatible.unexpected_keys or incompatible.missing_keys:
#|        raise RuntimeError(
#|            "PBFA-v5/v6 projector contract mismatch: "
#|            f"unexpected={list(incompatible.unexpected_keys)[:5]} "
#|            f"missing={list(incompatible.missing_keys)[:5]}"
#|        )
#|
#|    for parameter in model.parameters():
#|        parameter.requires_grad = False
#|    for parameter in model.projector.parameters():
#|        parameter.requires_grad = True
#|    model.projector.set_group_priors(
#|        [training_counts[name] for name in PHENOMENON_GROUPS]
#|    )
#|    norm_name = attach_semantic_readout(model.llm, model.projector)
#|    trainable = sum(
#|        parameter.numel()
#|        for parameter in model.projector.parameters()
#|        if parameter.requires_grad
#|    )
#|    print(f"[rgc-semantic-readout-v6] source LoRA: {lora_path}")
#|    print(f"[rgc-semantic-readout-v6] source projector: {projector_path}")
#|    print(
#|        "[rgc-semantic-readout-v6] continued from PBFA-v5; "
#|        f"final_norm={norm_name}; trainable_projector={trainable:,}; "
#|        "lora_frozen=true; graph_tokens=0"
#|    )
#|
#|
#|def build_optimizer(model, torch, args):
#|    parameters = [
#|        parameter
#|        for parameter in model.projector.parameters()
#|        if parameter.requires_grad
#|    ]
#|    if not parameters:
#|        raise RuntimeError("v6 selected no trainable projector parameters")
#|    return torch.optim.AdamW(
#|        parameters,
#|        lr=float(args.projector_lr),
#|        weight_decay=float(args.projector_weight_decay),
#|    )
#|
#|
#|def main() -> None:
#|    _verify_namespace_contract()
#|    args = build_parser().parse_args()
#|    if args.num_tokens != 0:
#|        raise ValueError("PBFA-RGSR-v6 forbids graph prompt tokens")
#|
#|    training_counts = {}
#|
#|    def installer(module, concept_graph_path, **kwargs):
#|        del kwargs
#|        _, counts = base_v4.load_phenomenon_groups(concept_graph_path)
#|        training_counts.update(counts)
#|        return install_v6_training(module, concept_graph_path, args=args)
#|
#|    def initializer(model, module, paths, device):
#|        if not training_counts:
#|            raise RuntimeError("v6 phenomenon priors were not initialized")
#|        initialize_from_v5(
#|            model,
#|            module,
#|            paths,
#|            device,
#|            args,
#|            training_counts,
#|        )
#|        print(
#|            "[rgc-semantic-readout-v6] adaptive_soft_negatives=true; "
#|            "robust_tail_weighting=true; manual_phenomenon_weights=false; "
#|            f"mad_floor={args.soft_negative_mad_floor}; "
#|            f"tail_ema={args.tail_error_ema}"
#|        )
#|
#|    base_v4.base_train.graph_train.train(
#|        args,
#|        install_training=installer,
#|        initialize_model=initializer,
#|        build_optimizer=build_optimizer,
#|        extra_batch_keys=(
#|            "graph_semantic_ids",
#|            "graph_semantic_mask",
#|            "phenomenon_group",
#|        ),
#|        collect_metrics=collect_v6_metrics,
#|    )
#|
#|
#|if __name__ == "__main__":
#|    main()
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: train_llava_claim_rgc_semantic_readout_stage_7.py ===
#|"""Continue PBFA-RGSR v6 with decoder-grounded graph alignment."""
#|
#|from __future__ import annotations
#|
#|import os
#|from pathlib import Path
#|
#|
#|DEFAULT_CKPT_NAME = "checkpoints_llava_claim_rgc_semantic_readout_v7"
#|PROJECTOR_SUFFIX = "_claim_rgc_semantic_readout_v7"
#|_TARGET_CKPT_NAME = os.environ.get("RGC_SR_V7_CKPT_NAME", DEFAULT_CKPT_NAME)
#|_TARGET_PROJECTOR_SUFFIX = os.environ.get(
#|    "RGC_SR_V7_PROJECTOR_SUFFIX", PROJECTOR_SUFFIX
#|)
#|for _name in (
#|    "RGC_SR_V6_CKPT_NAME",
#|    "RGC_SR_V5_CKPT_NAME",
#|    "RGC_SR_V4_CKPT_NAME",
#|    "RGC_SR_CKPT_NAME",
#|    "PAPER2_CKPT_NAME",
#|    "PAPER2_DEFAULT_CKPT_NAME",
#|):
#|    os.environ[_name] = _TARGET_CKPT_NAME
#|for _name in (
#|    "RGC_SR_V6_PROJECTOR_SUFFIX",
#|    "RGC_SR_V5_PROJECTOR_SUFFIX",
#|    "RGC_SR_V4_PROJECTOR_SUFFIX",
#|    "RGC_SR_PROJECTOR_SUFFIX",
#|    "PAPER2_PROJECTOR_SUFFIX",
#|):
#|    os.environ[_name] = _TARGET_PROJECTOR_SUFFIX
#|
#|import train_llava_claim_rgc_semantic_readout_stage_6 as pbfa_v6  # noqa: E402
#|from rgc_semantic_readout import attach_semantic_readout  # noqa: E402
#|from rgc_semantic_readout_stage_4 import PHENOMENON_GROUPS  # noqa: E402
#|from rgc_semantic_readout_stage_7 import (  # noqa: E402
#|    DecoderGroundedReadoutConfig,
#|    collect_v7_metrics,
#|    make_v7_readout_classes,
#|)
#|
#|
#|base_v4 = pbfa_v6.base_v4
#|
#|
#|def _verify_namespace_contract() -> None:
#|    graph_train = base_v4.base_train.graph_train
#|    if str(graph_train.DEFAULT_CKPT_NAME) != _TARGET_CKPT_NAME:
#|        raise RuntimeError("v7 checkpoint namespace leaked from an older entrypoint")
#|    if str(graph_train.PROJECTOR_SUFFIX) != _TARGET_PROJECTOR_SUFFIX:
#|        raise RuntimeError("v7 projector suffix leaked from an older entrypoint")
#|
#|
#|def config_from_args(args) -> DecoderGroundedReadoutConfig:
#|    base = pbfa_v6.config_from_args(args)
#|    values = dict(base.__dict__)
#|    values.update(
#|        decoder_alignment_dim=args.decoder_alignment_dim,
#|        decoder_alignment_weight=args.decoder_alignment_weight,
#|        decoder_alignment_temperature=args.decoder_alignment_temperature,
#|        decoder_alignment_ema=args.decoder_alignment_ema,
#|        decoder_min_explanation_tokens=args.decoder_min_explanation_tokens,
#|    )
#|    return DecoderGroundedReadoutConfig(**values)
#|
#|
#|def build_parser():
#|    parser = pbfa_v6.build_parser()
#|    parser.set_defaults(
#|        epochs=1,
#|        source_ckpt_root="checkpoints_llava_claim_rgc_semantic_readout_v6",
#|        source_epoch=1,
#|        source_projector_suffix="_claim_rgc_semantic_readout_v6",
#|        llm_lr=0.0,
#|        projector_lr=5e-6,
#|        graph_dropout=0.0,
#|        semantic_loss_weight=0.0,
#|        cf_loss_weight=0.01,
#|        alignment_nce_weight=0.0,
#|        alignment_final_nce_weight=0.0,
#|        alignment_decay_start=0.50,
#|    )
#|    parser.add_argument("--decoder_alignment_dim", type=int, default=256)
#|    parser.add_argument("--decoder_alignment_weight", type=float, default=0.02)
#|    parser.add_argument(
#|        "--decoder_alignment_temperature", type=float, default=0.08
#|    )
#|    parser.add_argument("--decoder_alignment_ema", type=float, default=0.95)
#|    parser.add_argument(
#|        "--decoder_min_explanation_tokens", type=int, default=4
#|    )
#|    return parser
#|
#|
#|def _source_paths(paths, args) -> tuple[Path, Path]:
#|    root = Path(args.source_ckpt_root)
#|    if not root.is_absolute():
#|        root = paths.output_root / root
#|    lora = root / f"lora_epoch_{args.source_epoch}{args.source_projector_suffix}"
#|    projector = root / (
#|        f"proj_epoch_{args.source_epoch}{args.source_projector_suffix}.pth"
#|    )
#|    if not lora.is_dir():
#|        raise FileNotFoundError(f"missing PBFA-v6 source LoRA: {lora}")
#|    if not projector.is_file():
#|        raise FileNotFoundError(f"missing PBFA-v6 source projector: {projector}")
#|    if not (
#|        (lora / "adapter_model.safetensors").is_file()
#|        or (lora / "adapter_model.bin").is_file()
#|    ):
#|        raise FileNotFoundError(f"missing source adapter weights under {lora}")
#|    return lora, projector
#|
#|
#|def install_v7_training(module, concept_graph_path, *, args, **_kwargs):
#|    base_v4.base_train.make_semantic_readout_classes = make_v7_readout_classes
#|    base_v4.base_train.config_from_args = config_from_args
#|    module = base_v4.install_v4_training(
#|        module,
#|        concept_graph_path,
#|        args=args,
#|    )
#|    BaseModel = module.Hybrid_MoE_LLaVA
#|
#|    class FrozenLoRAV7(BaseModel):
#|        def train(self, mode: bool = True):
#|            super().train(mode)
#|            self.llm.eval()
#|            self.projector.train(mode)
#|            return self
#|
#|    module.Hybrid_MoE_LLaVA = FrozenLoRAV7
#|    return module
#|
#|
#|def initialize_from_v6(model, module, paths, device, args, training_counts):
#|    from peft import PeftModel
#|
#|    lora_path, projector_path = _source_paths(paths, args)
#|    base_model = (
#|        model.llm.base_model.model
#|        if hasattr(model.llm, "base_model")
#|        else model.llm
#|    )
#|    model.llm = PeftModel.from_pretrained(
#|        base_model,
#|        str(lora_path),
#|        is_trainable=False,
#|    ).to(device)
#|    if hasattr(model.llm, "config"):
#|        model.llm.config.use_cache = False
#|
#|    source_state = module.torch.load(projector_path, map_location=device)
#|    incompatible = model.projector.load_state_dict(source_state, strict=False)
#|    unexpected = list(incompatible.unexpected_keys)
#|    allowed_prefixes = (
#|        "decoder_alignment_projection.",
#|        "graph_alignment_projection.",
#|        "target_alignment_projection.",
#|    )
#|    invalid_missing = [
#|        key
#|        for key in incompatible.missing_keys
#|        if not key.startswith(allowed_prefixes)
#|    ]
#|    if unexpected or invalid_missing:
#|        raise RuntimeError(
#|            "PBFA-v6/v7 projector contract mismatch: "
#|            f"unexpected={unexpected[:5]} missing={invalid_missing[:5]}"
#|        )
#|    if not incompatible.missing_keys:
#|        raise RuntimeError("v7 source unexpectedly contains decoder alignment")
#|
#|    for parameter in model.parameters():
#|        parameter.requires_grad = False
#|    for parameter in model.projector.parameters():
#|        parameter.requires_grad = True
#|    model.projector.set_group_priors(
#|        [training_counts[name] for name in PHENOMENON_GROUPS]
#|    )
#|    norm_name = attach_semantic_readout(model.llm, model.projector)
#|    trainable = sum(
#|        parameter.numel()
#|        for parameter in model.projector.parameters()
#|        if parameter.requires_grad
#|    )
#|    print(f"[rgc-semantic-readout-v7] source LoRA: {lora_path}")
#|    print(f"[rgc-semantic-readout-v7] source projector: {projector_path}")
#|    print(
#|        "[rgc-semantic-readout-v7] continued from PBFA-v6; "
#|        f"final_norm={norm_name}; trainable_projector={trainable:,}; "
#|        "lora_frozen=true; graph_tokens=0"
#|    )
#|
#|
#|def build_optimizer(model, torch, args):
#|    parameters = [
#|        parameter
#|        for parameter in model.projector.parameters()
#|        if parameter.requires_grad
#|    ]
#|    if not parameters:
#|        raise RuntimeError("v7 selected no trainable projector parameters")
#|    return torch.optim.AdamW(
#|        parameters,
#|        lr=float(args.projector_lr),
#|        weight_decay=float(args.projector_weight_decay),
#|    )
#|
#|
#|def main() -> None:
#|    _verify_namespace_contract()
#|    args = build_parser().parse_args()
#|    if args.num_tokens != 0:
#|        raise ValueError("PBFA-RGSR-v7 forbids graph prompt tokens")
#|    training_counts = {}
#|
#|    def installer(module, concept_graph_path, **kwargs):
#|        del kwargs
#|        _, counts = base_v4.load_phenomenon_groups(concept_graph_path)
#|        training_counts.update(counts)
#|        return install_v7_training(module, concept_graph_path, args=args)
#|
#|    def initializer(model, module, paths, device):
#|        if not training_counts:
#|            raise RuntimeError("v7 phenomenon priors were not initialized")
#|        initialize_from_v6(
#|            model,
#|            module,
#|            paths,
#|            device,
#|            args,
#|            training_counts,
#|        )
#|        print(
#|            "[rgc-semantic-readout-v7] decoder_global_alignment=true; "
#|            "graph_token_coverage=true; automatic_loss_balance=true; "
#|            f"alignment_dim={args.decoder_alignment_dim}; "
#|            f"alignment_weight={args.decoder_alignment_weight}"
#|        )
#|
#|    base_v4.base_train.graph_train.train(
#|        args,
#|        install_training=installer,
#|        initialize_model=initializer,
#|        build_optimizer=build_optimizer,
#|        extra_batch_keys=(
#|            "graph_semantic_ids",
#|            "graph_semantic_mask",
#|            "phenomenon_group",
#|        ),
#|        collect_metrics=collect_v7_metrics,
#|    )
#|
#|
#|if __name__ == "__main__":
#|    main()
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: train_llava_claim_rgc_semantic_readout_stage_8.py ===
#|"""Train reliability-gated decoder grounding under a v6 trust region."""
#|
#|from __future__ import annotations
#|
#|import os
#|from pathlib import Path
#|
#|
#|DEFAULT_CKPT_NAME = "checkpoints_llava_claim_rgc_semantic_readout_v8"
#|PROJECTOR_SUFFIX = "_claim_rgc_semantic_readout_v8"
#|_TARGET_CKPT_NAME = os.environ.get("RGC_SR_V8_CKPT_NAME", DEFAULT_CKPT_NAME)
#|_TARGET_PROJECTOR_SUFFIX = os.environ.get(
#|    "RGC_SR_V8_PROJECTOR_SUFFIX", PROJECTOR_SUFFIX
#|)
#|for _name in (
#|    "RGC_SR_V7_CKPT_NAME",
#|    "RGC_SR_V6_CKPT_NAME",
#|    "RGC_SR_V5_CKPT_NAME",
#|    "RGC_SR_V4_CKPT_NAME",
#|    "RGC_SR_CKPT_NAME",
#|    "PAPER2_CKPT_NAME",
#|    "PAPER2_DEFAULT_CKPT_NAME",
#|):
#|    os.environ[_name] = _TARGET_CKPT_NAME
#|for _name in (
#|    "RGC_SR_V7_PROJECTOR_SUFFIX",
#|    "RGC_SR_V6_PROJECTOR_SUFFIX",
#|    "RGC_SR_V5_PROJECTOR_SUFFIX",
#|    "RGC_SR_V4_PROJECTOR_SUFFIX",
#|    "RGC_SR_PROJECTOR_SUFFIX",
#|    "PAPER2_PROJECTOR_SUFFIX",
#|):
#|    os.environ[_name] = _TARGET_PROJECTOR_SUFFIX
#|
#|import train_llava_claim_rgc_semantic_readout_stage_7 as decoder_v7  # noqa: E402
#|from rgc_semantic_readout import attach_semantic_readout  # noqa: E402
#|from rgc_semantic_readout_stage_4 import PHENOMENON_GROUPS  # noqa: E402
#|from rgc_semantic_readout_stage_8 import (  # noqa: E402
#|    ReliabilityTrustReadoutConfig,
#|    collect_v8_metrics,
#|    make_v8_readout_classes,
#|)
#|
#|
#|base_v4 = decoder_v7.base_v4
#|
#|
#|def _verify_namespace_contract() -> None:
#|    graph_train = base_v4.base_train.graph_train
#|    if str(graph_train.DEFAULT_CKPT_NAME) != _TARGET_CKPT_NAME:
#|        raise RuntimeError("v8 checkpoint namespace leaked from an older entrypoint")
#|    if str(graph_train.PROJECTOR_SUFFIX) != _TARGET_PROJECTOR_SUFFIX:
#|        raise RuntimeError("v8 projector suffix leaked from an older entrypoint")
#|
#|
#|def config_from_args(args) -> ReliabilityTrustReadoutConfig:
#|    base = decoder_v7.config_from_args(args)
#|    values = dict(base.__dict__)
#|    values.update(
#|        reliability_temperature=args.reliability_temperature,
#|        reliability_absolute_temperature=(
#|            args.reliability_absolute_temperature
#|        ),
#|        reliability_deviation_floor=args.reliability_deviation_floor,
#|        trust_radius=args.trust_radius,
#|        trust_dual_lr=args.trust_dual_lr,
#|        trust_augmented_weight=args.trust_augmented_weight,
#|        trust_dual_cap=args.trust_dual_cap,
#|    )
#|    return ReliabilityTrustReadoutConfig(**values)
#|
#|
#|def build_parser():
#|    parser = decoder_v7.build_parser()
#|    parser.set_defaults(
#|        epochs=1,
#|        source_ckpt_root="checkpoints_llava_claim_rgc_semantic_readout_v6",
#|        source_epoch=1,
#|        source_projector_suffix="_claim_rgc_semantic_readout_v6",
#|        llm_lr=0.0,
#|        projector_lr=5e-6,
#|        graph_dropout=0.0,
#|        semantic_loss_weight=0.0,
#|        cf_loss_weight=0.0,
#|        alignment_nce_weight=0.0,
#|        alignment_final_nce_weight=0.0,
#|        decoder_alignment_weight=0.015,
#|    )
#|    parser.add_argument("--reliability_temperature", type=float, default=1.0)
#|    parser.add_argument(
#|        "--reliability_absolute_temperature", type=float, default=0.10
#|    )
#|    parser.add_argument(
#|        "--reliability_deviation_floor", type=float, default=0.05
#|    )
#|    parser.add_argument("--trust_radius", type=float, default=5e-4)
#|    parser.add_argument("--trust_dual_lr", type=float, default=0.02)
#|    parser.add_argument(
#|        "--trust_augmented_weight", type=float, default=0.01
#|    )
#|    parser.add_argument("--trust_dual_cap", type=float, default=0.10)
#|    return parser
#|
#|
#|def _source_paths(paths, args) -> tuple[Path, Path]:
#|    root = Path(args.source_ckpt_root)
#|    if not root.is_absolute():
#|        root = paths.output_root / root
#|    lora = root / f"lora_epoch_{args.source_epoch}{args.source_projector_suffix}"
#|    projector = root / (
#|        f"proj_epoch_{args.source_epoch}{args.source_projector_suffix}.pth"
#|    )
#|    if not lora.is_dir():
#|        raise FileNotFoundError(f"missing PBFA-v6 source LoRA: {lora}")
#|    if not projector.is_file():
#|        raise FileNotFoundError(f"missing PBFA-v6 source projector: {projector}")
#|    if not (
#|        (lora / "adapter_model.safetensors").is_file()
#|        or (lora / "adapter_model.bin").is_file()
#|    ):
#|        raise FileNotFoundError(f"missing source adapter weights under {lora}")
#|    return lora, projector
#|
#|
#|def install_v8_training(module, concept_graph_path, *, args, **_kwargs):
#|    base_v4.base_train.make_semantic_readout_classes = make_v8_readout_classes
#|    base_v4.base_train.config_from_args = config_from_args
#|    module = base_v4.install_v4_training(
#|        module,
#|        concept_graph_path,
#|        args=args,
#|    )
#|    BaseModel = module.Hybrid_MoE_LLaVA
#|
#|    class FrozenLoRAV8(BaseModel):
#|        def train(self, mode: bool = True):
#|            super().train(mode)
#|            self.llm.eval()
#|            self.projector.train(mode)
#|            return self
#|
#|    module.Hybrid_MoE_LLaVA = FrozenLoRAV8
#|    return module
#|
#|
#|def initialize_from_v6(model, module, paths, device, args, training_counts, memory_source=None):
#|    from peft import PeftModel
#|
#|    lora_path, projector_path = _source_paths(paths, args) if memory_source is None else ('in-memory v6 LoRA', 'in-memory v6 controller')
#|    base_model = (
#|        model.llm.base_model.model
#|        if hasattr(model.llm, "base_model")
#|        else model.llm
#|    )
#|    model.llm = PeftModel.from_pretrained(
#|        base_model,
#|        str(lora_path),
#|        is_trainable=False,
#|    ).to(device) if memory_source is None else memory_source.restore_lora(model.llm)
#|    if hasattr(model.llm, "config"):
#|        model.llm.config.use_cache = False
#|
#|    source_state = module.torch.load(projector_path, map_location=device) if memory_source is None else memory_source.projector
#|    incompatible = model.projector.load_state_dict(source_state, strict=False)
#|    allowed_missing = (
#|        "decoder_alignment_projection.",
#|        "graph_alignment_projection.",
#|        "target_alignment_projection.",
#|    )
#|    invalid_missing = [
#|        key
#|        for key in incompatible.missing_keys
#|        if not key.startswith(allowed_missing)
#|    ]
#|    if incompatible.unexpected_keys or invalid_missing:
#|        raise RuntimeError(
#|            "PBFA-v6/v8 projector contract mismatch: "
#|            f"unexpected={list(incompatible.unexpected_keys)[:5]} "
#|            f"missing={invalid_missing[:5]}"
#|        )
#|    if not incompatible.missing_keys:
#|        raise RuntimeError("v8 source unexpectedly contains decoder alignment")
#|
#|    for parameter in model.parameters():
#|        parameter.requires_grad = False
#|    trainable_prefixes = (
#|        "semantic_readout.",
#|        "decoder_alignment_projection.",
#|        "graph_alignment_projection.",
#|        "target_alignment_projection.",
#|    )
#|    for name, parameter in model.projector.named_parameters():
#|        parameter.requires_grad = name.startswith(trainable_prefixes)
#|    model.projector.set_group_priors(
#|        [training_counts[name] for name in PHENOMENON_GROUPS]
#|    )
#|    norm_name = attach_semantic_readout(model.llm, model.projector)
#|    model.projector.set_trust_reference()
#|    trainable = sum(
#|        parameter.numel()
#|        for parameter in model.projector.parameters()
#|        if parameter.requires_grad
#|    )
#|    print(f"[rgc-semantic-readout-v8] source LoRA: {lora_path}")
#|    print(f"[rgc-semantic-readout-v8] source projector: {projector_path}")
#|    print(
#|        "[rgc-semantic-readout-v8] branched from PBFA-v6; "
#|        f"final_norm={norm_name}; trainable={trainable:,}; "
#|        "condition_encoder_frozen=true; lora_frozen=true; graph_tokens=0"
#|    )
#|
#|
#|def build_optimizer(model, torch, args):
#|    parameters = [
#|        parameter
#|        for parameter in model.projector.parameters()
#|        if parameter.requires_grad
#|    ]
#|    if not parameters:
#|        raise RuntimeError("v8 selected no trainable parameters")
#|    return torch.optim.AdamW(
#|        parameters,
#|        lr=float(args.projector_lr),
#|        weight_decay=float(args.projector_weight_decay),
#|    )
#|
#|
#|def main() -> None:
#|    _verify_namespace_contract()
#|    args = build_parser().parse_args()
#|    if args.num_tokens != 0:
#|        raise ValueError("PBFA-RGSR-v8 forbids graph prompt tokens")
#|    training_counts = {}
#|
#|    def installer(module, concept_graph_path, **kwargs):
#|        del kwargs
#|        _, counts = base_v4.load_phenomenon_groups(concept_graph_path)
#|        training_counts.update(counts)
#|        return install_v8_training(module, concept_graph_path, args=args)
#|
#|    def initializer(model, module, paths, device):
#|        if not training_counts:
#|            raise RuntimeError("v8 phenomenon priors were not initialized")
#|        initialize_from_v6(
#|            model,
#|            module,
#|            paths,
#|            device,
#|            args,
#|            training_counts,
#|        )
#|        print(
#|            "[rgc-semantic-readout-v8] reliability_gated_coverage=true; "
#|            "source_trust_region=true; manual_phenomenon_weights=false; "
#|            f"decoder_weight={args.decoder_alignment_weight}; "
#|            f"trust_radius={args.trust_radius}"
#|        )
#|
#|    base_v4.base_train.graph_train.train(
#|        args,
#|        install_training=installer,
#|        initialize_model=initializer,
#|        build_optimizer=build_optimizer,
#|        extra_batch_keys=(
#|            "graph_semantic_ids",
#|            "graph_semantic_mask",
#|            "phenomenon_group",
#|        ),
#|        collect_metrics=collect_v8_metrics,
#|    )
#|
#|
#|if __name__ == "__main__":
#|    main()
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: train_llava_final.py ===
#|"""One LLaVA initialization, in-memory stages, one final model.pt per variant."""
#|import argparse,json,math,random
#|from pathlib import Path
#|from dataclasses import asdict
#|from iesfd_stage_13_repair import digest,write_json
#|from llava_final_runtime import VARIANTS,load_runtime,graph_inputs,context,prompt,forward_answer,export_payload,enable_training_checkpointing,final_controller_config,fresh_lora_settings
#|from llava_final_runtime import configure_stage,set_stage_seed,generator_versions,assert_frozen_generator
#|
#|
#|def validate_training_rows(rows):
#|    if len(rows)!=4578 or len({str(r['id']) for r in rows})!=len(rows):raise ValueError('expected all 4578 unique TRAIN records')
#|
#|
#|def warmup_cosine(step,total,warmup):
#|    if step<warmup:return float(step)/max(1,warmup)
#|    progress=min(1.,max(0.,(step-warmup)/max(1,total-warmup)))
#|    return .5*(1.+math.cos(math.pi*progress))
#|
#|
#|def prepare_run_contract(out,contract):
#|    """Allow code-only repair of a run that failed before producing training results."""
#|    path=out/'contract.json'
#|    if path.exists():
#|        previous=json.loads(path.read_text(encoding='utf-8'))
#|        if previous!=contract:
#|            same_settings={k:v for k,v in previous.items() if k!='code'}=={k:v for k,v in contract.items() if k!='code'}
#|            artifacts=any((out/name).exists() for name in ('training_history.json','model.pt','model.tmp','complete.json','resume.pt'))
#|            if not same_settings or artifacts:raise ValueError('changed run; choose a new output directory')
#|            archive=out/('contract.before_fix_'+digest(path)[:12]+'.json')
#|            if not archive.exists():write_json(archive,previous)
#|            print('[final] archived startup-only contract; applying code compatibility fix without changing training settings',flush=True)
#|    write_json(path,contract)
#|
#|
#|def main():
#|    p=argparse.ArgumentParser();p.add_argument('--variant',choices=VARIANTS,required=True);p.add_argument('--output',required=True)
#|    p.add_argument('--device',default='cuda:0');p.add_argument('--train-graph');p.add_argument('--warrant-cache');p.add_argument('--warrant-manifest')
#|    p.add_argument('--foundation-epochs',type=int,default=2);p.add_argument('--consolidation-epochs',type=int,default=1)
#|    p.add_argument('--verifier-epochs',type=int,default=2);p.add_argument('--accum',type=int,default=8);p.add_argument('--seed',type=int,default=2026)
#|    p.add_argument('--lora-lr',type=float,default=2e-4);p.add_argument('--controller-lr',type=float,default=5e-5);p.add_argument('--verifier-lr',type=float,default=2e-4)
#|    p.add_argument('--warmup-ratio',type=float,default=.03)
#|    a=p.parse_args()
#|    if min(a.foundation_epochs,a.consolidation_epochs,a.verifier_epochs,a.accum)<1:raise ValueError('epoch/accum must be positive')
#|    if not all(math.isfinite(x) and x>0 for x in (a.lora_lr,a.controller_lr,a.verifier_lr)):raise ValueError('invalid learning rate')
#|    if not 0<=a.warmup_ratio<1:raise ValueError('invalid warmup ratio')
#|    import torch,pickle
#|    from paths_paper2 import Paper2Paths
#|    from rgc_semantic_readout_stage_8 import ReliabilityTrustReadoutConfig
#|    from rgc_semantic_readout import masked_mean_token_embeddings
#|    from iesfd_stage_10 import explanation_state_mask,evidence_verifier_ranking_loss
#|    from oiec_completion import replace_exact_warrant
#|    paths=Paper2Paths.from_env();out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
#|    rows=json.loads(paths.train_json.read_text(encoding='utf-8'))
#|    validate_training_rows(rows)
#|    config=final_controller_config()
#|    lora_settings={k:v for k,v in fresh_lora_settings(0).items() if k!='target_modules'}
#|    lora_settings['target_rule']='every language decoder layer: q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj'
#|    contract=dict(schema='llava_final_train_v2',controller_config=config,lora_settings=lora_settings,args=vars(a),base_model=paths.llm_path,train_sha256=digest(paths.train_json),
#|        features_sha256=digest(paths.train_features),records=len(rows),test_accessed=False,starting_point='raw LLaVA; fresh LoRA and new modules',
#|        graph_sha256=digest(a.train_graph) if a.variant!='innovation2' else None,
#|        warrant_sha256=digest(a.warrant_cache) if a.variant!='innovation1' else None,
#|        code={n:digest(Path(__file__).with_name(n)) for n in ('train_llava_final.py','llava_final_runtime.py','final_original_verifier.py','iesfd_stage_10.py')})
#|    prepare_run_contract(out,contract)
#|    print('[final config] '+json.dumps(dict(controller=config,lora_rank=128,lora_alpha=256,lora_dropout=.05,lora_modules='q,k,v,o,gate,up,down',warmup_ratio=a.warmup_ratio)),flush=True)
#|    if (out/'complete.json').exists():
#|        done=json.loads((out/'complete.json').read_text())
#|        if digest(out/'model.pt')!=done['sha256']:raise ValueError('final model modified')
#|        print('[final] complete model retained');return
#|    if (out/'model.pt').exists():raise ValueError('uncommitted model.pt exists; inspect before restarting')
#|    records=None
#|    if a.variant!='innovation1':
#|        from cwct_warrant_data import load_warrant_map
#|        import hashlib
#|        records=load_warrant_map(a.warrant_cache)
#|        wm=json.loads(Path(a.warrant_manifest).read_text(encoding='utf-8'))
#|        if wm['cache_sha256']!=digest(a.warrant_cache) or set(records)!={str(r['id']) for r in rows}:raise ValueError('warrant coverage/hash mismatch')
#|        for r in rows:
#|            if hashlib.sha256(r['conversations'][1]['value'].encode('utf-8')).hexdigest()!=records[str(r['id'])]['answer_sha256']:raise ValueError('TRAIN answer does not match warrant')
#|    torch.manual_seed(a.seed);random.seed(a.seed)
#|    rt=load_runtime(paths,a.variant,a.device,config)
#|    graphs,texts=graph_inputs(rt,a.train_graph,'train');groups={}
#|    if rt.controller is not None:
#|        from train_llava_claim_rgc_semantic_readout_stage_4 import load_phenomenon_groups
#|        from rgc_semantic_readout_stage_4 import PHENOMENON_GROUPS
#|        groups,counts=load_phenomenon_groups(a.train_graph);rt.controller.set_group_priors([counts[n] for n in PHENOMENON_GROUPS])
#|    with paths.train_features.open('rb') as f:features=pickle.load(f)
#|    # Checkpointing reduces backbone activation memory; non-reentrant preserves hook graphs.
#|    enable_training_checkpointing(rt.model)
#|    rt.model.enable_input_require_grads();history=[]
#|    for stage,epochs in (('foundation',a.foundation_epochs),('consolidation',a.consolidation_epochs),('verifier',a.verifier_epochs if rt.verifier is not None else 0)):
#|        if not epochs:continue
#|        stage_seed=set_stage_seed(torch,a.seed,stage)
#|        is_verifier,consolidate=configure_stage(rt,stage)
#|        frozen_versions=generator_versions(rt) if is_verifier else None
#|        print(f'[final stage] {stage} seed={stage_seed} generator_frozen={is_verifier}',flush=True)
#|        optim_groups=[]
#|        for obj,lr in ((rt.model,a.lora_lr),(rt.controller,a.controller_lr if not consolidate else 5e-6),(rt.verifier,a.verifier_lr),(rt.roles,a.verifier_lr)):
#|            if obj is not None:
#|                params=[q for q in obj.parameters() if q.requires_grad]
#|                if params:optim_groups.append(dict(params=params,lr=lr))
#|        optimizer=torch.optim.AdamW(optim_groups,weight_decay=1e-4)
#|        total_steps=math.ceil(len(rows)/a.accum)*epochs
#|        warmup_steps=int(total_steps*a.warmup_ratio)
#|        scheduler=torch.optim.lr_scheduler.LambdaLR(optimizer,lambda step:warmup_cosine(step,total_steps,warmup_steps))
#|        for epoch in range(epochs):
#|            order=list(rows);random.Random(stage_seed+epoch).shuffle(order);total=0.;active=0;optimizer.zero_grad(set_to_none=True)
#|            for i,row in enumerate(order):
#|                if rt.controller is not None and not is_verifier:
#|                    rt.controller.set_training_progress((epoch*len(order)+i)/max(1,epochs*len(order)-1))
#|                record=records[str(row['id'])] if records else None
#|                eligible=bool(record and record['auxiliary_eligible'] and record['same_label_hard_mismatch']['length_ratio']>=.5)
#|                loss=None
#|                if not is_verifier or eligible:
#|                    condition=context(rt,row,features,graphs,texts,groups.get(str(row['id'])) if not is_verifier else None)
#|                    with torch.no_grad():embeds,mask,_=prompt(rt,row)
#|                    # The frozen prompt embedding still enables backbone checkpoint autograd.
#|                    if not is_verifier and not consolidate:embeds=embeds.detach().requires_grad_(True)
#|                    answer=row['conversations'][1]['value']
#|                    if is_verifier:
#|                        values=[]
#|                        for text in (answer,replace_exact_warrant(answer,record)):
#|                            with torch.no_grad():output,hidden,ids,labels=forward_answer(rt,embeds,mask,text,training=True)
#|                            body=explanation_state_mask(torch,labels,ignore_index=-100,label_token_count=4)
#|                            values.append(rt.verifier.score_evidence_candidates(hidden.detach(),body)[0]);del output,hidden
#|                        loss,_,_=evidence_verifier_ranking_loss(torch,*values,margin=.3,temperature=.1,anchor_weight=.1);loss=.2*loss
#|                    else:
#|                        semantic=None
#|                        if rt.controller is not None:
#|                            target_ids=rt.tokenizer(answer,add_special_tokens=False,return_tensors='pt').input_ids.to(a.device)
#|                            with torch.no_grad():target,present=masked_mean_token_embeddings(rt.model.get_input_embeddings(),target_ids,torch.ones_like(target_ids),vocab_size=rt.model.config.vocab_size)
#|                            semantic=rt.controller.semantic_alignment_loss(condition,target,present)
#|                        output,hidden,ids,labels=forward_answer(rt,embeds,mask,answer,training=True);loss=output.loss
#|                        if rt.controller is not None:
#|                            loss=loss+rt.controller.extra_language_loss(output.logits,labels,-100)+rt.controller.decoder_alignment_loss(labels,-100)
#|                            if not consolidate:loss=loss+.03*semantic
#|                            if consolidate:loss=loss+rt.controller.parameter_trust_loss()
#|                        del output,hidden
#|                    if not bool(torch.isfinite(loss)):raise FloatingPointError('nonfinite training loss')
#|                    size=min(a.accum,len(order)-(i//a.accum)*a.accum)
#|                    (loss/size).backward();total+=float(loss.detach());active+=1
#|                if (i+1)%a.accum==0 or i+1==len(order):
#|                    params=[q for g in optimizer.param_groups for q in g['params']]
#|                    if any(q.grad is not None for q in params):
#|                        torch.nn.utils.clip_grad_norm_(params,1.,error_if_nonfinite=True);optimizer.step();scheduler.step()
#|                        if rt.controller is not None and not is_verifier:rt.controller.on_optimizer_step()
#|                    optimizer.zero_grad(set_to_none=True)
#|                if rt.controller is not None:rt.controller.clear_group_context()
#|                if (i+1)%100==0 or i+1==len(order):print(f'[final {a.variant}] stage={stage} epoch={epoch+1} records={i+1}/{len(order)} active={active} loss={total/(i+1):.7f} lr={scheduler.get_last_lr()}',flush=True)
#|            if not active:raise RuntimeError('stage has no active training records')
#|            if is_verifier:assert_frozen_generator(rt,frozen_versions)
#|            history.append(dict(stage=stage,epoch=epoch+1,records=len(order),active=active,loss=total/len(order),stage_seed=stage_seed,
#|                generator_version_check='passed' if is_verifier else 'not_applicable'))
#|            write_json(out/'training_history.json',history)
#|        del optimizer
#|    payload=export_payload(rt,config,dict(contract=contract,history=history))
#|    tmp=out/'model.tmp';torch.save(payload,tmp);tmp.replace(out/'model.pt')
#|    write_json(out/'complete.json',dict(variant=a.variant,records=len(rows),sha256=digest(out/'model.pt'),single_weight_file=True,test_accessed=False))
#|    print(f'[final] one final weight file: {out / "model.pt"}',flush=True)
#|
#|if __name__=='__main__':
#|    # Keep the old command name, but never run the superseded R3 protocol.
#|    from train_llava_replay import main as replay_main
#|    replay_main()
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: train_llava_replay.py ===
#|"""Historical v5 -> v6 -> v8 -> IESFD-v10, one final weight file.
#|
#|Historical training functions, data preprocessing and optimizers are reused.
#|The standalone innovation2 branch is a separately declared LLaVA ablation.
#|"""
#|import argparse
#|import gc
#|import importlib
#|import json
#|import os
#|from pathlib import Path
#|from types import SimpleNamespace
#|
#|from iesfd_stage_13_repair import digest, write_json
#|from llava_replay_memory import MemorySource, split_final_modules
#|
#|ROOT = Path(__file__).resolve().parent
#|EXTRA_GRAPH = ('graph_semantic_ids', 'graph_semantic_mask', 'phenomenon_group')
#|EXTRA_PAIR = ('oiec_negative_ids', 'oiec_negative_mask', 'oiec_negative_labels', 'oiec_eligible', 'oiec_length_ratio')
#|
#|
#|def stage_args(stage, device, graph, warrant=None, manifest=None, source_json=None):
#|    """Historical parser defaults + historical full-run shell overrides."""
#|    names = {'v5': 'train_llava_claim_rgc_semantic_readout_stage_5',
#|             'v6': 'train_llava_claim_rgc_semantic_readout_stage_6',
#|             'v8': 'train_llava_claim_rgc_semantic_readout_stage_8',
#|             'verifier': 'train_llava_claim_iesfd_stage_10'}
#|    mod = importlib.import_module(names[stage])
#|    argv = ['--device', device, '--concept_graph_cache', str(graph), '--num_tokens', '0']
#|    if stage == 'verifier':
#|        argv += ['--epochs', '2', '--seed', '2026', '--batch_size', '1', '--accum_steps', '8',
#|                 '--num_workers', '2', '--llm_lr', '1e-8', '--projector_lr', '2e-4',
#|                 '--projector_weight_decay', '1e-4', '--graph_dropout', '0',
#|                 '--warrant_cache', str(warrant), '--warrant_manifest', str(manifest),
#|                 '--cache_source_json', str(source_json), '--cache_partition_seed', '2026',
#|                 '--completion_weight', '1e-8', '--completion_margin', '.10',
#|                 '--completion_temperature', '.10', '--completion_anchor_weight', '0',
#|                 '--completion_head_lr', '1e-8', '--l2sp_weight', '0', '--use_full_train']
#|    # Other stages' shell numeric defaults equal their parser defaults.
#|    return mod, mod.build_parser().parse_args(argv)
#|
#|
#|def run_stage(stage, args, source, variant, history, output):
#|    from paths_paper2 import Paper2Paths
#|    import train_llava_claim_graphprompt as loop
#|    from train_llava_claim_rgc_semantic_readout_stage_4 import load_phenomenon_groups
#|    from rgc_semantic_readout_stage_4 import PHENOMENON_GROUPS
#|    from rgc_semantic_readout import attach_semantic_readout
#|    from llava_final_runtime import enable_training_checkpointing
#|    counts = {}
#|    standalone = variant == 'innovation2'
#|    modules = {'v5': 'train_llava_claim_rgc_semantic_readout_stage_5',
#|               'v6': 'train_llava_claim_rgc_semantic_readout_stage_6',
#|               'v8': 'train_llava_claim_rgc_semantic_readout_stage_8',
#|               'verifier': 'train_llava_claim_iesfd_stage_10'}
#|    mod = importlib.import_module(modules[stage])
#|    if stage == 'verifier':
#|        mod.oiec._validate_manifest(args, Paper2Paths.from_env())
#|    if standalone:
#|        from llava_replay_standalone import install_standalone
#|        def installer(module, graph, **_):
#|            return install_standalone(module, graph, args, stage == 'verifier')
#|        def initialize(model, module, paths, device):
#|            if source is not None: model.llm = source.restore_lora(model.llm)
#|            for p in model.llm.parameters(): p.requires_grad_(False)
#|            if stage == 'v5':
#|                for name, p in model.llm.named_parameters(): p.requires_grad_('lora_' in name)
#|        def optimizer(model, torch, _args):
#|            params = model.projector.parameters() if stage == 'verifier' else (p for p in model.llm.parameters() if p.requires_grad)
#|            return torch.optim.AdamW(params, lr=args.projector_lr if stage == 'verifier' else args.llm_lr,
#|                                     weight_decay=args.projector_weight_decay if stage == 'verifier' else 0.)
#|        metrics = None
#|    else:
#|        def installer(module, graph, **_):
#|            _, values = load_phenomenon_groups(graph)
#|            counts.update(values)
#|            if stage == 'v5':
#|                mod.base_v4.base_train.make_semantic_readout_classes = mod.make_v5_readout_classes
#|                mod.base_v4.base_train.config_from_args = mod.config_from_args
#|                return mod.base_v4.install_v4_training(module, graph, args=args)
#|            if stage == 'v6': return mod.install_v6_training(module, graph, args=args)
#|            if stage == 'v8':
#|                # v10 imports replace this factory; explicitly select the actual v8 stage.
#|                from rgc_semantic_readout_stage_8 import make_v8_readout_classes
#|                mod.make_v8_readout_classes = make_v8_readout_classes
#|                return mod.install_v8_training(module, graph, args=args)
#|            mod.oiec.v8.make_v8_readout_classes = mod.make_iesfd_v10_readout_classes
#|            installed, _ = mod.install_iesfd_v10_training(module, graph, args=args)
#|            return installed
#|        def initialize(model, module, paths, device):
#|            if stage == 'v5':
#|                model.projector.set_group_priors([counts[name] for name in PHENOMENON_GROUPS])
#|                attach_semantic_readout(model.llm, model.projector)
#|            elif stage == 'v6': mod.initialize_from_v5(model, module, paths, device, args, counts, memory_source=source)
#|            elif stage == 'v8': mod.initialize_from_v6(model, module, paths, device, args, counts, memory_source=source)
#|            else:
#|                mod.initialize_from_v8(model, module, paths, device, args, counts, memory_source=source)
#|                for name in ('last_oiec_pair', 'last_oiec_auxiliary', 'last_oiec_gap', 'last_oiec_positive',
#|                             'last_oiec_negative', 'last_oiec_l2sp', 'last_oiec_eligible', 'last_oiec_length_ratio'):
#|                    setattr(model.projector, name, module.torch.tensor(0., device=device))
#|        optimizer = mod.base_v4.base_train.build_optimizer if stage == 'v5' else mod.build_optimizer
#|        metrics = getattr(mod, {'v5': 'collect_v5_metrics', 'v6': 'collect_v6_metrics',
#|                               'v8': 'collect_v8_metrics', 'verifier': 'collect_metrics'}[stage])
#|    frozen = {}
#|    def prepare(model, module):
#|        enable_training_checkpointing(model.llm)
#|        # Preserve original mode/forward path, check only parameters that must freeze.
#|        frozen.update({name: p._version for name, p in model.named_parameters() if not p.requires_grad})
#|        print('[replay trainable] ' + json.dumps({
#|            'stage': stage, 'parameters': sum(p.numel() for p in model.parameters() if p.requires_grad),
#|            'generator_trainable': any(p.requires_grad for p in model.llm.parameters())}), flush=True)
#|    def epoch_done(model, epoch, nan_count):
#|        for name, p in model.named_parameters():
#|            if name in frozen and (p._version != frozen[name] or p.requires_grad):
#|                raise RuntimeError('Frozen parameter changed: ' + name)
#|        history.append({'stage': stage, 'epoch': epoch, 'nan_count': nan_count, 'args': vars(args)})
#|        write_json(output / 'training_history.json', history)
#|        print('[replay] epoch completed; intermediate weights not written', flush=True)
#|    extra = (() if standalone else EXTRA_GRAPH) + (EXTRA_PAIR if stage == 'verifier' else ())
#|    cwd = Path.cwd()
#|    try:
#|        return loop.train(args, install_training=installer, initialize_model=initialize,
#|                          build_optimizer=optimizer, extra_batch_keys=extra, collect_metrics=metrics,
#|                          checkpoint_writer=epoch_done, prepare_model=prepare, expected_records=4578)
#|    finally:
#|        os.chdir(cwd)
#|
#|
#|def main():
#|    p = argparse.ArgumentParser(description=__doc__)
#|    p.add_argument('--variant', required=True, choices=('innovation1', 'innovation2', 'combined'))
#|    p.add_argument('--output', required=True)
#|    p.add_argument('--device', default='cuda:0')
#|    p.add_argument('--train-graph', required=True)
#|    p.add_argument('--warrant-cache')
#|    p.add_argument('--warrant-manifest')
#|    p.add_argument('--print-plan', action='store_true')
#|    a = p.parse_args()
#|    from paths_paper2 import Paper2Paths
#|    paths = Paper2Paths.from_env()
#|    output = Path(a.output).resolve()
#|    graph = Path(a.train_graph).resolve()
#|    warrant = Path(a.warrant_cache).resolve() if a.warrant_cache else None
#|    manifest = Path(a.warrant_manifest).resolve() if a.warrant_manifest else None
#|    if a.variant != 'innovation1' and (warrant is None or manifest is None):
#|        p.error('Both warrant cache and manifest are required for innovation2')
#|    stages = ['v5'] if a.variant == 'innovation2' else ['v5', 'v6', 'v8']
#|    if a.variant != 'innovation1': stages.append('verifier')
#|    plans = [stage_args(stage, a.device, graph, warrant, manifest,
#|                        paths.orig_root / 'data/no_prompt_train.json')[1] for stage in stages]
#|    if a.variant == 'innovation2':
#|        # These objectives/modules do not exist in the standalone ablation.
#|        # Keep the printed plan honest even though its SFT hyperparameters use v5's parser.
#|        plans[0].projector_lr = 0.
#|        plans[0].projector_weight_decay = 0.
#|        for args in plans:
#|            args.cf_loss_weight = 0.
#|            args.semantic_loss_weight = 0.
#|            args.graph_dropout = 0.
#|            args.alignment_nce_weight = 0.
#|            args.alignment_final_nce_weight = 0.
#|            if hasattr(args, 'decoder_alignment_weight'): args.decoder_alignment_weight = 0.
#|    plan = {'variant': a.variant, 'stages': [{'name': name, 'args': vars(args)} for name, args in zip(stages, plans)],
#|            'standalone_ablation': a.variant == 'innovation2', 'innovation1_controller': a.variant != 'innovation2',
#|            'standalone_v5_name_means': 'LLaVA SFT only; historical v5 LoRA hyperparameters, no v5 controller' if a.variant == 'innovation2' else None,
#|            'intermediate_weights': False}
#|    if a.print_plan:
#|        print(json.dumps(plan, ensure_ascii=False, indent=2)); return
#|    import torch
#|    from train_llava_final import validate_training_rows, prepare_run_contract
#|    from llava_final_runtime import export_payload
#|    validate_training_rows(json.loads(paths.train_json.read_text(encoding='utf-8')))
#|    output.mkdir(parents=True, exist_ok=True)
#|    names = ['train_llava_replay.py', 'llava_replay_memory.py', 'llava_replay_standalone.py',
#|             'llava_final_runtime.py', 'train_llava_final.py', 'iesfd_stage_10.py', 'final_original_verifier.py',
#|             'oiec_completion.py', 'cwct_warrant_data.py', 'concept_graph_integration.py', 'paths_paper2.py',
#|             'train_llava_claim_graphprompt.py', 'train_llava_claim_oiec_stage_1.py', 'train_llava_claim_iesfd_stage_10.py']
#|    names += [prefix + suffix + '.py' for prefix in ('train_llava_claim_rgc_semantic_readout', 'rgc_semantic_readout')
#|              for suffix in ('', '_stage_4', '_stage_5', '_stage_6', '_stage_7', '_stage_8')]
#|    sources = [ROOT / name for name in names]
#|    contract = {'schema': 'llava_replay_v4', 'base_model': paths.llm_path, 'plan': plan,
#|                'train_sha256': digest(paths.train_json), 'feature_sha256': digest(paths.train_features),
#|                'graph_sha256': digest(graph), 'warrant_sha256': digest(warrant) if warrant else None,
#|                'manifest_sha256': digest(manifest) if manifest else None,
#|                'original_train_sha256': digest(paths.orig_root / 'train_moe_创新点1.py'),
#|                'code': {s.name: digest(s) for s in sources}, 'test_accessed': False}
#|    prepare_run_contract(output, contract)
#|    if (output / 'complete.json').exists():
#|        done = json.loads((output / 'complete.json').read_text())
#|        if done['sha256'] != digest(output / 'model.pt'): raise ValueError('Final model hash mismatch')
#|        print('[replay] complete final weight retained'); return
#|    if (output / 'model.pt').exists(): raise ValueError('Uncommitted final weight exists')
#|    print('[replay plan] ' + json.dumps(plan), flush=True)
#|    # Imported historical modules set checkpoint namespaces; fix only the output namespace.
#|    os.environ['PAPER2_CKPT_NAME'] = str(output)
#|    history, source, model = [], None, None
#|    for stage, args in zip(stages, plans):
#|        model = run_stage(stage, args, source, a.variant, history, output)
#|        if stage != stages[-1]:
#|            source = MemorySource.capture(model)
#|            del model
#|            model = None
#|            gc.collect(); torch.cuda.empty_cache()
#|    controller, verifier, roles, config = split_final_modules(torch, model, a.variant)
#|    rt = SimpleNamespace(model=model.llm, controller=controller, verifier=verifier, roles=roles, variant=a.variant)
#|    payload = export_payload(rt, config, {'contract': contract, 'history': history})
#|    tmp = output / 'model.tmp'
#|    torch.save(payload, tmp)
#|    tmp.replace(output / 'model.pt')
#|    write_json(output / 'complete.json', {'variant': a.variant, 'sha256': digest(output / 'model.pt'),
#|                                        'single_weight_file': True, 'protocol': 'historical_replay_v4'})
#|    print('[replay] final weight: ' + str(output / 'model.pt'), flush=True)
#|
#|
#|if __name__ == '__main__':
#|    main()
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: tspib_stage_6_losses.py ===
#|"""Pure loss helpers for reliability-aware trust and teacher consistency.
#|
#|The shared graph-prompt trainer imports :func:`masked_teacher_kl` lazily, so
#|experiments that do not enable teacher consistency do not depend on this file.
#|SCBEA-v2 enables that optional branch and therefore requires this module.
#|"""
#|
#|from __future__ import annotations
#|
#|import torch
#|import torch.nn.functional as F
#|
#|
#|def validate_trust_radii(
#|    reliable_radius: float,
#|    uncertain_radius: float,
#|) -> None:
#|    reliable = float(reliable_radius)
#|    uncertain = float(uncertain_radius)
#|    if reliable <= 0.0 or uncertain <= 0.0 or reliable >= uncertain:
#|        raise ValueError(
#|            "expected 0 < reliable_radius < uncertain_radius"
#|        )
#|
#|
#|def interpolate_trust_radius(
#|    reliability,
#|    reliable_radius: float,
#|    uncertain_radius: float,
#|):
#|    """Linearly tighten the radius as reliability increases."""
#|
#|    validate_trust_radii(reliable_radius, uncertain_radius)
#|    if torch.is_tensor(reliability):
#|        clipped = reliability.detach().float().clamp(0.0, 1.0)
#|        return float(uncertain_radius) + (
#|            float(reliable_radius) - float(uncertain_radius)
#|        ) * clipped
#|    clipped = min(max(float(reliability), 0.0), 1.0)
#|    return float(uncertain_radius) + (
#|        float(reliable_radius) - float(uncertain_radius)
#|    ) * clipped
#|
#|
#|def reliability_weight_with_floor(reliability, floor: float):
#|    """Map reliability to ``[floor, 1]`` without allowing gradients through it."""
#|
#|    floor = float(floor)
#|    if not 0.0 <= floor <= 1.0:
#|        raise ValueError("reliability floor must be in [0, 1]")
#|    if torch.is_tensor(reliability):
#|        clipped = reliability.detach().float().clamp(0.0, 1.0)
#|        return floor + (1.0 - floor) * clipped
#|    clipped = min(max(float(reliability), 0.0), 1.0)
#|    return floor + (1.0 - floor) * clipped
#|
#|
#|def _per_sample_mean(value: torch.Tensor) -> torch.Tensor:
#|    if value.dim() <= 1:
#|        return value.reshape(value.size(0), -1).mean(dim=1)
#|    return value.reshape(value.size(0), -1).mean(dim=1)
#|
#|
#|def _per_sample_reliability(
#|    reliability: torch.Tensor,
#|    batch_size: int,
#|    *,
#|    device,
#|) -> torch.Tensor:
#|    weights = reliability.detach().to(device=device, dtype=torch.float32)
#|    if weights.numel() == batch_size:
#|        weights = weights.reshape(batch_size)
#|    elif weights.size(0) == batch_size:
#|        weights = weights.reshape(batch_size, -1).mean(dim=1)
#|    else:
#|        raise ValueError(
#|            "reliability must provide one value per batch sample"
#|        )
#|    return weights.clamp(0.0, 1.0)
#|
#|
#|def reliability_trust_region_loss(
#|    teacher_prompt: torch.Tensor,
#|    student_prompt: torch.Tensor,
#|    reliability: torch.Tensor,
#|    *,
#|    reliable_radius: float,
#|    uncertain_radius: float,
#|    soft: bool = False,
#|    eps: float = 1e-8,
#|) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
#|    """Return dimensionless prompt trust loss, amplitude ratio, and radius."""
#|
#|    validate_trust_radii(reliable_radius, uncertain_radius)
#|    if teacher_prompt.shape != student_prompt.shape:
#|        raise ValueError("teacher/student prompt shapes differ")
#|    if teacher_prompt.dim() < 2:
#|        raise ValueError("prompt tensors must include batch and feature axes")
#|    if eps <= 0.0:
#|        raise ValueError("eps must be positive")
#|
#|    teacher = teacher_prompt.detach().float()
#|    student = student_prompt.float()
#|    batch_size = student.size(0)
#|    residual_rms = _per_sample_mean(
#|        (student - teacher).square()
#|    ).sqrt()
#|    teacher_rms = _per_sample_mean(teacher.square()).sqrt().clamp_min(eps)
#|    amplitude_ratio = residual_rms / teacher_rms
#|    weights = _per_sample_reliability(
#|        reliability,
#|        batch_size,
#|        device=student.device,
#|    )
#|    radius = interpolate_trust_radius(
#|        weights,
#|        reliable_radius,
#|        uncertain_radius,
#|    )
#|    normalized = amplitude_ratio / radius.clamp_min(eps)
#|    if soft:
#|        loss = normalized.square().mean()
#|    else:
#|        loss = F.relu(normalized - 1.0).square().mean()
#|    return loss, amplitude_ratio.mean(), radius.mean()
#|
#|
#|def masked_teacher_kl(
#|    student_logits: torch.Tensor,
#|    teacher_logits: torch.Tensor,
#|    labels: torch.Tensor,
#|    *,
#|    ignore_index: int,
#|    temperature: float,
#|    reliability: torch.Tensor,
#|) -> torch.Tensor:
#|    """Teacher-to-student KL on shifted, valid answer-token positions.
#|
#|    Reliability is an absolute per-sample weight.  The final reduction is a
#|    batch mean rather than normalization by the sum of weights; this preserves
#|    reliability strength when the training batch size is one.
#|    """
#|
#|    if student_logits.shape != teacher_logits.shape:
#|        raise ValueError("student/teacher logit shapes differ")
#|    if student_logits.dim() != 3:
#|        raise ValueError("teacher KL expects [batch, sequence, vocabulary]")
#|    if labels.dim() != 2 or labels.shape[:2] != student_logits.shape[:2]:
#|        raise ValueError("teacher KL labels must match batch and sequence")
#|    if student_logits.size(1) <= 1:
#|        return student_logits.sum() * 0.0
#|    temperature = float(temperature)
#|    if temperature <= 0.0:
#|        raise ValueError("temperature must be positive")
#|
#|    student = student_logits[:, :-1, :].float() / temperature
#|    teacher = teacher_logits.detach()[:, :-1, :].float() / temperature
#|    shifted_labels = labels[:, 1:]
#|    valid = shifted_labels.ne(int(ignore_index))
#|    teacher_probability = torch.softmax(teacher, dim=-1)
#|    student_log_probability = torch.log_softmax(student, dim=-1)
#|    token_kl = F.kl_div(
#|        student_log_probability,
#|        teacher_probability,
#|        reduction="none",
#|    ).sum(dim=-1)
#|    token_kl = token_kl * (temperature * temperature)
#|    valid_float = valid.to(dtype=token_kl.dtype)
#|    per_sample = (
#|        token_kl * valid_float
#|    ).sum(dim=1) / valid_float.sum(dim=1).clamp_min(1.0)
#|    weights = _per_sample_reliability(
#|        reliability,
#|        student_logits.size(0),
#|        device=student_logits.device,
#|    )
#|    return (per_sample * weights).mean()
# === END REQUIRED SOURCE ===

# === BEGIN REQUIRED SOURCE: verify_cwct_stage_1_checkpoint.py ===
#|"""Audit that CWCT changed only the traced global LoRA circuit."""
#|
#|from __future__ import annotations
#|
#|import argparse
#|import json
#|from pathlib import Path
#|
#|from cwct_circuit_tuning import (
#|    COMPONENT_MODULES,
#|    load_circuit_manifest,
#|    manifest_sha256,
#|    parse_lora_parameter,
#|    selected_circuits,
#|)
#|
#|
#|def _load_adapter(path: Path):
#|    safe = path / "adapter_model.safetensors"
#|    binary = path / "adapter_model.bin"
#|    if safe.is_file():
#|        from safetensors.torch import load_file
#|
#|        return load_file(str(safe), device="cpu")
#|    if binary.is_file():
#|        import torch
#|
#|        return torch.load(binary, map_location="cpu")
#|    raise FileNotFoundError(f"missing adapter weights under {path}")
#|
#|
#|def _config(path: Path):
#|    with (path / "adapter_config.json").open("r", encoding="utf-8") as handle:
#|        return json.load(handle)
#|
#|
#|def verify(args: argparse.Namespace) -> None:
#|    import torch
#|
#|    source_lora = Path(args.source_lora).resolve()
#|    target_lora = Path(args.target_lora).resolve()
#|    source_projector = Path(args.source_projector).resolve()
#|    target_projector = Path(args.target_projector).resolve()
#|    circuit_path = Path(args.circuit_manifest).resolve()
#|    if source_lora == target_lora or source_projector == target_projector:
#|        raise RuntimeError("CWCT source and target paths must be isolated")
#|    manifest = load_circuit_manifest(circuit_path)
#|    selected = selected_circuits(manifest)
#|    source = _load_adapter(source_lora)
#|    target = _load_adapter(target_lora)
#|    if _config(source_lora) != _config(target_lora):
#|        raise RuntimeError("CWCT source/target adapter configs differ")
#|    if set(source) != set(target):
#|        raise RuntimeError("CWCT source/target adapter keys differ")
#|    if any(not bool(torch.isfinite(value).all()) for value in target.values()):
#|        raise RuntimeError("CWCT target adapter has non-finite tensors")
#|
#|    def allowed(key: str) -> bool:
#|        parsed = parse_lora_parameter(key)
#|        if parsed is None:
#|            return False
#|        layer, component, module_name, factor = parsed
#|        return bool(
#|            (layer, component) in selected
#|            and module_name in COMPONENT_MODULES[component]
#|            and factor in set(args.train_lora_factors)
#|        )
#|
#|    changed = [key for key in source if not torch.equal(source[key], target[key])]
#|    if not changed:
#|        raise RuntimeError("CWCT adapter is byte-equivalent to clean v8")
#|    illegal = [key for key in changed if not allowed(key)]
#|    if illegal:
#|        raise RuntimeError(f"non-circuit LoRA tensors changed: {illegal[:5]}")
#|    expected_groups = {
#|        (layer, component, factor)
#|        for layer, component in selected
#|        for factor in set(args.train_lora_factors)
#|    }
#|    changed_groups = {
#|        (parsed[0], parsed[1], parsed[3])
#|        for key in changed
#|        if (parsed := parse_lora_parameter(key)) is not None
#|    }
#|    missing_groups = expected_groups - changed_groups
#|    if missing_groups:
#|        raise RuntimeError(
#|            "selected circuit/factor received no measurable update: "
#|            f"{sorted(missing_groups)}"
#|        )
#|
#|    source_proj = torch.load(source_projector, map_location="cpu")
#|    target_proj = torch.load(target_projector, map_location="cpu")
#|    if set(source_proj) != set(target_proj):
#|        raise RuntimeError("CWCT frozen projector keys changed")
#|    if any(not bool(torch.isfinite(value).all()) for value in target_proj.values()):
#|        raise RuntimeError("CWCT target projector has non-finite tensors")
#|    projector_changed = [
#|        key for key in source_proj if not torch.equal(source_proj[key], target_proj[key])
#|    ]
#|    if projector_changed:
#|        raise RuntimeError(
#|            f"CWCT frozen projector tensors changed: {projector_changed[:5]}"
#|        )
#|
#|    embedded_path = target_lora / "cwct_manifest.json"
#|    if not embedded_path.is_file():
#|        raise FileNotFoundError(f"missing embedded CWCT manifest: {embedded_path}")
#|    with embedded_path.open("r", encoding="utf-8") as handle:
#|        embedded = json.load(handle)
#|    if manifest_sha256(embedded) != manifest_sha256(manifest):
#|        # Training metadata is allowed, but the traced contract must be exact.
#|        stripped = dict(embedded)
#|        stripped.pop("training", None)
#|        if manifest_sha256(stripped) != manifest_sha256(manifest):
#|            raise RuntimeError("embedded CWCT circuit differs from trace manifest")
#|
#|    delta_sq = torch.zeros((), dtype=torch.float64)
#|    reference_sq = torch.zeros((), dtype=torch.float64)
#|    for key in source:
#|        if allowed(key):
#|            delta_sq += (target[key].double() - source[key].double()).square().sum()
#|            reference_sq += source[key].double().square().sum()
#|    relative = float(torch.sqrt(delta_sq / reference_sq.clamp_min(1e-12)))
#|    if relative > args.max_relative_drift + args.tolerance:
#|        raise RuntimeError(
#|            f"CWCT relative drift {relative:.8f} exceeds {args.max_relative_drift:.8f}"
#|        )
#|    print(
#|        f"[cwct-v1-verify] passed changed={len(changed)} "
#|        f"changed_groups={len(changed_groups)} "
#|        f"relative_drift={relative:.8f} projector_equal=true "
#|        "train_only_trace=true fixed_global_circuit=true"
#|    )
#|
#|
#|def parse_args():
#|    parser = argparse.ArgumentParser()
#|    parser.add_argument("--source_lora", required=True)
#|    parser.add_argument("--target_lora", required=True)
#|    parser.add_argument("--source_projector", required=True)
#|    parser.add_argument("--target_projector", required=True)
#|    parser.add_argument("--circuit_manifest", required=True)
#|    parser.add_argument("--train_lora_factors", default="B")
#|    parser.add_argument("--max_relative_drift", type=float, default=0.01)
#|    parser.add_argument("--tolerance", type=float, default=1e-7)
#|    return parser.parse_args()
#|
#|
#|if __name__ == "__main__":
#|    verify(parse_args())
# === END REQUIRED SOURCE ===
