# 新接触仿真资产：查看、验证、训练与续训

新增[V4与实测尺寸仿真入口](measured_v4_simulation.md)：SIM-r06使用V4-r05及18.8 × 8.8 mm插槽，机械臂规则循环3/3通过。下文保留旧SIM-r03与旧训练任务的操作，不能用它们复现新尺寸结果。

当前资产是独立的 **SIM-OM001-OS001-r03**，原V3／r04不改。它以7个等效柔顺触点完成接触插入，已通过局部及机械臂规则插入／退出；不代表实物弹片参数或接触抓取已经校准。

## 直接查看

- [新Blender资产](/data/omi_runtime/assets/sim_insertion/r03/SIM-OM001-OS001-r03.blend)
- [机械臂插入＋退出视频](/data/omi_runtime/runs/contact_robot_validation_20261121_final/robot_contact_cycle.mp4)
- [三视图GIF](/data/omi_runtime/runs/contact_robot_validation_20261121_final/robot_contact_cycle.gif)
- [局部接触循环](/data/omi_runtime/runs/sim_asset_final_nominal/cycle.gif)
- [当前进展与剩余问题](../docs/agent/simulation/evolution/contact-simulation-asset.md)

视频由规则老师驱动，头部／腕部图像是真实MuJoCo渲染。全景只供展示，不是额外策略输入。

## 路径与环境

| 内容 | 路径 |
| --- | --- |
| 新资产 | `/data/omi_runtime/assets/sim_insertion/r03/` |
| 机械臂场景 | `/data/omi_runtime/runs/contact_robot_scene_20261121_final/` |
| 规则数据 | `/data/omi_runtime/runs/contact_rule_dataset_20261121_final/` |
| 已验证训练任务 | `/data/omi_runtime/runs/contact_visual_training_20261121_final/` |
| 资产构建环境 | `/data/omi_runtime/envs/omi_mesh_audit/bin/python` |
| 仿真／训练环境 | `/data/omi_runtime/envs/omi_sim_train/bin/python` |

所有新输出必须使用未存在的目录。资产MJCF包含绝对网格路径，迁移时连同依赖恢复或重新构建，不能只拷贝XML。

## 运行局部接触测试

```bash
cd /home/linux/omi_folder
MUJOCO_GL=egl PYTHONPATH=omi_shapeforge/src \
  /data/omi_runtime/envs/omi_mesh_audit/bin/python \
  -m omi_shapeforge.sim.contact_asset_validate \
  --asset-dir /data/omi_runtime/assets/sim_insertion/r03 \
  --output /data/omi_runtime/runs/my_contact_cycle --render
```

预期 `accepted_local_cycle=true`，到位51.28mm、退回−3mm、触点回弹。另用新目录分别添加 `--locked`、`--x-offset-mm 1`、`--yaw-deg 2` 检查阻挡，负例预期不能到位。`--timestep .0001` 用于步长复核。

## 运行机械臂插入与退出验证

```bash
MUJOCO_GL=egl PYTHONPATH=omi_shapeforge/src \
  /data/omi_runtime/envs/omi_sim_train/bin/python \
  -m omi_shapeforge.sim.contact_robot_validate \
  --scene /data/omi_runtime/runs/contact_robot_scene_20261121_final \
  --output /data/omi_runtime/runs/my_robot_contact_check
```

会检查三个初态、逐物理步侵入、双相机连续历史和非主动臂保持，生成报告、逐步轨迹及MP4。环境入口为 `ContactInsertionEnv`，工厂名 `robot_contact_insertion`。原 `robot_reach`／预插入环境保留。

## 使用规则示范启动新训练

```bash
cd /home/linux/omi_folder
omi_proj/scripts/train_shapeforge_sim.sh \
  --scene-dir /data/omi_runtime/runs/contact_robot_scene_20261121_final \
  --run /data/omi_runtime/runs/my_contact_visual_run \
  --pretrained omi_proj/local/pretrained/serl_resnet10/backbone.pt \
  --rule-dataset /data/omi_runtime/runs/contact_rule_dataset_20261121_final \
  --bc-steps 400 --bc-weight 10 --actor-learning-rate .00001 \
  --critic-warmup-updates 8 --episodes 2 --max-steps 350 \
  --updates-per-episode 8 --capacity 1024 --batch-size 16 --device cuda
```

这会实际进行BC和SAC更新，但当前短实验的视觉闭环仍未通过；查看 `rule_bc/report.json`、`rule_bc/closed_loop_test.json` 和 `rule_policy_test_*/closed_loop_test.json`，不要把更新次数当作任务成功率。

继续同一任务：

```bash
omi_proj/scripts/train_shapeforge_sim.sh \
  --scene-dir /data/omi_runtime/runs/contact_robot_scene_20261121_final \
  --run /data/omi_runtime/runs/my_contact_visual_run --resume \
  --episodes 1 --max-steps 350 --updates-per-episode 4 \
  --capacity 1024 --batch-size 16 --device cuda
```

续训恢复原规则数据、混合比例、Actor学习率、优化器和BC参考，不重新BC。完整原始回合在 `episodes/`＋`frames/`，在线replay是容量1024的环形池；累计采集数与当前保留数可能不同。

## 从源资源重建独立资产

```bash
PYTHONPATH=omi_shapeforge/src /data/omi_runtime/envs/omi_mesh_audit/bin/python \
  -m omi_shapeforge.sim.contact_asset \
  --inputs /data/omi_runtime/runs/mesh_insertability_20261121/collision_repaired_inputs \
  --cache /data/omi_runtime/runs/mesh_insertability_20261121/decomposition_normalized \
  --output /data/omi_runtime/assets/sim_insertion/my_new_copy

/data/omi_runtime/tools/blender-4.5.16-linux-x64/blender -b \
  --python omi_shapeforge/scripts/simulation/author_contact_asset.py -- \
  --asset-dir /data/omi_runtime/assets/sim_insertion/my_new_copy

PYTHONPATH=omi_shapeforge/src /data/omi_runtime/envs/omi_sim_train/bin/python \
  -m omi_shapeforge.sim.contact_robot_scene \
  --source /data/omi_runtime/runs/dual_camera_scene_20261121_final \
  --asset /data/omi_runtime/assets/sim_insertion/my_new_copy \
  --output /data/omi_runtime/runs/my_contact_robot_scene
```

当前构建器生成固定r03规范；改变几何／参数时应另立修订身份和新输出，再重跑验收。它不会保存回原Blender或mesh文件。

重新采集规则数据时使用 `collect_shapeforge_rules --scene-dir 新场景 --max-steps 350 --joint-jitter .0005`，其他参数见[规则示范教程](rule_demonstrations.md)。不要套用原预插入任务的180步／0.015rad参数。
