# 在Isaac中复用WG-r10＋OM-r08

先阅读[固定资产交接](../docs/agent/simulation/evolution/wrist-assets-handoff.md)和[本轮接入记录](../docs/agent/simulation/evolution/wrist-bundle-isaac.md)。来源清单不变，原模型保留。

## 已生成场景

```bash
cd /home/linux/omi_folder/omi_shapeforge
env -u CONDA_PREFIX -u CONDA_DEFAULT_ENV -u PYTHONHOME -u PYTHONPATH -u LD_LIBRARY_PATH \
  /data/isaac-sim-5.1.0/python.sh -u scripts/simulation/view_isaac_asset.py \
  --scene /data/omi_runtime/runs/wg_r10_om_r08_isaac_20261122/isaac_preview/WG-r10_OM-r08_robot.usdc
```

默认时间线暂停，视口选择Overview。可以在相机菜单查看头部/腕部针孔检查视角；最终鱼眼图为同目录`closed_wrist_fisheye_1920.png`，不能把90° fovy检查视角等同于鱼眼。GUI启动脚本不保存回源文件。

## 从副本重建

按[复用教程](reuse_wrist_visual_assets.md)逐文件验证固定清单，并复制工具/模块目录到自己的`inputs/tool`、`inputs/module`。保留复制清单原字节，加载时映射网格到副本；不要覆盖发布目录。

```bash
PYTHONPATH=src /data/omi_runtime/envs/omi_mesh_audit/bin/python \
  scripts/simulation/integrate_wrist_visual_bundle.py \
  --source /data/omi_runtime/runs/measured_v4_sim_20261121/robot_scene \
  --inputs /data/omi_runtime/runs/wg_r10_om_r08_isaac_20261122/inputs \
  --output /data/omi_runtime/runs/wrist_integration_NEW

PYTHONPATH=src /data/omi_runtime/envs/omi_mesh_audit/bin/python \
  scripts/simulation/audit_wrist_bundle_mount.py \
  --integration /data/omi_runtime/runs/wrist_integration_NEW

/data/omi_runtime/envs/omi_sim_train/bin/python scripts/simulation/export_isaac_contact.py \
  --source /data/omi_runtime/runs/wrist_integration_NEW/robot_scene/scene.xml \
  --manifest /data/omi_runtime/runs/wrist_integration_NEW/robot_scene/robot_manifest.json \
  --output /data/omi_runtime/runs/wrist_transfer_NEW

timeout --signal=TERM --kill-after=10s 600s \
  env -u CONDA_PREFIX -u CONDA_DEFAULT_ENV -u PYTHONHOME -u PYTHONPATH -u LD_LIBRARY_PATH \
  /data/isaac-sim-5.1.0/python.sh -u scripts/simulation/preview_wrist_bundle_isaac.py \
  --transfer /data/omi_runtime/runs/wrist_transfer_NEW \
  --mount-audit /data/omi_runtime/runs/wrist_integration_NEW/mount_audit.json \
  --output /data/omi_runtime/runs/wrist_isaac_preview_NEW
```

`NEW`必须为未存在目录。工具和模块在米制公共坐标中导入，夹指相对位移只应用一次。新模块按source_part_index映射；49件工具的camera/camera_mount必须随TCP，不能随夹指。

预览输出完整USD、闭合/打开/再次闭合的1920×1080鱼眼图、针孔截图和开合MP4。视频按5 fps展示21个观察状态，约4.2秒；这不是完整插入轨迹。原模块固定附着，工具碰撞关闭，真实抓取与新训练未验证。
