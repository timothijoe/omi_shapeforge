# 生成单模块或方阵场景

前提：按[Blender 教程](blender_assets.md)得到 `asset.json` 与 OBJ；独立 simulation 环境包含 NumPy 和 OpenUSD。

下面使用本机已验证的导出资产，在新的目录中生成 2×2 场景：

```bash
RUNTIME_ROOT=/data/omi_runtime
SIMPY="$RUNTIME_ROOT/envs/simulation/bin/python"
ASSET_DIR="$RUNTIME_ROOT/assets/optical_module_sim_20261120"
SCENE_DIR="$RUNTIME_ROOT/assets/scene_$(date +%Y%m%d_%H%M%S)"
"$SIMPY" scripts/simulation/build_scenes.py --asset "$ASSET_DIR" \
  --output "$SCENE_DIR" --rows 2 --columns 2
```

预期输出 `scene.xml`、`scene.usda`、`scene_manifest.json` 和复制后的 `meshes/`。用 `--rows 1 --columns 1` 生成单模块；两参数均为正整数，总数不超过 16。

场景以米为单位，台面 Z=0。布局是合成位置，轨道是示意支撑，不按真实夹具或点云位姿复原。质量、摩擦和碰撞体是[当前简化模型](../docs/agent/simulation/evolution/engine-scenes.md)。

生成器只写文件，不证明引擎加载成功。继续使用[MuJoCo](mujoco_scene.md)或[Isaac](isaac_scene.md)教程运行。目录已有时拒绝，换新 SCENE_DIR；中断后保留原输入和失败输出。
