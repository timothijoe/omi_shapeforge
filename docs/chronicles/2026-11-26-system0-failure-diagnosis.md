# 2026-11-26 System0失败原因与规则对照

用户追问为何System0仍无法插入，以及规则干预本身能否完成任务。针对先前220000～220004五个目标，保持相同资产、GT参考、XY±3mm范围、5子步、900步预算和腕力合同，追加纯规则与BC-only对照。

纯规则5/5成功；按原数据、初始化seed200000和1000次更新重建的BC-only 0/5；原BC＋RL保持0/5。重建BC的10个已记录loss值与原阶段逐值一致，但原BC检查点当时未单独保存，因此明确标记为重建对照。规则349～371步完成；BC四例入口资格失败、一例近落座超时；RL五例最终IK拒绝。BC和RL评估无teacher请求。该批目标已用于诊断，不称新增盲测。

第一目标中，老师先停止轴向推进纠正横向误差，BC却第一步就输出约0.464前进动作并迅速升高，说明对准／推进切换没有学稳。在相同验证示范上，RL动作MSE约为BC的4.89倍，旋转动作误差增加。原训练23个硬失败均发生在策略控制的一步，现有按状态触发的接管不能救回已终止的步骤。数据覆盖、阶段不平衡、RL更新和探索等具体因果仍需消融，不能宣称已锁定唯一原因。

新增BC-only保存和纯规则评估入口，补齐之前直接从BC进入SAC而缺少独立闭环验收的流程。所有新结果写入 `/data/shapeforge/runtime/runs/hier_s0_diagnosis_20261126/`，没有改动原数据或RL模型。

[能力与结论](../agent/simulation/evolution/hierarchical-intervention.md) · [汇总](/data/shapeforge/runtime/runs/hier_s0_diagnosis_20261126/summary.json) · [登记](../../manifests/system0_failure_diagnosis_20261126.json)
