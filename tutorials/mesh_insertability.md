# 检查真实 mesh 是否可以插入

当前结论为**完整V3／r04刚体插入不通过**，不是训练失败。原始几何、错误凸包和保留孔形的接触测试已分别运行。详见[能力记录](../docs/agent/simulation/evolution/mesh-insertability.md)。

- [结果图](/data/omi_runtime/runs/mesh_insertability_20261121/mesh_insertion_findings.png)
- 运行目录：`/data/omi_runtime/runs/mesh_insertability_20261121/`
- 独立环境：`/data/omi_runtime/envs/omi_mesh_audit/bin/python`
- 清理后的碰撞导出：运行目录 `collision_repaired_inputs/`；不替换原 Blender。

所有新运行使用尚不存在的输出目录。以下命令从工作区根目录执行：

```bash
cd /home/linux/omi_folder
PYTHONPATH=omi_shapeforge/src /data/omi_runtime/envs/omi_mesh_audit/bin/python \
  -m omi_shapeforge.sim.mesh_audit \
  --inputs /data/omi_runtime/runs/mesh_insertability_20261121/inputs \
  --output /data/omi_runtime/runs/my_topology_report.json
```

如需重新生成凸分解缓存（耗时约几十秒，近似程度需重新检查）：

```bash
PYTHONPATH=omi_shapeforge/src /data/omi_runtime/envs/omi_mesh_audit/bin/python \
  -m omi_shapeforge.sim.prepare_collision_parts \
  --inputs /data/omi_runtime/runs/mesh_insertability_20261121/inputs \
  --output /data/omi_runtime/runs/my_collision_parts
```

运行保留孔形、全部入口部件仍刚性的实际接触测试：

```bash
MUJOCO_GL=egl PYTHONPATH=omi_shapeforge/src \
  /data/omi_runtime/envs/omi_mesh_audit/bin/python \
  -m omi_shapeforge.sim.mesh_contact_probe \
  --inputs /data/omi_runtime/runs/mesh_insertability_20261121/inputs \
  --cache /data/omi_runtime/runs/mesh_insertability_20261121/decomposition_normalized \
  --output /data/omi_runtime/runs/my_rigid_insertion_probe \
  --mode split_rigid --render
```

预期卡在约4.21 mm，报告为 `dynamic_report.json`；`--render` 输出图和GIF。其他模式：`raw_hulls` 演示孔被凸包封死；`structural_diagnostic` 排除22个入口组件的碰撞，仅用于定位主体通路；`split_compliant` 为未通过的整体铰链假设。**诊断模式到达51.28 mm不能作为完整插入成功。** `--x-offset-mm 1` 可检查偏心阻挡。

修复网格拓扑的碰撞派生副本：

```bash
PYTHONPATH=omi_shapeforge/src /data/omi_runtime/envs/omi_mesh_audit/bin/python \
  -m omi_shapeforge.sim.repair_collision_export \
  --inputs /data/omi_runtime/runs/mesh_insertability_20261121/inputs \
  --output /data/omi_runtime/runs/my_repaired_collision_inputs
```

上述操作清理退化面和细管端口，保持包围尺寸；不调整孔宽、模块尺度或弹片形状，因此不会自动解除4.21 mm阻挡。

环境依赖和版本保存于运行目录 `environment.txt`，源码快照见验证清单。完整刚体结论同时由 Blender 原三角面相交和独立包含检查支持，不以单一引擎接触报告代替全部几何证据。
