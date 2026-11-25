# 查看腕部相机、夹爪与光模块

> 本机迁移提示（2026-11-24）：运行资源实体已迁至 `/data/shapeforge/runtime`；本文中的 `/data/omi_runtime` 是保留的兼容入口，指向同一份内容。目录映射与恢复要求见[当前资源契约](../docs/agent/interfaces/local-resources.md)。

当前视觉组合为 **WG-r10工具＋OM-001/V4 r08光模块**。其他Agent复用请先读[接入说明](../docs/agent/simulation/evolution/wrist-assets-handoff.md)与[固定版本清单](../manifests/wrist_visual_asset_handoff_20261122.json)；校验、坐标与新目录重渲染按[复用教程](reuse_wrist_visual_assets.md)。

## 当前组合窗口

```bash
MUJOCO_GL=glfw /data/omi_runtime/envs/omi_mesh_audit/bin/python /data/omi_runtime/runs/wrist_primary_refinement_20261122/view_primary_scene.py
```

默认自由视角、隐藏侧栏，可旋转／平移／缩放。1恢复自由视角，2为针孔检查视角。此窗口不进行物理步进，固定参考装配也不代表已经实现真实夹持。

鱼眼图像对照：

```bash
/data/omi_runtime/envs/omi_mesh_audit/bin/python /data/omi_runtime/runs/wrist_primary_refinement_20261122/view_comparison.py
```

[组合对比图](/data/omi_runtime/runs/wrist_primary_refinement_20261122/primary_refinement_comparison.png) · [工具Blender](/data/omi_runtime/assets/daimon/wrist_gripper_observation_r10/WG-DAIMON-OBS-r10.blend) · [模块Blender](/data/omi_runtime/assets/optical_module_v4/r08/OM-001-V4-r08.blend)。完整工具GLB不含模块；工具Blender另有17件参考模块。两份资产的独立GLB都保留公共装配坐标，不自动居中。

## 历史点云与r08/r09对照

```bash
/data/omi_runtime/envs/foundation_stereo/bin/python /data/omi_runtime/runs/wrist_pointcloud_refinement_20261122/view_cloud_overlay.py
```

1只看点云，2叠加冻结r08，3叠加r09。这是此前点云修订的对照，尚未将r10加入该查看器。点云使用近似指尖锚定坐标，叠加不等于真机标定。

历史r09工具开合窗口仍可单独查看：

```bash
MUJOCO_GL=glfw /data/omi_runtime/envs/omi_mesh_audit/bin/python /data/omi_runtime/runs/wrist_pointcloud_refinement_20261122/view_cloud_tool.py
```

该窗口O张开、C闭合；1自由、2针孔、3固定俯视。其每指0～12 mm为展示量，质量／惯量是占位值，视觉网格关闭碰撞。

## 重新生成结果

使用[独立输出目录的复现步骤](reuse_wrist_visual_assets.md)，不要把已交付运行目录作为新实验输出。构建或挂载代码的更改应在新版本中完成，并重新检查来源、坐标、相机绑定及所需物理条件。
