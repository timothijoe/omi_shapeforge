# 分阶段合同与在线恢复下的BC／规则反馈RL重训

> 本机迁移提示（2026-11-24）：运行资源实体已迁至 `/data/shapeforge/runtime`；本文中的 `/data/omi_runtime` 是保留的兼容入口，指向同一份内容。目录映射与恢复要求见[当前资源契约](../../interfaces/local-resources.md)。

2026-11-23，用户要求先检查进程收尾问题，并尝试重新训练BC、RL。[收尾排查](isaac-process-lifecycle.md)的两组短复现均正常退出，历史143尚未复现；本轮使用新增监督器保存即时原生回执，并对长运行调度器记录系统信号。

## 固定实验配置

运行根：`/data/omi_runtime/runs/isaac_staged_retrain_20261123`。输入仍为WG-r10＋OM-r08的`staged_contact_20261123/robot_transfer`；固定附着、六盒碰撞代理、摩擦和分阶段判据不变。物理步长0.2 ms、控制100 ms、回合上限900步，规则末段最小步进0.05 mm、目标预载0.1 mm。

| 项目 | 预登记设置 |
| --- | --- |
| 规则示范 | 2段训练＋1段验证；训练候选1100～1103、验证1120～1121，失败保留但不作为成功示范 |
| 独立评估 | 1700、1701，BC与最终RL使用相同初态；确定性策略、无teacher、无额外规则动作限幅 |
| BC | 3000次更新，按验证误差选择权重；冻结视觉编码器 |
| 反馈RL | 1800～1802三个回合；Critic预热128次，每回合256次更新，Actor学习率1e-5，BC权重10 |
| 恢复检查 | 前两个RL回合后独立进程重载，再执行第三回合；核对网络、优化器、经验池和来源 |
| 模型选择 | 最终RL检查点在协议中指定，不按测试成绩挑选中间检查点 |

所有种子集合互不重叠。只复用既有冻结视觉骨干，从新规则示范重建BC，不导入旧经验或强行加载旧任务策略。训练动作来源区分policy与scripted_intervention，真人为0；规则是仿真真值反馈，不是人工数据。基础观测仍为双RGB历史，state／tactile填零，实仿语义缺口没有因此消失。

这是一次小规模试验，RL有额外在线数据与更新预算。可以比较两个最终模型在这两个初态的实际表现，不能把差异全部归因于RL算法，也不能与旧碰撞／旧合同的0/4直接合并或计算提升率。没有测试任意孔位、宽范围扰动、真实夹持或真机。

## 实际结果

本轮固定预算已完成：规则示范3次尝试全部成功，原2训练＋1验证配额满足；训练792条、验证391条。BC执行3000次更新，按验证误差选中第2800步。Critic实际896次更新、Actor实际384次更新。

无接管评估：**BC 0/2，最终RL 0/2**；带规则接管的在线训练为2/3。这两种口径分别报告。所有测试teacher请求为0，检查点哈希与实际评估权重一致。

| 策略 | 留出种子 | 结果 | 步数 | 最终深度mm | 失败／终止原因 |
| --- | --- | --- | --- | --- | --- |
| BC | 1700 | 失败 | 68 | 6.1263 | entrance_not_qualified |
| BC | 1701 | 失败 | 804 | 51.1994 | large_mean_contact_load |
| RL | 1700 | 失败 | 123 | 6.0158 | entrance_not_qualified |
| RL | 1701 | 失败 | 72 | 6.0077 | entrance_not_qualified |

在线经验共925条：策略653、规则272、真人0。训练回合／接管段统计与经验池核对一致，human_mask为0。前2回合后的独立进程续训和最终独立CPU重载均通过网络／优化器状态精确核对；冻结视觉编码器未变化。不宣称随机采样流或任意崩溃点恢复是逐位可复现的。

进一步核验发现：三回合训练中完整退回重插的启动次数为0；31个中途接管段均交回策略，实际提供的是普通对准／插入修正。本轮数据没有完整恢复训练样本，不能宣称学会了上一轮诊断脚本展示的恢复行为。

BC／1700在跨过5 mm时横偏0.15325 mm，超过0.15 mm入口阈值，资格计数清零；BC／1701虽到达51.1994 mm，最终横偏0.3385 mm、角度0.01089 rad仍不合格，随后触发大平均接触负载。其100 ms接触代理均值峰值214.417 N、物理子步峰值36481.892 N均保留；这是未标定仿真冲量指标，极大峰值须另行复核模型／控制，不能解释为真实腕力，也未据此删除失败。

最终RL两例均未通过入口；1700最终横偏达13.7503 mm，1701为0.3160 mm，不能只看相近的最终轴向深度掩盖偏差。该小预算试验没有证明自主改善。当前普通门控横偏阈值0.25 mm比入口资格0.15 mm宽，且`recovery_required`主要由接触卡滞／负载触发；应另立协议检查入口阶段的提前接管与资格丢失恢复，以及增加带扰动／恢复的示范。这里是基于本轮证据提出的下一步，不是已验证的修复或失败因果归因。

[逐例行为分析](/data/omi_runtime/runs/isaac_staged_retrain_20261123/behaviour_analysis.json)

本轮初始化、采集、BC、BC评估、RL、续训、RL评估、shutdown客户端及worker均有独立原生退出0回执；worker clean shutdown文件完整。源码哈希复核未漂移。历史143的信号来源仍未查明，不能将本轮正常收尾回写成历史正常退出。

[完整汇总](/data/omi_runtime/runs/isaac_staged_retrain_20261123/summary.json) · [学习／评估图](/data/omi_runtime/runs/isaac_staged_retrain_20261123/learning_summary.png) · [逐进程回执](/data/omi_runtime/runs/isaac_staged_retrain_20261123/pipeline_receipts.json)

## 代码与证据

`scripts/simulation/run_isaac_learning_study.py`负责独立目录、固定阶段、每个子进程独立进程组、即时退出回执、信号／错误记录和有界关闭。`omi_hil_rl.training.isaac_rule_feedback --preset staged-retrain`登记本轮训练预算；实际学习仍复用现有Actor／SAC、EpisodeSpool、TransitionReplay和检查点实现。

运行根的`protocol.json`登记整个流程，`study/protocol.json`和`study/contract.json`固定学习配置及执行合同；`*_process.json`保存每个原生进程的命令、PID／PGID和退出状态。worker及学习侧源码快照、输入／骨干哈希、原始日志、示范失败记录和模型保存在运行根，不纳入Git。

操作入口在ShapeForge根目录：使用新的`--output`，执行`.venv/bin/python -u scripts/simulation/run_isaac_learning_study.py --output <新目录> --transfer /data/omi_runtime/runs/staged_contact_20261123/robot_transfer --pretrained /data/omi_runtime/baselines/omi_transfer_20261120_004618/omi_proj/local/pretrained/serl_resnet10/backbone.pt`。不要覆盖本轮固定输出。复现历史版本应先核对源码快照，不能仅依赖当前HEAD。
