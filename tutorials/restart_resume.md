# 重启后恢复工作

先读 [HANDOFF](../HANDOFF.md) 和[重启前完整快照](../docs/chronicles/2026-11-20-restart-handoff.md)。本教程面向同一机器重启，不需要重新解压数据或重建环境。

## 1. 最小检查

```bash
cd /home/linux/omi_folder/omi_shapeforge
git status --short --branch
.venv/bin/omi-shapeforge --help
.venv/bin/omi-shapeforge doctor
```

预期代码位于本地 dev，doctor 路径检查就绪；以实际工作树为准保留用户改动。doctor 不运行 GPU 或仿真。没有必要仅为恢复桌面就重跑所有实验。

## 2. 恢复 Blender V3

本轮检测到未保存标记，已把当前会话保存为独立副本。需要恢复当时场景／视图时：

```bash
blender --disable-autoexec \
  /data/omi_runtime/baselines/restart_handoff_20261120T043105Z/V3-live-session.blend
```

该副本成功重开，保存时可见几何与磁盘工作副本一致。此命令打开备份；后续编辑后请另存到工作目录或新修订，保留原备份。若用户在快照保存后又操作过，应优先采用用户后来保存的版本。

正常的 V3 主工作文件入口：

```bash
blender --disable-autoexec \
  /data/omi_runtime/assets/optical_module_v3/work/OM-001-V3.blend
```

若 shell 找不到 blender，用完整路径 `/data/omi_runtime/tools/blender-4.5.16-linux-x64/blender` 替代。冻结 r01 位于 `assets/optical_module_v3/releases/r01/`；工作副本与会话副本不应未经比较互相覆盖。

## 3. 打开 V2 辅助参考

在已登录的本机桌面终端运行：

```bash
OLD_PROJECT=/data/omi_runtime/baselines/reconstruction_20261119/workspace/BundleSDF_trial
/data/omi_runtime/envs/foundation_stereo/bin/python \
  "$OLD_PROJECT/scripts/view_prior_data_refinement.py" \
  --fit "$OLD_PROJECT/assets/optical_module_v2" \
  --title 'OMI ShapeForge | V2 辅助参考与对比'
```

Open3D 原生窗口的左键旋转、滚轮缩放、Ctrl＋左键平移与模型选择沿用旧界面。它只读旧结果，主编辑仍使用 Blender V3。关闭窗口即可退出；旧 PID 不用于再次启动。

## 4. 网页对照和历史结果

```bash
xdg-open /data/omi_runtime/runs/optical_asset_versions_20261120/preview.html
```

如果浏览器未出现在前台，可用新窗口：

```bash
google-chrome --new-window \
  file:///data/omi_runtime/runs/optical_asset_versions_20261120/preview.html
```

网页默认 V3、V2 辅助；左键旋转、Shift＋左键平移、滚轮缩放。支持无 WebGL 时自动 CPU 网格渲染。当前网页已经包含该修复，不能用早期只支持 WebGL 的旧备份覆盖它。本轮持久备份中的 `comparison-desktop.html` 是当前版本副本。

历史原图、交互页面、模型文件及 78 个分组图册见[可视化目录](../docs/visual-results.md)。

## 5. 继续开发或按需验证

正常恢复时不自动启动下面的计算；需要验证变更时选择相关项，输出使用新目录：

```bash
.venv/bin/python -m unittest discover -s tests -v
python3 scripts/validation/check_contracts.py
.venv/bin/omi-shapeforge smoke stereo
.venv/bin/omi-shapeforge smoke bundlesdf
.venv/bin/omi-shapeforge simulate mujoco --steps 240
```

合同检查脚本依赖开发检查环境中的 jsonschema；本机 `python3` 已有，主 .venv 仍为标准库控制层。实际 smoke／仿真调用均产生新运行目录，旧结果不覆盖。MuJoCo 默认 2×2 简化场景，尚未接入机器人或精细槽接触。

下一工程任务为 ENG-004 自动检查，资产方向为 Blender V3 迭代，V2 提供参考和对照。没有确定的新几何需求时，先从[统一开发方案](../docs/design/unified-development.md)接续，不自行更改模型外形或启动真机脚本。
