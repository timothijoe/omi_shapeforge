# 2026-11-26 GT参考下只改变插口位置

用户提出暂用仿真真值System1，只训练System0检验不同target，并明确暂不改变插口本身，只改变位置。本轮执行位置切换演示，保持同一模型、尺寸、材质和朝向，不更换孔型或扩大到完整六维姿态。

使用已有可移动插口接口，在同一初始化种子160000下依次设置原位、世界X±3 mm、世界Y±3 mm。五次实际机器人TCP位置和旋转逐值相同；插口实际USD／PhysX位姿检查、接触垫跟随以及目标同步平移检查通过。原传递包和网格哈希保持，worker退出0。轻量95项29通过／66跳过，插口数值测试3项通过。

输出 `/data/shapeforge/runtime/runs/s0_target_translation_20261126_v1/`：逐位置实际观测、JSON状态、对照图和回执。图已直接在桌面打开。本轮没有System0训练或插接执行；后续以GT参考和位置变化开展训练，当前不构成泛化验证。

[能力页](../agent/simulation/evolution/hierarchical-insertion.md) · [证据](../../manifests/system0_target_translation_20261126.json)
