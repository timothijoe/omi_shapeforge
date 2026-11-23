# 双相机仿真训练与续训

需要示范时使用新增[规则老师教程](rule_demonstrations.md)：实际机械臂执行规则动作、生成独立 scripted 数据，先 BC 再与在线经验混合训练。下文保留原无示范入口。

已接通：真实双臂 URDF＋V3／r04 → 两路 MuJoCo RGB → 十帧观测 → OMI 视觉 Actor → 仿真动作 → 单帧存储／经验池 → SAC 更新 → 新 Actor。当前任务为无接触预插入，state／tactile 补零。完整语义见[能力说明](../docs/agent/simulation/evolution/visual-training.md)。

## 当前可用环境和产物

- Python：`/data/omi_runtime/envs/omi_sim_train/bin/python`，独立于既有环境。
- 场景：`/data/omi_runtime/runs/dual_camera_scene_20261121_final/`。
- 已验证训练：`/data/omi_runtime/runs/dual_camera_training_20261121_final/`。
- 双相机画面：训练目录 `cameras_000000.png`；每个 `episodes/episode_*/cameras.gif` 为实际采集画面。
- `report_000000.json` 是首次训练，`report_000002.json` 是续训；`latest_report.json` 指向最新内容。
- `learner.pt` 包含网络／优化器／更新计数；`actor.pt` 为发布策略；`replay/` 为独立仿真经验池；`episodes/` 和 `frames/` 保留完整采集。

## 新建一次短训练

从工作区根目录执行，`--run` 必须尚不存在：

```bash
cd /home/linux/omi_folder
omi_proj/scripts/train_shapeforge_sim.sh \
  --scene-dir /data/omi_runtime/runs/dual_camera_scene_20261121_final \
  --run /data/omi_runtime/runs/my_visual_sim_run \
  --pretrained omi_proj/local/pretrained/serl_resnet10/backbone.pt \
  --episodes 2 --max-steps 100 --updates-per-episode 8 \
  --capacity 512 --batch-size 8 --device cuda
```

`--episodes` 是本次新增采集回合数；`--updates-per-episode` 是每个完整回合后的 Critic 更新数，现有 SAC 每两次 Critic 更新一次 Actor。初始权重是新策略，首次没有成功很正常；此短命令用于链路验证。`--capacity` 为磁盘环形池容量，必须能容纳一个完整回合。磁盘 replay 保存展开历史，容量 512 的数组约 1.2 GB；完整采集帧另存。

启动脚本通过两个源码目录的 `PYTHONPATH` 连接仓库，不要求合并 Git 仓库。默认 EGL 和独立解释器，可通过 `MUJOCO_GL`、`OMI_SIM_PYTHON`、`OMI_SHAPEFORGE_REPO` 覆盖。

## 续训

```bash
cd /home/linux/omi_folder
omi_proj/scripts/train_shapeforge_sim.sh \
  --scene-dir /data/omi_runtime/runs/dual_camera_scene_20261121_final \
  --run /data/omi_runtime/runs/my_visual_sim_run --resume \
  --episodes 1 --max-steps 100 --updates-per-episode 4 \
  --capacity 512 --batch-size 8 --device cuda
```

这是新的仿真专用 CLI，显式支持 `--resume`；旧真机 `run_async_rl.sh` 的自动恢复规则不变。续训要求相同场景／依赖哈希、回合上限和 replay 容量；完整恢复 learner 和磁盘池后重新发布 Actor。新增回合使用新编号，旧报告保留；不承诺恢复前后随机轨迹逐位一致。

Ctrl+C 会正常停止：完整回合保留入池，未完成回合保存并标为 discarded。正常 learner 退出会发布 checkpoint。硬中断后的脏 replay 仍遵循已有拒绝恢复规则。

## 从已有 URDF 场景重新装配

```bash
cd /home/linux/omi_folder
PYTHONPATH=omi_shapeforge/src \
  /data/omi_runtime/envs/omi_sim_train/bin/python \
  -m omi_shapeforge.sim.vision_scene \
  --source /data/omi_runtime/runs/robot_urdf_mvp_20261120T090059Z/scene \
  --output /data/omi_runtime/runs/my_dual_camera_scene
```

输出必须是新目录；若尚无源场景，先按[真实 URDF 教程](robot_sim_mvp.md)生成。派生场景引用现有网格并登记全部 175 个依赖的哈希，迁移时须保留这些网格路径或重新装配，不能只复制 `scene.xml`。

## 重建环境和验证

本机显卡驱动已验证 Torch 2.6.0+cu124，因此使用独立 `sim-train` 依赖组。它固定 SB3 2.7.1；项目原 `train` 组的 SB3 2.9 要求 Torch ≥2.8，不要把两组一起安装到旧环境。

```bash
uv venv --python 3.12 /data/omi_runtime/envs/omi_sim_train_new
uv pip install --python /data/omi_runtime/envs/omi_sim_train_new/bin/python \
  torch==2.6.0 --index-url https://download.pytorch.org/whl/cu124
uv pip install --python /data/omi_runtime/envs/omi_sim_train_new/bin/python \
  -r /home/linux/omi_folder/omi_proj/requirements/sim-train-cu124.txt
```

行为验证：

```bash
cd /home/linux/omi_folder
MUJOCO_GL=egl \
OMI_VISION_SCENE=/data/omi_runtime/runs/dual_camera_scene_20261121_final \
PYTHONPATH=omi_proj/src:omi_shapeforge/src \
  /data/omi_runtime/envs/omi_sim_train/bin/python -m pytest \
  omi_shapeforge/tests/test_vision_env.py \
  omi_shapeforge/tests/test_insertion_env.py \
  omi_proj/tests/test_shapeforge_training.py -q
```

验收应查看实际 learner 更新数、两个视觉分支参数变化、下一回合 policy_version、两路相机可见像素、图像消融结果和 checkpoint 重载一致性；不能只看命令退出码。独立评估成功率需后续更多训练和多种子验证。
