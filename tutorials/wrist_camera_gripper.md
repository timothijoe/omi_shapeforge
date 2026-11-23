# 查看带相机与夹爪外观候选的仿真

当前工具候选 **WG-DAIMON-VIS-r04**，接在SIM-r06实测插槽场景上。视频外形与光学安装位置为估计；工具接触抓取和真实鱼眼未标定。完整实现与范围见[能力记录](../docs/agent/simulation/evolution/wrist-camera-gripper.md)。

## 交互窗口

```bash
cd /home/linux/omi_folder
MUJOCO_GL=glfw PYTHONPATH=omi_shapeforge/src \
  /data/omi_runtime/envs/omi_sim_train/bin/python \
  /data/omi_runtime/runs/wrist_camera_gripper_20261121/live_demo_final.py
```

窗口初始暂停，默认末端近看。左键／右键拖动和滚轮使用MuJoCo原生视角操作。

| 按键 | 功能 |
| --- | --- |
| 空格或P | 播放／暂停规则动作 |
| R | 重置到预插入初态 |
| 1 | 全景 |
| 2 | 腕部相机图像 |
| 3 | 头部相机图像 |
| 4 | 末端近看 |

一次演示连续完成插入和退出后暂停。控制来自规则老师，非已训练视觉策略。模块从初始状态就固定附着于工具，没有拾取／真实夹紧阶段；状态和触觉仍为padding。

## 直接打开资产或看录像

- [工具Blender](/data/omi_runtime/assets/daimon/wrist_gripper_video_r04/WG-DAIMON-VIS-r04.blend)：31件工具加18件仅作参考的光模块。
- [工具GLB](/data/omi_runtime/assets/daimon/wrist_gripper_video_r04/WG-DAIMON-VIS-r04.glb)：只包含工具。
- [最终规则插入退出录像](/data/omi_runtime/runs/wrist_camera_gripper_20261121/corrected_final_cycle/robot_contact_cycle.mp4)。
- [头部图像](/data/omi_runtime/runs/wrist_camera_gripper_20261121/camera_check_corrected/head_rgb.png) · [腕部图像](/data/omi_runtime/runs/wrist_camera_gripper_20261121/camera_check_corrected/wrist_rgb.png)。

## 重跑验证

使用未存在的输出目录：

```bash
MUJOCO_GL=egl PYTHONPATH=omi_shapeforge/src \
  /data/omi_runtime/envs/omi_sim_train/bin/python \
  -m omi_shapeforge.sim.contact_robot_validate \
  --scene /data/omi_runtime/runs/wrist_camera_gripper_20261121/robot_scene_final \
  --output /data/omi_runtime/runs/my_wrist_tool_validation
```

命令默认三个种子；本轮最终场景实际完成的是19／41两例。安装专用检查：

```bash
MUJOCO_GL=egl \
OMI_WRIST_TOOL_SCENE=/data/omi_runtime/runs/wrist_camera_gripper_20261121/robot_scene_final \
PYTHONPATH=omi_shapeforge/src \
  /data/omi_runtime/envs/omi_sim_train/bin/python \
  -m unittest discover -s omi_shapeforge/tests -p test_wrist_tool_scene.py -v
```

模型／构建／清理／IK／间隙检查／查看脚本的快照在`/data/omi_runtime/runs/wrist_camera_gripper_20261121/source_snapshot/`。挂载入口为`omi_shapeforge.sim.wrist_tool_scene`，输出必须是新目录，并需要匹配的工具资产和已收敛的安装IK解。模型和脚本带绝对资源路径，迁移时要恢复全部依赖或重新挂载，不能只复制单个场景XML。
