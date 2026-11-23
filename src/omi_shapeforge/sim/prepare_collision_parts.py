"""Reproducible approximate convex pieces for the three non-convex contact parts."""
import argparse
import importlib.metadata
import json
from pathlib import Path

import coacd
import numpy as np

from .mesh_audit import load_parts, geometry_hash


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    _, parts = load_parts(args.inputs)
    args.output.mkdir(parents=True, exist_ok=False)
    coacd.set_log_level("warn")
    settings = dict(threshold=.01, preprocess_mode="auto", preprocess_resolution=60,
        resolution=2000, mcts_nodes=20, mcts_iterations=100, mcts_max_depth=3, merge=True, seed=7)
    for kind, index in (("socket", 33), ("module", 14), ("socket", 120)):
        part = parts[kind][index]
        mesh = part["mesh"].copy()
        mesh.process(validate=True)
        result = coacd.run_coacd(coacd.Mesh(mesh.vertices / 1000, mesh.faces), **settings)
        folder = args.output / f"{kind}_{index:03d}"
        folder.mkdir()
        for i, (vertices, faces) in enumerate(result):
            np.savez_compressed(folder / f"{i:03d}.npz", vertices=vertices * 1000, faces=faces)
        record = dict(source=part["name"], source_sha256=part["sha256"], pieces=len(result),
            geometry_sha256=geometry_hash(part["mesh"]),
            coacd_version=importlib.metadata.version("coacd"), settings=settings,
            units="input converted mm to m before decomposition; output stored mm",
            scope="approximation, validated by contact probes; normalized threshold is not a certified distance bound")
        (folder / "record.json").write_text(json.dumps(record, indent=2) + "\n")
        print(kind, index, len(result), flush=True)


if __name__ == "__main__":
    main()
