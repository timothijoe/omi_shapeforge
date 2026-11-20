# MuJoCo 离屏运行

前提：独立 simulation 环境准备好，场景及相邻 `meshes/` 完整。推荐通过统一运行层调用：

```bash
.venv/bin/omi-shapeforge simulate mujoco --steps 240
.venv/bin/omi-shapeforge simulate mujoco \
  --scene /data/omi_runtime/assets/optical_scene_v2_20261120/scene.xml --steps 240
```

第一条使用配置中的 2×2 场景，第二条选择单模块。可用 `--output` 指定尚不存在的目录；运行层保存 v1 清单和日志，图像、轨迹、原报告及独立检查结果位于 `backend/`。检查器从保存的末态重新计算碰撞体底部高度、落差和接触，并记录到 `backend/inspection.json`。仅适用于本项目生成的自由刚体光模块原型。

以下直接 Python 入口仍可用于调试；它保持旧输出布局，不自动生成 v1 外层记录：

```bash
RUNTIME_ROOT=/data/omi_runtime
SIMPY="$RUNTIME_ROOT/envs/simulation/bin/python"
SCENE_DIR="$RUNTIME_ROOT/assets/optical_scene_v2_20261120"
RUN_DIR="$RUNTIME_ROOT/runs/mujoco_$(date +%Y%m%d_%H%M%S)"
"$SIMPY" scripts/simulation/run_mujoco.py --help
MUJOCO_GL=egl "$SIMPY" scripts/simulation/run_mujoco.py \
  --scene "$SCENE_DIR/scene.xml" --output "$RUN_DIR" --steps 240
```

预期执行 2 秒仿真，保存 `initial.png`、`settled.png`、`trajectory.npz`、`samples.json`、`report.json`。报告状态为 `passed_mujoco_load_step_render_and_settle`。程序会检查状态有限、物体下落、最终接触和稳定，不只是尝试打开文件。

若要运行已生成方阵，把 SCENE_DIR 换成该目录；本机已验证例子是 `assets/optical_array_2x2_20261120`。用[场景教程](scene_generation.md)可生成新的场景。

已有 RUN_DIR 拒绝。无图像或失败时读取终端／重定向日志，不把空目录当作成功。可 Ctrl+C 停止，下一次换新目录。EGL 需要本机图形库支持，详情见[排错](troubleshooting.md)。

当前测试不含机器人、真实夹爪或精细槽接触，也不认证质量、摩擦或跨引擎精度。
