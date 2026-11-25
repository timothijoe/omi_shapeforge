# 仿真器记录：模型、接触、相机与训练

2026-11-25：[System1与System0当前交接](chronicles/2026-11-25-system1-system0-handoff.md)集中记录新独立原型、理想腕部六维力、旧流程720步兼容对照、60轮System1训练与九位置泛化缺口。当前采用path参考、下层自主推进／倒退；三类旧System0评估均失败，新上层未重做组合评估。

2026-11-24当前确认：规则精度回归20／5子步均5/5，快速5子步最大终点横向误差约0.059 mm、角度0.0059°、深度误差＜0.001 mm；同一冻结RL网络五回合执行时间462.170→32.644秒，约14倍，但自主成功率新旧均0/5。速度、环境可插入性与策略能力分别记录，默认配置未改；按用户要求保存进展，本次不启动新实验。 [纪传体](agent/simulation/evolution/isaac-rule-precision.md) · [编年体](chronicles/2026-11-24-isaac-rule-precision.md)。

2026-11-24：[快速配置规则精度回归](agent/simulation/evolution/isaac-rule-precision.md)完成。20／5子步各5例均成功；终点横向误差最大0.048／0.059 mm，角度最大0.0048／0.0059°，深度误差均小于0.001 mm。入口、稳定落座、位姿偏移及受阻恢复均核查；规则／判据未调参，物理诊断与带RGB正常轨迹一致。结论限于当前仿真场景，未重训BC／RL。

2026-11-24本窗口已按用户要求收口：[纪传体／控制吞吐总账](agent/simulation/evolution/isaac-control-throughput.md) · [编年体／学习与性能交接](chronicles/2026-11-24-isaac-performance-window-handoff.md)。建议快速配方为CPU＋原厂IK＋5物理子步＋双渲染子帧＋异步记录，约55 ms完整规则采集周期；最早基线约770 ms，约14倍，包含物理步长与算法变化。代码默认未切换，BC／RL未因提速新增训练成绩；本次仅整理文档。

2026-11-24：[5子步与异步记录对照](agent/simulation/evolution/isaac-fast-collection.md)完成。CPU＋原厂IK完整周期约95→75 ms（20→5子步），异步记录后约55 ms，单渲染子帧组合约48 ms；5子步同步／异步均3/3规则通过，1776条异步转移图像完整性核查通过。单子帧仅正常案例，未验证BC／RL；新选项显式启用，默认不变。

2026-11-24：[CPU完整控制周期核查](agent/simulation/evolution/isaac-step-profile.md)：当前规则采集周期约90.6 ms＝决策1.7＋step65.0＋记录23.6＋整理0.3 ms；记录中每步4次fsync共约16.5 ms，图像捕获每步触发4次Kit应用更新。此次只做测量，未改变生产行为；与此前step RPC口径分开。

2026-11-24：[GPU物理兼容模式](agent/simulation/evolution/isaac-gpu-physics.md)已接入并验证。GPU正常与±1 mm受阻恢复3/3通过；原生GPU求解器统计确认启用，但当前单环境＋CPU回读下RPC约111 ms，同批CPU约65 ms，保持CPU默认。可用`--physics-device gpu`显式选择，新GPU执行合同单独登记。

2026-11-24：[完整控制步排查与优化](agent/simulation/evolution/isaac-step-profile.md)完成。修复奖励重复测量、SAT小数组循环、腕图复制及无界面仍更新的默认预览；原厂IK＋20子步的RPC从约96 ms降到69～71 ms，三场景物理轨迹／奖励一致。真实双RGB与双渲染子帧保留；新渲染合同明确登记，旧配方可恢复。

2026-11-24：[天机原厂IK已接入](agent/simulation/evolution/tianji-native-ik.md)。坐标／单位／TCP适配及逐次回代验收完成；离线500/500，实际PhysX正常与±1 mm受阻恢复3/3通过。worker与训练编排可显式选择原厂后端，新旧合同分开；尚未重训BC／RL或连接真机。

2026-11-24：[50段多样化示范完成](agent/simulation/evolution/diverse-demonstrations.md)。40训练＋10验证，准备动作不作专家监督；BC闭环验证0/10、留出0/8；BC未达到预登记门槛，本轮未启动RL。有效完成阶段退出0，启动失败及接续记录保留；仍仅是当前仿真范围。

2026-11-24：[控制吞吐与四档子步对照](agent/simulation/evolution/isaac-control-throughput.md)完成。原实现每动作500／20子步约734／222 ms；等价FK缓存后20子步约117 ms。新批量入口默认20，原50段研究仍保留500合同；原生异常和限定验证范围另记。


> 本机迁移提示（2026-11-24）：运行资源实体已迁至 `/data/shapeforge/runtime`；本文中的 `/data/omi_runtime` 是保留的兼容入口，指向同一份内容。目录映射与恢复要求见[当前资源契约](agent/interfaces/local-resources.md)。

2026-11-23：[收尾监督补强与新合同重训](agent/simulation/evolution/staged-retraining.md)完成。BC无接管0/2、最终RL无接管0/2，接管训练2/3；本轮原生阶段全部退出0。历史143未复现、来源未定，旧结果不重算。

2026-11-23续开发：[在线接管恢复已接入](agent/simulation/evolution/online-insertion-recovery.md)。固定三例真实RPC验证通过：正常、±1 mm受阻退回／重对准／重插及交回；任务目标与奖励不随子目标改变。提议方为诊断脚本，未重训或新增学习策略成绩。

2026-11-23：[规则插入与实际demo收尾](agent/simulation/evolution/rule-insertion-review.md)：预登记正常8/8、恢复4/4，原生进程均退出0；外层工具143另记。三视图录像已打开并获用户正面反馈；该批次未重训且当时未含在线恢复；后续接入见上方记录，实仿对齐仍待完成。

2026-11-23新增[分阶段插入合同](agent/simulation/evolution/staged-insertion-contract.md)：入口须先通过对准资格，内部按接触均值／持续时间判定。几何与摩擦保持不变；五条脚本轨迹完成新判据，旧BC／RL成绩不改，未重训。脚本恢复验证与在线RL恢复仲裁仍分开。

新增[GC-r01接触版腕部视觉监督训练](agent/perception/evolution/contact-wrist-surface-learning.md)：接触筛选3072帧、25轮微调和同图旧新评估已完成；不改变BC／RL任务，也未验证插槽接触或真机。

2026-11-23新增[入口受阻、内部顺滑接触候选](agent/simulation/evolution/smooth-guide-contact.md)：连续通道／止挡、真实退回纠偏探针、接触方向统计和目标过渡对照。局部检查通过，但完整机器人仍有瞬时穿透越限，尚未重训BC／RL。

夹持修订查看后已归档：GC-r01交互窗口已打开，用户反馈“感觉好很多”。本方面统一从[黑胶垫双面接触修订](agent/simulation/evolution/wrist-contact-closure.md)阅读，含接触验证、对比图、启动命令及对应编年记录；尚未验证接触插槽后的稳定性。

接触问题已确认并另建[GC-r01黑胶垫双面接触修订](agent/simulation/evolution/wrist-contact-closure.md)：WVA-01原左右间隙约0.046／0.602 mm；新场景以自由模块＋可闭合双指产生真实接触，5种初态及半步长通过保持／移动／释放。源mesh和WVA-01保留；这是局部夹持验证，非插入或训练验收。

## 最新仿真资产状态：WVA-01已具备

已具备用户接受的**WVA-01「腕部实拍对齐版」仿真视觉资产**：r15相机／夹爪、r08光模块、SIM-r06插槽参考场景，以及可加载的MuJoCo场景和真实腕部／仿真鱼眼对比。资产本体与版本快照保存在外部目录，固定清单记录路径和哈希；后续修改另存版本。

本版完成视觉几何、导出、加载、开合和静态成像验证。已有插接碰撞资产和BC／RL实验另有各自版本；当前r10的Isaac训练并未自动升级到WVA-01，新版没有新增接触抓取或自主插入成功结论。

[纪传体：版本与模块能力](agent/simulation/evolution/wrist-visual-wva01.md) · [编年体：阶段经过](agent/simulation/chronicles/2026-11-22-wva01-assets.md) · [固定清单](../manifests/wrist_visual_wva01_20261122.json)


2026-11-22：[Isaac规则反馈RL完整链路已实际运行](agent/simulation/evolution/isaac-rule-feedback-rl.md)。当前WG-r10＋OM-r08/右臂停放场景，2段训练示范441条＋1段验证220条；BC1000次、Critic224次、Actor96次；3回合在线采集728条，接管下2/3到位，独立进程续训/重载通过。无接管评估仍0/2，策略尚未达标。

用户已认可并命名 **[WVA-01「腕部实拍对齐版」](agent/simulation/evolution/wrist-visual-wva01.md)**：当前腕部视觉基线固定WG-r15＋OM-r08及SIM-r06插槽参考场景，保留真实／鱼眼仿真对比和依赖哈希。源mesh、历史版本和既有训练任务不变；接受范围为视觉。

新增[r15真实腕部采集／仿真鱼眼对比](agent/simulation/evolution/wrist-logo.md#r15真实腕部采集仿真对比)：同像素区域展示原始采集与新标志版，保留材质／拉环／背景差异；未重新拟合或训练。

新增[WG-r15 DAIMON表面标志版](agent/simulation/evolution/wrist-logo.md)：按实拍增加两侧红色图标与黑色字样，朝向相反；49件几何保持r14不变，Blender／GLB与MuJoCo贴图显示检查通过，旧版保留。

新增[WG-r14实拍比例复核候选](agent/simulation/evolution/wrist-tip-photo-review.md)：以原始实物照片收窄前端、缩短根部平段；红线只表达结构。两份银壳修改，前端齐平及其他47件保留；照片比例估计不是尺寸标定。

新增[WG-r13红线轮廓候选](agent/simulation/evolution/wrist-marked-tip.md)：银色外缘改为斜边接根部平段，继承前端齐平，仅修改两份银壳；47件及所有旧版本保留。

新增视觉监督用途：[腕部视频与完整点云训练](agent/perception/evolution/sim-wrist-surface-learning.md)。基于已装配WG-r10／OM-r08的完整MuJoCo机械臂场景，运动学改变抓取与胳膊位置，生成256段鱼眼视频和每帧特权位姿，再实际训练图像网络。该实验没有验证新夹持接触动力学，也没有改动下方BC／RL策略；结果窗口8892。

新增[WG-r12梯形齐平指尖候选](agent/simulation/evolution/wrist-trapezoid-tip.md)：按用户确认的伸出方向对齐银壳与胶皮前端，包边后退0.2 mm；四边梯形主轮廓、胶皮及间隙保留，旧版不改。

2026-11-22按用户要求将非操作右臂临时水平伸向身体右侧，保留旧场景；当前腕部鱼眼中右臂像素为0，全景仍可见。[停放与人类反馈训练就绪性](agent/simulation/evolution/right-arm-park-and-hil.md)：当前Isaac新组合尚未接入人工反馈训练，旧接管RL来自规则老师。

2026-11-22：[固定WG-r10＋OM-r08已接入并打开独立Isaac场景](agent/simulation/evolution/wrist-bundle-isaac.md)。49件工具/17件模块、夹指开合、镜头绑定与1920×1080鱼眼检查通过；22个静态路径点最小工具/插槽间隙约5.07 mm。工具碰撞关闭，动态插入/抓取/训练尚未验收，旧资产和旧成绩保留。

新增[WG-r11宽钝头倒角候选](agent/simulation/evolution/wrist-fingertip-chamfer.md)：依据实物照片加宽两侧银色指尖前段，保留黑垫、间隙及其他47件；r10原资产和固定交接清单不变。

历史r10视觉资产接入入口：[WG-r10＋OM-r08合同](agent/simulation/evolution/wrist-assets-handoff.md)与[固定版本清单](../manifests/wrist_visual_asset_handoff_20261122.json)。静态鱼眼复现已在新目录运行；完整场景有675个依赖，加载时还需设定−2 mm插入初态。机器人／Isaac／训练接入需另行适配和验证，现有实验成绩不自动转移。

新增[WG-r10主体轮廓修正与OM-r08粗补U形拉环](agent/simulation/evolution/wrist-primary-refinement.md)：保留r09相机／夹持变换，只改两侧内沿；最终三单元黄色外缘约10.9→6.2 px、黑臂基本不变，旧任务与资产保留。

2026-11-22新增[Isaac接触力与图像改进](agent/simulation/evolution/isaac-contact-visual-review.md)：gentle候选三初态及半步长的到位/退出与10 Hz采样门控通过，seed7峰值21.3→3.04 N；仍有子步尖峰和两次工具会话收尾异常。实际512×512双相机、768静态对照与40.6秒清晰视频已保存，未作真机成像标定。

此前[固定r09位姿与开度试验](agent/simulation/evolution/wrist-pose-study.md)：镜头微调只改善部分指标，未替换主版本；模块相对位置随单元变化，且当时绿色件缺U形连接，不能仅靠全局相机位姿解决。

2026-11-22新增[Isaac Sim同源SIM-r06插接实验](agent/simulation/evolution/isaac-contact.md)：PGS局部7项与机械臂3初态规则循环通过，RTX双相机及36.9秒视频已生成。seed7控制采样力峰值约21.3 N，尚未满足学习评估10 N门控；未运行Isaac BC/RL。

新增[WG-r09多视角点云约束候选](agent/simulation/evolution/wrist-pointcloud-refinement.md)：r08已完整冻结保留；11视角点云支持修改8件局部mesh，镜头和夹持变换不变，黑臂轮廓改善明显，黄色与相机残差仍保留。

后续[整块轮廓诊断](agent/simulation/evolution/wrist-contour-diagnosis.md)确认：约3 px只适用于选定边缘；靠腕部黑臂每侧仍偏内约49～54 px，黄色外缘约18～28 px。优先查局部mesh／装配并联合复核相机，未将诊断探测相机作为新资产。

新增[WG-r08腕部投影对齐候选](agent/simulation/evolution/wrist-alignment.md)：调整镜头安装、同步移动相机壳／短颈和参考夹持变换，夹爪几何保留；4个留出单元选定边缘约16～18→3 px，完整画面和绿色拉环仍未一致。

最新[尺寸与腕部图像核对](agent/simulation/evolution/wrist-camera-consistency.md)：网格尺寸符合建模参数，但真实尺寸未认证；当前针孔与真机不一致，同位姿鱼眼候选仍有黄色区域、掌部遮挡和绿色拉环差异，尚未完成外参／夹持关系校准。

历史阶段的[WG-r07照片轮廓修正版](agent/simulation/evolution/wrist-tool-photo-profile.md)：双峰黄色衬垫、中央凹口与收窄指臂，侧视复核衬垫厚度27→12 mm；49件检查通过，基体／相机保持r06不变，旧资产保留。

历史阶段的[WG-r06黄色衬垫修正版](agent/simulation/evolution/wrist-tool-refinement.md)：按用户反馈去掉偏红色调，49件几何保持r05不变；旧资产保留。

新增[WG-r05相机／夹爪精修](agent/simulation/evolution/wrist-tool-refinement.md)，基于四组双目尺寸证据和原照片／视频，提供49件视觉资产及独立MuJoCo开合场景。未替换下方机器人／接触／训练场景；新工具尺寸变大，需重新检查插槽路径净空。

最新统一汇总：[2026-11-22完整进展与下一步](chronicles/2026-11-22-simulation-mesh-visual-progress.md)。当前[r07与真机对比](/data/omi_runtime/runs/module_v4_plain_material_20261122/real_vs_r07_plain_comparison.png)已经生成，右侧为仿真资产＋真实夹爪像素的静态预览。它尚未进入实时观测或新场景训练。

核对日期：2026-11-22。本页是仿真专门记录，直接汇总当前实现、验证结果、问题和运行入口；后续仿真改动应同步本页及对应领域能力文档。交接文档用于保存阶段快照，不能代替本页的持续维护。

## 当前状态

最新[光模块V4-r07纯色银灰材质候选](agent/simulation/evolution/module-material-r06.md)：保留r06色调并移除新增颗粒纹理，18件几何不变，原V4-r05和SIM-r06文件均保留。已在同视角混合预览中对比颜色，未自动替换实时场景或训练数据；模型版本V4-r06与接触资产SIM-r06是不同命名空间。

2026-11-22 用户对[真实夹爪像素＋仿真资产单帧预览](agent/simulation/evolution/hybrid-wrist-preview.md)整体观感给出正向反馈，并指出应由白色指尖内侧的黑色接触面夹持模块。已补回这两处真实前景像素，另存修正图；原预览保留。此项是静态观测合成，不改变下面的物理仿真、实时观测或训练合同；[本轮进展](chronicles/2026-11-22-hybrid-wrist-contact-review.md)。

新增[视频参考腕部相机与夹爪候选](agent/simulation/evolution/wrist-camera-gripper.md)：31件工具外观已挂载到独立场景，腕部RGB从模型镜头位置渲染；名义工具路径间隙检查及两个初态规则循环通过。交互窗口支持空格播放、1全景／2腕部／3头部／4末端。该场景保留固定附着模块、padding触觉和未标定针孔相机，工具几何尚未作为动态碰撞抓取模型；[操作入口](../tutorials/wrist_camera_gripper.md)。

光模块外观暂定采用 **V4-r05「双窗尾槽版」**（2026-11-21用户确认）。它含尾端双空窗、三个金属端及可取下的双脚胶件；[完整开发过程](chronicles/2026-11-21-v4-double-window-baseline.md)已归档。现已从它派生新尺寸接触候选SIM-r06；原视觉文件、旧SIM-r03和旧训练任务保留。

最新实验使用 **MuJoCo 3.15.0＋完整厂商双臂／夹爪URDF＋SIM-OM001-OS001-r06**：V4-r05模块、18.8 × 8.8 mm金属孔口、按正面窄边口径6.9 mm的孔位（方向／外缘口径待用户进一步确认）。局部插入退出及机械臂三初态规则循环3/3通过，双相机均真实可见模块与插座。完整参数、失败修正和证据见[新尺寸仿真记录](agent/simulation/evolution/measured-v4-simulation.md)与[操作入口](../tutorials/measured_v4_simulation.md)。

旧模型同侧距离约7.0 mm，与用户补充6.9 mm差0.1 mm；新候选网格已核对为6.9 mm。旧内部支撑仍保留，使深部上下每侧余量约0.0479 mm；真实接触和孔内部形状尚未标定。

新尺寸下旧BC和旧RL直接迁移各0/2，均无接管。**规则链路通过不代表旧视觉策略能直接沿用**；本轮未重新执行新几何的10BC＋20接管RL，下一步需采集新场景示范并建立新的训练合同。

旧SIM-r03学习结果曾取得无接管成功：两批8个初态中加权BC为7/8、第一轮RL为8/8。该成绩保留为旧几何结果，不作为新尺寸成功率。实物标定、真实接触抓取和整机自碰撞仍未验收。

## 资产与场景

模块mesh的建模、修订、部件和几何验证单独维护在[Mesh开发记录](mesh-development.md)及[Blender资产管线](agent/simulation/evolution/asset-pipeline.md)。本节以下记录的是仿真正在使用的资产，不能据此把已暂定的V4外观版当作已接入训练。

当前“一套独立资产”是装配包，内部对象分开，并非单一mesh。

| 组成 | 当前实现 |
| --- | --- |
| 光模块 `sim_module` | 当前r06含18个V4-r05外观件、156个凸碰撞件；外观源文件逐字节保留 |
| 插接座／支架 `sim_socket` | 113个保留外观件、335个凸碰撞件，保留通道空腔和机械台阶 |
| 7个等效弹性触点 | 独立被动滑动关节，有碰撞、行程限制和回弹 |
| 资产封装 | 当前r06装配Blender含632个对象、622份OBJ、MJCF和清单；另导出独立插槽OS-001/M1888-r01，模块仍引用独立V4-r05基线 |
| 机械臂场景 | 完整厂商URDF、圆桌、独立SIM资产、头部／腕部相机；模块固定附着于工具 |

原OM-001/V3和OS-001/r04及历史输入保留。原完整刚体在约4.212mm处被入口弹片／卷边挡住的结论仍有效。新资产用7个等效触点替换了未标定的22件入口细件，其通过不意味着原mesh已被实物校准。

当前r06等效触点半径／行程／名义压入量为0.15／0.15／0.10 mm；刚度100 N/m、阻尼0.63 Ns/m、每个触点1 g均未实物标定。静态余量从新几何计算，完整行程保守界最小约0.1104 mm。旧r03的0.35 mm半径／0.27 mm行程及约0.03 mm余量属于历史参数；新r04／r05候选失败原因另保存在新尺寸记录。

详见[接触资产能力](agent/simulation/evolution/contact-simulation-asset.md)、[原mesh检查](agent/simulation/evolution/mesh-insertability.md)和[资产登记](../manifests/simulation_assets.json)。

## 2026-11-21 实物截面尺寸复核

用户新报告：插孔 **18.8 × 8.8 mm**，模块 **18.1 × 8.2 mm**。这里按插入方向垂直截面的横向宽度／竖向高度理解，暂按金属净开口比较；测量位置、是否包含弹片及测量误差尚未确认。不是模块轴向长度。

| 比较对象 | 当前模型（mm） | 用户实测（mm） | 模型减实测（mm） |
| --- | --- | --- | --- |
| SIM-r03／V3 模块参考插入截面 | 18.1741 × 7.8383 | 18.1 × 8.2 | +0.0741 × −0.3617 |
| SIM-r03／OS-r04 金属基本通道 | 19.0 × 9.6 | 18.8 × 8.8 | +0.2 × +0.8 |
| 刚展示的历史 OS-r01 金属基本通道 | 20.9 × 9.6 | 18.8 × 8.8 | +2.1 × +0.8 |

模块参考截面为源坐标 `Y=5 mm`，从SIM实际OBJ重新切片，外观与碰撞mesh均得到同样尺寸；并非沿全长的最大包络。历史V2同一坐标截面约16.9771 × 7.4487 mm，完整模型横向最大包络仅17.3580 mm，仍小于实测18.1 mm；其10.3765 mm总高度包含凸起头部，不能拿来当插入段厚度。

居中矩形截面估算：实测横向／竖向每侧间隙0.35／0.30 mm，当前仿真参考截面为0.413／0.881 mm。该估算不扣除弹片、凸筋，也不包含偏心／倾斜，不能视为沿插入路径的最小净空。**当前资产尚未按这次实测校准；旧规则和BC／RL成功结果仍只适用于旧几何。** 特别是竖向余量偏大，需要在后续新修订中修正并重新验证接触与策略。

本次只核对和记录，未修改历史或当前mesh，未运行新尺寸训练。原始顶点、切片和对比证据见[尺寸核对报告](/data/omi_runtime/runs/measured_dimensions_audit_20261121/comparison.json)。后续保持原文件，另建实测尺寸修订，确认孔口测量位置后同时校准模块、通道及入口接触件。

### 后续新增：独立实测模块mesh

已按用户补充创建 **OM-001/MEASURED-r01**：插入段最大横向18.1 mm（含侧弹片）、厚度选8.2 mm，下部前伸段上翘0.2 mm，尖端厚度8.0 mm。斜面长度暂沿用V3的5.19 mm，待实测；8.0 mm标在下唇前端，上唇仍向前多伸约3.16 mm。

新Blender／OBJ／GLB均可重开；实际截面、101点斜面单调性及13个实体部件拓扑检查通过，另2个装饰折缝仅作外观。503个旧文件哈希未变。**这是新增模块几何，尚未替换当前仿真资产，插座、动态接触和训练结果仍沿用旧版本。** 文件、尺寸图、验证边界见[实测模块修订记录](agent/simulation/evolution/measured-module.md)。

### 后续新增：V4尾端结构

已依据用户视频和指认，从V3→MEASURED-r01派生独立 **OM-001/V4 r01**。重点是在金属上盖尾缘切掉一小块长方形，并切除下方挡住缺口的旧盖板，形成真实凹字形轮廓；另补侧片下沿缺口和黑色尾件内凹。主体截面、前端上翘和上下壳同种金属保留。

新槽尺寸为视频建模估计，尚未实测。5个部件修改、10个部件几何不变；实体、切口空腔、截面及导出重开检查通过，529个旧文件哈希未变。已打开独立Open3D窗口。V4尚未接入真实视觉定位、碰撞代理或训练，不能把新增结构等同于视觉精度改善。详见[V4持续记录与文件](agent/simulation/evolution/module-v4.md)。

### 当前V4修订：r03胶件与金属片下沉

最新正视近照复核：用户仍认为r03不符。已定位到黑色胶件端面过矮、下方余量过大的问题；整体下移不能替代尺寸／结构修正。当前仅分析并保留r03，不作为外观已认可版本，详见[V4最新复核](agent/simulation/evolution/module-v4.md)。

两张新照片确认黑色件可取下且有两条内伸胶脚，缺口口沿有三个金属凸片；r01固定黑色盲凹块已被替换。r02初版高度被用户指出偏高，当前另存r03，将胶件和三个金属片一起下沉1.5 mm，并重建下方容纳空间；这个下沉量仍是建模估计。当前胶件／金属片顶面低于金属头盖约1.96／1.81 mm。

18个mesh含独立胶件，16个实体通过拓扑检查；双脚连通性、下沉量、主体尺寸、文件重开及31个离散拔出位置检查通过，599个旧文件未变。独立V4-r03窗口支持装入／拔出、单看胶件和侧视高度。未验证橡胶变形、真实夹持力或视觉定位改善，训练资产仍未切换。最新文件和历史纠正见[V4记录](agent/simulation/evolution/module-v4.md#当前修订r03双脚胶件三个金属片与下沉修正)。

### V4当前为r04：已落实尾端正视比例修正

用户要求继续建模后，已创建并打开V4-r04：胶件端面由3.95增至7.1 mm，底部余量由4.9减为约1.2 mm；三个金属端面宽度改为1.8／3.2／1.8 mm，并开出露出内伸黑胶的两个上侧窗口。几何射线核对了“金属—黑胶—金属—黑胶—金属”排列，16个实体、31点静态拔出和导出重开检查通过；644个旧文件未变。尺寸为照片估计，尚待用户外观认可，未切换训练。最新文件和查看命令见[V4记录](agent/simulation/evolution/module-v4.md)。

### V4当前为r05：金属端同高度区域留空

按用户纠正，移除r04错误填入两个上侧窗口的胶件延伸。下方端面、低位双胶脚及17个主体部件保留，窗口同高度区域实际为空。280个点内外检查与正面射线确认无胶件填充，拓扑、离散拔出和旧文件保护检查通过，窗口已更新为r05。详见[V4记录](agent/simulation/evolution/module-v4.md)；训练未切换。

## 仿真器、控制和任务接口

| 层 | 代码／接口 | 作用 |
| --- | --- | --- |
| 独立资产构建 | `sim/contact_asset.py`、`scripts/simulation/author_contact_asset.py` | 新目录生成MJCF／OBJ／Blender，不保存回原mesh |
| 机器人场景装配 | `sim/contact_robot_scene.py` | 接入URDF、接触资产、相机和固定工具变换 |
| 接触环境 | `sim/contact_env.py` 的 `ContactInsertionEnv` | 接触、成功／失败、回合和图像观测 |
| 环境工厂 | `make_env("robot_contact_insertion", scene_dir=...)` | 明确选择新接触任务 |
| 控制 | `sim/robot_env.py` | 世界系6D TCP增量→阻尼最小二乘IK→关节位置伺服 |
| 规则老师 | `sim/contact_teacher.py` | 对准、插入；单独支持已到位后的退出检查 |
| 学习与接管实验 | `omi_proj/training/contact_intervention_study.py` | 规则示范、BC、在线接管、SAC和关闭接管评估 |

物理步长为0.2ms，控制周期100ms（10Hz）。平移每轴上限为 `1 mm / √3`，旋转每轴上限为 `1° / √3`。请求动作、实际采用动作和物理运动分别记录。

开启的接触范围是模块／插接座／等效触点／台面。机器人仍用固定工具附着、重力补偿和假设伺服参数；这不是已验证的接触抓取。旧 `robot_reach` 和无接触预插入场景保留，不能与新任务混用结论。

## 相机和观测

另已生成[真实夹爪像素与仿真模块／插槽的单帧混合图](agent/simulation/evolution/hybrid-wrist-preview.md)：使用用户提供的1920×1080鱼眼K／D，前景核心像素直接保留源图。2026-11-22又补齐真正接触模块的左右黑色接触面，区分其与后方橙色内衬、模块自身黑色胶塞。该实验仅用于静态视觉预览，未改动下面实时环境的观测或训练合同。

以下是通用观测合同。最新视频参考工具场景把腕部光学位置改为TCP下(57.73,0,65.536) mm、估计fovy=90°，并与可见镜头绑定；此前SIM-r06基线仍保留(100,−60,70) mm／68°配置。两场景文件独立，不能混用策略成绩，真实鱼眼尚未复现。详见[相机安装记录](agent/simulation/evolution/wrist-camera-gripper.md)。

| 字段 | 形状 | 来源 |
| --- | --- | --- |
| `rgb` | 10×3×128×128，uint8 | 固定头部视角的MuJoCo RGB |
| `wrist_rgb` | 同上 | 随末端运动的腕部RGB |
| `camera_mask` | 10×2 | 有效相机帧标记 |
| `history_mask` | 10 | 过去到当前的因果历史，不足时左补零 |
| `state` | 10×14 | 当前仍为零padding |
| `tactile` | 10×10×16×24 | 当前仍为零padding |

两张图来自同一物理状态；每个控制步重新渲染。全景视频只用于展示，不进入策略。真值位姿用于规则老师、奖励、接管和评估，不进入学生的观测。相机外参／成像模型为仿真假设，尚未复现实物鱼眼和工具标定。额外marker贴纸可忽略，本轮仿真不加载该贴纸纹理。

## 成功与失败如何判断

接触插入成功必须同时满足：

1. 台阶深度误差小于0.15mm，横向误差小于0.35mm。
2. 模块相对插座姿态角误差小于0.01rad。
3. 实际头部／口沿接触，并连续稳定3个控制时刻。
4. 不发生超过0.05mm的数值侵入，且满足环境间隙条件。

超时为截断，不算成功。实验评估还会在10Hz控制时刻模拟接触力模长总和超过10N时停止并计失败；这是实验停止规则，不是实物安全力认证。

退出验证从插入后的物理状态继续动作，不瞬移或reset模块。该退出能力已由规则控制验证；学习策略的最新成功统计只针对插入到位。

## 旧SIM-r03已执行的验证

| 检查 | 结果 |
| --- | --- |
| 局部正常插入／退出 | 到约51.28171mm台阶，退回−3mm起点，触点回弹 |
| 锁死弹性触点 | 约4.725mm处阻挡，证明柔顺接触参与通过 |
| 偏心±1mm／偏航±2° | 在孔口附近阻挡 |
| 步长0.2ms→0.1ms | 到位／退出结论一致，局部最大侵入均<0.008mm |
| 完整允许触点行程 | 固定结构间隙约0.03mm |
| 机械臂规则插入＋退出 | 独立初态3/3通过，逐物理步最大侵入<0.004mm |
| 规则示范与相机链路 | 数据实际采集，历史连续；无真人标签混用 |

模型接触证据见[资产验证清单](../manifests/contact_simulation_asset_20261121.json)。

## 旧SIM-r03学习结果（新尺寸迁移结果见当前状态）

最新试验用10个BC训练回合（1749条），验证另留2回合（350条）；普通BC与旋转加权BC各运行3000次更新。旋转加权BC验证2/2成功，随后执行两组各20回合的在线规则接管RL。

| 关闭接管后的评估 | 测试700–703 | 新确认800–803 |
| --- | --- | --- |
| 旋转加权BC | 3/4 | 4/4 |
| 第一轮20回合RL | 4/4 | 4/4 |
| 有界探索＋旋转约束RL | 0/4 | 未追加 |
| 等保留数据／Actor步数的额外BC | 0/4 | 未追加 |

第一轮训练中包含接管，训练成功率19/20；第二轮训练20/20，但独立测试失败。**接管成功率与自主成功率分别记录。** 第一轮Critic累计5462次更新含1000次预热，Actor更新2231次；第二轮共享同一预热初始状态。旧22次更新、0/2结果只是前序短试跑。

两批不同初态合计BC 7/8、第一轮RL 8/8，有小规模改善证据。成功回合平均BC 175步、RL 228.5步，RL并非所有指标都更好。额外BC是回顾性数据对照，第二轮又同时改了两个因素，不能作唯一因果归因。

详细训练事实由 [omi_proj训练纪传](../../omi_proj/docs/agent/training/evolution/contact-intervention-study.md)维护，原始结果见[策略试验清单](../manifests/contact_policy_study_20261121.json)。真实图像的六维定位／遮挡跟踪仍是独立的[感知主线](agent/perception/current.md)，不能由仿真成功替代验收。

## 当前入口与观看

- 当前新尺寸资产：`/data/omi_runtime/assets/sim_insertion/r06/`，独立插槽在`/data/omi_runtime/assets/optical_socket/measured/r01/`。
- 当前机器人场景：`/data/omi_runtime/runs/measured_v4_sim_20261121/robot_scene/`。
- 新尺寸验证与旧策略迁移试验：`/data/omi_runtime/runs/measured_v4_sim_20261121/`；旧几何训练试验保留在`/data/omi_runtime/runs/contact_intervention_study_20261121/`。
- 仿真／训练环境：`/data/omi_runtime/envs/omi_sim_train`；资产检查环境：`omi_mesh_audit`。
- [新尺寸规则插入＋退出视频](/data/omi_runtime/runs/measured_v4_sim_20261121/robot_validation/robot_contact_cycle.mp4) · [旧几何RL自主插入视频](/data/omi_runtime/runs/contact_intervention_study_20261121/final_comparison/rl_success_video/policy.mp4)。
- [新尺寸仿真复现及新训练入口](../tutorials/measured_v4_simulation.md)。
- [新资产及接触验证命令](../tutorials/contact_simulation.md) · [10BC＋20接管RL及续训命令](../../omi_proj/tutorials/contact_intervention_study.md)。

旧 `omi-shapeforge simulate mujoco` 仍对应早期单模块／方阵工作流，不能当成新接触任务的通用启动器。

## 问题和后续工作

- 扩大无接管测试的初态／场景／种子，当前8例只覆盖固定场景和每关节±0.0005rad小扰动。
- 分别研究探索、旋转约束、图像增广和纠偏数据的作用，保留失败对照。
- 完善姿态保持、卡滞恢复和有根据的力限制；补齐机器人状态／触觉输入。
- 标定真实工具、相机、惯量和接触参数，验证抓取与整机自碰撞。
- 将模块／插座另行封装为独立可复用子资产，保持原mesh不变。
- Isaac目前只有早期PhysX CPU落台验证，未完成本插入任务或RTX／GUI验收。

## 领域与历史索引

- [仿真章程](agent/simulation/charter.md) · [仿真当前摘要](agent/simulation/current.md) · [能力索引](agent/simulation/evolution/README.md)。
- [Blender资产管线](agent/simulation/evolution/asset-pipeline.md) · [独立接触资产](agent/simulation/evolution/contact-simulation-asset.md) · [机器人资源](agent/simulation/evolution/robot-assets.md)。
- [早期MuJoCo／Isaac单模块及阵列场景](agent/simulation/evolution/engine-scenes.md)。
- [阶段编年](agent/simulation/chronicles/README.md) · [最新策略实验快照](chronicles/2026-11-21-contact-policy-improvement.md)。

本页的当前事实与领域能力文档持续更新，历史编年保留原结论；维护规则见[文档制度](design/documentation-system.md)。
