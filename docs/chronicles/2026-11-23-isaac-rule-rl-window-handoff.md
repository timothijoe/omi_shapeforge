# 2026-11-23：当前窗口交接——Isaac插入、规则反馈RL与阶段收尾

本交接覆盖本窗口的Isaac插接实验、接触判断、BC／规则反馈RL、规则插入复核和demo展示。用户已要求当前阶段收尾，并要求纪传体、编年体及本交接同时保存。**既定实验已经结束，目前没有安排新的训练或扩大测试。** 并行外观资产、GC-r01夹持、PCG-01及感知数据工作各有独立交接，不能混入本窗口成果。

## 接手先读

1. [规则插入纪传体](../agent/simulation/evolution/rule-insertion-review.md)：最新行为、成功率范围、录像、复现与缺项。
2. [规则插入编年体](2026-11-23-rule-insertion-review.md)：实际执行顺序、用户反馈与收尾。
3. [分阶段插入合同](../agent/simulation/evolution/staged-insertion-contract.md)：入口／内部／到位判据、共享实现、力指标含义。
4. [最近一次BC／RL重训](../agent/simulation/evolution/smooth-guide-retraining.md)及[OMI实仿对齐清单](../../../omi_proj/docs/agent/training/evolution/isaac-hil-alignment.md)：学习结果和仍未对齐的语义。
5. [WG-r10＋OM-r08固定交接](../agent/simulation/evolution/wrist-assets-handoff.md)、[固定清单](../../manifests/wrist_visual_asset_handoff_20261122.json)及[复用教程](../../tutorials/reuse_wrist_visual_assets.md)。

纪传体和编年体均已写完，并已同步`docs/current.md`、仿真领域摘要、`docs/simulation.md`、各级索引及资源清单。本交接集中说明接续位置，不替代各能力页的完整事实。

## 用户意图与约束

- 用户希望在仿真中开发可用于真机的训练方法和方案，认可规则接管可以作为反馈来源；数据仍须区分规则示范／规则干预／真人反馈，不能把规则动作标作真人动作。
- 当前Isaac实验明确使用WG-r10＋OM-r08，保留原资产；右臂水平伸向身体右侧，避免遮挡。并行视觉基线WVA-01是WG-r15＋OM-r08，不能自动替换本实验版本；GC-r01自由夹持同样尚未接入本插入任务。
- 期望入口需要严格对准，偏移时会真实受阻，必要时后退重插；正确进入后内部平顺，小幅短时接触不应直接失败。
- 用户希望直接打开展示。已实际打开本轮视频，用户反馈“很好，我看了一下你的这个，比之前好很多”，随后要求收尾。此反馈仅对应展示的外观／行为，不等于真实力学、策略或部署验收。
- 保留历史失败、数据、权重、协议修订与资产。不同碰撞模型／任务合同的成功率不可合并，也不可放宽新判据后重写旧成绩。

## 当前确切结果

| 阶段 | 实际结果 | 如何理解 |
| --- | --- | --- |
| 11月22日初版Isaac规则反馈RL | BC自主0/2、RL自主0/2，接管训练2/3 | 历史碰撞模型与预算；链路跑通不等于策略达标 |
| 11月23日顺滑通道候选重训 | 规则示范5/8；BC自主0/4、最终RL自主0/4；接管训练4/6 | 旧保护合同；BC三例接近到位触发穿透保护，RL均在入口附近失败 |
| 分阶段合同验证 | 5条脚本轨迹通过：对准、正负偏移恢复、半步长、内部轻擦 | 新任务合同；未重训BC／RL |
| 最新规则成功率与demo | 正常8/8，±1 mm偏移恢复4/4；最终深度约51.281 mm | 预登记的小范围规则测试；不代表未知孔位、任意初态或真机成功率 |

最近重训BC执行3000次更新、按验证误差选1700步；Critic1664次（含128预热）、Actor768次。在线1966条：策略1128、规则838、真人0。6回合训练含接管4/6，最终无接管评估0/4；续训与独立重载已验证。原成功示范配额4训练＋2验证未满足，采集退出1；学习之前保存原协议并修订为4＋1，失败仍保留。详细证据在重训纪传体，不把修改配额写成原协议成功。

最新规则组正常种子500～503、520～523，只施加主动关节±0.0005 rad小扰动；恢复种子700、701各配±1 mm。四条恢复均实际受阻、保持偏移退回约−4.9 mm、外部对准、重新插入；每例仅开始reset一次，外部子目标从未算任务成功。本轮没有测试到位后的完整拔出。

最新12个原生子进程均退出0、报告／轨迹完整；外层工具会话返回143，原因未诊断，须分别记录。全12例执行源码哈希一致，原WG-r10的90份、OM-r08的66份交付文件复核通过；控制测试14项执行通过、36项因可选资源跳过。平均接触指标最高约0.3774 N，子步峰值最高约17.198 N；不能只报告均值来宣称没有瞬时尖峰。

## 模型和任务判断现在是什么

当前输入是`/data/omi_runtime/runs/staged_contact_20261123/robot_transfer`。它从顺滑候选r06另存，视觉与碰撞几何、摩擦0.2保持不变，采用固定附着模块和六个原生盒碰撞代理。不是完整真实双指接触抓取模型。

新合同为`entry-strict-interior-tolerant-v1`，Isaac学习客户端对应奖励合同`isaac-staged-contact-terminal-potential-v2`。入口在深度1～5 mm内需横偏<0.15 mm、角度<0.003 rad、连续3样本合格，深度达到5 mm才取得内部资格；深度超过6 mm仍未合格则失败，退回1 mm以下须重新取得资格。入口100 ms接触均值>5 N连续3次、内部>20 N连续5次终止；保留大异常、接触点穿透及控制采样几何重叠检查。到位要求资格、姿态／深度、肩部接触及连续稳定共同满足。

共享判断在`omi_proj/src/omi_hil_rl/hil/insertion_task.py`，不依赖ROS／Isaac。力信号明确为`simulation_contact_impulse_norm_sum_mean`，是冲量模长之和对应指标，不是真实腕部净力；现有阈值仅是仿真假设。控制时刻盒体重叠诊断不是物理微步全过程最大值。

规则使用仿真精确位姿和已知目标。脚本恢复流程已经验证，但**在线SAC接管仲裁尚未接入完整退回—重对准—重插状态机**；共享`recovery_required`信号不等于RL已经学会恢复。旧策略state／tactile仍有零填充，真机观测／动作／执行回执语义尚未完全对齐。

## 产物、录像与恢复入口

| 内容 | 固定位置 |
| --- | --- |
| 最新规则批次 | `/data/omi_runtime/runs/staged_rule_review_20261123/` |
| 分阶段任务与输入包 | `/data/omi_runtime/runs/staged_contact_20261123/` |
| 最近BC／RL重训 | `/data/omi_runtime/runs/isaac_smooth_retrain_20261123/` |
| 前一顺滑碰撞候选 | `/data/omi_runtime/runs/smooth_guide_20261122/r06/robot_transfer/` |
| 原始Isaac RL试验 | `/data/omi_runtime/runs/isaac_rl_20261122/` |

[当前demo](/data/omi_runtime/runs/staged_rule_review_20261123/review/rule_demonstration.mp4)为1440×960、10 fps、104.9秒。试验前指定正常500和恢复700/+1 mm，非结果挑选。三视图分别是插口近景、机械臂全景、腕部鱼眼ROI；动作帧来自实际PhysX＋RTX，渲染时核验仿真时间及真实关节位置／速度不变。正常／恢复分别397／582个采集帧，各加15帧展示停留，合片再加两张2秒标题卡；展示帧不算动作样本。

交接核查时ffplay仍播放上述视频，PID为4043477、标题为`Isaac rule demo: normal insertion and blocked-entry recovery`。PID仅是当时状态，后续须重新检查，不能盲目复用或终止同号进程。恢复展示可直接打开上述MP4，无需重新跑仿真；GUI启动遵循工具环境审批规则。用户未要求关闭播放器。

最新运行根内：`protocol.json`固定案例；`receipts.json`与`suite_complete.json`记录12/12结束；`summary.json`汇总；`summarize.py`校验并重建汇总；每例有`execution.json`、`code_snapshot/`、`trajectory.jsonl`、`report.json`。录像例另有`demo.mp4`、`recording_scene.usda`、`recording.json`、`render_audit.jsonl`；合片来源在`review/video_sources.json`。静态`camera_preview`明确排除在试验分母外。

机器登记分别是[规则复核](../../manifests/rule_insertion_review_20261123.json)、[分阶段合同](../../manifests/staged_contact_20261123.json)、[最近重训](../../manifests/isaac_smooth_retrain_20261123.json)。完整复现命令在规则纪传体；再次试验必须另建输出目录，先核对执行源码快照，不直接重跑指向旧目录的`run_suite.py`。

## 代码位置、环境与工作树

ShapeForge负责仿真与编排：`scripts/simulation/build_staged_contact_candidate.py`生成独立新合同输入；`probe_smooth_contact.py`执行规则探针及录像；`isaac_rl_worker.py`桥接学习；`src/omi_shapeforge/sim/isaac_contact_runtime.py`实现运行与统计；`box_overlap.py`做控制采样盒几何诊断；`isaac_demo_recorder.py`保存真实状态画面。本轮demo主要新增录像器、`--render`／`--preview-only`和真实关节日志。

OMI共享侧：`src/omi_hil_rl/hil/insertion_task.py`负责阶段判断；`hil/intervention_metrics.py`区分干预段、交回与任务成功；`training/isaac_client.py`管理Isaac客户端合同。Actor／SAC／经验／检查点已有复用，不能因此宣称真实观测和动作执行边界已统一。

本机Isaac为`/data/isaac-sim-5.1.0/python.sh`，支持环境在`/data/omi_runtime/envs/isaac_contact_support`；学习环境在`/data/omi_runtime/envs/omi_sim_train`，网格／绘图环境在`/data/omi_runtime/envs/omi_mesh_audit`，轻量编排检查使用ShapeForge `.venv`。原生Isaac启动需清理继承的CONDA、PYTHONPATH和LD_LIBRARY_PATH，具体命令以纪传体为准。

交接时ShapeForge分支`feature/isaac-contact-insertion`，HEAD为`66ff11720e5dc4327041d709b661dec73c83f605`；OMI分支`feature/shapeforge-vision-training`，HEAD为`963a7c29f8e39bff59ba4eb285693976b224961e`。两仓库都有大量未提交／未跟踪开发内容和并行工作，**HEAD不足以恢复实际实验源码**，须结合逐例快照和清单。不要reset、clean、切换覆盖或整树提交其他工作。本窗口未执行提交／推送；原始产物留在`/data`，不纳入Git。

## 后续讨论与建议顺序

当前已收尾，以下是待办，尚未执行：

1. 明确真机可获得的观测和动作合同：世界系／左臂基座／TCP、SDK实际接受命令、相机时间／预处理、状态／触觉／力，以及奖励／终止含义。
2. 将脚本恢复迁入在线接管状态机；保持固定任务目标与控制子目标分离，不用中途reset拼接成功，不把退到入口外标为任务完成。
3. 扩充真实夹持、插槽接触与力学校验，以及更大姿态／位置误差和扰动覆盖；不能仅凭当前8＋4例发布一般成功率。
4. 冻结新合同后采集新示范，开展同数据／同预算BC与反馈RL比较，再做独立无接管评估；旧合同经验和新合同经验不能无说明混用。真机验证单独安排。

下一窗口先确认用户希望推进哪一项。当前请求只是交接归档，不能据此自动开始新训练、替换资产或连接真机。用户长期意图是可迁移的研发平台，而非仅提高单次仿真演示分数。
