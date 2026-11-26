# Agent 知识库

- **System1／System0会话交接**：[接手文档](../chronicles/2026-11-26-system1-system0-session-handoff.md)。先核对当前状态与测试暂停指令，勿把旧模型演示当成本轮新模型成绩。

- **System0随机化重训已完成，最终测试暂停**：[纪传体](simulation/evolution/system0-randomized-retraining.md) · [编年体](simulation/chronicles/2026-11-26-system0-randomized-retraining.md) · [重启操作交接](../chronicles/2026-11-26-system0-rl-reboot-handoff.md)。

- [System1 与 System0 最新交接](../chronicles/2026-11-25-system1-system0-handoff.md)：当前先扩充System1接近位置覆盖；区分旧System0冒烟、新60轮视觉模型和九位置诊断。

- [System1 与 System0 独立插接原型](simulation/evolution/hierarchical-insertion.md)：当前实现与验证边界，旧RL默认保留。

- [System1 与 System0 路径条件化插接讨论](../design/system1-system0-path-conditioned-rl-discussion.md)：2026-11-25设计接续，含已核对实现、异步坐标、路径条件与真机奖励边界；不代表新策略能力。

- [2026-11-25：当前点云展示与r11插接视频交接](../chronicles/2026-11-25-pointcloud-video-handoff.md)，汇总腕部重点叠加、完整三维点云、配色、验证和复现。

2026-11-24当前确认：规则精度回归20／5子步均5/5，快速5子步最大终点横向误差约0.059 mm、角度0.0059°、深度误差＜0.001 mm；同一冻结RL网络五回合执行时间462.170→32.644秒，约14倍，但自主成功率新旧均0/5。速度、环境可插入性与策略能力分别记录，默认配置未改；按用户要求保存进展，本次不启动新实验。 [纪传体](simulation/evolution/isaac-rule-precision.md) · [编年体](../chronicles/2026-11-24-isaac-rule-precision.md)。

2026-11-24本窗口已按用户要求收口：[纪传体／控制吞吐总账](simulation/evolution/isaac-control-throughput.md) · [编年体／学习与性能交接](../chronicles/2026-11-24-isaac-performance-window-handoff.md)。建议快速配方为CPU＋原厂IK＋5物理子步＋双渲染子帧＋异步记录，约55 ms完整规则采集周期；最早基线约770 ms，约14倍，包含物理步长与算法变化。代码默认未切换，BC／RL未因提速新增训练成绩；本次仅整理文档。

2026-11-24：[50段多样化示范完成](simulation/evolution/diverse-demonstrations.md)。40训练＋10验证，准备动作不作专家监督；BC闭环验证0/10、留出0/8；BC未达到预登记门槛，本轮未启动RL。有效完成阶段退出0，启动失败及接续记录保留；仍仅是当前仿真范围。


资源定位先读[本地存储与恢复契约](interfaces/local-resources.md)。运行资源实体已位于`/data/shapeforge/runtime/`，导入与交付资料位于同级storage，旧runtime路径保留兼容。见[runtime迁移编年](../chronicles/2026-11-23-runtime-relocation.md)及[此前导入／交付迁移](../chronicles/2026-11-23-storage-layout.md)。

2026-11-23：[收尾监督补强与新合同重训](simulation/evolution/staged-retraining.md)完成。BC无接管0/2、最终RL无接管0/2，接管训练2/3；本轮原生阶段全部退出0。历史143未复现、来源未定，旧结果不重算。

2026-11-23续开发：[在线接管恢复已接入](simulation/evolution/online-insertion-recovery.md)。固定三例真实RPC验证通过：正常、±1 mm受阻退回／重对准／重插及交回；任务目标与奖励不随子目标改变。提议方为诊断脚本，未重训或新增学习策略成绩。

[规则插入收尾／纪传体](simulation/evolution/rule-insertion-review.md) · [编年体](../chronicles/2026-11-23-rule-insertion-review.md)：正常8/8、受阻恢复4/4，保留demo、复现证据及实仿／学习缺项。

感知细网格数据 v1： [纪传体／范围与能力](perception/evolution/grid-perception-data-v1.md) · [编年体／阶段经过](perception/chronicles/2026-11-23-grid-perception-data-v1.md) · [操作与恢复](../../tutorials/grid_perception_data_v1.md)。采样标注已完成，网络训练另行记录。

PCG-01纯几何资产已完成独立导出、可视化和Downloads便携交付，全部记录已补齐：[纪传体／主阅读入口](perception/evolution/pointcloud-geometry-pcg01.md) · [编年体／执行经过](perception/chronicles/2026-11-23-pointcloud-geometry.md)。两个PLY共0.565MB，顶点＋索引数组约0.535MB，ZIP约0.915MB；去掉颜色及指定附件，未改旧资产或替换训练模板。

新增[GC-r01接触版腕部视觉监督训练](perception/evolution/contact-wrist-surface-learning.md)：接触筛选3072帧、25轮微调和同图旧新评估已完成；不改变BC／RL任务，也未验证插槽接触或真机。

最新仿真资产状态已同步：[WVA-01能力纪传体](simulation/evolution/wrist-visual-wva01.md) · [WVA-01阶段编年体](simulation/chronicles/2026-11-22-wva01-assets.md) · [仿真当前摘要](simulation/current.md)。

- [Isaac规则反馈RL运行记录](simulation/evolution/isaac-rule-feedback-rl.md)：链路已运行，独立策略评估0/2。

用户已认可并命名 **[WVA-01「腕部实拍对齐版」](simulation/evolution/wrist-visual-wva01.md)**：当前腕部视觉基线固定WG-r15＋OM-r08及SIM-r06插槽参考场景，保留真实／鱼眼仿真对比和依赖哈希。源mesh、历史版本和既有训练任务不变；接受范围为视觉。

- [WG-r10＋OM-r08的Isaac接入记录](simulation/evolution/wrist-bundle-isaac.md)：已打开完整场景，动态接触和训练另行验证。

复现历史WG-r10腕部／模块视觉成果时，先读[资产接入说明](simulation/evolution/wrist-assets-handoff.md)及[固定版本清单](../../manifests/wrist_visual_asset_handoff_20261122.json)，再按[教程](../../tutorials/reuse_wrist_visual_assets.md)在独立目录复现。该历史组合是WG-r10＋OM-r08；视觉结果与感知标注、接触动力学、训练结果各有范围。

- [Isaac接触峰值与清晰图像复核](simulation/evolution/isaac-contact-visual-review.md)：gentle候选与高分辨率渲染。

- 新增[Isaac Sim同源插接实验](simulation/evolution/isaac-contact.md)，保留MuJoCo基线及所有失败对照。

新采集资料已同步至[本项目docs/data/nov22](../data/nov22/README.md)，后续接续先阅读本机初检，再查采集机器原文快照。

新会话先读[当前进展交接](../chronicles/2026-11-22-simulation-mesh-visual-progress.md)、[当前总览](../current.md)和对应领域现状。根目录[交接文档](../../HANDOFF.md)保留恢复索引；[2026-11-20重启快照](../chronicles/2026-11-20-restart-handoff.md)与[源码基线](../design/source-baseline.md)是历史版本，不能覆盖后续未提交工作。

推荐阅读顺序：[当前总览](../current.md) → [能力总表](../capabilities.md) → 对应领域的 charter/current/evolution → 接口和阶段证据。开始修改前检查分支及未提交工作树。

仿真工作另有可直接阅读的[仿真器专门记录](../simulation.md)，持续同步模型、接触、相机、任务、训练和未完成项；更新仿真进展时同时维护它和领域能力页，不能只追加交接快照。

mesh工作另有[开发专门记录](../mesh-development.md)，记录建模修订、部件与坐标、导出、几何验证和未标定范围，并同步[Blender资产管线](simulation/evolution/asset-pipeline.md)及具体版本能力页。几何开发、碰撞接入和训练结果分别记录，不能只在仿真交接中带过。

| 领域 | 导航 | 当前能力 |
| --- | --- | --- |
| perception | [感知](perception/README.md) | 双目／配准与无marker结构线原型；真实精细遮挡位姿尚未通过 |
| simulation | [仿真](simulation/README.md) | 独立接触资产、真实URDF规则循环、双相机及小样本自主策略成功 |
| interfaces | [稳定边界](interfaces/README.md) | CLI、配置、格式、资源及外部系统 |

资产编辑采用Blender；本轮用户暂定外观基线为V4-r05「双窗尾槽版」，后续从该版另存新修订。V3和旧资产保留，V2用于辅助对比；先查看[资产版本](../asset-versions.md)及[完整开发记录](../chronicles/2026-11-21-v4-double-window-baseline.md)。

维护遵循[文档制度](../design/documentation-system.md)。能力事实写纪传体，已验证阶段追加编年，架构决定递增编号；先核实证据，再更新摘要。

未完成范围：完整视频在线重建、59帧尺寸重新估计、实物机器人／夹爪接入、真实接触抓取与自碰撞校准、可靠的真实遮挡位姿、Isaac GUI验收（RTX双相机已在同源插接实验验证）及实物精度认证。仿真URDF和新接触资产已接入，不再把历史“未接入机器人”当作当前仿真状态。来源及恢复见[清单说明](../../manifests/README.md)。
