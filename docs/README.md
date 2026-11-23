# 开发文档总目录

当前Isaac实验窗口交接：[插入、规则反馈RL与阶段收尾](chronicles/2026-11-23-isaac-rule-rl-window-handoff.md)。纪传体和编年体均已完成；本交接集中提供状态、证据与恢复入口。

[规则插入阶段收尾：纪传体](agent/simulation/evolution/rule-insertion-review.md) · [编年体](chronicles/2026-11-23-rule-insertion-review.md)：正常8/8、受阻恢复4/4，实际demo已展示；限定规则测试，未新增学习策略成绩。

当前感知任务交接：[三变量采样、细网格数据与后续预训练](chronicles/2026-11-23-perception-grid-pretraining-handoff.md)。含已确认目标、数据入口、验证、历史模型区别、恢复和接续事项；不替代并行资产／控制任务交接。

[感知细网格数据 v1](agent/perception/evolution/grid-perception-data-v1.md)已完成采样与标注审核：
[纪传体／范围与能力](agent/perception/evolution/grid-perception-data-v1.md) · [编年体／阶段经过](agent/perception/chronicles/2026-11-23-grid-perception-data-v1.md) · [操作与恢复](../tutorials/grid_perception_data_v1.md)。本阶段未重训网络。

- [2026-11-23本窗口交接：外观、接触及纯几何交付](chronicles/2026-11-23-mesh-contact-pcg-window-handoff.md)

- [2026-11-23：入口严格、内部容错的新任务合同](agent/simulation/evolution/staged-insertion-contract.md)：保持几何／摩擦，五条脚本行为检查通过；旧成绩不重算，未重训策略。

PCG-01纯几何资产已完成独立导出、可视化和Downloads便携交付，全部记录已补齐：[纪传体／主阅读入口](agent/perception/evolution/pointcloud-geometry-pcg01.md) · [编年体／执行经过](agent/perception/chronicles/2026-11-23-pointcloud-geometry.md)。两个PLY共0.565MB，顶点＋索引数组约0.535MB，ZIP约0.915MB；去掉颜色及指定附件，未改旧资产或替换训练模板。

新增[GC-r01接触版腕部视觉监督训练](agent/perception/evolution/contact-wrist-surface-learning.md)：接触筛选3072帧、25轮微调和同图旧新评估已完成；不改变BC／RL任务，也未验证插槽接触或真机。

- [2026-11-23：顺滑通道候选BC／规则反馈RL重训](agent/simulation/evolution/smooth-guide-retraining.md)：已完成；BC与RL均自主0/4、接管训练4/6，保留失败与实仿对齐缺口。

接触问题已确认并另建[GC-r01黑胶垫双面接触修订](agent/simulation/evolution/wrist-contact-closure.md)：WVA-01原左右间隙约0.046／0.602 mm；新场景以自由模块＋可闭合双指产生真实接触，5种初态及半步长通过保持／移动／释放。源mesh和WVA-01保留；这是局部夹持验证，非插入或训练验收。

最新仿真资产已具备：**WVA-01**。查[当前总览](current.md)、[纪传体](agent/simulation/evolution/wrist-visual-wva01.md)和[编年体](agent/simulation/chronicles/2026-11-22-wva01-assets.md)。

- [Isaac规则反馈RL完整链路与结果](agent/simulation/evolution/isaac-rule-feedback-rl.md)：真实采集、SAC更新、续训与无接管评估；自主插入仍未达标。

用户已认可并命名 **[WVA-01「腕部实拍对齐版」](agent/simulation/evolution/wrist-visual-wva01.md)**：当前腕部视觉基线固定WG-r15＋OM-r08及SIM-r06插槽参考场景，保留真实／鱼眼仿真对比和依赖哈希。源mesh、历史版本和既有训练任务不变；接受范围为视觉。

新增[WG-r15 DAIMON表面标志版](agent/simulation/evolution/wrist-logo.md)：按实拍增加两侧红色图标与黑色字样，朝向相反；49件几何保持r14不变，Blender／GLB与MuJoCo贴图显示检查通过，旧版保留。

新增[WG-r14实拍比例复核候选](agent/simulation/evolution/wrist-tip-photo-review.md)：以原始实物照片收窄前端、缩短根部平段；红线只表达结构。两份银壳修改，前端齐平及其他47件保留；照片比例估计不是尺寸标定。

新增[WG-r13红线轮廓候选](agent/simulation/evolution/wrist-marked-tip.md)：银色外缘改为斜边接根部平段，继承前端齐平，仅修改两份银壳；47件及所有旧版本保留。

新增[WG-r12梯形齐平指尖候选](agent/simulation/evolution/wrist-trapezoid-tip.md)：按用户确认的伸出方向对齐银壳与胶皮前端，包边后退0.2 mm；四边梯形主轮廓、胶皮及间隙保留，旧版不改。

- [右臂水平停放与Isaac人类反馈训练就绪性](agent/simulation/evolution/right-arm-park-and-hil.md)

- [WG-r10＋OM-r08已接入独立Isaac场景](agent/simulation/evolution/wrist-bundle-isaac.md)：固定版本校验、重新挂载、夹指开合与鱼眼观测，旧资产保留。

新增[WG-r11宽钝头倒角候选](agent/simulation/evolution/wrist-fingertip-chamfer.md)：依据实物照片加宽两侧银色指尖前段，保留黑垫、间隙及其他47件；r10原资产和固定交接清单不变。

- **历史WG-r10复现入口**：[腕部／模块视觉资产接入说明](agent/simulation/evolution/wrist-assets-handoff.md) · [可执行复现步骤](../tutorials/reuse_wrist_visual_assets.md) · [固定版本与哈希](../manifests/wrist_visual_asset_handoff_20261122.json)。

新增[WG-r10主体轮廓修正与OM-r08粗补U形拉环](agent/simulation/evolution/wrist-primary-refinement.md)：保留r09相机／夹持变换，只改两侧内沿；最终三单元黄色外缘约10.9→6.2 px、黑臂基本不变，旧任务与资产保留。

- [Isaac接触峰值与清晰图像复核](agent/simulation/evolution/isaac-contact-visual-review.md)：门控测试、同位姿画面对照与新版视频。

此前[固定r09位姿与开度试验](agent/simulation/evolution/wrist-pose-study.md)：镜头微调只改善部分指标，未替换主版本；模块相对位置随单元变化，且当时绿色件缺U形连接，不能仅靠全局相机位姿解决。

- [Isaac Sim同源插接实验](agent/simulation/evolution/isaac-contact.md)：SIM-r06独立USD、PhysX、规则控制与RTX双相机；[方案](design/isaac-contact-experiment.md) · [复现](../tutorials/isaac_contact_insertion.md)。

新增[WG-r09多视角点云约束候选](agent/simulation/evolution/wrist-pointcloud-refinement.md)：r08已完整冻结保留；11视角点云支持修改8件局部mesh，镜头和夹持变换不变，黑臂轮廓改善明显，黄色与相机残差仍保留。

- [WG-r08轮廓误差与mesh／相机／URDF归因](agent/simulation/evolution/wrist-contour-diagnosis.md)。

新增[WG-r08腕部投影对齐候选](agent/simulation/evolution/wrist-alignment.md)：调整镜头安装、同步移动相机壳／短颈和参考夹持变换，夹爪几何保留；4个留出单元选定边缘约16～18→3 px，完整画面和绿色拉环仍未一致。

最新[尺寸与腕部图像核对](agent/simulation/evolution/wrist-camera-consistency.md)：网格尺寸符合建模参数，但真实尺寸未认证；当前针孔与真机不一致，同位姿鱼眼候选仍有黄色区域、掌部遮挡和绿色拉环差异，尚未完成外参／夹持关系校准。

历史阶段的[WG-r07照片轮廓修正版](agent/simulation/evolution/wrist-tool-photo-profile.md)：双峰黄色衬垫、中央凹口与收窄指臂，侧视复核衬垫厚度27→12 mm；49件检查通过，基体／相机保持r06不变，旧资产保留。

历史阶段的[WG-r06黄色衬垫修正版](agent/simulation/evolution/wrist-tool-refinement.md)：按用户反馈去掉偏红色调，49件几何保持r05不变；旧资产保留。

- [腕部相机与夹爪WG-r05精修资产](agent/simulation/evolution/wrist-tool-refinement.md)：四帧双目尺寸参考、49件建模、独立相机／夹爪导出和开合预览。

- [11月22日采集资料本地文档入口](data/nov22/README.md)：备份说明、原项目开发记录、采集操作文档和本机初检结论。

- [11月22日新采集数据接收与初检](chronicles/2026-11-22-new-capture-intake.md)：287组四图全部哈希／PNG检查通过，两段工具MCAP来源与接入限制。

- [2026-11-22完整进展：mesh、材质、真机对比、仿真与训练](chronicles/2026-11-22-simulation-mesh-visual-progress.md)：当前r07无颗粒版、旧版保留、各场景验证结果、问题和下一步。

- [光模块V4-r07纯色银灰材质候选](agent/simulation/evolution/module-material-r06.md)：保留改色、移除颗粒贴图、几何不变校验、同视角真机／新旧材质对照。

- [真实夹爪像素＋仿真资产：当前预览与黑色接触面修正](agent/simulation/evolution/hybrid-wrist-preview.md)：鱼眼内参、真实像素来源、用户反馈与静态验证范围；[2026-11-22进展](chronicles/2026-11-22-hybrid-wrist-contact-review.md)。

- [视频参考腕部相机与夹爪资产](agent/simulation/evolution/wrist-camera-gripper.md)：31件外观、光学位置绑定、握持变换与间隙检查；[MuJoCo交互窗口和视频](../tutorials/wrist_camera_gripper.md)。

- [V4与实测插槽尺寸接触仿真](agent/simulation/evolution/measured-v4-simulation.md)：18.8 × 8.8 mm／窄边6.9 mm候选、代理修正、机械臂3/3与旧策略迁移0/2；[视频和命令](../tutorials/measured_v4_simulation.md)。

- [Mesh开发专门记录](mesh-development.md)：建模与几何修订、18个部件、尺寸／坐标合同、Blender与OBJ／GLB导出、拓扑／空腔检查、碰撞与视觉接口。

- [V4-r05「双窗尾槽版」：暂定基线与完整开发过程](chronicles/2026-11-21-v4-double-window-baseline.md)：用户已暂定采用，记录实测尺寸、r01～r05纠正、验证范围、模型与查看入口。

- [真实视觉位姿与结构特征开发交接](chronicles/2026-11-21-perception-progress-handoff.md)：用户约束、最新四组结构线、失败边界、数据/源码/复现命令及感知范围快照。

- [仿真器专门记录](simulation.md)：直接记录当前资产、碰撞、控制、相机、学习结果和待办，仿真维护优先从这里阅读。

- [当前完整交接：进展、结果、问题和路径](chronicles/2026-11-21-current-progress-handoff.md)：本次统一整理入口，区分最新仿真策略、真实感知和历史阶段。

- [最新汇总：资产数量、成功案例与策略改善实验](chronicles/2026-11-21-contact-policy-improvement.md)：10回合BC＋两组20回合接管RL、无接管测试与新初态复验，包含成功视频及未解决问题。

- [实验前阶段复核：资产数量与当时问题](chronicles/2026-11-21-simulation-status-review.md)：保留旧短试跑的未通过状态及后续实验计划；最新结果看上方交接。

- [独立接触仿真资产与整条训练链路](agent/simulation/evolution/contact-simulation-asset.md)：原mesh不改，新资产通过局部／机械臂规则插入退出；[视频和操作](../tutorials/contact_simulation.md)。原短试跑和后续自主策略成功分别记录。

- [V3／r04 实际 mesh 插入检查](agent/simulation/evolution/mesh-insertability.md)：凸包封孔、拓扑修复、约4.21mm弹片阻挡及主体通路验证；[结果和复现](../tutorials/mesh_insertability.md)。

- [规则示范与三视图回放](agent/simulation/evolution/rule-demonstrations.md)：16 段预插入老师轨迹、视觉 BC 与规则／在线混合训练；[观看和命令](../tutorials/rule_demonstrations.md)。

- [2026-11-21：双相机 MuJoCo → OMI 视觉训练](agent/simulation/evolution/visual-training.md)：已跑通采集、经验池、SAC 更新、权重回用和续训；[启动教程](../tutorials/dual_camera_training.md)。

本目录面向维护者和 Agent；实际操作者优先阅读[教程](../tutorials/README.md)。

- [根目录交接文档](../HANDOFF.md)：接手阅读顺序、工作树、环境与数据位置、验证边界及下一步。
- [历史阶段交接：2026-11-20插接资产与机械臂仿真](chronicles/2026-11-20-robot-simulation-progress.md)：保留当时r04、URDF原型和恢复记录。
- [机械臂仿真与 RL 开发计划](design/robot-rl-development-plan.md)：架构、开发难度及 M0–M4 路线。
- [最新重启交接](chronicles/2026-11-20-restart-handoff.md) · [重启恢复步骤](../tutorials/restart_resume.md)：包含 Blender 会话备份、V3 主线和持久源码备份位置。
- [当前总览](current.md)：全项目唯一的当前摘要，链接领域现状。
- [资产与可视化目录](visual-results.md)：代表图、模型源文件及全部历史图册。
- [光模块资产版本](asset-versions.md)：OM-001当前暂定外观基线、历史版本与场景实例命名。
- [源码基线](design/source-baseline.md)：本地版本、bundle 恢复步骤及对应验证。
- [统一运行合同 v1](agent/interfaces/run-contract.md)：字段、产物、验收与旧报告兼容规则；两个 smoke 与 MuJoCo 已接入；见对应运行验证。
- [全部进展交接快照](chronicles/2026-11-20-workspace-handoff.md)：仓库、环境、数据、复现、仿真、机器人、证据位置和待办。
- [跨领域阶段记录](chronicles/README.md)：保留全局交接历史，后续现状仍看 current。
- [能力总表](capabilities.md)：已实现、已验证、待验证和缺少资源的区别。
- [开发入口](quickstart.md)：环境、代码与验证的阅读顺序。
- [副作用与证据边界](safety.md)：文件、环境、仿真与硬件的边界。
- [设计索引](design/README.md)：仓库分工、依赖方向、文档制度。
- [统一开发方案](design/unified-development.md)：五类工作汇总、分阶段计划和共同交付标准；与已验收能力分开维护。
- [Agent 知识库](agent/README.md)：感知、仿真及稳定接口。
- [资源清单](../manifests/README.md)：资源的来源、恢复方式和验证记录。

[simulation.md](simulation.md) 作为可直接阅读的仿真专门记录持续维护，并与对应能力纪传体同步；[development.md](development.md) 保留开发导航。阶段历史写入各领域的 `chronicles/`，交接快照不代替领域文档更新。
