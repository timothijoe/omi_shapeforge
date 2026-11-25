# 仿真领域导航

2026-11-24：[快速配置规则精度回归](evolution/isaac-rule-precision.md)完成。20／5子步各5例均成功；终点横向误差最大0.048／0.059 mm，角度最大0.0048／0.0059°，深度误差均小于0.001 mm。入口、稳定落座、位姿偏移及受阻恢复均核查；规则／判据未调参，物理诊断与带RGB正常轨迹一致。结论限于当前仿真场景，未重训BC／RL。

2026-11-24本窗口已按用户要求收口：[纪传体／控制吞吐总账](evolution/isaac-control-throughput.md) · [编年体／学习与性能交接](../../chronicles/2026-11-24-isaac-performance-window-handoff.md)。建议快速配方为CPU＋原厂IK＋5物理子步＋双渲染子帧＋异步记录，约55 ms完整规则采集周期；最早基线约770 ms，约14倍，包含物理步长与算法变化。代码默认未切换，BC／RL未因提速新增训练成绩；本次仅整理文档。

2026-11-24：[5子步与异步记录对照](evolution/isaac-fast-collection.md)完成。CPU＋原厂IK完整周期约95→75 ms（20→5子步），异步记录后约55 ms，单渲染子帧组合约48 ms；5子步同步／异步均3/3规则通过，1776条异步转移图像完整性核查通过。单子帧仅正常案例，未验证BC／RL；新选项显式启用，默认不变。

2026-11-24：[GPU物理兼容模式](evolution/isaac-gpu-physics.md)已接入并验证。GPU正常与±1 mm受阻恢复3/3通过；原生GPU求解器统计确认启用，但当前单环境＋CPU回读下RPC约111 ms，同批CPU约65 ms，保持CPU默认。可用`--physics-device gpu`显式选择，新GPU执行合同单独登记。

2026-11-24：[完整控制步排查与优化](evolution/isaac-step-profile.md)完成。修复奖励重复测量、SAT小数组循环、腕图复制及无界面仍更新的默认预览；原厂IK＋20子步的RPC从约96 ms降到69～71 ms，三场景物理轨迹／奖励一致。真实双RGB与双渲染子帧保留；新渲染合同明确登记，旧配方可恢复。

2026-11-24：[天机原厂IK已接入](evolution/tianji-native-ik.md)。坐标／单位／TCP适配及逐次回代验收完成；离线500/500，实际PhysX正常与±1 mm受阻恢复3/3通过。worker与训练编排可显式选择原厂后端，新旧合同分开；尚未重训BC／RL或连接真机。

2026-11-24：[50段多样化示范完成](evolution/diverse-demonstrations.md)。40训练＋10验证，准备动作不作专家监督；BC闭环验证0/10、留出0/8；BC未达到预登记门槛，本轮未启动RL。有效完成阶段退出0，启动失败及接续记录保留；仍仅是当前仿真范围。


2026-11-23：[收尾监督补强与新合同重训](evolution/staged-retraining.md)完成。BC无接管0/2、最终RL无接管0/2，接管训练2/3；本轮原生阶段全部退出0。历史143未复现、来源未定，旧结果不重算。

2026-11-23续开发：[在线接管恢复已接入](evolution/online-insertion-recovery.md)。固定三例真实RPC验证通过：正常、±1 mm受阻退回／重对准／重插及交回；任务目标与奖励不随子目标改变。提议方为诊断脚本，未重训或新增学习策略成绩。

当前窗口交接：[Isaac插入、规则反馈RL与阶段收尾](../../chronicles/2026-11-23-isaac-rule-rl-window-handoff.md)，含版本、历史与新结果区别、实际demo、源码和接续事项。

[规则插入与demo收尾](evolution/rule-insertion-review.md) · [阶段编年](../../chronicles/2026-11-23-rule-insertion-review.md)：正常8/8、受阻恢复4/4；固定r10实验，不替代视觉基线或策略成绩。

夹持修订查看后已归档：GC-r01交互窗口已打开，用户反馈“感觉好很多”。本方面统一从[黑胶垫双面接触修订](evolution/wrist-contact-closure.md)阅读，含接触验证、对比图、启动命令及对应编年记录；尚未验证接触插槽后的稳定性。

**最新资产入口：WVA-01「腕部实拍对齐版」已具备。** [能力纪传体](evolution/wrist-visual-wva01.md)说明版本组成／边界／接入；[阶段编年体](chronicles/2026-11-22-wva01-assets.md)记录形成过程；[当前摘要](current.md)区分视觉资产与接触／训练状态。

- [Isaac Sim同源插接与RTX双相机](evolution/isaac-contact.md) · [实验方案](../../design/isaac-contact-experiment.md)。

- [Mesh开发记录](../../mesh-development.md)：几何建模与修订、部件、导出、拓扑／空腔检查及视觉／碰撞接口。

- [仿真器专门记录](../../simulation.md)：当前模型／碰撞／相机／控制、训练结果、运行入口和问题。

- [总章程](charter.md)
- [当前摘要](current.md)
- [能力纪传体](evolution/README.md)
- [阶段编年](chronicles/README.md)
- [长期决定](decisions/README.md)
