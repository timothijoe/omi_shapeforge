# 2026-11-21：当前进展与接续交接

本页按用户要求汇总当前已验证进展、产物、问题和接续入口。数值来自现存报告，本次为文档整理，没有重新训练或修改模型。旧阶段记录保留；旧短试跑的0/2不再代表最新仿真策略结果。

## 用户确认的约定

- 不改现有mesh，仿真修改创建新的独立资产；光模块Blender V3仍为主，V2保留作参考。
- 附加marker贴纸可忽略，不作为模块固有几何或必要位姿特征。
- 先保证模型与接触通路，再接机械臂、头部／腕部相机、示范、RL和评估。
- 规则示范／规则接管明确标记为scripted，不能冒充真人数据；最终策略评估关闭接管。

## 当前完成情况

| 层级 | 已验证进展 | 边界 |
| --- | --- | --- |
| 原mesh检查 | 重新导出、拓扑／相交／包含检查；确认凸包封孔及约4.212mm入口组件阻挡 | 原V3／r04完整刚体仍未通过插入；历史失败不改写 |
| 新仿真资产 | SIM-OM001-OS001-r03；正常插入约51.28mm、退出、回弹、锁死触点和偏心／倾斜对照、步长复核通过 | 等效弹性触点，未标定实物；原mesh保持 |
| 机械臂接触循环 | 完整厂商URDF，3/3规则插入／退出，逐物理步最大侵入<0.004mm | 固定工具附着；真实接触抓取和整机自碰撞未验收 |
| 双相机与数据 | 两路真实MuJoCo RGB、十帧历史、有效掩码、动作／实际运动记录、replay与续训 | state／tactile仍为padding，真实相机／工具标定未完成 |
| 最新BC | 10个训练回合1749条，另留2个验证回合350条；同初始化／3000更新比较普通与旋转加权损失 | 普通BC验证0/2，旋转加权BC验证2/2 |
| 第一轮带接管RL | 20回合、4462条在线经验；5462次Critic更新含1000预热，2231次Actor更新 | 接管训练19/20成功，接管动作2301条，不能算自主成功率 |
| 第二轮组合 | 相同预热状态，有界探索＋更强旋转模仿约束；20回合、4215条在线经验 | 接管训练20/20，但自主测试0/4，未采用 |
| 自主策略评估 | 两批不同初态合计BC 7/8、第一轮RL 8/8，无接管 | 固定仿真、小范围初态、小样本；不能保证任意任务10＋20成功 |

原mesh、接触模型的事实见[可插入性检查](../agent/simulation/evolution/mesh-insertability.md)和[独立接触资产](../agent/simulation/evolution/contact-simulation-asset.md)。训练机制、来源审计和所有对照见[RL试验纪传](../../../omi_proj/docs/agent/training/evolution/contact-intervention-study.md)。

## 独立资产为什么是“一套”

目前一套装配包内有独立的模块body、插接座body和7个弹性触点body，并非单一mesh：模块15个外观件／28个碰撞件，插座113个外观件／335个碰撞件；一份装配Blender共501对象，另有491份OBJ。

模块／插接座尚未分别封装为两个独立资产条目或单独blend。r01／r02是保留的调试版本，当前通过版为r03。该封装问题与“是否存在插入成功案例”是两件事。

## 无接管结果与成功案例

| 方法 | 测试700–703 | 新确认800–803 |
| --- | --- | --- |
| 旋转加权BC基线 | 3/4 | 4/4 |
| 第一轮20回合带接管RL后 | 4/4 | 4/4 |
| 有界探索＋旋转约束RL | 0/4 | 未追加 |
| 等保留数据／Actor步数的额外BC | 0/4 | 未追加 |

BC成功回合平均175步，RL平均228.5步；RL本批多成功1例，但速度和角度误差并非全面优于BC。额外BC是最终保留数据池的回顾性对照，不是同序采样；第二轮同时改变两个因素，不能将收益归因于唯一因素。

- [学习到的RL策略自主插入视频](/data/omi_runtime/runs/contact_intervention_study_20261121/final_comparison/rl_success_video/policy.mp4)
- [BC自主成功视频（验证初态）](/data/omi_runtime/runs/contact_intervention_study_20261121/bc_rotation10/validation_success_video/policy.mp4)
- [规则控制的机械臂插入＋退出](/data/omi_runtime/runs/contact_robot_validation_20261121_final/robot_contact_cycle.mp4)
- [结果对比图](/data/omi_runtime/runs/contact_intervention_study_20261121/final_comparison/comparison.png)
- [完整无接管比较／新初态确认](/data/omi_runtime/runs/contact_intervention_study_20261121/final_comparison/report.json)

## 真实视觉感知的并行现状

后续补记：用户指出右侧候选混入夹爪后，已做模块/夹爪归属过滤，61帧均停用该右侧头部线，当前只采用四组结构。marker 明确不使用，精确位姿/遮挡定位仍未验收；下文五组结构是归属修正前的阶段。感知完整数据、源码、恢复和快照见[新交接](2026-11-21-perception-progress-handoff.md)。

真实腕部影像已转向[模块固有结构线](../agent/perception/chronicles/2026-11-21-markerless-structural-features.md)：61帧提取五组结构线，9项标贴替换不变性检查通过，附加marker不参与位姿对应。遮挡后约束不足时拒绝发布新的六维观测。

这仍是结构特征与位姿候选原型；精确连续六维位姿、遮挡跟踪、真实相对插入深度及到位判断尚未完成。不能把仿真策略成功当作真实视觉定位已通过。最新感知事实继续看[感知current](../agent/perception/current.md)。

## 关键路径与入口

| 内容 | 路径／文档 |
| --- | --- |
| 当前新资产 | `/data/omi_runtime/assets/sim_insertion/r03/`，含 `SIM-OM001-OS001-r03.blend`、MJCF、OBJ和清单 |
| 机械臂接触场景 | `/data/omi_runtime/runs/contact_robot_scene_20261121_final/` |
| 最新策略试验 | `/data/omi_runtime/runs/contact_intervention_study_20261121/` |
| 当前BC／RL权重 | 上述试验的 `bc_rotation10/actor.pt`、`rl/actor.pt`；完整RL恢复用 `rl/learner.pt`、replay、示范和协议 |
| 比较／确认报告 | 上述试验的 `final_comparison/` |
| 本轮源码及文档快照 | 上述试验的 `delivery/`；各阶段另有 `invocations/` |
| 环境 | `/data/omi_runtime/envs/omi_sim_train`；资产检查用 `omi_mesh_audit` |
| 模型／接触验证操作 | [接触仿真教程](../../tutorials/contact_simulation.md) |
| 10BC＋20接管RL及续训 | [试验教程](../../../omi_proj/tutorials/contact_intervention_study.md) |
| 来源与校验 | [资产清单](../../manifests/contact_simulation_asset_20261121.json)、[策略试验清单](../../manifests/contact_policy_study_20261121.json) |

## 剩余问题和后续顺序

1. 扩大无接管验证的初态、场景和随机种子，检验8例成功能否复现；保留BC基线和失败对照。
2. 分开检查探索方式、旋转模仿约束和图像增广的贡献。第一轮后期采样方差升高、接管比例很高；较低接管比例也不自动意味着策略更好。
3. 加强姿态纠偏、接触卡滞恢复和有依据的力限制。当前力统计为控制时刻模拟量，不是实物安全力认证。
4. 逐步补齐机器人状态／触觉观测、工具和相机标定，并验证真实夹持和整机自碰撞。
5. 整理模块／插座子资产封装；保持原mesh不变，新修订使用新目录并重跑验收。
6. 真实感知继续解决固有结构三维对应及遮挡下的可观测性，不恢复对额外marker贴纸的必要依赖。

## 保存与交接边界

当前代码／文档在两个功能分支工作树，存在多阶段未提交改动；本次文档整理不代表提交或推送完成。历史记录保留，新输出使用新目录。

已有[迁移包与恢复说明](../../tutorials/asset_migration_20261121.md)是当时的选择性快照，明确未包含打包时仍在推进的第二轮及新对照，不能假定它包含本页所有最新产物。恢复新试验需要对应完整目录、协议、权重、replay和帧；不能只拿actor文件当作完整训练恢复。
