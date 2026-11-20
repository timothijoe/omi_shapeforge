# 仿真当前摘要

核对日期：2026-11-20。

当前主线为 **Blender V3**，历史 V2 保留为辅助与对比。V3-r01 从现有连通槽模型登记，几何未变；来源及工作副本见[资产版本](../../asset-versions.md)。

- Blender 同版本安装、四模型后台重开、一张渲染与 15 部件导出已有实际证据，见[资产管线](evolution/asset-pipeline.md)。完整建模阶段重新生成未复验。
- 单模块与 2×2 场景在 MuJoCo 完成加载、2 秒落台和 EGL 图像；ENG-003 已接入统一 CLI 并复验 2×2 末态；Isaac Sim 5.1.0 完成本地 USD 与 PhysX CPU 落台，见[引擎场景](evolution/engine-scenes.md)。Isaac RTX 和 GUI 未验收。
- 机械臂与夹爪资源已由 OMI 包恢复，双臂 MJCF 离线加载／预检和静态渲染通过；两份完整 URDF 的滑动指关节及网格引用已核对。但它们尚未接入光模块场景，见[机器人资产](evolution/robot-assets.md)。

目前只对简化刚体接触做原型验证，质量／摩擦未标定，碰撞盒不保留凹槽。近期应优先核对已到达模型的工具与夹具几何，再设计精细接触验证。

阶段证据见[编年](chronicles/README.md)，长期简化边界见[ADR 001](decisions/001-visual-and-collision.md)。
