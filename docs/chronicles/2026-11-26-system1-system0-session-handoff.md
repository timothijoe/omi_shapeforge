# System1 / System0 会话交接（2026-11-26）

## 接手先读

**最新一轮随机化重训的BC和RL已经完成，最终留出测试按用户要求暂停，尚未启动。现在不要重训、不要自动评估，也不要自行重启机器。** 用户可能安排重启；待用户明确要求恢复测试后，使用本文的独立评估入口。

本交接覆盖本会话的训练、初态实验、可视化及后续工作，不接管并行的资产外观任务。

- [纪传体：当前训练成果与限制](../agent/simulation/evolution/system0-randomized-retraining.md)
- [编年体：采集、训练、中断与恢复](../agent/simulation/chronicles/2026-11-26-system0-randomized-retraining.md)
- [重启操作详单：校验清单、模型及恢复命令](2026-11-26-system0-rl-reboot-handoff.md)
- [上一窗口System1/System0背景](2026-11-25-system1-system0-handoff.md)

## 用户目标与已确定的做法

用户想比较：System0接受System1路径，是否比只接受目标位姿更容易学会插入；并希望数据覆盖不同插口位置、较远起点、横向偏移和末端姿态偏差。

当前System1使用**真值位姿＋规则解码路径**，不是路径规划器，本轮也没有重新训练视觉System1。System0先用规则示范做BC，再做带规则干预的SAC；老师会接管、恢复、交回，经验池存实际执行动作和原始策略提议。最终能力须在关闭接管后评估。

两组共享目标位姿、进度、参考年龄／有效位和历史；仅目标组将waypoint槽位置零且不生成路径序列。不能把它描述成完全不知道目标的盲控制器。

本轮输入：32×6＋9=201维参考，4×19=76维运动／实际动作／腕力历史，共277维；S0 actor不读取RGB。动作仍是归一化世界TCP位移和旋转增量。展示以夹爪接触垫中心为参考，X向前、Y向左、Z向上；这没有把训练坐标系改成夹爪中心。32点、0.5 mm路径是空间参考，不带时间参数；冻结实现到末端重复终点位姿，没有因早先mask讨论自动换成新的逐点mask方案。

## 最新训练状态：s0_rand_train_20261126

运行根：`/data/shapeforge/runtime/runs/s0_rand_train_20261126/`。

随机范围：插口世界X/Y各±5 mm，Z和插口朝向固定；夹爪相对当次插口从名义30～40 mm间隙、横移±10 mm、上下±2 mm、俯仰／偏航各±5°开始。参数独立采样，但夹爪起点按当前插口定义，不是固定世界夹爪起点下只移动插口。

已完成：

- 120/120条正式规则示范成功：96训练55784步、24验证14046步。
- 四个模型从新权重各完成30000次BC更新。
- 四个最终RL模型各保留20000条有效交互；权重、经验池、ZIP CRC、SHA、参数有限性及有效transition逐条核对通过。
- 最终BC与RL留出测试未执行；软件回归／保存完整性检查不等于策略评估。

| 初始化种子 | 组别 | 有效RL交互 | SAC更新 | 规则接管步占比 | 最终RL权重 |
| --- | --- | --- | --- | --- | --- |
| 430000 | 有路径 | 20000 | 20000 | 60.05% | [rl_path_430000](/data/shapeforge/runtime/runs/s0_rand_train_20261126/rl_path_430000/experiment/system0.zip) |
| 430000 | 仅目标 | 20000 | 20000 | 65.77% | [rl_goal_430000](/data/shapeforge/runtime/runs/s0_rand_train_20261126/rl_goal_430000/experiment/system0.zip) |
| 431000 | 有路径 | 20000 | 19999 | 62.80% | [resume_path_431000](/data/shapeforge/runtime/runs/s0_rand_train_20261126/resume_path_431000/experiment/system0.zip) |
| 431000 | 仅目标 | 20000 | 19999 | 89.33% | [resume_goal_431000](/data/shapeforge/runtime/runs/s0_rand_train_20261126/resume_goal_431000/experiment/system0.zip) |

**第二个种子必须用`resume_*_431000`下的最终权重。** 原`rl_*_431000`是中断分支。每个最终目录中保留`system0.json`、`replay.pkl`、`training_report.json`和`replay_validation.json`。BC权重在对应`bc_<path|goal>_<seed>/system0.zip`。

权威入口：

- [最终路径映射](/data/shapeforge/runtime/runs/s0_rand_train_20261126/training_routes.json)
- [训练完成与文件哈希](/data/shapeforge/runtime/runs/s0_rand_train_20261126/reboot_handoff/training_complete.json)
- [只训练完成回执](/data/shapeforge/runtime/runs/s0_rand_train_20261126/reboot_handoff/training_only_result.json)
- [重启就绪记录](/data/shapeforge/runtime/runs/s0_rand_train_20261126/reboot_handoff/reboot_readiness.json)

### 目前不能声称新模型已经学好

之前的24例BC验证，无接管：有路径两个种子分别0/24、2/24；仅目标两种子均0/24。RL最终自主成功率未知，训练仍有较高接管占比，尤其goal／431000约89.3%。训练期辅助成功、旧模型的视频和本轮最终模型能力必须分开。

## 必须保留的异常与恢复说明

原流水线19:34前后因`recovery_attempt_budget`中断：仅目标431000在19086条已确认交互后，请求第三次恢复时抛异常；总控同时停了有路径同批任务。

缺口发生在老师完成两次恢复并回到idle、随后再次受阻的情况。修复让预算耗尽在刚完成的真实step上记为失败并结束回合，而非下一次teacher查询才抛错。未增加恢复次数、放宽判据或伪造未执行动作。

原冻结`code/`不改，新`code_resume_training/`仅修改`isaac_recovery.py`。第二对从共同15000步检查点恢复，各补5000步，运行episode seed改为432000；初始化种子仍为431000。检查点在经验写入后、下一次梯度更新前保存，所以第二对各19999次SAC更新；第一对各20000次，总计79998次。有效交互仍各20000，总计80000。

未保存分支和失败回执保留，不能把约1.9万步旧日志与新5000步相加当作最终模型计数。包含弃用分支的正式RL worker记录为88532条，其中8532条未进入最终有效经验。原`study_result.json`继续保留失败状态；当前完成依据是`reboot_handoff/training_complete.json`。

后续分析应注明训练代码的这一变更，不能再宣称四个训练全过程源码完全相同。当前规则恢复回归44项通过，轻量104项中29通过、75跳过。

## 重启后接续：默认不启动测试

环境和资源均位于持久化`/data`目录。使用记录的Python环境，不混用系统Python或替换资产：

```bash
nvidia-smi
```

只读预检（已验证通过；不会启动worker或训练）：

```bash
/data/shapeforge/runtime/envs/omi_sim_train/bin/python \
  /data/shapeforge/runtime/runs/s0_rand_train_20261126/reboot_handoff/evaluate_after_reboot.py \
  --run /data/shapeforge/runtime/runs/s0_rand_train_20261126
```

预期输出包含`preflight: passed`、`models: 4`、`evaluation_started: false`。若文件、哈希或环境版本不匹配，先定位问题，不通过换权重或放宽检查掩盖。

**以下命令只在用户明确恢复测试后执行：**

```bash
/data/shapeforge/runtime/envs/omi_sim_train/bin/python -u \
  /data/shapeforge/runtime/runs/s0_rand_train_20261126/reboot_handoff/evaluate_after_reboot.py \
  --run /data/shapeforge/runtime/runs/s0_rand_train_20261126 \
  --start-evaluation
```

它仅评估四份BC和四份最终RL权重，每份24个原定留出条件，共192回合，最多两个worker并行，全部无接管；不重新采集、不训练。建议在持续运行的终端或记录PID、可停止的后台进程中执行。

输出为`deferred_eval/summary.json`、`launch.json`、`events.json`、`evaluation_result.json`。若有部分失败输出，保留原目录，改用短的新目录，如额外指定`--output-root /data/shapeforge/runtime/runs/s0_rand_train_20261126/eval2`。

**不要启动旧`study_supervisor.py`或原全流程`run_randomized_retraining.py --phase study`。** 它们不是重启接续入口。也不要直接使用旧汇总器去读取中断的第二对目录；独立评估入口已按最终路径映射处理。

完成评估后，应检查每例teacher请求为0、模型SHA及原定目标／初态一致，再分别报告各种子BC→RL变化和有路径→仅目标差异。改善、退步都如实记录，不能只挑成功视频。同步更新纪传体、编年体、current和清单。

## 历史成绩：全部与本轮新模型区分

以下运行的旧模型不是本轮430000／431000的新模型，不能用这些成绩回答“本轮RL自主成功率”。

| 历史实验 | 主要条件 | 有路径／仅目标结果 |
| --- | --- | --- |
| `s1_path_ablation_20261126` | 25训练＋8验证示范，两个种子340000／341000，24个平移目标测试 | 48/48 对20/48；逐种子24/24对0/24、24/24对20/24 |
| `s0_initial_pose_20261126` | 旧341000模型，孔外约10 mm，横移±2 mm、俯仰／偏航±2°及组合 | 10/10 对4/10 |
| `s0_far_start_20261126` | 旧341000模型，总间隙30／40 mm，保留姿态偏差 | 6/6 对2/6 |
| `s0_reorientation_20261126` | 旧341000模型，孔外约40 mm，横移±10 mm、俯仰／偏航±5°及组合 | 8/8 对0/8 |

这些输出都在`/data/shapeforge/runtime/runs/`下；后面三组均为一个冻结模型对、少量指定初态，不是大规模随机鲁棒性保证。最早BC10000的3/5、早期在线训练0/5等失败历史也保留，不与本轮数据混算。

## 用户看视频时的偏好与误解修正

用户希望起点离孔更远、位置／姿态明显偏离，能看清如何调回，并能看到清晰腕图。参考坐标原点是夹爪中心，X向前、Z向上，避免把光模块当作稳定不滑动的坐标基准。

曾用两个相反初态并排、叠加轨迹和坐标箭头的前15秒短片，用户明确表示没看懂。那个短片的左右都是有路径模型，不是有／无路径对照，也没有播放到完整插入。

随后改为**单个模型、单个初态、完整动作**：左外部大视图，右同一次动作的腕部图像，标清“偏斜起点→调整接近→入孔→完成”。优先从这个例子讲解，避免同时混合模型对照、初态对照和多个视角。

- [单例完整解释版（68秒）](/home/linux/Downloads/Reorientation_Demos_20261126/Single_Offset_To_Insertion_v2.mp4)
- [较远30／40 mm腕图合集](/home/linux/Downloads/Farther_Starts_Demos_20261126/Farther_Starts_30_40mm.mp4)
- [10／30／40 mm同相机初态对照](/home/linux/Downloads/Farther_Starts_Demos_20261126/initial_gap_comparison.jpg)
- [大偏差完整有／无路径对照](/home/linux/Downloads/Reorientation_Demos_20261126/Full_Reorientation_Comparisons.mp4)

影片是实际仿真执行状态的重渲染，不是原始相机录像。单例v2以真实尖端越过孔口的第333步切换入孔标记；v1较晚切换的阶段标签已修订，旧文件保留。较新的影片每两控制步采图（5 Hz），按仿真时间原速播放，中间保持前一帧；原始10 Hz状态完整保留。

## 代码与工作区注意事项

两库当前均在`feature/system1-system0-prototype`，工作区有大量未提交、跨任务修改。本轮没有做提交或推送；先看各库`git status`，不要全量reset、清理、覆盖或把不相关修改一起提交。模型复现优先使用上述冻结源码。

关键实现入口：

- `omi_proj/src/omi_hil_rl/training/hierarchical_insertion/`：`reference.py`、`environment.py`、`randomization.py`、`cli.py`、`intervention.py`。
- `omi_shapeforge/src/omi_shapeforge/sim/`：`initial_pose.py`、`isaac_recovery.py`、`pose_correction.py`。
- `omi_shapeforge/scripts/simulation/`：`run_randomized_retraining.py`、`evaluate_saved_randomized_models.py`，以及`capture_path_ablation_video.py`、`compose_path_ablation_video.py`、`compose_single_correction_demo.py`等展示入口。

当前资产外观线与训练线分开：其他会话的r30夹爪、新光模块／插孔和照明候选未替换本轮冻结WG-r10／OM-r08训练场景。不要为“看起来更新”直接换资产后沿用旧成绩。当前只使用固定夹持、理想GT和腕力，不应宣称真机或滑移恢复已验证。

## 下一位接手者的第一步

先读本页、纪传体和`reboot_handoff/training_complete.json`，根据最新用户指令判断是否已恢复测试；用户明确要求继续测试时，无需再次询问。若还没有，只核对文件／回答进展，保持评估暂停；若已明确恢复，执行独立预检后启动评估。新请求若涉及重新训练、改资产或新增扰动，应另建协议和输出目录，保留本轮完整历史。
