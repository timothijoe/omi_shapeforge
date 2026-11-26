# System0 RL完成与重启交接（2026-11-26）

本页专注重启操作；完整任务背景与后续工作见[System1／System0会话交接](2026-11-26-system1-system0-session-handoff.md)。

文档入口：[纪传体／当前成果与限制](../agent/simulation/evolution/system0-randomized-retraining.md) · [编年体／执行与恢复经过](../agent/simulation/chronicles/2026-11-26-system0-randomized-retraining.md)。本页保留重启接续操作。

**当前状态：RL训练已完成并保存；最终留出测试按用户要求暂停，未启动。**

完成核对时间：2026-11-26T19:57:32+08:00。本任务的训练worker已正常结束，权重和经验池已校验并同步落盘。这里只说明本任务的接续条件，不代表其他会话或程序都已结束；没有执行重启操作。

## 1. 已完成什么

- 正式规则示范120/120成功：训练96条、55784步；验证24条、14046步。
- 四个新模型均完成30000次BC更新。
- 四个RL模型各保留20000条有效交互，总计80000条；下表中的规则动作属于训练接管，不是自主成功。
- Actor、critic参数均为有限数值，模型ZIP CRC、模型／replay SHA-256通过；所有有效replay与实际动作、提议动作、历史、奖励、终止、超时及腕力逐条匹配。
- 没有运行本轮最终的`bctest`或`test`。此前已做过BC验证，不要把它与尚未执行的最终留出测试混淆。

| 初始化种子 | 组别 | 有效交互 | SAC更新 | 策略执行步 | 规则执行步 |
| --- | --- | --- | --- | --- | --- |
| 430000 | 有路径 | 20000 | 20000 | 7991 | 12009（60.05%） |
| 430000 | 仅目标 | 20000 | 20000 | 6847 | 13153（65.77%） |
| 431000 | 有路径 | 20000 | 19999 | 7439 | 12561（62.80%） |
| 431000 | 仅目标 | 20000 | 19999 | 2134 | 17866（89.33%） |

第二对从“写入第15000条经验、尚未做下一次梯度更新”的检查点恢复，所以最终各19999次SAC／纠正更新；同一对保持一致，交互数均满20000。实际总SAC更新79998，不能写成80000次梯度更新。

## 2. 最终应该加载哪些模型

- **有路径／430000**：[最终RL权重](/data/shapeforge/runtime/runs/s0_rand_train_20261126/rl_path_430000/experiment/system0.zip)；[BC权重](/data/shapeforge/runtime/runs/s0_rand_train_20261126/bc_path_430000/system0.zip)。
- **仅目标／430000**：[最终RL权重](/data/shapeforge/runtime/runs/s0_rand_train_20261126/rl_goal_430000/experiment/system0.zip)；[BC权重](/data/shapeforge/runtime/runs/s0_rand_train_20261126/bc_goal_430000/system0.zip)。
- **有路径／431000**：[最终RL权重](/data/shapeforge/runtime/runs/s0_rand_train_20261126/resume_path_431000/experiment/system0.zip)；[BC权重](/data/shapeforge/runtime/runs/s0_rand_train_20261126/bc_path_431000/system0.zip)。
- **仅目标／431000**：[最终RL权重](/data/shapeforge/runtime/runs/s0_rand_train_20261126/resume_goal_431000/experiment/system0.zip)；[BC权重](/data/shapeforge/runtime/runs/s0_rand_train_20261126/bc_goal_431000/system0.zip)。

**431000这一对必须加载`resume_path_431000`／`resume_goal_431000`中的最终文件。** 原来的`rl_*_431000`目录是中断分支，保留作取证，不是最终模型。

每份RL权重旁有：`system0.json`（配置、来源及哈希）、`replay.pkl`（继续RL用）、`training_report.json`、`replay_validation.json`。测试只加载策略权重和元数据；将来续训还需要经验池。

统一路径映射：[training_routes.json](/data/shapeforge/runtime/runs/s0_rand_train_20261126/training_routes.json)。完整文件校验清单：[training_complete.json](/data/shapeforge/runtime/runs/s0_rand_train_20261126/reboot_handoff/training_complete.json)。BC模型和正式数据都保留，未被此次恢复覆盖。

## 3. 中断、修复与计数口径

原流水线在2026-11-26 19:34前后停止：无路径431000模型在19086次已确认交互后，第三次请求恢复时抛出`recovery_attempt_budget`。旧总控随之终止同批有路径模型；它记录了19445次learner交互，worker另有1次已执行但未回传的动作。

根因：已有两次恢复完成、老师回到idle后再次受阻，预算耗尽只在下一次teacher查询时才抛异常，而未在上一条真实交互结束时记为失败。修复仅让这类状态在真实`step`后正常终止为失败并开始下一回合：**未增加恢复次数，未放宽接触／成功判据，未伪造未执行动作或额外transition。** 保存的原失败观测已做回归复现。

原冻结源码`code/`保持只读；新增`code_resume_training/`，相对原版本仅修改`isaac_recovery.py`。软件回归44项通过；轻量104项中29通过、75跳过。这些是训练必需的代码／完整性检查，不是用户暂停的策略留出评估。

第二对都从15000步检查点重新开始，各补5000步，共同使用新的episode seed432000。初始化种子仍是431000，模型内运行seed可显示432000。模型／优化器／旧经验池恢复，物理回合重新初始化。各1000步另存检查点，最终正常退出。

未保存分支不混入最终经验池，原始日志保留。最终有效交互80000；包括未保存分支在内的正式RL worker控制步记录为88532，其中8532条未进入最终有效模型预算。不要将旧日志的约1.9万步和续训5000步简单相加当成模型当前步数。

修复与恢复证据：

- [修复回归](/data/shapeforge/runtime/runs/s0_rand_train_20261126/reboot_handoff/failure_regression.json)
- [新冻结源码及唯一变更](/data/shapeforge/runtime/runs/s0_rand_train_20261126/reboot_handoff/resume_source_freeze.json)
- [只训练、不测试的完成回执](/data/shapeforge/runtime/runs/s0_rand_train_20261126/reboot_handoff/training_only_result.json)
- [模型参数完整性](/data/shapeforge/runtime/runs/s0_rand_train_20261126/reboot_handoff/model_integrity.json)

第一对使用原冻结代码；第二对后5000步使用上述修复。后续报告须注明，不能继续声称四个训练全过程的worker源码完全相同。

## 4. 重启后先检查，不启动测试

运行资源在持久化目录：

```text
/data/shapeforge/runtime/runs/s0_rand_train_20261126
/data/shapeforge/runtime/envs/omi_sim_train
/data/isaac-sim-5.1.0
/data/shapeforge/runtime/runs/staged_contact_20261123/robot_transfer
```

先检查GPU是否恢复：

```bash
nvidia-smi
```

再运行只读预检：

```bash
/data/shapeforge/runtime/envs/omi_sim_train/bin/python \
  /data/shapeforge/runtime/runs/s0_rand_train_20261126/reboot_handoff/evaluate_after_reboot.py \
  --run /data/shapeforge/runtime/runs/s0_rand_train_20261126
```

默认只验证四个模型及伴随文件、冻结源码、采样计划和Python包版本；**不会创建测试worker，也不会重训**。成功应输出`preflight: passed`、`models: 4`、`evaluation_started: false`。该命令已在本次交接前执行通过。

## 5. 等明确恢复测试时，再执行

以下命令会启动测试；当前没有执行它。建议在能持续运行的终端或可追踪后台进程中运行。

```bash
/data/shapeforge/runtime/envs/omi_sim_train/bin/python -u \
  /data/shapeforge/runtime/runs/s0_rand_train_20261126/reboot_handoff/evaluate_after_reboot.py \
  --run /data/shapeforge/runtime/runs/s0_rand_train_20261126 \
  --start-evaluation
```

该入口只测试，不采集、不做BC、不做RL。依次运行四个BC模型和四个最终RL模型，各24个同样的留出条件，共192回合，最多两个worker并行，全部关闭接管。

- 测试计划：`test.json`，种子405000～405023，保持原来的24个条件。
- 默认输出：`/data/shapeforge/runtime/runs/s0_rand_train_20261126/deferred_eval/`。
- 汇总：`deferred_eval/summary.json`；进程及阶段回执：`launch.json`、`events.json`、`evaluation_result.json`。
- 测试使用修复后的冻结代码；评估没有teacher调用，恢复预算修复不会触发。
- 如已有完整且哈希匹配的测试目录，会验证后复用；如存在不完整目录，保留它并使用新的短输出目录，例如额外指定`--output-root /data/shapeforge/runtime/runs/s0_rand_train_20261126/eval2`。

**不要重新运行旧`study_supervisor.py`或原`run_randomized_retraining.py --phase study`。** 它们是最初的完整采集／训练流水线，不是本次重启接续入口。旧`study_result.json`的失败状态保留，不代表现在四个最终模型仍未完成。

## 6. 已知结果与边界

此前BC验证：路径430000为0/24、431000为2/24；仅目标两种子均0/24，teacher均0。RL最终自主成功率仍未知，训练接管比例较高，尤其goal／431000约89.3%。训练完成只表示预算、权重和经验池保存完备，不表示策略能力验收通过。

插口只在世界XY各±5 mm随机移动，Z和朝向固定；夹爪相对当次插口从30～40 mm、左右±10 mm、上下±2 mm、俯仰／偏航±5°初始化。System1是GT规则路径，模块固定夹持，腕力理想化；不代表视觉误差、滑移或真机结果。

[本轮训练协议与历史记录](../agent/simulation/evolution/system0-randomized-retraining.md)。
