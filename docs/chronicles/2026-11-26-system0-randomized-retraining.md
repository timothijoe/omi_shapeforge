# 2026-11-26：随机化插口并重新采集、BC与RL

本页保留启动阶段记录；完整执行经过已整理到[仿真领域编年体](../agent/simulation/chronicles/2026-11-26-system0-randomized-retraining.md)，当前事实见[纪传体](../agent/simulation/evolution/system0-randomized-retraining.md)。**RL现已完成，最终测试暂停。**

用户在大初态偏差演示后要求随机化插口位置，重新采数据、重新模仿学习，再强化学习。固定新协议：插口世界XY各±5 mm，远起点30～40 mm，相对横移±10 mm／上下±2 mm／俯仰偏航±5°。继续GT System1和有／无路径配对，两初始化种子，共四模型。

计划96训练＋24验证示范；每模型BC30000更新、规则干预RL20000交互；24个留出条件在BC和最终RL各测试一次，关闭接管。采样计划预先保存且目标位置分割不重合，不按结果调测试集或选检查点。

240个离线IK检查通过，8个实际边界示范全部成功。随后独立BC20→RL64小检查验证新随机reset、加载、实际梯度和执行动作replay；小检查64步均规则接管，不算自主成绩，也不混入正式训练。

已冻结287个源码文件与计划输入，启动可追踪、支持SIGTERM的正式流水线。启动记录当时处于正式示范采集，训练／测试成绩仍待完整回执；后续变化见下节及领域编年体。质量检查要求所有正式计划示范成功，失败保留；后续阶段、汇总与归档已自动串联。

- [范围、预算与恢复入口](../agent/simulation/evolution/system0-randomized-retraining.md)
- 运行根：`/data/shapeforge/runtime/runs/s0_rand_train_20261126/`
- 总控：`study_supervisor.json`、`study_pipeline.log`、`study_progress.json`
- 计划：`protocol.json`、`input_hashes.json`、`split_audit.json`
- 清单：`manifests/system0_randomized_retraining_20261126.json`

本阶段不改变旧资产、旧模型或原成功判据；不新增视觉、模块滑移、插口旋转或真机结论。


## 后续：训练完成，评估延后

用户要求先完成RL、暂不测试以准备重启。原第二对约1.9万步时因recovery_attempt_budget异常停止；从双方15000步检查点统一接续5000步，补齐各20000有效交互，未保存分支保留且不计入有效模型预算。仅修复预算耗尽的回合终止处理；模型／经验池／全部执行记录审核通过。最终测试没有启动。

完整接续依据改为[RL完成与重启交接](2026-11-26-system0-rl-reboot-handoff.md)，不要重跑旧全流程。
