"""Explicit task selection; never substitute a proxy for a requested robot task."""


def make_env(task, *, scene_dir=None, render_mode=None, config=None):
    if task == "robot_contact_insertion":
        if scene_dir is None or config is not None:
            raise ValueError("robot_contact_insertion requires its independently built scene")
        from .contact_env import ContactInsertionEnv
        return ContactInsertionEnv(scene_dir,render_mode=render_mode)
    if task == "robot_preinsert_vision":
        if scene_dir is None or config is not None:
            raise ValueError("robot_preinsert_vision requires scene_dir and no proxy config")
        from .vision_env import DualCameraPreinsertEnv
        return DualCameraPreinsertEnv(scene_dir, render_mode=render_mode)
    if task == "robot_reach":
        if scene_dir is None:
            raise ValueError("robot_reach requires an imported URDF scene directory")
        if config is not None:
            raise ValueError("proxy config is not a robot task configuration")
        from .robot_env import RobotReachEnv
        return RobotReachEnv(scene_dir, render_mode=render_mode)
    if task == "insertion_proxy":
        if scene_dir is not None:
            raise ValueError("insertion_proxy uses its explicit primitive fixture, not a robot scene")
        from .insertion_env import SimpleInsertionEnv
        return SimpleInsertionEnv(config, render_mode=render_mode)
    if task == "robot_insertion":
        raise NotImplementedError("Robot insertion awaits tool/grasp calibration and contact validation")
    raise ValueError(f"unknown task: {task}")
