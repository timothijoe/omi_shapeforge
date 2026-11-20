# 原生桌面 mesh 查看器

本页是 **V2／V1 辅助对比**入口。主要建模和编辑改用[Blender V3](blender_assets.md)。

旧电脑使用 Open3D 原生 GUI。恢复的 `runtime/active_prior_fit_viewer.json` 指向 `assets/optical_module_v2`，原界面为“已认可 V2，可切换 V1”。本机已使用恢复脚本启动，并通过实际桌面截图确认窗口和网格显示，见[验证记录](../manifests/native_viewer_validation_20261120.json)。

在已登录的图形桌面终端运行：

```bash
OLD_PROJECT=/data/omi_runtime/baselines/reconstruction_20261119/workspace/BundleSDF_trial
/data/omi_runtime/envs/foundation_stereo/bin/python \
  "$OLD_PROJECT/scripts/view_prior_data_refinement.py" \
  --fit "$OLD_PROJECT/assets/optical_module_v2" \
  --title 'OMI ShapeForge | 原生 Mesh 查看器 | 历史 V2 / V1'
```

该命令需要现有 foundation_stereo 环境中的 Open3D、NumPy 和 trimesh，以及可用的本地桌面显示。它读取原网格、点云与报告，不重新运行重建，不保存模型修改。

- 左键拖动旋转，滚轮缩放，Ctrl＋左键平移。
- 左侧下拉框切换历史 V2、V1、结构先验与数据支持区域等已有对照。
- “叠加新位姿下的原始观测点”显示恢复的点云。
- “整体”和“插接端放大”切换观察范围。

该辅助查看器默认打开历史 V2 数据细化模型。它与[资产版本目录](../docs/asset-versions.md)中的当前 V3（旧别名 `GROOVE-r01`） 是不同来源，不能因为原界面写“当前版本”就覆盖项目现有版本定义。“已认可”沿用旧界面的历史命名，不表示已通过实物尺寸认证。

四份 Blender 文件也可直接用本机 Blender 打开，源文件入口见[资产与可视化目录](../docs/visual-results.md)。本次已验收的是上述 Open3D 原生窗口。
