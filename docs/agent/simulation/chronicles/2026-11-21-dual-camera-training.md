# 2026-11-21：双相机仿真接入 OMI 视觉训练

用户要求组合 `omi_shapeforge` 与 `omi_proj`，先用 MuJoCo，保证头部／腕部相机有输入，其他信息可 padding，完成到训练阶段的初步链路。

本次派生新的预插入场景：完整真实 URDF、V3 固定附着于 TCP、r04 和完整支架；两路针孔 RGB 实际渲染，头部固定、腕部随动。检查发现原 URDF TCP 位于法兰附近，最初 40 mm 附着偏移会把模块放进掌体，改为 140 mm 的显式假设后确认可见。调试目录 v1／v2 保留，正式目录为 `dual_camera_scene_20261121_final`，源网格未改。

新仿真观测采用已有十帧 current9stack 张量结构，state／tactile 全零，历史左 padding 有独立有效掩码。真实控制状态只用于 reward／诊断。动作是 MuJoCo 世界系六维 TCP 增量，独立 action contract 与真机隔离。

复用 OMI 的现有 Actor、SAC、learner、spool、单帧共享存储、TransitionReplay 和 checkpoint 发布，按完整回合采集／训练交替。没有接入硬件，旧权重／经验池未写入。

正式验证结果：

- 首次两回合 200 条 transition，16 次 Critic／8 次 Actor 更新；第二回合加载版本 8。
- 新进程 `--resume` 后继续一回合，总计 300 条、20 次 Critic／10 次 Actor 更新；续训回合加载版本 16，最终发布 20。
- 两路图像消融都改变实际策略输出；双路视觉投影、历史 stem 和 Actor 头参数均更新。
- 完整 learner 重载与发布 Actor 确定性动作一致，最大差 0；两次独立评估均超时未成功。
- 仿真／新合同测试 10 项通过；OMI replay／观测存储／HIL runtime／SERL 回归 44 项通过、1 项跳过；ShapeForge 控制环境 14 项通过，7 项可选仿真检查跳过。

产物位于 `/data/omi_runtime/runs/dual_camera_training_20261121_final/`，包含两个 session/report、三个完整 episode、replay 和 checkpoints。精确来源／哈希与证据见[清单](../../../../manifests/dual_camera_training_20261121.json)，长期事实见[能力文档](../evolution/visual-training.md)，命令见[教程](../../../../tutorials/dual_camera_training.md)。

当前仅完成无接触预插入训练链路。固定附着不是接触抓取，工具／相机未标定，弹片、插入力和触觉未实现；20 次更新不是已学会任务的证据。

本轮代码在 ShapeForge `feature/dual-camera-training` 和 OMI `feature/shapeforge-vision-training`，尚未提交／推送。ShapeForge 工作树继承此前未提交资产和感知工作，未执行清理。旧恢复 bundle 不包含本次修改，不能用其覆盖当前工作树。
