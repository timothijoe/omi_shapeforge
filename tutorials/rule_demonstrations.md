# 查看仿真与生成规则示范

> 本机迁移提示（2026-11-24）：运行资源实体已迁至 `/data/shapeforge/runtime`；本文中的 `/data/omi_runtime` 是保留的兼容入口，指向同一份内容。目录映射与恢复要求见[当前资源契约](../docs/agent/interfaces/local-resources.md)。

当前老师的任务是**对准并到达孔口前**；模型固定附着、接触关闭。规则和数据边界见[能力说明](../docs/agent/simulation/evolution/rule-demonstrations.md)。

## 看实际画面

- [三视图规则示范视频](/data/omi_runtime/runs/scripted_preinsert_20261121_v1/rule_demo.mp4)
- [GIF 回放](/data/omi_runtime/runs/scripted_preinsert_20261121_v1/rule_demo.gif)
- [初态全景＋双相机](/data/omi_runtime/runs/scripted_preinsert_20261121_v1/preview.png)
- [终态](/data/omi_runtime/runs/scripted_preinsert_20261121_v1/final.png)

左侧为机械臂全景，右侧为真正进入策略的两路 128×128 RGB（展示时放大），底部为控制阶段和 TCP 误差。全景不进入 policy。此回放是规则驱动，不是训练策略自主成功视频。

## 重新采集

从工作区执行，输出必须为新目录；需要前一阶段的 `omi_sim_train` 环境和系统 `ffmpeg`（仅用于预览 MP4）。

```bash
cd /home/linux/omi_folder
MUJOCO_GL=egl PYTHONPATH=omi_proj/src:omi_shapeforge/src \
  /data/omi_runtime/envs/omi_sim_train/bin/python \
  -m omi_hil_rl.training.collect_shapeforge_rules \
  --scene-dir /data/omi_runtime/runs/dual_camera_scene_20261121_final \
  --output /data/omi_runtime/runs/my_rule_demonstrations \
  --training 8 --validation 4 --test 4 \
  --seed 100 --joint-jitter 0.015 --max-steps 180
```

`dataset.json` 保存 split、种子、初始关节偏移和逐文件哈希；`episodes/rule_*/trace.json` 保存老师阶段、请求动作、IK 目标、实际位移与成功判定。`frames/` 采用原有单帧去重存储。只有成功回合被列为可学习示范，失败保留以便检查。

原始样本始终标为 scripted。这个目录不是传统真人 seed run，不能直接套用旧真人 BC／prepare 命令。

## 用示范初始化并训练

以下命令可以直接使用已生成的数据集，训练输出选新目录：

```bash
cd /home/linux/omi_folder
omi_proj/scripts/train_shapeforge_sim.sh \
  --scene-dir /data/omi_runtime/runs/dual_camera_scene_20261121_final \
  --run /data/omi_runtime/runs/my_rule_assisted_run \
  --pretrained omi_proj/local/pretrained/serl_resnet10/backbone.pt \
  --rule-dataset /data/omi_runtime/runs/scripted_preinsert_20261121_v1 \
  --bc-steps 200 --bc-weight 1 --critic-warmup-updates 8 \
  --rule-fraction 0.5 --episodes 2 --max-steps 180 \
  --updates-per-episode 8 --capacity 1024 --batch-size 16 --device cuda
```

示范与训练必须使用相同的场景合同及 max-steps。`rule_bc/` 保存 BC 历史、选中的 Actor、动作拟合评估和独立闭环测试。`training_settings.json` 固定规则数据路径、哈希、混合比例和预热设置；`learner.pt` 包含优化器和 BC 参考，`replay/` 只存在线策略经验。日志中的真人 demonstration=0 是正确状态，规则样本另由 scripted 指标统计。

学习时规则数据**只从 training split 采样**，按照比例与在线经验拼成一批。以 16 条、0.5 比例为例是 8＋8；原始真人训练接口和旧无示范仿真入口保留。

## 继续同一次训练

```bash
cd /home/linux/omi_folder
omi_proj/scripts/train_shapeforge_sim.sh \
  --scene-dir /data/omi_runtime/runs/dual_camera_scene_20261121_final \
  --run /data/omi_runtime/runs/my_rule_assisted_run --resume \
  --episodes 1 --max-steps 180 --updates-per-episode 4 \
  --capacity 1024 --batch-size 16 --device cuda
```

续训读取保存的 rule 设置和数据哈希，不重复 BC。正式验证输出在 `/data/omi_runtime/runs/rule_assisted_train_20261121_final/`。请保留整个示范目录、scene 依赖和训练目录；当前规则老师成功不等于视觉策略已经学会任务。
