# 仿真能力索引
- [随机插口与远初态重训（纪传体）](system0-randomized-retraining.md)：当前数据、四模型训练成果、最终权重与能力限制；RL已完成，留出测试暂停。

- [System0初始偏移与倾斜鲁棒性](system0-initial-pose-robustness.md)：夹爪中心±2 mm、俯仰／偏航±2°，冻结模型真实测试与四段视频。

- [System0在线规则干预](hierarchical-intervention.md)：真实恢复接口、执行动作replay、续训与独立评估；初轮自主插接尚未通过。


- [System1训练与路径可视化](system1-path-visualization.md)：预测位姿经规则解码，独立测试和最差帧展示。

- [System1 与 System0 独立插接原型](hierarchical-insertion.md)：GT／噪声／学习型参考、直接动作与腕力观测。

2026-11-24：[快速配置规则精度回归](isaac-rule-precision.md)完成。20／5子步各5例均成功；终点横向误差最大0.048／0.059 mm，角度最大0.0048／0.0059°，深度误差均小于0.001 mm。入口、稳定落座、位姿偏移及受阻恢复均核查；规则／判据未调参，物理诊断与带RGB正常轨迹一致。结论限于当前仿真场景，未重训BC／RL。

2026-11-24本窗口已按用户要求收口：[纪传体／控制吞吐总账](isaac-control-throughput.md) · [编年体／学习与性能交接](../../../chronicles/2026-11-24-isaac-performance-window-handoff.md)。建议快速配方为CPU＋原厂IK＋5物理子步＋双渲染子帧＋异步记录，约55 ms完整规则采集周期；最早基线约770 ms，约14倍，包含物理步长与算法变化。代码默认未切换，BC／RL未因提速新增训练成绩；本次仅整理文档。

2026-11-24：[5子步与异步记录对照](isaac-fast-collection.md)完成。CPU＋原厂IK完整周期约95→75 ms（20→5子步），异步记录后约55 ms，单渲染子帧组合约48 ms；5子步同步／异步均3/3规则通过，1776条异步转移图像完整性核查通过。单子帧仅正常案例，未验证BC／RL；新选项显式启用，默认不变。

2026-11-24：[GPU物理兼容模式](isaac-gpu-physics.md)已接入并验证。GPU正常与±1 mm受阻恢复3/3通过；原生GPU求解器统计确认启用，但当前单环境＋CPU回读下RPC约111 ms，同批CPU约65 ms，保持CPU默认。可用`--physics-device gpu`显式选择，新GPU执行合同单独登记。

2026-11-24：[完整控制步排查与优化](isaac-step-profile.md)完成。修复奖励重复测量、SAT小数组循环、腕图复制及无界面仍更新的默认预览；原厂IK＋20子步的RPC从约96 ms降到69～71 ms，三场景物理轨迹／奖励一致。真实双RGB与双渲染子帧保留；新渲染合同明确登记，旧配方可恢复。

2026-11-24：[天机原厂IK已接入](tianji-native-ik.md)。坐标／单位／TCP适配及逐次回代验收完成；离线500/500，实际PhysX正常与±1 mm受阻恢复3/3通过。worker与训练编排可显式选择原厂后端，新旧合同分开；尚未重训BC／RL或连接真机。

2026-11-24：[50段多样化示范完成](diverse-demonstrations.md)。40训练＋10验证，准备动作不作专家监督；BC闭环验证0/10、留出0/8；BC未达到预登记门槛，本轮未启动RL。有效完成阶段退出0，启动失败及接续记录保留；仍仅是当前仿真范围。

2026-11-24：[控制吞吐与四档子步对照](isaac-control-throughput.md)完成。原实现每动作500／20子步约734／222 ms；等价FK缓存后20子步约117 ms。新批量入口默认20，原50段研究仍保留500合同；原生异常和限定验证范围另记。


2026-11-23：[收尾监督补强与新合同重训](staged-retraining.md)完成。BC无接管0/2、最终RL无接管0/2，接管训练2/3；本轮原生阶段全部退出0。历史143未复现、来源未定，旧结果不重算。

2026-11-23续开发：[在线接管恢复已接入](online-insertion-recovery.md)。固定三例真实RPC验证通过：正常、±1 mm受阻退回／重对准／重插及交回；任务目标与奖励不随子目标改变。提议方为诊断脚本，未重训或新增学习策略成绩。

- [规则插入成功率、真实RTX demo与阶段收尾](rule-insertion-review.md)

- [入口严格、内部容错：新任务合同与脚本验证](staged-insertion-contract.md)

- [顺滑通道候选的BC／规则反馈RL重训](smooth-guide-retraining.md)

- [入口受阻、内部顺滑的接触候选：局部通过，完整机器人未验收](smooth-guide-contact.md)

- [GC-r01：黑胶垫双面接触、自由模块保持与释放](wrist-contact-closure.md)

- [Isaac规则反馈RL：环境与链路](isaac-rule-feedback-rl.md)

- [WVA-01「腕部实拍对齐版」：用户接受的视觉基线与接入](wrist-visual-wva01.md)

- [WG-r15：DAIMON表面标志](wrist-logo.md)

- [WG-r14：原始实拍比例复核](wrist-tip-photo-review.md)

- [WG-r13：按红线修正银色外侧轮廓](wrist-marked-tip.md)

- [WG-r12：梯形俯视面与胶皮前端齐平](wrist-trapezoid-tip.md)

- [右臂水平停放与人类反馈训练就绪性](right-arm-park-and-hil.md)

- [WG-r10＋OM-r08固定组合接入Isaac](wrist-bundle-isaac.md)

- [WG-r11：银色指尖宽钝头与倒角](wrist-fingertip-chamfer.md)

- [当前腕部／模块视觉资产：其他Agent接入说明](wrist-assets-handoff.md)

- [主体优先：WG-r10内沿与观测修正](wrist-primary-refinement.md) · [OM-r08 U形拉环](module-u-handle.md)

- [Isaac接触峰值与图像清晰度复核](isaac-contact-visual-review.md)

- [固定r09后的位姿、开度、焦距与拉环试验](wrist-pose-study.md)

- [Isaac Sim同源插接与RTX双相机](isaac-contact.md)

- [WG-r09：多视角点云约束的夹爪优化](wrist-pointcloud-refinement.md)

- [WG-r08：镜头安装与参考夹持投影对齐](wrist-alignment.md)

- [WG-r07尺寸与真实腕部相机一致性](wrist-camera-consistency.md)

- [WG-r07：照片轮廓与双峰黄色衬垫修正](wrist-tool-photo-profile.md)

- [WG-r05腕部相机与夹爪精修](wrist-tool-refinement.md)

- [光模块V4-r06独立材质修订](module-material-r06.md)

- [真实夹爪像素＋仿真资产的混合腕部预览](hybrid-wrist-preview.md)

- [视频参考腕部相机与夹爪资产](wrist-camera-gripper.md)

- [V4与实测插槽尺寸接触仿真](measured-v4-simulation.md)

- [Mesh开发专门记录](../../../mesh-development.md) · [Blender资产管线实现](asset-pipeline.md)

- [V4尾端上侧长方形缺口与视频结构补充](module-v4.md)

- [实测截面光模块与下部前端上翘独立mesh](measured-module.md)

- [独立接触仿真资产与训练链路](contact-simulation-asset.md)

- [V3／r04 mesh可插入性和碰撞表示](mesh-insertability.md)

- [规则老师示范与视觉 BC／SAC](rule-demonstrations.md)

- [双相机 MuJoCo → OMI 视觉训练](visual-training.md)

- [Blender 与外观资产管线](asset-pipeline.md)
- [MuJoCo／Isaac 同源场景](engine-scenes.md)
- [机械臂、夹爪与真实夹具资源](robot-assets.md)
