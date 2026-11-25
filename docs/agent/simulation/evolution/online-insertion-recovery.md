# Isaac在线接管：退回、外部对准与重新进入

> 本机迁移提示（2026-11-24）：运行资源实体已迁至 `/data/shapeforge/runtime`；本文中的 `/data/omi_runtime` 是保留的兼容入口，指向同一份内容。目录映射与恢复要求见[当前资源契约](../../interfaces/local-resources.md)。

后续：[143排查与进程监督](isaac-process-lifecycle.md)完成两组短复现检查；[新合同BC／RL重训](staged-retraining.md)已有独立最终结果。本页三例仍为原诊断脚本批次，不改写其143或原生回执缺失。

2026-11-23，用户在[上一窗口收尾交接](../../../chronicles/2026-11-23-isaac-rule-rl-window-handoff.md)后要求继续开发。本轮把已验证脚本中的恢复行为接入Isaac训练worker及SAC采集使用的接管门控。目标是补齐反馈链路；本轮没有训练Actor／Critic，也没有连接真机。

## 实现与边界

ShapeForge新增`src/omi_shapeforge/sim/isaac_recovery.py`。状态依次为`idle → retreat → align_outside → reinsert → idle`：

1. 共享任务判断发出`recovery_required`后，由门控请求规则。控制器保存当时实测横偏和姿态，沿插入轴退回预插入平面，不在孔口直接横移纠偏。
2. 实际TCP到达退回目标且深度<0后，才在入口外恢复名义位置与姿态。位置容差0.08 mm，姿态容差0.0015 rad。
3. 再次向插入目标推进。必须重新取得入口资格、深度≥5 mm、横偏<0.12 mm、角度<0.0015 rad，才释放恢复持有状态。
4. 原有接管门控还检查最少8步持有和当前任务的接触条件，再交还提议方。取得入口资格和交回控制都不算插入成功；最终成功仍由固定分阶段任务判据决定。

`contact_teacher.py`新增显式控制子目标参数，不修改`RobotExperiment.goal_pos`或任务phase。worker的任务目标始终是同一最终到位位置，奖励势函数也始终指向它；退回会增加距离，不能通过切换子目标取得虚假的奖励或成功。恢复中不reset、不瞬移、不清除失败锁定，也不借用历史`begin_withdrawal()`的独立拔出完成语义。

恢复默认最多2次，每阶段最多450个实际控制步。查询规则动作不会消耗物理步预算。超出恢复预算属于明确的失败终止，保存`recovery_attempt_budget`或`recovery_phase_timeout`；全回合最大步数仍独立控制时间截断。物理失败优先，不允许恢复覆盖失败。实际被采用的动作用于下一步动作平滑；切换恢复阶段时清除前一方向的平滑残留。

OMI新增`training/isaac_intervention.py`，由现有`isaac_rule_feedback.train_rl`导入同一个`Gate`。新合同下接管读取共享任务的阶段接触／卡滞判断，并在`recovery_active`期间持有控制；内部轻擦不再重新套旧的6 N瞬时门控。旧worker元数据不声明恢复时，继续原门控。动作来源仍是`scripted_intervention`，不会进入真人标签。独立策略评估不实例化Gate、不查询teacher；worker仅在teacher请求时启动恢复，单独的`step`不会替换提议动作。

新增执行元数据`recovery_controller`及合同`isaac-staged-recovery-ownership-v1`，配置纳入原有worker重连一致性检查。任务合同仍为`entry-strict-interior-tolerant-v1`，奖励公式仍为`isaac-staged-contact-terminal-potential-v2`。由于执行配方发生变化，旧检查点／经验不得绕过合同核查混用。worker保存执行源码快照、哈希、TCP与关节实际状态、固定目标和恢复状态。

## 验证口径

相关回归36项通过，包含恢复顺序、资格重取、阶段预算、失败拒绝、动作平滑、持有／交还、旧门控和合同登记。轻量控制环境的必需全套检查另行记录；可选依赖跳过不能计作实际执行。

真实验证入口为`scripts/simulation/probe_online_recovery.py`，调用实际`IsaacClient`和训练使用的Gate。预登记三个案例：正常800、+1 mm恢复801、−1 mm恢复802；worker开启真实RTX双RGB，PhysX步长0.2 ms、控制间隔100 ms、回合900步，末段最小步进0.05 mm、目标预载0.1 mm。每例只初始reset一次，偏移和受阻通过普通RPC动作生成。

测试中的提议方是使用精确位姿的**诊断脚本**，不是学习策略；日志将其记作`synthetic_probe`，规则接管仍记`scripted_intervention`。偏移先实际受阻，额外保持3步且不调用teacher，以检查worker不会自行接管，然后启用Gate。取得入口资格并交回后，诊断脚本继续完成插入。该检查验证训练接口中的自动恢复／交回，不是SAC训练效果或自主成功率。

正式三例功能检查均通过，累计1653个控制步，逐步客户端与worker记录交叉核对一致。**外层工具会话退出143**；缺失原生退出回执及worker clean shutdown文件，原生退出码未知。检查时worker／probe进程均已不存在，原因尚未诊断；不能把完整三例报告当作正常进程退出。

| 案例／种子 | 控制步 | 接管步 | 最终深度mm | 集成验收 |
| --- | --- | --- | --- | --- |
| normal／800 | 392 | 0 | 51.281033 | 通过 |
| recovery_plus／801 | 605 | 102 | 51.281126 | 通过 |
| recovery_minus／802 | 656 | 102 | 51.280987 | 通过 |

+1／−1 mm分别退到-4.923／-4.923 mm，在第276／319步交回，交回后深度分别5.172／5.178 mm；当时均已取得入口资格，均未被标作任务成功。正常例teacher查询为0，两条恢复各完成一次恢复并交回，没有中途reset。

负偏移例的3步无teacher等待后，恢复提示短暂消失，第217步先因横偏执行了1步普通规则对准，第218步收到恢复提示后才开始退回。该步计入102步接管总数，完整事件顺序保留在核验汇总，未重写成第一步就退回。这里验证的是提示存在时启动并完整持有恢复；尚未验证延迟仲裁下恢复提示的锁存策略。

另在`/data/omi_runtime/runs/online_recovery_lifecycle_20261123`进行独立生命周期检查：同版worker、独立进程会话、一次reset／一次零动作／shutdown，RPC确认成功，worker与外层检查均退出0，并有clean shutdown文件。这不是插入成功案例，不纳入三例统计；不能据此给v2补写原生退出码或宣称已诊断143。

三例100 ms接触指标均值最高0.322114 N，物理子步峰值最高17.225612 N。两种统计均保留，仍是冲量模长之和的仿真代理，不是真实腕部净力。[完整核验汇总](/data/omi_runtime/runs/online_recovery_20261123_v2/verified_summary.json) · [轨迹图](/data/omi_runtime/runs/online_recovery_20261123_v2/recovery_traces.png)。

轻量环境全套56项中14项实际执行通过、42项因可选依赖／场景缺失跳过；相关NumPy／学习环境36项实际通过；训练CLI导入检查通过。工作树worker源码与执行快照12份一致，transfer哈希与前一规则复核一致。


输入仍为`/data/omi_runtime/runs/staged_contact_20261123/robot_transfer`：WG-r10＋OM-r08、固定附着、六盒碰撞代理。几何、摩擦和任务阈值未改。这里只验证已知孔位和小范围横偏；真实抓取、腕力、感知误差、大姿态、多次恢复的物理覆盖及真机迁移仍需分别验证。原BC／RL自主0/4和旧规则8＋4例成绩均保留，不能与本轮相加。

## 证据与复现

正式运行根：`/data/omi_runtime/runs/online_recovery_20261123_v2/`。`protocol.json`固定启动参数和案例；`worker/execution.json`及`worker/code_snapshot/`固定实际源码；`probe/`保存合同、逐例轨迹、关键帧和报告；`process_observation.json`记录外层143及原生退出回执缺失；`summarize.py`交叉核对worker和客户端记录、固定目标／奖励、恢复顺序、资格交回，并保留进程状态未验收的限制。

初步`online_recovery_20261123_v1`在正常案例尚未完成时主动中断，以修正实际动作和teacher平滑状态的同步。客户端中断造成worker回复时BrokenPipe；原日志、失败记录与`interrupted.json`保留。该轮不是完成的案例，没有正常原生退出回执，不进入正式三例统计。

复现时在ShapeForge根目录启动worker，所有输出使用新目录，不重复运行固定目录的`run.py`：

```bash
env -u CONDA_PREFIX -u CONDA_DEFAULT_ENV -u PYTHONHOME -u PYTHONPATH -u LD_LIBRARY_PATH \
 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
 /data/isaac-sim-5.1.0/python.sh -u scripts/simulation/isaac_rl_worker.py \
 --transfer /data/omi_runtime/runs/staged_contact_20261123/robot_transfer \
 --output <新worker目录> --socket <新socket路径> --max-steps 900 \
 --teacher-min-step-mm .05 --target-overtravel-mm .1
```

另一个终端使用`/data/omi_runtime/envs/omi_sim_train/bin/python -u scripts/simulation/probe_online_recovery.py --transfer /data/omi_runtime/runs/staged_contact_20261123/robot_transfer --socket <同一socket路径> --output <新probe目录>`。运行前对照源码快照与合同，运行后关闭本次worker并保存退出码。只读复核使用`/data/omi_runtime/envs/omi_sim_train/bin/python /data/omi_runtime/runs/online_recovery_20261123_v2/summarize.py`，不重新运行物理。

下一步是在冻结的新执行合同下采集匹配示范，再做等数据／预算BC与规则反馈RL对照以及独立无接管评估。当前恢复仍依赖仿真精确位姿，不等于已经完成真机可用观测与动作合同。
