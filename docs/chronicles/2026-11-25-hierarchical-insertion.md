# 2026年11月25日 System1 与 System0 独立开发

用户要求在保留现有功能的前提下开发可独立调试的System1／System0，按GT参考训练下层、加入上层误差、训练上层、组合评估的顺序验证；后续明确暂不使用触觉，先按腕部力传感器设计。

两个仓库创建 `feature/system1-system0-prototype` 分支。学习侧新增独立包，ShapeForge新增实验编排与可选腕力观测；旧网络、训练入口和默认worker观测不变。原有感知路线文档等未提交工作保留，不混入本次功能提交。

先完成原型接口、因果延迟及坐标／动作隔离检查，再跑实际PhysX和RTX采集。初始标量接触代理试采保留为历史中间结果；按用户补充改为六维外部接触wrench后另开目录重新采集。三条新规则示范成功，随后完成独立小型视觉网络训练、System0短预算BC／SAC和重载评估。

本轮是模块实现与训练／评估链路验证，不把规则成功或短预算更新当作学习策略已学会插孔。当前能力、限制和完整结果见[能力记录](../agent/simulation/evolution/hierarchical-insertion.md)与[验证清单](../../manifests/hierarchical_insertion_20261125.json)，操作入口见[教程](../../tutorials/hierarchical_insertion.md)。

续训冒烟发现SB3初次reset仍可能使用旧检查点的种子，修正为显式注册的新种子，并保证后续自动reset递增；原续训目录保留，修订验证另存`resume_v2`。三种System1评估均未成功，原始失败保留。旧默认worker与启用腕力的相同两例720步对照，各项动作／状态／奖励差为0。
