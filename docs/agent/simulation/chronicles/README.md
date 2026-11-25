# 仿真阶段记录

- [2026-11-25：真实腕图追溯、1920原图域校核与r16候选](2026-11-25-wrist-photo-refinement.md)

- [2026-11-25：r15新版夹爪Isaac插入视频、UV标志和全组件版本核对](2026-11-25-wva01-isaac-insertion.md)
- [2026-11-24：旧视频r10身份复核与新版接入过程](2026-11-24-video-asset-version-audit.md)

- [2026-11-24：快速5子步规则插入精度核查](../../../chronicles/2026-11-24-isaac-rule-precision.md)

- [2026-11-24：Isaac学习与控制吞吐窗口收尾](../../../chronicles/2026-11-24-isaac-performance-window-handoff.md)：全链路优化、55 ms建议配方、默认值与接续限制。

- [2026-11-24：5子步、后台记录与渲染子帧对照](../../../chronicles/2026-11-24-isaac-fast-collection.md)

- [2026-11-24：GPU物理兼容模式与单环境CPU／GPU对照](../../../chronicles/2026-11-24-isaac-gpu-physics.md)

- [2026-11-24：完整控制步排查、默认预览与重复计算优化](../../../chronicles/2026-11-24-isaac-step-profile.md)

- [2026-11-24：天机原厂IK适配与PhysX闭环验证](../../../chronicles/2026-11-24-tianji-native-ik.md)

> 本机迁移提示（2026-11-24）：运行资源实体已迁至 `/data/shapeforge/runtime`；本文中的 `/data/omi_runtime` 是保留的兼容入口，指向同一份内容。历史阶段正文保留当时记录。目录映射与恢复要求见[当前资源契约](../../interfaces/local-resources.md)。

- [2026-11-23本窗口交接：Isaac插入与规则反馈RL](../../../chronicles/2026-11-23-isaac-rule-rl-window-handoff.md)

- [2026-11-23：规则插入成功率、demo展示与收尾](../../../chronicles/2026-11-23-rule-insertion-review.md)

- [2026-11-23：入口严格、内部容错任务合同](../../../chronicles/2026-11-23-staged-insertion-contract.md)

- [2026-11-23：顺滑通道候选BC／规则反馈SAC重训](../../../chronicles/2026-11-23-isaac-smooth-retraining.md)

- [2026-11-23：入口受阻、内部顺滑的碰撞与控制对照](2026-11-23-smooth-guide-contact.md)

- [2026-11-22：纠正装配间隙并建立双胶垫接触](2026-11-22-wrist-contact-closure.md)

- **最新资产阶段：[2026-11-22：仿真视觉资产形成并固定为WVA-01](2026-11-22-wva01-assets.md)**，含r09～r15开发顺序、用户接受、验证和接续范围。

- [2026-11-22：光模块银灰材质独立修订](../../../chronicles/2026-11-22-module-material-r06.md)

- [2026-11-22：混合腕部图像反馈与黑色接触面修正](../../../chronicles/2026-11-22-hybrid-wrist-contact-review.md)

- [2026-11-21：视频参考腕部相机与夹爪](../../../chronicles/2026-11-21-wrist-camera-gripper.md)

- [2026-11-21：V4与实测插槽接回MuJoCo](../../../chronicles/2026-11-21-v4-measured-simulation.md)

- [2026-11-21：V4-r05「双窗尾槽版」命名、暂定采用及完整演进](../../../chronicles/2026-11-21-v4-double-window-baseline.md)

- [2026-11-21：V4-r05移除上部胶件误填充](2026-11-21-v4-empty-windows-r05.md)

- [2026-11-21：V4-r04端面比例修正落地](2026-11-21-v4-front-r04.md)

- [2026-11-21：V4双脚胶件、三个金属片与高度下沉纠正](2026-11-21-v4-plug-height.md)

- [2026-11-21：V4尾端上侧长方形缺口](2026-11-21-module-v4.md)

- [2026-11-21：独立实测截面光模块与前端斜面](2026-11-21-measured-module.md)

- [2026-11-21：mesh可插入性及实际碰撞检查](2026-11-21-mesh-insertability.md)

- [2026-11-21：规则示范、回放与辅助训练](2026-11-21-rule-demonstrations.md)

- [2026-11-21：双相机仿真与视觉 SAC 全链路](2026-11-21-dual-camera-training.md)

- [2026-11-20：Blender 资产和双引擎场景](2026-11-20-blender-and-scenes.md)
- [2026-11-20：OMI 资源补齐与离线模型预检](2026-11-20-robot-resources-arrived.md)

依据本机现存报告补录于 2026-11-20。永久追加，若后续发现错误，另写勘误并链接原记录；不要把当时的简化条件改写成精细物理验证。

全项目交接及全部数据恢复状态见[跨领域快照](../../../chronicles/2026-11-20-workspace-handoff.md)。

- [2026-11-20：桌面网格查看兼容性修复](2026-11-20-viewer-cpu-fallback.md)

- [2026-11-20：恢复原机 Open3D 原生查看器](2026-11-20-native-mesh-viewer.md)
- [2026-11-20：用户指定 Blender V3 为主线](2026-11-20-blender-v3-primary.md)
- [2026-11-20：插接座后部 RealSense 观测核对](2026-11-20-socket-rear-review.md)
- [2026-11-20：圈选后凸体、原 mesh 与原生深度复核](2026-11-20-socket-original-mesh-and-depth.md)
- [2026-11-20：插接座改用 Open3D 查看](2026-11-20-socket-native-viewer.md)
- [2026-11-20：V3 插入照片、台阶限位及孔宽候选](2026-11-20-v3-insertion-and-width.md)
- [2026-11-20：孔宽与模块宽的双向证据复核](2026-11-20-width-evidence-review.md)
- [2026-11-20：插接座 r04 略放宽候选](2026-11-20-socket-r04-width.md)
- [2026-11-20：真实 URDF 场景和 RL 环境骨架](2026-11-20-robot-rl-mvp.md)
