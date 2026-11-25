# Blender 打开、检查与导出

> 本机迁移提示（2026-11-24）：运行资源实体已迁至 `/data/shapeforge/runtime`；本文中的 `/data/omi_runtime` 是保留的兼容入口，指向同一份内容。目录映射与恢复要求见[当前资源契约](../docs/agent/interfaces/local-resources.md)。

当前暂定外观基线为V4-r05「双窗尾槽版」；其文件、版本专用构建／验证脚本和只读查看入口见[Mesh开发记录](../docs/mesh-development.md)。下文保留原V3便携包检查／导出流程，不能直接用于重建V4或覆盖r05；后续几何编辑另建工作副本和修订。

历史V3流程前提：Blender 4.5.16 LTS和portable包已准备。软件位置与SHA256见[资源清单](../manifests/README.md)。Blender仍是主要建模工具，V3保留、V2用于辅助对比；当前暂定基线与历史副本见[资产版本](../docs/asset-versions.md)。

## 打开或检查保存模型

```bash
RUNTIME_ROOT=/data/omi_runtime
PACKAGE="$RUNTIME_ROOT/inputs/optical_packages_20261120_001316/optical_module_portable_20261119"
V3_MODEL="$RUNTIME_ROOT/assets/optical_module_v3/work/OM-001-V3.blend"
blender --version
blender --disable-autoexec "$V3_MODEL"
```

最后一条打开 V3 工作副本。迁移包的 connected_groove.blend 与 releases/r01 中的冻结副本保留为基线；后续编辑在工作副本进行。若只做后台检查，可在新目录保存报告：

```bash
CHECK_DIR=$(mktemp -d "$RUNTIME_ROOT/runs/blender_check_XXXXXX")
blender --background --factory-startup --disable-autoexec --python-exit-code 1 \
  --python "$PACKAGE/tests/check_models_blender.py" -- \
  --package "$PACKAGE" --report "$CHECK_DIR/models.json"
```

预期四个保存模型可读，图像已内嵌、无外部 `.blend` 库依赖。照片初稿是未定标，不能把它的数值直接当作米制尺寸。报告参数可能覆盖同名文件，因此使用新 CHECK_DIR。

## 导出当前米制资产

```bash
ASSET_DIR="$RUNTIME_ROOT/assets/optical_$(date +%Y%m%d_%H%M%S)"
blender --background "$V3_MODEL" --disable-autoexec \
  --python-exit-code 1 --python scripts/simulation/export_blender_asset.py -- \
  --package "$PACKAGE" --output "$ASSET_DIR"
```

预期输出 `asset.json`、`meshes/part_*.obj`，当前资产为 15 个外观部件。导出器仍依赖当前连通槽集合及便携包的刚体几何：若后续修改了 V3 的外形／碰撞边界，必须同步维护导出逻辑和碰撞源，不能直接沿用旧碰撞盒。不要把 Blender 专用脚本直接交给主 venv 的 Python；它依赖 bpy。导出不保存修改到源模型，已有输出目录拒绝。

## 可选重建入口的状态

包中提供 `scripts/rebuild_blender.py --blender 可执行文件 --stage photo|metric|groove --output 新目录`。这些完整重建阶段未在本机复跑，不作为已验收步骤；metric 使用冻结尺寸，不能重新估计 59 帧观测。当前已验证范围见[资产能力](../docs/agent/simulation/evolution/asset-pipeline.md)。

后台渲染或构建可 Ctrl+C 停止，保留日志和新目录；GUI 无法启动时先看[排错](troubleshooting.md)，不要据此覆盖原 `.blend`。
