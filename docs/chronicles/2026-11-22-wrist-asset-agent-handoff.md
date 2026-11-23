# 2026-11-22：当前资产文档与Agent复用交接

按用户要求更新当前视觉进度并新增跨Agent接入说明、独立复现教程和固定版本清单。组合为WG-r10＋OM-r08，原版本及感知／Isaac等既有工作保留。本轮只整理与核验，不改mesh或接入机器人。

实际校验两份资产包及675个静态场景依赖；复制渲染脚本／配置到新目录完成鱼眼重渲染，原6个结果文件哈希保持。新图1080×1920×3，平均通道差约3.22e−7，未要求跨GPU逐字节一致。验证了OpenCV相机矩阵与已保存渲染报告一致。

特别记录旧`wrist_tool_scene.py`不支持camera/camera_mount组件、材料RGBA读取、静态−2 mm初态、17件模块源索引映射及鱼眼／针孔区别。提供其他Agent可直接复制的接续任务说明；没有派生或发送任务给其他Agent。

[接入说明](../agent/simulation/evolution/wrist-assets-handoff.md) · [教程](../../tutorials/reuse_wrist_visual_assets.md) · [固定版本清单](../../manifests/wrist_visual_asset_handoff_20261122.json) · [本轮验证](/data/omi_runtime/runs/wrist_asset_handoff_check_20261122_181528/verification.json)。
