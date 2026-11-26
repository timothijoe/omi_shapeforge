# 随机插口与远初态的System0重训（纪传体）

跨会话接手先读[System1／System0会话交接](../../../chronicles/2026-11-26-system1-system0-session-handoff.md)。

**当前状态：四个模型的BC和RL训练已完成、文件已校验；最终无接管留出测试按用户要求暂停，尚未执行。** 完成核对时间为2026-11-26 19:57:32（北京时间）。训练完成不等于策略能力验收通过。

本文维护当前实现、训练成果、证据和限制。[编年体](../chronicles/2026-11-26-system0-randomized-retraining.md)记录执行经过；[重启交接](../../../chronicles/2026-11-26-system0-rl-reboot-handoff.md)提供模型清单及可执行恢复命令。

## 任务与随机化

| 项目 | 本轮设置 |
| --- | --- |
| 插口位置 | 世界X/Y各±5 mm；世界Z与插口朝向固定 |
| 夹爪起点 | 相对当前插口，名义尖端间隙30～40 mm |
| 夹爪横向／上下 | ±10 mm／±2 mm |
| 夹爪俯仰／偏航 | 各±5° |
| System1 | 真值位姿＋现有32点、0.5 mm间隔规则路径 |
| System0对照 | 有路径／仅目标与共同上下文；后者不生成waypoint序列 |
| 训练接管 | 规则老师接管、恢复和交回；不是人工干预 |

各初态参数独立采样，但夹爪的位姿定义在当次插口附近，绝对世界起点会随插口移动；不能称为固定世界夹爪起点下的独立插口扰动。旋转围绕夹爪中心，名义间隙定义在旋转前，实际尖端间隙另外审核。

保持本实验冻结的WG-r10／OM-r08场景、固定模块夹持和理想腕力。其他线程的视觉版本更新未替换本轮训练资产；未加入视觉估计误差、模块滑移、插口转角或真机实验。

## 数据与训练成果

正式规则示范120/120成功：训练96条、55784步；验证24条、14046步。另有24个留出条件，目标位置与训练／验证互不重合。正式采集按维度独立分层采样，训练中的横移、俯仰和偏航分别各48个正向／48个负向；边界小样本8条不混入正式数据。

每个模型从新权重进行30000次BC更新，按孔外／入口／内部／收尾四阶段平衡抽样；随后加载对应BC权重继续带干预SAC。两组网络输入形状和参数数量相同，每一配对种子的初始actor及BC样本顺序已核对一致。

| 初始化种子 | 组别 | BC更新 | 有效RL交互 | SAC更新 | 规则接管步占比 |
| --- | --- | --- | --- | --- | --- |
| 430000 | 有路径 | 30000 | 20000 | 20000 | 60.05% |
| 430000 | 仅目标 | 30000 | 20000 | 20000 | 65.77% |
| 431000 | 有路径 | 30000 | 20000 | 19999 | 62.80% |
| 431000 | 仅目标 | 30000 | 20000 | 19999 | 89.33% |

总有效交互80000，实际SAC更新79998。第二对从写入15000条经验、下一次梯度更新之前的检查点恢复，各补5000步，因此各少1次更新，同一对内一致。规则接管比例不是自主成功率。

运行配方：actor LR=1e−5、critic LR=3e−4；初始Gaussian std=.02、上限.03（tanh前）；entropy=`auto_0.001`、target entropy=−18；规则专用采样份额.5、纠正BC权重10，`learning_starts=0`。原计划每5000步保存，恢复阶段每1000步保存。

在线`--reset-distribution`按episode seed及固定salt独立均匀采样，局部RNG不改变BC／策略的全局随机状态。同一seed得到相同初态，实际回合数、自主动作量和在线经验仍可能不同。分布写入模型config，续训要求一致；与旧`--target-schedule`互斥，显式reset参数可覆盖对应字段。

## 当前可确认的能力与限制

此前已经完成的BC验证，每组24回合、无接管：

| 初始化种子 | 有路径 | 仅目标 |
| --- | --- | --- |
| 430000 | 0/24 | 0/24 |
| 431000 | 2/24 | 0/24 |

这些是BC验证集成绩，不是尚未执行的最终留出测试。失败涉及入口资格、接触点穿入、超时、IK拒绝和几何重叠；不能用训练动作MSE或辅助训练成功率替代自主能力。

四个最终模型、经验池和完整有效交互已审核：实际／提议动作、历史、奖励、终止／超时、腕力匹配；ZIP CRC与SHA-256通过，actor和critic参数均有限。恢复的15000步经验前缀保留，后续参数确实发生更新。代码回归44项通过；轻量104项中29通过、75跳过。这些是完整性检查，不是用户暂停的策略评估。

## 恢复实现与计数边界

第二对原无路径模型在19086次已确认交互后触发`recovery_attempt_budget`，旧总控连带中断有路径模型。问题是两次恢复已经完成、老师回到idle后再次受阻，预算耗尽直到下一次teacher查询才抛异常。

修复让该状态在刚发生的真实step结束时记为失败并终止回合。恢复次数、关节限位、接触／成功判据均未放宽，也未为未执行动作补造transition。原冻结`code/`保留；`code_resume_training/`相对它仅修改`isaac_recovery.py`。第二对从共同15000步检查点恢复，模型、优化器和经验池加载，物理回合重新开始，共同使用新episode seed432000；初始化种子仍为431000。

未保存分支和失败回执全部保留，不计入最终有效预算。包括这些分支在内的正式RL worker控制记录共88532条，比最终有效经验多8532条；其中有1条在有路径worker执行后未回传。第一对使用原代码，第二对后5000步使用修复代码，后续报告必须注明，不能宣称四个训练全过程的worker源码完全一致。

## 最终资源与接续

| 初始化种子 | 组别 | 最终RL权重所在目录（链接到system0.zip） |
| --- | --- | --- |
| 430000 | 有路径 | [rl_path_430000](/data/shapeforge/runtime/runs/s0_rand_train_20261126/rl_path_430000/experiment/system0.zip) |
| 430000 | 仅目标 | [rl_goal_430000](/data/shapeforge/runtime/runs/s0_rand_train_20261126/rl_goal_430000/experiment/system0.zip) |
| 431000 | 有路径 | [resume_path_431000](/data/shapeforge/runtime/runs/s0_rand_train_20261126/resume_path_431000/experiment/system0.zip) |
| 431000 | 仅目标 | [resume_goal_431000](/data/shapeforge/runtime/runs/s0_rand_train_20261126/resume_goal_431000/experiment/system0.zip) |

第二对必须加载`resume_*_431000`，不要误用中断的`rl_*_431000`目录。每份RL权重旁的`system0.json`、`replay.pkl`、`training_report.json`和`replay_validation.json`保留配置、续训经验和审核依据。

运行根：`/data/shapeforge/runtime/runs/s0_rand_train_20261126/`。

| 证据 | 文件 |
| --- | --- |
| 原协议、随机范围与数据划分 | `protocol.json`、`reset_distribution.json`、`split_audit.json` |
| 正式数据 | `dataset/dataset.json`，引用两个collect分片 |
| 配对初始化／BC抽样 | `pairing_audit.json` |
| 最终模型路径 | `training_routes.json` |
| 训练完成与文件校验 | `reboot_handoff/training_complete.json` |
| 仅续训、不评估的回执 | `reboot_handoff/training_only_result.json` |
| 故障回归与修复源码 | `reboot_handoff/failure_regression.json`、`resume_source_freeze.json` |
| 重启就绪检查 | `reboot_handoff/reboot_readiness.json` |

原总控和`study_result.json`保留失败历史；当前训练完成状态以`reboot_handoff/training_complete.json`为准。原全流程的`summary.json`／`comparison.png`没有产出，不能当作现有成绩引用。

**最终评估仍暂停。** 不重启旧`study_supervisor.py`或原全流程。新的`reboot_handoff/evaluate_after_reboot.py`默认只验证文件、源码与环境；只有明确恢复测试并加`--start-evaluation`才运行四份BC及四份RL的同24条件留出评估，不采集、不训练。完整命令与异常处理见[重启交接MD](../../../chronicles/2026-11-26-system0-rl-reboot-handoff.md)。
