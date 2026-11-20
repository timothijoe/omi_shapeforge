# Blender 打开、检查与导出

前提：Blender 4.5.16 LTS 和 portable 包已准备。软件位置与 SHA256 见[资源清单](../manifests/README.md)。本机已后台重开、渲染和导出；GUI 操作尚未验收。

## 打开或检查保存模型

```bash
RUNTIME_ROOT=/data/omi_runtime
PACKAGE="$RUNTIME_ROOT/inputs/optical_packages_20261120_001316/optical_module_portable_20261119"
blender --version
blender "$PACKAGE/models/connected_groove.blend"
```

第二条启动图形界面。若只做后台检查，可在新目录保存报告：

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
blender --background "$PACKAGE/models/connected_groove.blend" --disable-autoexec \
  --python-exit-code 1 --python scripts/simulation/export_blender_asset.py -- \
  --package "$PACKAGE" --output "$ASSET_DIR"
```

预期输出 `asset.json`、`meshes/part_*.obj`，当前资产为 15 个外观部件。不要把 Blender 专用脚本直接交给主 venv 的 Python；它依赖 bpy。导出不保存修改到源模型，已有输出目录拒绝。

## 可选重建入口的状态

包中提供 `scripts/rebuild_blender.py --blender 可执行文件 --stage photo|metric|groove --output 新目录`。这些完整重建阶段未在本机复跑，不作为已验收步骤；metric 使用冻结尺寸，不能重新估计 59 帧观测。当前已验证范围见[资产能力](../docs/agent/simulation/evolution/asset-pipeline.md)。

后台渲染或构建可 Ctrl+C 停止，保留日志和新目录；GUI 无法启动时先看[排错](troubleshooting.md)，不要据此覆盖原 `.blend`。
