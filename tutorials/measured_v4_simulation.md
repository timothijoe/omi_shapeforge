# V4与18.8 × 8.8 mm插槽仿真

本轮通过的独立仿真候选是 **SIM-OM001-OS001-r06**，源模块为V4-r05「双窗尾槽版」。插槽净开口18.8 × 8.8 mm；正对孔口的窄边距离按6.9 mm建模，测量外缘／方向口径仍待进一步确认。完整结果和边界见[能力记录](../docs/agent/simulation/evolution/measured-v4-simulation.md)。

## 查看结果

- [规则插入与退出视频](/data/omi_runtime/runs/measured_v4_sim_20261121/robot_validation/robot_contact_cycle.mp4)。
- [完整装配Blender](/data/omi_runtime/assets/sim_insertion/r06/SIM-OM001-OS001-r06.blend) · [独立插槽Blender](/data/omi_runtime/assets/optical_socket/measured/r01/OS-001-M1888-r01.blend)。
- [头部图像](/data/omi_runtime/runs/measured_v4_sim_20261121/camera_check/head_rgb.png) · [腕部图像](/data/omi_runtime/runs/measured_v4_sim_20261121/camera_check/wrist_rgb.png)。

## 重跑局部接触与机械臂循环

在工作区根目录运行，输出目录必须不存在：

```bash
cd /home/linux/omi_folder
MUJOCO_GL=egl PYTHONPATH=omi_shapeforge/src \
  /data/omi_runtime/envs/omi_mesh_audit/bin/python \
  -m omi_shapeforge.sim.contact_asset_validate \
  --asset-dir /data/omi_runtime/assets/sim_insertion/r06 \
  --output /data/omi_runtime/runs/my_v4_local_cycle --render

MUJOCO_GL=egl PYTHONPATH=omi_shapeforge/src \
  /data/omi_runtime/envs/omi_sim_train/bin/python \
  -m omi_shapeforge.sim.contact_robot_validate \
  --scene /data/omi_runtime/runs/measured_v4_sim_20261121/robot_scene \
  --output /data/omi_runtime/runs/my_v4_robot_cycle
```

局部可另建输出目录，加`--locked`、`--x-offset-mm 1`或`--yaw-deg 2`复查反例；预期不能到位。`--timestep .0001`用于减半步长复核。报告里的最小静态余量是由资产几何距离计算的保守界。

## 继续派生新的资产

模块碰撞分解缓存及准备脚本位于`/data/omi_runtime/runs/measured_v4_sim_20261121/module_collision/`和`prepare_module.py`；缓存与源OBJ哈希绑定。若改模块几何，要在新目录重新生成分解，不能沿用旧缓存。

```bash
PYTHONPATH=omi_shapeforge/src /data/omi_runtime/envs/omi_mesh_audit/bin/python \
  -m omi_shapeforge.sim.measured_contact_asset \
  --parent-asset /data/omi_runtime/assets/sim_insertion/r03 \
  --module-asset /data/omi_runtime/assets/optical_module_v4/r05 \
  --decomposition /data/omi_runtime/runs/measured_v4_sim_20261121/module_collision \
  --front-left-margin-mm 6.9 \
  --asset-id SIM-OM001-OS001-r07 \
  --output /data/omi_runtime/assets/sim_insertion/r07
```

该示例创建后续r07，不覆盖已验证的r06。需要Blender封装和机器人场景时分别使用`author_contact_asset.py`与`contact_robot_scene`，源机器人参考场景为`/data/omi_runtime/runs/dual_camera_scene_20261121_final`。新候选必须重跑验证，不能沿用r06的通过结论。

## 新几何下重新训练

旧BC／RL直接迁移各0/2，尚未重训。新任务需使用新的root及新场景，旧replay合同与新场景哈希不同：

```bash
MUJOCO_GL=egl PYTHONPATH=omi_proj/src:omi_shapeforge/src \
  /data/omi_runtime/envs/omi_sim_train/bin/python \
  -m omi_hil_rl.training.contact_intervention_study init \
  --root /data/omi_runtime/runs/my_v4_contact_study \
  --scene /data/omi_runtime/runs/measured_v4_sim_20261121/robot_scene \
  --pretrained omi_proj/local/pretrained/serl_resnet10/backbone.pt
```

后续按[10BC＋20接管RL教程](../../omi_proj/tutorials/contact_intervention_study.md)对这个新root采集与训练。该命令是后续操作入口，本轮没有执行新几何训练；内部支撑使有效竖向余量很小，需检查新数据和闭环结果，不能承诺固定回合数必成功。
