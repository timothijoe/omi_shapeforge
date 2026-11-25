# 当前总览

2026-11-25：[System1训练与路径可视化](agent/simulation/evolution/system1-path-visualization.md)完成。60轮按验证选择第47轮，独立3回合1074帧位姿平移均值0.228 mm、最大2.207 mm；交付腕图叠加与三维8点短段视频。当前为同资产小扰动，网络预测位姿、几何程序解码路径，未验证新插接成功率。

2026-11-25：[System1 与 System0 独立插接原型](agent/simulation/evolution/hierarchical-insertion.md)新增GT／噪声／学习型参考、独立SAC和虚拟腕部六维力。旧RL默认入口保留；规则采集3/3通过，短预算训练及组合评估用于链路验证，尚未建立可靠自主插接能力。

2026-11-25：[System1 与 System0 路径条件化插接讨论](design/system1-system0-path-conditioned-rl-discussion.md)已整理。当前倾向先验证路径条件化SAC直接六维动作，residual为备选对照；三维路径、horizon、异步消息及真机奖励均保留待验证项。本次未实施该架构或新增训练成绩。

2026-11-25：[真实1920腕图追溯与r16外观候选](agent/simulation/evolution/wrist-photo-refinement-r16.md)：15单元287张原腕图哈希通过，确认完整原图与389ROI→128显示链；按原图域约束银壳正面，7个开发参考边缘平均约5.62→2.86 px，颜色由亮黄改为与真实橙色ROI接近。K/D及安装保持，r16仅候选，不替代已认可r15、碰撞或RL。

2026-11-25：[r11腕部仅橙绿重点叠加](agent/perception/evolution/alignment-insertion-film.md)按用户追加要求制作：中间视图只画可见尖端／孔口点，其余恢复原腕图；右侧完整冷银灰点云及其他画面保持。新默认为`focus-only`，用户已确认显示规则并要求归档；[完整交接](chronicles/2026-11-25-pointcloud-video-handoff.md)已记录交付、验证和恢复，r10原片保留。

2026-11-25：[r10冷银灰分层点云版已获用户认可](agent/perception/evolution/alignment-insertion-film.md)，登记为当前展示版本并采纳为后续模块普通点云默认色RGB(216,221,228)。普通稀疏／重点加密、同一点径和橙绿重点保持；正式视频与原试版字节一致，r9及旧片保留。此为展示认可，物理／网络边界不变。

2026-11-25：[r9视频已被用户接受为可用版本，r10限定光模块普通点云配色候选](agent/perception/evolution/alignment-insertion-film.md)。比较三组低饱和中性色并制作冷银灰试版；源点、重点橙绿、其余部件和轨迹／镜头不变，旧片保留。制作阶段为候选；随后用户认可冷银灰r10并采纳为默认，见上条。物理／网络事实不变。

2026-11-25：[分层点云展示方式获用户认可并设为多数后续展示的默认约定](agent/perception/evolution/pointcloud-presentation.md)：整体稀疏、重点加密，两层相同点径，普通面灰阶、指定橙／绿重点；兼容查看器和来源已留档。[r9插接视频](agent/perception/evolution/alignment-insertion-film.md)按此格式导出，18.07秒／1080p／3×，沿用r15固定夹持轨迹；旧影片／数据／训练合同保留，新影片待用户复审。

2026-11-25：[r8插接点云中性灰阶](agent/perception/evolution/alignment-insertion-film.md)替代用户否定的r7配色：普通模块深灰、插座上部中灰、底座浅灰蓝，只有指定尖端橙／孔口绿保留鲜亮。沿用r15固定夹持回放、三视图及3×，仅改展示，历史片保留，r8待复审。

2026-11-25：[r7插接点云部件分色](agent/perception/evolution/alignment-insertion-film.md)已按追加偏好导出：普通光模块暖灰橙、插座上部灰绿、底座原浅灰蓝，亮橙尖端与亮绿孔口不变。沿用r15固定夹持回放及三视图／3×，只改展示，历史影片保留；尚未获用户复审认可。

2026-11-25：[WG-r15新版夹爪的Isaac插入视频及全组件版本表](agent/simulation/evolution/wva01-isaac-insertion.md)已交付，r10旧片留存。r15原网格／UV标志已接入，OM-r08、插座、URDF与相机核对为当前采用版本；新固定夹持回合586步通过，18.07秒／1080p／3×。GC-r01仅提供闭合参考，自由接触夹持移动未验收；无新网络或策略成绩。

2026-11-24：用户已认可[简洁三视图r4展示](agent/perception/evolution/alignment-insertion-film.md)，原片与哈希保留；按其追加偏好交付r5，仅让模块普通点云比插座略深，橙色尖端／绿色孔口及排版节奏不变。偏好和认可范围已记录；18.07秒／1080p／3×，未运行网络或新物理试验。

2026-11-24：[插接影片r4简洁版](agent/perception/evolution/alignment-insertion-film.md)已交付：仅模块尖端橙色、孔口绿色，其余点云浅灰；去掉辅助放大窗，改为三个等高主视图。18.07秒／1080p／标注3×回放，全部470状态保留，解码、画面与来源核查通过；仅改展示，未运行网络或物理新试验。

2026-11-24：[橙绿点云与18.07秒插接展示版](agent/perception/evolution/alignment-insertion-film.md)已交付。模块橙色、插孔绿色，腕部空背景小窗改为局部放大；全部470状态按画面标明的3×连续回放，三视图同步。原轨迹中段约1.86mm/s，末段另减速；本次仅调整展示，物理控制及网络未改。

2026-11-24：[未对准→对准→完整插入视频](agent/perception/evolution/alignment-insertion-film.md)已按参考图重做，51.5秒／1080p：实际18.62mm横向偏差和2.50°姿态偏差起步，在孔口外对准后再插入落座；三视图同步，浅灰完整表面、绿色重点，标题“几何位姿估计”。点云仍为仿真位姿参考，未运行网络或训练。

2026-11-24：[完整插入三视图视频](agent/perception/evolution/insertion-gt-multiview.md)已交付：39.8秒／1080p，同一成功PhysX轨迹从未插入到落座，机器人第三人称、腕部叠加GT、重点着色三维点云同步显示。358个源状态无跳步，全片解码与来源核查通过；GT示意，未运行网络或新训练。

2026-11-24：[点云估计展示视频](agent/perception/chronicles/2026-11-24-pointcloud-showcase-video.md)已交付，56秒／1080p／30fps，三维运镜与真实测试预测对照，保留最大误差；全片解码与来源核查通过。本次仅制作视频，未训练新细网格数据。

2026-11-24当前确认：规则精度回归20／5子步均5/5，快速5子步最大终点横向误差约0.059 mm、角度0.0059°、深度误差＜0.001 mm；同一冻结RL网络五回合执行时间462.170→32.644秒，约14倍，但自主成功率新旧均0/5。速度、环境可插入性与策略能力分别记录，默认配置未改；按用户要求保存进展，本次不启动新实验。 [纪传体](agent/simulation/evolution/isaac-rule-precision.md) · [编年体](chronicles/2026-11-24-isaac-rule-precision.md)。

2026-11-24：[快速配置规则精度回归](agent/simulation/evolution/isaac-rule-precision.md)完成。20／5子步各5例均成功；终点横向误差最大0.048／0.059 mm，角度最大0.0048／0.0059°，深度误差均小于0.001 mm。入口、稳定落座、位姿偏移及受阻恢复均核查；规则／判据未调参，物理诊断与带RGB正常轨迹一致。结论限于当前仿真场景，未重训BC／RL。

2026-11-24后续：[真实RL策略5组新旧速度对照](agent/simulation/evolution/isaac-control-throughput.md)完成。同一冻结Actor，新旧各5回合：462.170→32.644秒，整体约14.16倍；按控制周期约13.50倍。两组均0/5成功、入口资格失败；无teacher或梯度更新，未连接真机。

2026-11-24本窗口已按用户要求收口：[纪传体／控制吞吐总账](agent/simulation/evolution/isaac-control-throughput.md) · [编年体／学习与性能交接](chronicles/2026-11-24-isaac-performance-window-handoff.md)。建议快速配方为CPU＋原厂IK＋5物理子步＋双渲染子帧＋异步记录，约55 ms完整规则采集周期；最早基线约770 ms，约14倍，包含物理步长与算法变化。代码默认未切换，BC／RL未因提速新增训练成绩；本次仅整理文档。

2026-11-24：[5子步与异步记录对照](agent/simulation/evolution/isaac-fast-collection.md)完成。CPU＋原厂IK完整周期约95→75 ms（20→5子步），异步记录后约55 ms，单渲染子帧组合约48 ms；5子步同步／异步均3/3规则通过，1776条异步转移图像完整性核查通过。单子帧仅正常案例，未验证BC／RL；新选项显式启用，默认不变。

2026-11-24：[CPU完整控制周期核查](agent/simulation/evolution/isaac-step-profile.md)：当前规则采集周期约90.6 ms＝决策1.7＋step65.0＋记录23.6＋整理0.3 ms；记录中每步4次fsync共约16.5 ms，图像捕获每步触发4次Kit应用更新。此次只做测量，未改变生产行为；与此前step RPC口径分开。

2026-11-24：[GPU物理兼容模式](agent/simulation/evolution/isaac-gpu-physics.md)已接入并验证。GPU正常与±1 mm受阻恢复3/3通过；原生GPU求解器统计确认启用，但当前单环境＋CPU回读下RPC约111 ms，同批CPU约65 ms，保持CPU默认。可用`--physics-device gpu`显式选择，新GPU执行合同单独登记。

2026-11-24：[完整控制步排查与优化](agent/simulation/evolution/isaac-step-profile.md)完成。修复奖励重复测量、SAT小数组循环、腕图复制及无界面仍更新的默认预览；原厂IK＋20子步的RPC从约96 ms降到69～71 ms，三场景物理轨迹／奖励一致。真实双RGB与双渲染子帧保留；新渲染合同明确登记，旧配方可恢复。

2026-11-24：[天机原厂IK已接入](agent/simulation/evolution/tianji-native-ik.md)。坐标／单位／TCP适配及逐次回代验收完成；离线500/500，实际PhysX正常与±1 mm受阻恢复3/3通过。worker与训练编排可显式选择原厂后端，新旧合同分开；尚未重训BC／RL或连接真机。

2026-11-24：[天机SDK离线IK核查](agent/simulation/evolution/isaac-control-throughput.md)已完成。本地已有运动学库；500个小目标计算及FK回代通过，TCP增量IK中位约0.102 ms。该离线核查阶段尚未接入Isaac；随后完成的适配与模型一致性验证见上方新记录。始终未连接真机。

2026-11-24：[50段多样化示范完成](agent/simulation/evolution/diverse-demonstrations.md)。40训练＋10验证，准备动作不作专家监督；BC闭环验证0/10、留出0/8；BC未达到预登记门槛，本轮未启动RL。有效完成阶段退出0，启动失败及接续记录保留；仍仅是当前仿真范围。

2026-11-24：[控制吞吐与四档子步对照](agent/simulation/evolution/isaac-control-throughput.md)完成。原实现每动作500／20子步约734／222 ms；等价FK缓存后20子步约117 ms。新批量入口默认20，原50段研究仍保留500合同；原生异常和限定验证范围另记。



2026-11-23：[runtime实体归拢已完成](chronicles/2026-11-23-runtime-relocation.md)。运行资源已迁入`/data/shapeforge/runtime/`，原`/data/omi_runtime`为兼容链接；此前[四批导入／交付资料](chronicles/2026-11-23-storage-layout.md)位于同级storage。当前布局统一见[本地资源契约](agent/interfaces/local-resources.md)。各自内容完整保留，未进行去重或改变资产版本及实验结论。

2026-11-23：[收尾监督补强与新合同重训](agent/simulation/evolution/staged-retraining.md)完成。BC无接管0/2、最终RL无接管0/2，接管训练2/3；本轮原生阶段全部退出0。历史143未复现、来源未定，旧结果不重算。

2026-11-23续开发：[在线接管恢复已接入](agent/simulation/evolution/online-insertion-recovery.md)。固定三例真实RPC验证通过：正常、±1 mm受阻退回／重对准／重插及交回；任务目标与奖励不随子目标改变。提议方为诊断脚本，未重训或新增学习策略成绩。 三例运行的外层会话143、原生退出回执缺失另记；独立生命周期检查正常，原因尚未诊断。

2026-11-23：[规则插入与demo收尾](agent/simulation/evolution/rule-insertion-review.md)完成：预登记正常组8/8、偏移受阻后恢复4/4；实际录像已打开，用户反馈比之前好。固定WG-r10＋OM-r08；小范围规则结果，未重训BC／RL或验证真机。

当前感知任务交接：[三变量采样、细网格数据与后续预训练](chronicles/2026-11-23-perception-grid-pretraining-handoff.md)。含已确认目标、数据入口、验证、历史模型区别、恢复和接续事项；不替代并行资产／控制任务交接。

[感知细网格数据v1](agent/perception/evolution/grid-perception-data-v1.md)已完成：16490候选全部检查，16251张物理有效图；严格三变量主集14549张（训练12463／验证987／测试1099），辅助1702张，未收录239个。窗口8895，模块和插座范围／步长、有效区域及标注均可查看；当前仅孔口前静态样本，未训练新网络。推荐入口`grid_perception_20261123_v1/data_strict/`。

2026-11-23：[入口严格、内部容错的新任务合同](agent/simulation/evolution/staged-insertion-contract.md)已实现，五条脚本轨迹满足新判据：偏置受阻后真实退回重插、对准、半步长和内部轻擦。几何／摩擦未改，旧成绩未重算，未重训BC／RL，真机标定仍未完成。


PCG-01纯几何资产已完成独立导出、可视化和Downloads便携交付，全部记录已补齐：[纪传体／主阅读入口](agent/perception/evolution/pointcloud-geometry-pcg01.md) · [编年体／执行经过](agent/perception/chronicles/2026-11-23-pointcloud-geometry.md)。两个PLY共0.565MB，顶点＋索引数组约0.535MB，ZIP约0.915MB；去掉颜色及指定附件，未改旧资产或替换训练模板。

2026-11-23新增[PCG-01点云匹配纯几何版](agent/perception/evolution/pointcloud-geometry-pcg01.md)：无颜色／纹理，模块主体＋插口上部，源尺寸不变；已在Downloads交付可直接复制的文件夹与ZIP。

用户已查看可视化并确认光模块相对夹爪只采样**前后、上下、俯仰**，左右居中、偏转和侧倾固定。[三变量预览](agent/perception/evolution/three-variable-grasp-preview.md)已完成27组静态夹持检查，窗口8894；三变量含义与可视化表达已获认可，正式采样范围／步长另议，未开始新训练。

2026-11-23：GC-r01接触版感知训练已完成。256段／3072帧经接触与可见网格筛选，方案一模板续训25轮；同一新测试集尖端误差旧模型12.26mm→新模型0.98mm，P90为1.38mm，最差仍10.97mm。窗口8893；仅接近阶段仿真，非插入／真机验收。 [进展与范围](agent/perception/evolution/contact-wrist-surface-learning.md)。

2026-11-23：[顺滑通道候选的BC／规则反馈RL重训](agent/simulation/evolution/smooth-guide-retraining.md)已完成：BC与最终RL均自主0/4，RL在入口更早失败；接管训练4/6成功。BC3000次、Critic1664／Actor768次，独立续训与重载通过。共享干预统计已补，实仿语义及物理验收仍未完成。

2026-11-23：[入口受阻、内部顺滑的Isaac接触候选](agent/simulation/evolution/smooth-guide-contact.md)已建立并做有界对照；局部检查通过，完整机械臂仍触发瞬时穿透保护，尚未接入新一轮BC／RL。原WG-r10＋OM-r08和旧训练成绩保留。

夹持修订查看后已归档：GC-r01交互窗口已打开，用户反馈“感觉好很多”。本方面统一从[黑胶垫双面接触修订](agent/simulation/evolution/wrist-contact-closure.md)阅读，含接触验证、对比图、启动命令及对应编年记录；尚未验证接触插槽后的稳定性。

8892点云结果页现支持“完整规则网格＋重点加密”和“仅尖端／孔口”两方案；普通0.8mm、重点0.2mm，灰色普通点／绿色真值／橙色预测。沿用已有预测位姿，未重新训练；详情见仿真腕部点云能力记录。

用户确认：方案一“完整规则网格＋重点加密”为主方案；方案二“仅尖端与孔口”保留为备选。此确认针对点云表征与显示，不代表重新训练或位姿精度验收。

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

历史首轮基线：[仿真腕部RGB→完整点云](agent/perception/evolution/sim-wrist-surface-learning.md)已完成256配置／3072帧、25轮3600更新和独立测试，结果窗口8892已打开。测试均值：模块1.16mm、插座1.37mm、尖端相对1.92mm；仅是仿真随机范围内效果，尚未认证真机或插入精度。[操作](../tutorials/sim_wrist_surface_learning.md)。

新增[WG-r12梯形齐平指尖候选](agent/simulation/evolution/wrist-trapezoid-tip.md)：按用户确认的伸出方向对齐银壳与胶皮前端，包边后退0.2 mm；四边梯形主轮廓、胶皮及间隙保留，旧版不改。

2026-11-22按用户要求将非操作右臂临时水平伸向身体右侧，保留旧场景；当前腕部鱼眼中右臂像素为0，全景仍可见。[停放与人类反馈训练就绪性](agent/simulation/evolution/right-arm-park-and-hil.md)：当前Isaac新组合尚未接入人工反馈训练，旧接管RL来自规则老师。

表征窗口显示修正：8891现在默认保留完整物体，并在同一坐标下显示尖端／孔口加密层及局部小窗；原网络点集、位姿和训练状态不变。[操作](../tutorials/interaction_surface_representation.md)。

感知表征最新：[尖端与孔口优先的精细点集](agent/perception/evolution/interaction-surface-representation.md)。新增8891局部窗口、精确ROI表面及真实边缘，网络点预算22528／43008并分层加权；旧整体点集和8890窗口保留，未进行网络训练。[操作](../tutorials/interaction_surface_representation.md)。

2026-11-22：[固定WG-r10＋OM-r08已接入并打开独立Isaac场景](agent/simulation/evolution/wrist-bundle-isaac.md)。49件工具/17件模块、夹指开合、镜头绑定与1920×1080鱼眼检查通过；22个静态路径点最小工具/插槽间隙约5.07 mm。工具碰撞关闭，动态插入/抓取/训练尚未验收，旧资产和旧成绩保留。

新增[WG-r11宽钝头倒角候选](agent/simulation/evolution/wrist-fingertip-chamfer.md)：依据实物照片加宽两侧银色指尖前段，保留黑垫、间隙及其他47件；r10原资产和固定交接清单不变。

新增[单张图像到完整表面点云](agent/perception/evolution/image-to-surface-network.md)：已建立固定点数模板与可运行图像网络原型，包含遮挡面的先验补全；端口8890可查看点数对比。网络尚未训练，仅完成前向／梯度／显示检查。[操作](../tutorials/image_to_complete_surface.md)。

## 当前视觉资产复用摘要（2026-11-22）

**当前已接受视觉基线是WVA-01「腕部实拍对齐版」：WG-r15工具49件＋OM-r08模块17件＋SIM-r06插槽参考场景。** Blender／GLB／OBJ与纹理、静态MuJoCo场景、1920×1080鱼眼和实拍对比均已具备，677个外部文件依赖已登记／校验。按[版本纪传体](agent/simulation/evolution/wrist-visual-wva01.md)和[固定清单](../manifests/wrist_visual_wva01_20261122.json)复用；[领域编年](agent/simulation/chronicles/2026-11-22-wva01-assets.md)记录形成过程。

### 历史r10视觉阶段（保留原证据）

该历史组合为 **WG-r10工具＋OM-001/V4 r08模块**；49件工具、17件模块，原r09相机和夹持变换不变，原r07的16件模块主体不变。先读[其他Agent接入说明](agent/simulation/evolution/wrist-assets-handoff.md)，用[固定版本清单](../manifests/wrist_visual_asset_handoff_20261122.json)解析路径／哈希，操作见[独立复现教程](../tutorials/reuse_wrist_visual_assets.md)。

最终004／007／011三个单元的黄色外缘均值10.93→6.17 px，黑臂7.33→7.53 px基本不变；内沿局部点云P90约0.71→1.00 mm的折中有记录。拉环为次要粗补，旧版本及冻结WG-r08保留。新组合通过静态加载／渲染与名义装配检查，尚未替换已验证的机器人、MuJoCo／Isaac接触或训练任务；原控制／训练结果仍按其各自版本理解。

下方视觉资产条目保留开发阶段信息；跨领域任务进度继续分别维护。


新增[WG-r10主体轮廓修正与OM-r08粗补U形拉环](agent/simulation/evolution/wrist-primary-refinement.md)：保留r09相机／夹持变换，只改两侧内沿；最终三单元黄色外缘约10.9→6.2 px、黑臂基本不变，旧任务与资产保留。

感知窗口新增四点结构引导初始化、密集RGB点云和选区高亮，优先解决旧点云初值偏差导致难以精调的问题。首条建议候选可撤销，原标注保留，真实精度仍未认证。[记录](agent/perception/chronicles/2026-11-22-guided-initialization-color.md)。

2026-11-22新增[Isaac接触力与图像改进](agent/simulation/evolution/isaac-contact-visual-review.md)：gentle候选三初态及半步长的到位/退出与10 Hz采样门控通过，seed7峰值21.3→3.04 N；仍有子步尖峰和两次工具会话收尾异常。实际512×512双相机、768静态对照与40.6秒清晰视频已保存，未作真机成像标定。

此前[固定r09位姿与开度试验](agent/simulation/evolution/wrist-pose-study.md)：镜头微调只改善部分指标，未替换主版本；模块相对位置随单元变化，且当时绿色件缺U形连接，不能仅靠全局相机位姿解决。

位姿窗口更新：已将点云与腕部像素调节拆为两组常显XYZ／RPY控件，支持独立调整、恢复和保存；原始点云固定。外参需显式应用，不自动覆盖精调结果。[教程](../tutorials/head_wrist_pose_review.md)。

2026-11-22新增[Isaac Sim同源SIM-r06插接实验](agent/simulation/evolution/isaac-contact.md)：PGS局部7项与机械臂3初态规则循环通过，RTX双相机及36.9秒视频已生成。seed7控制采样力峰值约21.3 N，尚未满足学习评估10 N门控；未运行Isaac BC/RL。

新增[WG-r09多视角点云约束候选](agent/simulation/evolution/wrist-pointcloud-refinement.md)：r08已完整冻结保留；11视角点云支持修改8件局部mesh，镜头和夹持变换不变，黑臂轮廓改善明显，黄色与相机残差仍保留。

最新感知工具：[逐条头部点云／腕部位姿调节](agent/perception/evolution/head-wrist-pose-review.md)已实现并打开窗口。287组可切换；复用五组旧点云并实际生成一组新点云；两个对象独立六轴调整、结构点精修、外参候选及保存恢复通过功能检查。首条演示并非准确位姿，未完成批量定位或标定。[操作教程](../tutorials/head_wrist_pose_review.md)。

后续[整块轮廓诊断](agent/simulation/evolution/wrist-contour-diagnosis.md)确认：约3 px只适用于选定边缘；靠腕部黑臂每侧仍偏内约49～54 px，黄色外缘约18～28 px。优先查局部mesh／装配并联合复核相机，未将诊断探测相机作为新资产。

新增[WG-r08腕部投影对齐候选](agent/simulation/evolution/wrist-alignment.md)：调整镜头安装、同步移动相机壳／短颈和参考夹持变换，夹爪几何保留；4个留出单元选定边缘约16～18→3 px，完整画面和绿色拉环仍未一致。

当前优先任务（2026-11-22）：用户要求回到**腕部图像光模块位姿估计＋头部双目点云约束**。已阅读新备份说明、数据总览、开发记录与头腕采集总结，并查看代表图；接续顺序与未标定边界见[感知任务记录](chronicles/2026-11-22-perception-priority.md)。本次没有新增位姿精度验收，Isaac／RL工作保留为后续方向。

最新[尺寸与腕部图像核对](agent/simulation/evolution/wrist-camera-consistency.md)：网格尺寸符合建模参数，但真实尺寸未认证；当前针孔与真机不一致，同位姿鱼眼候选仍有黄色区域、掌部遮挡和绿色拉环差异，尚未完成外参／夹持关系校准。

历史阶段的[WG-r07照片轮廓修正版](agent/simulation/evolution/wrist-tool-photo-profile.md)：双峰黄色衬垫、中央凹口与收窄指臂，侧视复核衬垫厚度27→12 mm；49件检查通过，基体／相机保持r06不变，旧资产保留。

历史阶段的[WG-r06黄色衬垫修正版](agent/simulation/evolution/wrist-tool-refinement.md)：按用户反馈去掉偏红色调，49件几何保持r05不变；旧资产保留。

新增[WG-r05腕部相机／夹爪精修资产](agent/simulation/evolution/wrist-tool-refinement.md)：综合新双目数据与旧照片／视频，49件几何与导出验证通过，提供独立相机、夹爪GLB和MuJoCo开合预览。尺寸为建模估计；尚未验证新工具插槽路径、真实抓取或新策略。

11月22日数据说明及采集开发记录已同步到[docs/data/nov22](data/nov22/README.md)，源文档逐文件哈希一致，原图／MCAP保留在外部数据目录。

新增[11月22日采集数据初检](chronicles/2026-11-22-new-capture-intake.md)：15单元287组／1148图本机检查通过；两段约30秒工具建模MCAP已定位。该批腕部标定、mesh位姿和训练标签仍未建立，未直接用于新训练。

本轮统一接续入口：[2026-11-22完整进展](chronicles/2026-11-22-simulation-mesh-visual-progress.md)。最新展示为r07无颗粒材质，已完成[真机同区域对比](/data/omi_runtime/runs/module_v4_plain_material_20261122/real_vs_r07_plain_comparison.png)。新尺寸规则成功、旧场景策略成绩和静态混合视觉分别记录；新组合尚未重新训练。

2026-11-22最新[V4-r07纯色银灰材质候选](agent/simulation/evolution/module-material-r06.md)：修正金属偏蓝、胶塞近纯黑和拉手色调，保留r06色调并按用户要求去除新增颗粒贴图；18件几何与r05一致，旧文件哈希不变。同视角颜色拟合有改善，未作色彩标定或训练验证；已采用基线仍为r05。

2026-11-22：[混合腕部图像预览](agent/simulation/evolution/hybrid-wrist-preview.md)整体观感得到用户正向反馈；用户进一步指出黑色指尖接触面才夹持模块，已补回这两处真实像素并另存修正图。[开发进展](chronicles/2026-11-22-hybrid-wrist-contact-review.md)已归档，静态效果不代表动态映射、物理抓取或训练验收。

新增[视频参考腕部相机与夹爪](agent/simulation/evolution/wrist-camera-gripper.md)：独立WG-DAIMON-VIS-r04外观资产及新MuJoCo场景已打开，镜头对应真实渲染位置；31件网格检查、相机／关节绑定和两个初态规则循环通过。模块仍固定附着，工具接触／触觉／鱼眼未标定；[窗口与视频操作](../tutorials/wrist_camera_gripper.md)。

最新新尺寸仿真为[SIM-r06：V4-r05＋18.8 × 8.8 mm插槽](agent/simulation/evolution/measured-v4-simulation.md)，正面窄边暂按6.9 mm定位（测量口径待进一步确认）。局部插入／退出、反例与半步长检查通过，机械臂规则循环3/3，双相机有效。旧BC／RL直接迁移各0/2，未按新几何重训；[视频与操作](../tutorials/measured_v4_simulation.md)。

Mesh建模与修订的当前实现已专门整理到[Mesh开发记录](mesh-development.md)，并同步原有[Blender资产管线](agent/simulation/evolution/asset-pipeline.md)，包含18件组织、坐标与导出、空腔／拓扑验证及尚未接入的新碰撞资产范围。

当前光模块暂定外观基线为 **V4-r05「双窗尾槽版」**，已由用户于2026-11-21确认暂时采用。尾端三个金属端之间的两个窗口为空，黑色胶件保留较低的双脚；主体参考截面18.1 × 8.2 mm、下部尖端8.0 mm。命名未改变模型，后续从此版另存新修订；[完整开发过程、纠正和恢复入口](chronicles/2026-11-21-v4-double-window-baseline.md)，持续事实见[V4记录](agent/simulation/evolution/module-v4.md)。

既有训练任务仍保留SIM-r03旧通道19.0 × 9.6 mm及旧模块参考截面，旧成功率只属于旧几何。新的18.8 × 8.8 mm组合已完成上述规则仿真验证，内部结构和真实接触仍需标定。V2、V3、MEASURED-r01及V4-r01～r05均保留。

本轮真实感知已整理为[完整接续交接](chronicles/2026-11-21-perception-progress-handoff.md)，并保存感知范围的源码/文档/主要证据快照。当前采用归属过滤后的四组结构，marker 停用，精确位姿尚未验收。

2026-11-21 用户指出右侧结构点混入夹爪；已完成[模块/夹爪边缘归属过滤](agent/perception/chronicles/2026-11-21-structural-edge-ownership.md)并重跑 61 帧。右侧头部线支持不足，当前不使用，保留四组结构；marker 仍屏蔽。分割与候选位姿均未作真实精度认证。

仿真器的当前模型、碰撞、控制、相机、训练与问题直接维护在[仿真器专门记录](simulation.md)及对应领域能力文档；跨领域接续快照见[当前进展、结果、问题和路径](chronicles/2026-11-21-current-progress-handoff.md)。下面保留带日期的形成过程；旧预插入／短试跑与最新接触策略不能混为同一验收结果。

2026-11-21 用户要求忽略附加 marker；当前主线为[模块固有结构线](agent/perception/chronicles/2026-11-21-markerless-structural-features.md)。已在 61 帧提取五组壳体/头部/黑色端壳边缘并生成候选，9 项标贴替换不变性检查通过。遮挡后位姿仍不可靠，已拒绝发布不充分约束下的新六维观测；精确插入定位尚未完成。

2026-11-21 新增[光模块候选特征与鱼眼跟踪原型](agent/perception/evolution/mesh-feature-tracking.md)：原分辨率视频 61 帧、三段 episode 共 541 帧及受控遮挡测试已运行。当前默认只做二维观测更新，深度/旋转沿用先验；三维绑定不准和自由六维漂移尚未解决，实验六维模式默认关闭。用户随后明确不使用附加标贴，该路线停用，不再等待贴位确认。

最新对照已完成：10个BC训练回合、两组20回合带规则接管RL及无接管评估已实际执行。旋转加权BC验证2/2成功；在两批共8个不同测试／确认初态中，BC为7/8、第一轮RL为8/8。另一RL组合与等数据额外BC均在首批测试0/4，不采用；小样本不能保证任意任务10＋20成功。见[完整进展、资产说明、成功视频与问题](chronicles/2026-11-21-contact-policy-improvement.md)和[训练纪传](../../omi_proj/docs/agent/training/evolution/contact-intervention-study.md)。下文旧22次更新阶段的0/2是历史试跑，不能继续代表最新策略状态。

2026-11-21 用户进一步明确目标为[插接过程的局部视觉位姿与遮挡跟踪](design/visual-insertion-local-tracking.md)：将视觉特征绑定到 mesh，在面向/粗位姿/夹持先验下估计模块相对金属插口的位姿，推算隐藏插接端。已实现两端位姿到局部偏差/插入深度的纯几何换算并通过合成检查；遮挡跟踪、物理精度和插入成功判定尚未验证。

2026-11-21 用户明确正反面可作为先验，要求精细连续位姿；已进行[固定面向的纹理/端部细化](agent/perception/chronicles/2026-11-21-known-face-fine-pose.md)。三个视角的检查角点仍约 2.8–3.5 px，端部轮廓 P90 约 5–7 px；尚未达到精细结构对齐要求，不能宣称精确位姿已实现。位置/角度容差尚待用户明确。

接触资产交付阶段：保留现有mesh，创建独立 **SIM-OM001-OS001-r03** 并通过局部／机械臂规则插入退出。该阶段22次更新的视觉短试跑为0/2；随后10BC＋20接管RL已得到上方的新结果。原V3／r04完整刚体阻挡结论保持。见[资产能力](agent/simulation/evolution/contact-simulation-asset.md)、[操作](../tutorials/contact_simulation.md)、[阶段记录](chronicles/2026-11-21-contact-asset-completed.md)及[开发前卡点](chronicles/2026-11-21-simulation-asset-start.md)。

新增（2026-11-21）：按用户最新优先级完成[实际mesh插入检查](agent/simulation/evolution/mesh-insertability.md)。修复碰撞导出退化面／开放端口，并验证孔形分解；完整刚体仍在约4.212mm被入口弹片挡住，**完整插入未通过**。只有排除入口组件的主体诊断能到51.282mm台阶，不能计为插入成功。下一步应修入口弹片／横向卷边的几何和接触，让主体通路与完整接触分别验收。

2026-11-21 用户未认可上一轮双目位姿质量；[局部结构复核](agent/perception/chronicles/2026-11-21-stereo-pose-structure-review.md)确认 0885 虽 IoU 0.886，附着标贴跨帧投影偏差仍约 75 px，朝向不可靠。扩展候选能修正该例却会翻错其他帧；人工局部特征约束仅为诊断，自动算法尚未通过结构验收。

2026-11-21 已完成[真实双目点云初值＋像素联合精修](agent/perception/chronicles/2026-11-21-stereo-cloud-pixel-trial.md)：从 59 组同步光模块样本中测试 11 组，重新执行 22 次 FoundationStereo 前向，再由点云求初值，未沿用旧物体位姿或 PnP。RGB mask IoU 均值 0.814→0.918，检查点 P90 的逐帧均值 0.344→0.371 mm；4 帧仍有近似候选。绿色挂件排除、模型尺寸固定。数据曾参与 V3 尺寸估计，不能作为独立泛化或真实 6D 精度认证。

新增（2026-11-21）：[规则示范与视觉辅助训练](agent/simulation/evolution/rule-demonstrations.md)。规则老师经 IK／伺服完成 16/16 预插入回合、824 条动作；生成全景＋双相机视频，完成200次视觉 BC及规则／在线经验混合训练。数据明确标 scripted，不冒充 human；闭环视觉策略尚未在留出初态成功。[观看及命令](../tutorials/rule_demonstrations.md)。

2026-11-21 已实际运行 [Video to Data 腕部试验](agent/perception/chronicles/2026-11-21-video-to-data-wrist-trial.md)：SAM2／MoGe 各 61 帧，FoundationPose 两种入口各 7 帧；直接预测深度分支贴合失败。SAM2＋自编有界像素精修 61 帧，掩码拟合 IoU 均值 0.657→0.914，非位姿真值精度。此轮仍用图像 PnP 初值，没有头部点云到腕部外参；绿色挂件排除，模型尺寸固定。

新增（2026-11-21）：[双相机 MuJoCo → OMI 视觉训练链路](agent/simulation/evolution/visual-training.md)已经实际运行。真实 URDF＋V3 固定附着＋r04，头部／腕部 RGB 实际输入，state／tactile padding；共 300 条经验、20 次 SAC 更新，包含独立进程续训、权重回用和 checkpoint 校验。当前无接触预插入，策略评估未成功。接续用[新教程](../tutorials/dual_camera_training.md)。下文旧原型“未训练／未附着”描述仅适用于保留的 11 月 20 日场景。

新增（2026-11-21）：[插座点云粗配准及 NVIDIA Video to Data 评估](agent/perception/chronicles/2026-11-21-socket-cloud-and-video-to-data.md)。已显示独立拟合的插座与已翻面模块；绿色挂件不参与配准、默认隐藏。插座检查点 P90 4.31 mm、原始选区 P90 11.33 mm，仅为粗解；默认解中模块更接近另一侧开口，未确认金属通道对应。Video to Data 已做源码评估，尚未运行。

用户正反面纠正（2026-11-21）：点云叠加默认已改为槽面朝采集相机，插入端仍朝插座；当前结果目录为 `/data/omi_runtime/runs/pointcloud_v3_overlay_20261121_face_corrected`。旧默认解保留，朝向来自用户先验，未认证绝对位姿精度。

2026-11-21 感知新增：已在用户指定的同一 HTML 点云及已确认选区重跑当前 V3 主体配准，完整 15 部件叠加页面已打开并验证。默认按插接场景选择头尾，正反面仍有歧义；保留全部 10 万原始点，模型未缩放。见[点云叠加记录](agent/perception/chronicles/2026-11-21-v3-pointcloud-overlay.md)。

核对日期：2026-11-20。工程基线 ENG-001～003 已完成；其 GPU smoke／2×2 验证见历史记录。后续新增插接座 r04 候选、实际 V3 插入检查、真实双臂／夹爪 URDF 场景、Gym 到达接口和交互查看。没有运行 RL 训练或硬件控制。

最新接续见[插接资产与机械臂仿真阶段交接](chronicles/2026-11-20-robot-simulation-progress.md)。本轮代码和文档尚未提交，早期重启 bundle 不含这些工作。此前 Blender 会话备份与旧恢复步骤仍见[重启交接](chronicles/2026-11-20-restart-handoff.md)，完整历史保留，能力事实以领域纪传体为准。

## 已完成范围

| 领域 | 当前已验证状态 | 详细入口 |
| --- | --- | --- |
| 项目基础 | 本地 Git 与公开远端建立；main 空分支；主 CLI、两种 smoke 及控制层测试有记录 | [架构](design/project-architecture.md) · [CLI](agent/interfaces/cli.md) |
| 感知 | 官方双目与原生组件检查、已圈选目标 CPU 配准、V2 冻结几何回放通过 | [领域摘要](agent/perception/current.md) · [双目](agent/perception/evolution/stereo-and-backends.md) · [配准](agent/perception/evolution/confirmed-registration.md) |
| 数据与恢复 | 00–05 及 OMI／portable／quick 共 9 包均已校验解压，两个 data／DATA 目录完整恢复 | [数据与回放](agent/perception/evolution/data-and-replay.md) · [解压索引](../manifests/extracted_archives.json) |
| 仿真 | Blender 模型与导出、单模块／2×2 的 MuJoCo 渲染及 PhysX CPU 测试通过 | [领域摘要](agent/simulation/current.md) · [资产](agent/simulation/evolution/asset-pipeline.md) · [场景](agent/simulation/evolution/engine-scenes.md) |
| 机器人资源与原型 | 完整双臂／夹爪 URDF 已导入 MuJoCo，参考场景、6D TCP→IK→伺服的小幅到达与 Gym 接口检查通过 | [机器人资产](agent/simulation/evolution/robot-assets.md) · [开发计划](design/robot-rl-development-plan.md) |

## 当前状态边界

数据恢复完成与算法全链路复现是不同状态。光模块真实录制尚未在本机重新执行完整双目／59 帧尺寸／在线重建流程；组件检查、条件配准或冻结几何回放不能替代这些验收。

机械臂与夹爪已组合到含光模块／插接座参考外观的 MuJoCo 场景，但当前机器人接触关闭、模块未被夹持，工具坐标与动力学待核对。早期光模块原型的碰撞仍是简化代理，质量／摩擦为假设。Isaac RTX、真实插接接触、实物位姿精度及真机动作均未验收。

04 的 Python 3.11.18／Torch 2.7.1+cu128 原环境已恢复，但未执行 conda-unpack 或兼容性验收；当前 envs 中已验证的开发环境保持不变。OMI 包的完整逐样本／Actor 校验、BC／RL 重新训练也未执行。

主 CLI 现有 doctor、两种 smoke 和 simulate mujoco；doctor 的 ready 只代表路径检查。便携配准、Blender 和 Isaac 仍走独立脚本，详见[能力表](capabilities.md)和[教程](../tutorials/README.md)。

## 当前工作与下一步

最新腕部感知诊断（2026-11-21）：已核对文档中的 ROI 裁剪和采样，沿用所给内参，对真实 9 回合做 V3 粗位姿与 mesh 回投影；完整帧库导出 1682 张腕部图、生成 72 张代表性叠加图。1572 个控制时刻中 949 为粗候选、280 带风险、343 拒绝；这不是准确率，抽查发现低拟合误差但错配到插座的情况。相机系位姿为未独立验证的条件估计，记录末端位姿仍单列。见[批量记录](agent/perception/chronicles/2026-11-21-episode-mesh-batch.md)。

用户最新优先级：先搭真实机械臂仿真和 RL 软件架构，尽快做可运行小版本。完整厂商 URDF 双臂／夹爪已导入 MuJoCo，配有圆桌和 r04／V3 静态参考资产；6D TCP 增量经 IK／伺服的小幅到达与 Gym 接口检查通过。当前接触关闭、抓取及工具 TCP 待核对，未运行 RL 训练；代理夹具只作回归。下一步为机械臂夹持模块的预插入到达。见[开发计划与难度](design/robot-rl-development-plan.md)、[原型教程](../tutorials/robot_sim_mvp.md)。

当前插接座候选为 **r04**：按用户要求从 r03 的 18.60 mm 略放宽至 **19.00 mm**，白色孔口宽 **20.60 mm**，相对未改动的 V3 单侧名义间隙约 **0.41 mm**。已另存、重开、重跑插入几何检查并在 Open3D 显示完整下部。台阶限位仍约 51.28 mm；候选尺寸未独立测准，弹片让位未验证。见[r04 清单](../manifests/socket_r04_20261120.json)与[当前教程](../tutorials/v3_socket_insertion.md)。

孔宽归因补充：候选没有独立图像／点云定量拟合依据，不能先认定 V3 尺寸正确而只改插座。已复算原 59 视角统计比较模块放宽假设，仍存在共同尺度和双方误差可能。复核时曾回到 r01，当前按用户略放宽要求显示 r04；历史候选保留，见[证据复核](agent/simulation/evolution/v3-insertion.md)。

V3 插入关系：用户确认照片中的机械终点由较大头部台阶限位，模型对应约 51.28 mm；全刚体约 4.21 mm 已接触弹片，未模拟弹性。背面结构保留，r02 平背面不采用；r03 收紧候选保留供对照，当前 r04 略放宽。路径／包含／间隙检查和 Open3D 深度交互已执行，见[V3 插入记录](agent/simulation/evolution/v3-insertion.md)。

插接座查看已改用 Open3D 双视图，默认原 TSDF 对照保留背面结构的 r01；V3／r04 组合另有可调深度的[插入查看器](../tutorials/v3_socket_insertion.md)。桌面显示与交互已检查。

光模块插接座（OS-001）已比较原 TSDF／人工清孔 SDF，并从 MCAP 提取 28 帧精确同步的 RealSense 原生深度，与已有双目缓存复跑 21 项尺寸对照。不同来源结果有差异，孔内尺寸仍缺乏稳定约束；历史 r02 平背面未采用。原模型、各候选与 V3 均保留，见[插接座能力](agent/simulation/evolution/optical-socket.md)及[修订清单](../manifests/socket_assets.json)。

用户已确定 **V3（Blender）为主模型，V2 为辅助参考与对比**。V3-r01 对应现有连通槽几何，已建立冻结副本与独立工作副本；未改变几何和精度结论。具体见[资产版本](asset-versions.md)与[ADR 002](agent/simulation/decisions/002-blender-v3-primary.md)。

ENG-001 已完成：仿真、知识库和基线记录纳入本地 `dev`；两个后端适配分别提交在 `feature/local-runtime-baseline`，四仓库源码 bundle 均成功恢复。原工作区与恢复副本各 4 项控制层测试通过，两项 GPU smoke 通过；见[基线说明](design/source-baseline.md)和[新阶段记录](chronicles/2026-11-20-source-baseline.md)。未推送，远端默认分支仍不含这些本地提交。

ENG-002 已完成[运行与产物合同 v1](agent/interfaces/run-contract.md)：三项流程规则、11 个合成示例、27 个反例及严格 JSON 检查通过，现有 4 项控制层测试通过。该阶段只读核对旧报告；后续 ENG-003 已接入运行层，旧报告转换器仍待实现。原阶段见[记录](chronicles/2026-11-20-run-contract.md)。

ENG-003 已完成，14 项控制层测试通过，两个 smoke 与 MuJoCo 2×2 的执行／产物／验收均通过，见[验证清单](../manifests/workflow_validation_20261120.json)。资产另已建立[版本名称](asset-versions.md)及[完整图册入口](visual-results.md)，模型原文件哈希保持不变。

1. 下一项 ENG-004：将 CPU 回归与合同检查纳入自动流程，并规范 GPU／仿真证据关联。
2. 选择机器人／工具配置，核对轴、TCP、限位、惯量、夹具与精细碰撞，然后接入当前场景。
3. 分别推进完整重建、Blender 生成、Isaac RTX／GUI 和 OMI Actor／数据合同检查，保留每项独立证据。
4. 历史环境是否需要启用单独决定，不作为继续使用当前环境的前置条件。

运行层最新干净版本与中断回收补强后的复验见[最终验证](../manifests/workflow_final_validation_20261120.json)。

资产查看器另修复了桌面 Chrome 无 WebGL 时的空白问题，已加入 CPU 网格渲染并核对真实桌面画面；详见[兼容性验证](../manifests/viewer_compatibility_validation_20261120.json)，资产几何与能力精度结论不变。

进展形成过程见[全局快照](chronicles/README.md)、[感知编年](agent/perception/chronicles/README.md)和[仿真编年](agent/simulation/chronicles/README.md)。

原电脑的 Open3D 原生查看器也已在本机打开，实际显示历史 V2 mesh；启动方式与 V1／点云切换范围见[原生查看教程](../tutorials/native_mesh_viewer.md)。这不是当前 V3（旧别名 GROOVE-r01） 的几何更新。
