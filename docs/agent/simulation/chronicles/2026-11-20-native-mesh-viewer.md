# 2026-11-20：恢复原机 Open3D 原生查看器

根据恢复的启动记录确认原机使用 Open3D GUI，默认加载历史 optical_module_v2 并提供 V1 等对照。使用本机 foundation_stereo 环境及显式 --fit 路径，直接运行恢复的 view_prior_data_refinement.py，未修改旧脚本或模型。

日志出现 READY，进程存活；桌面窗口处于前台，实际截图确认 V2 网格可见。原界面保留模型选择、观测点云叠加与插接端放大入口。未将历史 V2 重新定义为当前 GROOVE-r01，也没有新增物理精度结论。

证据见[原生查看器验证](../../../../manifests/native_viewer_validation_20261120.json)。
