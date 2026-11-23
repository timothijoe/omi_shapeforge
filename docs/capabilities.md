# 项目能力总表

此表按证据范围分类，不以“文件存在”代替运行验证。

| 能力 | 实现与已验证状态 | 主要限制／证据入口 |
| --- | --- | --- |
| 有边界的感知细网格数据 v1 | 16490候选逐项检查，16251物理有效图；严格三变量主集14549张，实际位姿／mask／模板点云标注和状态重放通过 | 只含孔口前静态样本，分层覆盖而非九变量全组合；本阶段未重训，未验收真机；[纪传体](agent/perception/evolution/grid-perception-data-v1.md) · [编年体](agent/perception/chronicles/2026-11-23-grid-perception-data-v1.md) |
| PCG-01纯几何交付 | 模块15件／插口上部112件，原几何不简化；无颜色PLY／NPZ、灰色可视化与相对路径ZIP交付，回读及哈希检查通过 | 去拉环／阴影块／大支架；未新做配准或替换旧模板；[纪传体](agent/perception/evolution/pointcloud-geometry-pcg01.md) · [编年体](agent/perception/chronicles/2026-11-23-pointcloud-geometry.md) |
| GC-r01双黑胶垫夹持 | 自由模块＋双指闭合；5例重力保持／22.36 mm移动／释放及半步长通过，可见表面接触核对 | 局部接触场景、试验质量／摩擦，插槽碰撞关闭，非机器人插入／训练验收；[记录](agent/simulation/evolution/wrist-contact-closure.md) |
| WVA-01仿真视觉资产（用户已接受） | WG-r15相机／夹爪49件、OM-r08模块17件、SIM-r06插槽参考场景；导出／MuJoCo加载与开合、鱼眼实拍对比通过；677个依赖哈希已核对 | 视觉基线，未认证尺寸／标定／真实抓取，未将当前r10训练成绩迁入；[纪传体](agent/simulation/evolution/wrist-visual-wva01.md) · [编年体](agent/simulation/chronicles/2026-11-22-wva01-assets.md) |
| Isaac规则反馈RL | 两路实际RGB→规则示范→BC→接管SAC→检查点续训→无接管评估已运行；Critic224/Actor96次更新 | 接管下2/3、独立策略0/2；冻结编码器/小样本，非真人或真机验收；[记录](agent/simulation/evolution/isaac-rule-feedback-rl.md) |
| Isaac接触与图像候选 | gentle三初态及半步长到位/退出、10 Hz采样门控通过；实际512双相机与40.6秒高清视频 | 子步瞬时峰值仍达18.8 N，2次工具会话收尾143；未实物/成像标定；[记录](agent/simulation/evolution/isaac-contact-visual-review.md) |
| V4与实测插槽接触仿真 | SIM-r06净孔18.8 × 8.8 mm、正面窄边暂按6.9 mm；局部／反例／半步长及机械臂规则3/3通过，两路图像有效 | 旧BC／RL直接迁移各0/2，未重训；内部支撑与接触参数未实物标定；[新尺寸记录](agent/simulation/evolution/measured-v4-simulation.md) |
| 光模块mesh建模与修订 | V4-r05「双窗尾槽版」暂定采用；18件、16实体与2外观折缝；拓扑、280点空腔、导出重开及胶件31点静态拔出检查通过 | 局部尺寸仍含估计；未生成V4新碰撞代理或验证真实定位收益；[Mesh开发](mesh-development.md) |
| 自主视觉接触插入试验 | 旋转加权BC及20回合接管RL后，关闭接管的两批8初态中BC 7/8、第一轮RL 8/8 | 固定仿真／小范围初态，小样本；另一RL组合0/4，不能保证10＋20普遍成功；[新汇总](chronicles/2026-11-21-contact-policy-improvement.md) |
| 旧独立接触仿真资产 | SIM-r03局部、负例、步长及机械臂规则循环通过，旧几何训练和续训已接通 | 固定附着、等效触点未实物标定；后续旧几何BC7/8、RL8/8不能代表新尺寸成绩；[能力](agent/simulation/evolution/contact-simulation-asset.md) |
| mesh可插入性检查 | 原Blender重新导出、拓扑／三角面／包含／实际MuJoCo接触检查通过执行；碰撞派生副本和孔形分解已保存 | 完整插入验收失败：约4.212mm被入口弹片挡住；主体通路仅为诊断；[报告](agent/simulation/evolution/mesh-insertability.md) |
| 规则示范与视觉辅助训练 | 16段预插入规则轨迹／824条动作，实际双RGB、独立 scripted 来源、视觉BC及混合SAC通过 | 老师读仿真真值，policy仍只看RGB；留出闭环未成功；[能力](agent/simulation/evolution/rule-demonstrations.md) |
| 双相机视觉训练 | 真实 URDF 预插入环境接入 OMI；两路 RGB、十帧历史、replay、SAC 更新、权重回用和续训通过；300 条／20 次更新 | 固定附着、无接触，state／tactile padding；评估未成功；[能力](agent/simulation/evolution/visual-training.md) |
| 工作区诊断 | CLI 已运行，检查路径、解释器及 Git 信息 | 不验证 GPU、动态库或全部资产；[接口](agent/interfaces/cli.md) |
| 样例进程调度 | 两个 smoke 与 MuJoCo 已经 v1 共用运行层实际执行；14 项控制层测试通过 | 三项新工作流的执行、内容检查与限定验收通过；尚未推送或从零重编译；[能力](agent/perception/evolution/stereo-and-backends.md) |
| 双目深度与点云 | 官方 960×540 样例，约 47 万点；两次独立推理数组一致 | 不是光模块原始录包或外部深度真值验收 |
| BundleSDF 基础组件 | C++ 绑定、CUDA 编码／采样、梯度、Kaolin、Warp、LoFTR 检查通过 | 不代表完整视频跟踪和 mesh 重建通过 |
| 光模块 CPU 配准 | 10 万点样例中已确认区域的刚体配准及独立检查通过 | 已知 ROI／方向先验；残差不是真实位姿误差；[能力](agent/perception/evolution/confirmed-registration.md) |
| Blender 保存模型 | 四份模型重开、内嵌资源／单位检查与一张后台渲染通过 | 照片初稿未定标；照片／尺寸／槽的完整重新构建未在本机复验 |
| 外观mesh导出 | V3历史导出15件；当前V4-r05为18件，提供Blender、整件与分组件OBJ／MTL、GLB，重开核对通过 | 材质／柔性不是实物标定；V4外观导出不等于已接入MuJoCo碰撞；[能力](agent/simulation/evolution/asset-pipeline.md) |
| MuJoCo 场景 | 单模块及 2×2：加载、240 步、落台稳定、EGL 图像通过 | 包围盒碰撞，20 g／摩擦 0.6 为假设；[能力](agent/simulation/evolution/engine-scenes.md) |
| Isaac Sim场景与插接 | 5.1.0/PhysX CPU同源SIM-r06：局部7项、机械臂3初态规则循环及RTX双相机通过 | 规则验收不含学习10 N门控，seed7已超限；未训练/GUI/实物标定；[能力](agent/simulation/evolution/isaac-contact.md) |
| 机械臂与夹爪资产 | 完整厂商 URDF 已导入 MuJoCo；圆桌／插接资产参考场景、6D TCP→IK→伺服的小幅到达与 Gym 接口检查通过 | 接触关闭、尚未抓取模块或执行插入，工具／惯量／限位未实物校准；[资源](agent/simulation/evolution/robot-assets.md) · [计划](design/robot-rl-development-plan.md) |
| 数据／环境归档恢复 | 9 个包均已解压，02／03 全部成员恢复和代表数据检查通过，04 链接完整 | 04 未重定位或运行验收；[数据与回放](agent/perception/evolution/data-and-replay.md) |
| V2 冻结几何回放 | 01 包恢复后实际执行，64 个源文件校验及粗／细几何比较通过 | 不从原始传感器重新估计；[迁移验证](../manifests/transfer_validation.json) |
| 全场景自动识别、59 帧尺寸重估、完整在线重建 | 当前项目未验收 | 数据已恢复，仍需入口适配和逐阶段重跑／独立验收 |
| 真机控制和生产操作 | 本项目未接入 | 不把其他仓库的控制记录当成本项目能力 |

历史阶段见[感知编年](agent/perception/chronicles/README.md)和[仿真编年](agent/simulation/chronicles/README.md)。
