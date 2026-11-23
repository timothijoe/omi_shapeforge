"""Interactive inspection of the imported robot scene, without stepping a policy."""
import argparse
from pathlib import Path
import time

import mujoco.viewer

from .robot_env import RobotReachEnv


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene-dir", type=Path, required=True)
    args = parser.parse_args()
    env = RobotReachEnv(args.scene_dir)
    try:
        env.reset(seed=7)
        with mujoco.viewer.launch_passive(env.model, env.data, show_left_ui=False, show_right_ui=False) as viewer:
            with viewer.lock():
                viewer.cam.lookat[:] = [.30, 0, .75]
                viewer.cam.distance = 2.5
                viewer.cam.azimuth = 135
                viewer.cam.elevation = -20
            print("ROBOT_VIEWER_READY: inspection only, no policy or physics stepping", flush=True)
            while viewer.is_running():
                viewer.sync()
                time.sleep(.02)
    finally:
        env.close()


if __name__ == "__main__":
    main()
