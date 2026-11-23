# Isaac规则插入：成功率复核与可视化收尾

2026-11-23，本阶段已完成。固定WG-r10＋OM-r08、右臂水平停放，在[入口严格、内部容错合同](staged-insertion-contract.md)下完成预先登记的12例：正常插入8/8，偏移受阻后恢复4/4。用户已观看实际仿真demo并反馈“很好，我看了一下你的这个，比之前好很多”。该反馈针对当前展示效果／行为，不扩展为真机、力学精度或学习策略验收。

## 当前能力与实验范围

输入为`/data/omi_runtime/runs/staged_contact_20261123/robot_transfer`，合同`entry-strict-interior-tolerant-v1`。固定附着模块、六个原生盒碰撞代理、摩擦0.2保持不变；本轮增加真实状态录像和日志，没有重新设计控制器／几何／任务阈值。WG-r10的90份与OM-r08的66份交付文件哈希全部复核通过，原资产和历史结果保留；未升级为WG-r15、WVA-01或GC-r01。

规则利用仿真精确位姿与已知插槽目标，通过IK／PhysX动作执行。正常流程为入口外对准后插入；恢复流程先在入口外施加已知横偏，推进到实体口沿受阻，再保持横偏退回、在外部对准、重新插入。每例仅初始reset一次，恢复中不重置、不瞬移；到达外部子目标不算插入成功。

物理步长0.2 ms，控制间隔100 ms。正常组只在同一名义预插入姿态对7个主动关节施加±0.0005 rad均匀扰动。恢复组是两个种子各测±1 mm已知偏移，只有一次规定的恢复流程。不是未知孔位搜索、大角度、多轮重试或任意初态成功率。本轮跳过到位后的完整拔出。

| 分组 | 预登记案例 | 结果 |
| --- | --- | --- |
| 正常规则插入 | 500、501、502、503、520、521、522、523 | 8/8，100% |
| 偏移受阻后恢复 | 700、701各配+1／−1 mm | 4/4，100% |

两组分别报告，静态`camera_preview`不计入分母。最终深度51.2808～51.2816 mm；4例均在口沿附近受阻，实际退回到−4.9 mm附近，再取得入口资格并稳定到位。12例均有完整轨迹和报告，原生子进程退出码均为0。外层工具会话返回143，原因未诊断；保留该事实，不把外层状态改写成0。

全12例的100 ms平均接触指标最大约0.3774 N，物理子步瞬时峰值最大约17.198 N；两者统计窗口不同，不能只引用较小值声称没有尖峰。它们是接触冲量模长之和对应的仿真代理量，不是真实腕部净力。内部轻擦另见上一阶段的独立测试，本轮正常组不替代侧向持续接触验证。

## 已交付demo与代码

[演示视频](/data/omi_runtime/runs/staged_rule_review_20261123/review/rule_demonstration.mp4)：1440×960、10 fps、104.9秒，已直接打开播放。两条录像在试验前指定为`normal_500`和`recovery_700_plus`，没有按结果挑选种子。左侧插口近景、右侧机械臂全景与腕部鱼眼ROI同帧展示，HUD记录阶段、深度、偏差、接触指标及入口资格；右臂保持水平避让。

动作帧来自实际PhysX运行中的RTX渲染；每个控制步记录真实关节位置、速度、TCP及目标。渲染不推进仿真时间，并检查实际关节位置／速度不变。正常与恢复分别保存397／582帧（各含初始帧），另各15帧末尾展示停留；合片增加两张2秒文字标题卡，标题和停留帧不算动作／试验样本。保留原始视频、场景、逐帧审计和关键帧，合成来源见`review/video_sources.json`。

入口为`scripts/simulation/probe_smooth_contact.py --render`，录像器为`src/omi_shapeforge/sim/isaac_demo_recorder.py`。所有12例的12份执行源码哈希一致，逐例源码快照已校验。运行期间应用外观配方前后检查几何摘要不变；鱼眼使用已有内参，尚未认证与真实相机／新采集数据的绑定和成像一致性。控制环境50项测试中14项执行通过、36项因可选资源跳过。

## 证据与复现

运行根为`/data/omi_runtime/runs/staged_rule_review_20261123`。`protocol.json`固定案例与展示选择；`receipts.json`记录原生进程退出；`summary.json`汇总；每例保存`execution.json`、`code_snapshot/`、`report.json`、`trajectory.jsonl`。录像例另有`recording.json`、`render_audit.jsonl`和`demo.mp4`。`summarize.py`可重复做只读输入复核并重建汇总，不启动仿真。

在ShapeForge根目录复现单例时使用新的输出目录：

```bash
env -u CONDA_PREFIX -u CONDA_DEFAULT_ENV -u PYTHONHOME -u PYTHONPATH -u LD_LIBRARY_PATH OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /data/isaac-sim-5.1.0/python.sh -u scripts/simulation/probe_smooth_contact.py --transfer /data/omi_runtime/runs/staged_contact_20261123/robot_transfer --output <新的输出目录> --seed 500 --offset-mm 0 --dt .0002 --skip-final-withdrawal --render
```

恢复演示改为`--seed 700 --offset-mm 1`。精确历史复现应先对照执行源码快照，勿假定未来工作树与本次一致；不要直接重跑固定输出目录的旧批处理。依赖已有Isaac 5.1及本机支持环境，完整参数在每例execution／回执中。[登记清单](../../../../manifests/rule_insertion_review_20261123.json) · [汇总](/data/omi_runtime/runs/staged_rule_review_20261123/summary.json) · [编年体](../../../chronicles/2026-11-23-rule-insertion-review.md)。

## 收尾后仍缺什么

1. **在线恢复仲裁**：把已验证脚本的退回—重对准—重插接入SAC接管状态机，区分固定任务目标和控制子目标。目前不能声称RL自己具备该恢复能力。
2. **实仿语义和物理验证**：明确世界系／左臂基座／TCP动作及SDK实际接受命令的边界；补真实状态、触觉／力、相机预处理与时间延迟对齐。当前仍用仿真真值和简化固定抓持，尚缺完整夹爪—模块—插槽接触、力标定和更广扰动覆盖。
3. **新合同下的学习评估**：采集匹配示范、重训BC及规则反馈RL，并做独立无接管评估与同数据／预算比较。本轮没有训练；[旧合同下BC与RL各0/4](smooth-guide-retraining.md)保持原样，不能用规则8/8替代。真机验证另行开展。

按用户要求本阶段收尾：完成既定批次、保存展示和证据、同步纪传体／编年体，不继续扩大试验或启动训练。
