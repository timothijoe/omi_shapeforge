"""Run deterministic interface checks and save a short, explicitly scripted rollout."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import struct
import zlib

import gymnasium
from gymnasium.utils.env_checker import check_env
import mujoco
import numpy as np

from .config import InsertionConfig
from .insertion_env import SimpleInsertionEnv


def _json(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(type(value).__name__)


def _save_png(path, rgb):
    """Standard-library PNG output for the optional rendered RGB frame."""
    height, width, _ = rgb.shape
    def chunk(name, data):
        return struct.pack(">I", len(data)) + name + data + struct.pack(">I", zlib.crc32(name + data) & 0xffffffff)
    raw = b"".join(b"\0" + row.tobytes() for row in np.asarray(rgb, dtype=np.uint8))
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    config = InsertionConfig()
    probe = SimpleInsertionEnv(config)
    try:
        check_env(probe, skip_render_check=True)
    finally:
        probe.close()
    env = SimpleInsertionEnv(config, render_mode="rgb_array" if args.render else None)
    results = []
    try:
        (args.output / "scene.xml").write_text(env.scene_xml)
        (args.output / "contract.json").write_text(json.dumps(config.contract(), indent=2))
        with (args.output / "transitions.jsonl").open("w") as stream:
            for episode, scenario in enumerate(["scripted_aligned", "blocked_offset", "idle_timeout"]):
                options = {"initial_pose": [.003, .005, 0, 0, 0, 0]} if scenario == "blocked_offset" else None
                observation, _ = env.reset(seed=7, options=options)
                if args.render and episode == 0:
                    _save_png(args.output / "initial.png", env.render())
                contacts = 0
                for step in range(config.max_steps):
                    action = env.scripted_action() if scenario == "scripted_aligned" else np.array([0, -1, 0, 0, 0, 0], np.float32) if scenario == "blocked_offset" else np.zeros(6, np.float32)
                    next_observation, reward, terminated, truncated, info = env.step(action)
                    contacts = max(contacts, info["contact_count"])
                    row = {"schema_version": 1, "contract": config.contract()["id"], "episode": episode,
                           "scenario": scenario, "step": step, "observation": observation,
                           "requested_action": action, "reward": reward, "next_observation": next_observation,
                           "terminated": terminated, "truncated": truncated, "info": info,
                           "policy_source": "scripted_test_not_learned"}
                    stream.write(json.dumps(row, default=_json) + "\n")
                    observation = next_observation
                    if terminated or truncated:
                        break
                assert info["is_success"] == (scenario == "scripted_aligned"), (scenario, info)
                if scenario == "blocked_offset":
                    assert contacts > 0
                if args.render:
                    _save_png(args.output / f"{scenario}.png", env.render())
                results.append({"scenario": scenario, "steps": step + 1, "reason": info["reason"],
                                "success": info["is_success"], "contacts": contacts,
                                "depth_m": info["depth_m"], "terminated": terminated, "truncated": truncated})
        report = {"status": "interface_smoke_passed", "config": asdict(config), "episodes": results,
                  "gymnasium_checker_passed": True, "versions": {"mujoco": mujoco.__version__, "gymnasium": gymnasium.__version__, "numpy": np.__version__},
                  "training_run": False, "robot_model_integrated": False, "physical_insertion_verified": False,
                  "limitations": ["Primitive collision proxy, not full V3/r04 mesh", "No elastic fingers, robot, camera or tactile observation", "Scripted controller does not demonstrate RL learning", "Not compatible with existing HIL replay without an explicit adapter"],
                  "files_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in args.output.iterdir() if p.is_file()}}
        (args.output / "report.json").write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))
    finally:
        env.close()


if __name__ == "__main__":
    main()
