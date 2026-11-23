# 机械臂 URDF 仿真原型

目前主线使用完整机械臂 URDF。它已包含双臂与夹爪，提供一个无接触的小幅 TCP 到达任务；**尚非机器人插入任务**。完整架构、里程碑和难度见[开发计划](../docs/design/robot-rl-development-plan.md)。

已生成场景：`/data/omi_runtime/runs/robot_urdf_mvp_20261120T090059Z/scene/scene.xml`。

打开 MuJoCo 原生交互窗口（只查看，不运行策略或物理步进）：

```bash
cd /home/linux/omi_folder/omi_shapeforge
MUJOCO_GL=glfw PYTHONPATH=src /data/omi_runtime/envs/omi_assets/bin/python \
  -m omi_shapeforge.sim.robot_viewer \
  --scene-dir /data/omi_runtime/runs/robot_urdf_mvp_20261120T090059Z/scene
```

拖动旋转、滚轮缩放；关闭窗口退出。下面的命令则执行脚本到达检查。

```bash
cd /home/linux/omi_folder/omi_shapeforge
PYTHONPATH=src /data/omi_runtime/envs/omi_assets/bin/python - <<'PY'
from omi_shapeforge.sim.factory import make_env

env = make_env("robot_reach", scene_dir="/data/omi_runtime/runs/robot_urdf_mvp_20261120T090059Z/scene")
try:
    observation, info = env.reset(seed=7)
    for step in range(env.max_steps):
        observation, reward, terminated, truncated, info = env.step(env.scripted_action())
        if terminated or truncated:
            print(info)
            break
finally:
    env.close()
PY
```

这段脚本控制只验证 IK／伺服／环境接口，不是 RL 训练。主动臂为 URDF L，TCP 沿用原 URDF 坐标架；夹爪的实际抓取中心仍待标定。机器人接触关闭，光模块与插接座是静态参考，不能以该任务成功声称已经插入。

重建时指定全新输出目录：

```bash
PYTHONPATH=src /data/omi_runtime/envs/omi_assets/bin/python -m omi_shapeforge.sim.robot_scene \
  --urdf /home/linux/omi_folder/omi_proj/local/vendor/optical_module_pu/source/OpticalModule_PU/omi_ws/src/marvin_stand_viz/urdf/marvin_stand.urdf \
  --optical-inputs /data/omi_runtime/runs/v3_socket_r04_20261120T082303Z/inputs \
  --output /data/omi_runtime/runs/robot_scene_new
```

纯接口夹具仍可独立运行，输出也必须是新目录：

```bash
MUJOCO_GL=egl PYTHONPATH=src /data/omi_runtime/envs/omi_assets/bin/python \
  -m omi_shapeforge.sim.smoke --output /data/omi_runtime/runs/insertion_proxy_new --render
```

它不含机器人，仅用于简化几何及 Gym 接口回归。`make_env("robot_insertion")` 目前明确报未实现，避免误把夹具实验当成机械臂任务。
