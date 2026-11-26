# System1 训练与路径可视化

## 2026-11-26修正候选：末段沿孔轴接近

用户指出线条看起来没有瞄准入口。进一步检查发现：旧规则的终点位置和模块朝向正确，但未约束到达方向；三例最后两个尖端采样点的移动方向与孔轴夹角为68.677／59.083／44.529°。此前解释只强调夹爪中心与尖端不同，没有充分说明这一规则局限。该偏差不是二维投影错位；旧路径在预插入位姿处仍需切换运动方向，不能将“终点对准”直接解释为“沿孔轴接近”。

新增独立候选 `build_axial_system1_gt.py`：在插座坐标中构造名义模块尖端的轴向单调推进和平滑横向修正，SO(3)朝向同时平滑到目标；尖端距孔口25 mm时完成对准，后续20 mm固定朝向沿孔轴直线接近到入口前5 mm。再由当前固定夹持变换换算为TCP和夹爪中心位姿。前段使用65点，后段20个新增点，共85个位姿；该采样是候选几何检查分辨率，不是32点运行时接口。起点已越过对准平面时拒绝此规则，需要另行设计退回策略。

三例末段偏轴角均为0°（浮点精度），横向偏差小于1e−10 mm；255个位姿均通过原厂IK和回代，最大误差0.00366 mm／0.00140°。FCL检查了这些采样位姿下夹爪／模块可视网格与插座装配的相交，255处均未相交，模块所有顶点到孔口平面的最小间距约5 mm。此检查不包含连续碰撞扫掠、机器人自碰撞、完整环境或动力学，因此仍不是已验证插接轨迹。

展示新增橙色模块尖端线、灰色孔轴和绿色孔口中心标记，紫色仍为夹爪中心线；两条轨迹的末段平行，表达同一刚体运动。另有起点／孔口前25mm完成对准／入口前5mm的实体姿态对照。交付 `/data/shapeforge/runtime/runs/hier_s1_gt_axial_20261126_v2/`，v1和原路径保留。v2仅增补孔口标注，位姿数组与v1逐值相同，保留同一几何检查结果。**候选未接入运行时ReferenceProvider或训练，未做物理路径执行。**

[修正后的2D／3D图](/data/shapeforge/runtime/runs/hier_s1_gt_axial_20261126_v2/case_01_corrected.png) · [三时点实体图](/data/shapeforge/runtime/runs/hier_s1_gt_axial_20261126_v2/corrected_poses.png) · [证据](../../../../manifests/system1_axial_gt_candidate_20261126.json)

## 2026-11-26：移动与旋转起点后的GT独立展示

后续用户认为图义不清，追问是否已规划好。明确纠正命名：这是“基于GT几何生成的规则接近位姿路径”，并非经完整规划／连续避障／物理执行验证的专家轨迹。旧图的资产停在初态，仅叠加未来夹爪中心线；夹爪中心终点不在孔口，容易误读。新增[三时点实体解释图](/data/shapeforge/runtime/runs/hier_s1_gt_explained_20261126_v1/gt_explained.png)，把70 mm案例资产分别摆到0／50／100%的参考位姿，标记当前中心与模块尖端。对应尖端距孔口70.0／33.2／5.0 mm，夹爪中心距孔口140.4／106.8／79.4 mm（轴向）。这些是静态参考姿态重渲染，不是新执行回放；输出目录 `hier_s1_gt_explained_20261126_v1`，原图保留。

用户要求先把对象移动、旋转，查看System1 GT效果。本轮插座固定，通过普通IK／PhysX动作移动夹爪和固定夹持模块到三组新起点：尖端距孔口50／70／90 mm，横向−20／+20／−15 mm，高度+12／−12／−15 mm，合成角度偏差20.806／23.831／19.721°。输入配置 `configs/system1_gt_pose_probe_20261126.json` 的 `rotation_deg` 是插座坐标系下的旋转向量角度分量，不是XYZ欧拉角。种子150000～150002；2555步准备加12步保持，teacher请求0，最大准备位置误差0.03710 mm、朝向误差0.00829°，worker退出0。

交付仅显示紫色GT规则接近路径和夹爪中心XYZ三轴，二维与三维同源。原规则仍是TCP直线平移＋平滑旋转插值，再换算至夹爪中心；终点是预插入位姿，未沿GT执行插接。3条路径的99个采样位姿分别通过原厂IK、关节限制／连续性与FK回代检查；最大回代误差0.00366 mm／0.00141°。该离线检查不包含连续碰撞扫掠或接触动力学，不能据此标记整条路径安全或插接成功。

物理记录 `/data/shapeforge/runtime/runs/hier_s1_gt_pose_20261126_v1/`；资产底图 `hier_s1_gt_pose_assets_20261126_v1/`；GT交付 `hier_s1_gt_pose_visual_20261126_v1/`，均在相同runs根下。采集沿用冻结模型探针并保存其原始推理，最终PNG和Blender明确只保留GT，不把模型预测改称GT。新增 `--cases-json`／`--seed-start` 定义诊断起点，渲染用 `--only-gt`，既有默认采集配置保留。无训练。

15组姿态标注通过生产参考及独立鱼眼投影核对，最大投影差2.85e−13显示像素；源哈希保持。轻量回归95项：29通过、66跳过。[三例总图](/data/shapeforge/runtime/runs/hier_s1_gt_pose_visual_20261126_v1/three_gt_starts.jpg) · [70mm案例](/data/shapeforge/runtime/runs/hier_s1_gt_pose_visual_20261126_v1/case_01_gt_orientation.png) · [证据](../../../../manifests/system1_gt_pose_visualization_20261126.json)。

## 当前展示坐标约定：夹爪中心、X向前、Z向上

2026-11-25用户进一步指出模块可能滑动、不能保证精确估计其位姿，要求原点改到夹爪正中心。当前展示采用两指接触垫包围盒中心的中点，按原固定开度计算，约为原TCP系 `(0,0,198.5)` mm；此TCP原点是法兰参考，夹爪中心与其不是同一点。轴向由工具自身定义：`X_new=Z_TCP`、`Y_new=-Y_TCP`、`Z_new=X_TCP`，即X向指尖前方、Y向左、Z朝夹爪上方。变换 `T_TCP_from_gripper_center` 完全由夹爪几何和运动学得到，不依赖模块的位姿或夹持变换。

曲线与三轴共同跟踪夹爪中心。展示默认 `--frame gripper-center-forward`；模块中心和尖端模式保留为显式历史选项。新目录 `/data/shapeforge/runtime/runs/hier_s1_gripper_frame_20261125_v1/` 含三例6张对照及3份Blender场景。26组坐标与生产TCP参考换算核对，原点最大差7.28e−6 mm、旋转矩阵元素差1.31e−8、独立鱼眼投影差4.02e−13显示像素；另在检查副本中修改模块位置和旋转，确认夹爪坐标系保持不变。

该中心是当前仿真工具的几何定义，未完成真机工具中心标定。底层模型、路径解码与动作合同仍为原固定夹持原型，本次只改显示参考点，不代表已处理滑移；模块相对夹爪的位姿变化仍需感知或接触反馈，并影响目标生成与接触控制。后续正式接口应区分夹爪参考、原TCP动作和动态夹持关系，不能只换原点名称而忽略六维变换。[设计修正](../../../design/system1-system0-path-conditioned-rl-discussion.md#夹爪参考点与模块滑移2026-11-25后续修正)

[夹爪中心预测图](/data/shapeforge/runtime/runs/hier_s1_gripper_frame_20261125_v1/case_01_pred_orientation.png) · [GT图](/data/shapeforge/runtime/runs/hier_s1_gripper_frame_20261125_v1/case_01_gt_orientation.png) · [证据清单](../../../../manifests/system1_gripper_frame_visualization_20261125.json)

## 历史展示坐标约定：模块主壳体中心

2026-11-25用户要求将红X改为向插入前方，蓝Z朝上，原点置于光模块正中央。新展示默认采用主壳体包围盒中心（下壳、左右侧壁、上壳；排除拉环、可拆尾塞及局部凸起附件），不是质量中心。新基底相对原模块坐标为 `X_new = -Y_old`、`Y_new = X_old`、`Z_new = Z_old`，保持右手系；Z表示模块自身上方，随姿态转动。曲线同步改为壳体中心轨迹，避免将中心坐标轴放在尖端轨迹上；中心在壳内，以透视标注显示。

该变化仅是展示参考点与基底的刚体变换，原TCP参考、网络权重、插接合同和源网格保持。当时采用 `--frame body-center-forward`，现作为历史显式选项；尖端版可显式 `--frame tip-native`复现。三例6张对照和3份含中心轨迹及三维箭头的Blender场景保存在 `/data/shapeforge/runtime/runs/hier_s1_orientation_center_20261125_v1/`。26组坐标与生产参考核对，原点差最大7.45e−6 mm，旋转矩阵元素差1.31e−8，独立鱼眼投影差3.22e−13显示像素；主壳体中心、轴向和右手系已核对，源哈希保持。

[中心坐标系预测图](/data/shapeforge/runtime/runs/hier_s1_orientation_center_20261125_v1/case_01_pred_orientation.png) · [GT图](/data/shapeforge/runtime/runs/hier_s1_orientation_center_20261125_v1/case_01_gt_orientation.png) · [证据清单](../../../../manifests/system1_center_frame_visualization_20261125.json)

## 2026-11-25续：沿途orientation三轴

用户初步认可远距离版本的显示逻辑，并要求每隔几个点增加表征orientation的坐标系箭头。复用三组远距离冻结预测，在原33点接近参考的0／8／16／24／32号位姿显示局部三轴；坐标原点位于模块尖端中心，旋转为参考TCP旋转乘固定TCP→模块旋转。红／绿／蓝分别为模块+X／+Y／+Z，插入方向为−Y，轴长6 mm。箭头不是位置曲线的切线；不重新定义模型输出或改变路径。

预测和GT各出一张3D资产／2D腕图对照，避免两套三轴重叠；三例共6张完整对照图和3份包含真实三维圆柱／锥体箭头的Blender场景。40 mm案例的预测接近段不足12 mm，仅显示末端坐标系，避免5组三轴挤在一起；其余路径每隔8点显示一组，共26组。输出：`/data/shapeforge/runtime/runs/hier_s1_orientation_20261125_v1/`，旧版本保留。

与实际 `ReferenceProvider.features` 生成的参考核对，最大原点差7.65e−6 mm、旋转矩阵元素差1.31e−8；箭头方向与旋转矩阵列向量一致，OpenCV独立鱼眼投影最大差5.68e−13显示像素，源哈希保持。仅增加姿态可视化，未新增训练或执行预测。脚本 `render_system1_orientation.py`，检查入口 `audit_system1_orientation.py`；[证据清单](../../../../manifests/system1_orientation_visualization_20261125.json)。

[65mm预测姿态图](/data/shapeforge/runtime/runs/hier_s1_orientation_20261125_v1/case_01_pred_orientation.png) · [同起点GT姿态图](/data/shapeforge/runtime/runs/hier_s1_orientation_20261125_v1/case_01_gt_orientation.png)

## 2026-11-25续：更远、未对准的起点与渐变路径

用户进一步要求增大起点距离，不要一开始对准，并参考提供的视觉规划图改进2D／3D轨迹画法。新增 `probe_system1_far.py`，使用普通IK／PhysX动作先退开，再移动和转动到三组固定诊断起点；冻结第47轮模型读取到位后的实际双RGB。没有重训或执行预测路径，也没有请求teacher。

| 孔口前距离 | 横向／高度偏移 | 实际角度偏差 | 插座位姿平移／旋转误差 | 解码接近终点与GT差 |
| --- | --- | --- | --- | --- |
| 40 mm | −15／+10 mm | 10.814° | 38.745 mm／10.846° | 38.392 mm |
| 65 mm | +20／+15 mm | 14.427° | 79.196 mm／14.338° | 40.910 mm |
| 90 mm | −25／−12 mm | 17.489° | 96.293 mm／17.505° | 57.050 mm |

三例准备均到位，TCP最大位置误差0.03683 mm、朝向误差0.00994°；准备动作2138步（另有12步保持），worker原生退出0。该范围当前模型仍明显失效；三例是指定范围的诊断，不代表统计成功率。不能把后续GT参考或画图平滑解释为模型已学会远距离接近。

新版展示采用较宽三维资产视角、白色描边的蓝→青渐变预测、紫色虚线GT、末端箭头和起点标记；另有等比例纯三维空间图。展示的是现有几何解码器从起点到预插入位姿的整段参考，保留原33点折线并沿弧长重采样，仅改变画法，没有人为弯曲或替换预测。原型仍发送8点短段，不因图中完整曲线而改变动作接口。二维为真实128×128腕图放大，曲线穿透遮挡，非高分辨率新传感器观测；三维按对应记录重建，固定夹指开度与展示光照约定不变。

物理诊断目录：`/data/shapeforge/runtime/runs/hier_s1_far_20261125_v1/`；展示交付：`/data/shapeforge/runtime/runs/hier_s1_far_visual_20261125_v2/`。v1展示视角保留；v2调整观察方向，避免前后距离被投影重叠掩盖。生成入口为 `render_system1_far.py`；独立检查 `audit_system1_assets.py <输出> --wide`。三例鱼眼投影独立检查最大差5.93e−13显示像素，Blender正交投影核对最大差0.000133像素，源文件哈希保持。轻量回归95项：29通过、66跳过。

[65mm起点大图](/data/shapeforge/runtime/runs/hier_s1_far_visual_20261125_v2/case_01_wide_comparison.png) · [三组对照](/data/shapeforge/runtime/runs/hier_s1_far_visual_20261125_v2/far_starts.jpg) · [纯三维空间图](/data/shapeforge/runtime/runs/hier_s1_far_visual_20261125_v2/paths_space.png) · [证据清单](../../../../manifests/system1_far_visualization_20261125.json)

## 2026-11-25续：实体资产与二维投影对照

用户指出原三维图只有孔口框线，缺少实体空间参照。本次复用九位置冻结记录与对应的 `staged_contact_20261123/robot_transfer` 原始可视网格，在Blender中重建夹爪、模块、插座装配，生成每例的三维全景、孔口近景和原始腕图投影，共9张2304×1296对照图、九位置总图与9份可旋转检查的 `.blend` 场景。历史图像保留，新输出为 `/data/shapeforge/runtime/runs/hier_s1_assets_20261125_v1/`。

三维场景使用记录的TCP／插座相对位姿；夹指使用原传递包的固定名义开度。材质色来自原传递包，Blender光照仅用于空间展示，不声称复现RTX光度。原始腕图128×128直接放大5倍，沿原鱼眼K／D、389像素ROI和实际128点采样映射投影。两侧展示同一条模块尖端参考，橙色预测、绿色GT、紫色当前尖端；粗线8点、细虚线后续参考，显示至实际入口后6mm。完整剩余路径仍保存在场景数据和Blender曲线中。三维图对被网格遮挡的参考用虚线透视标注，腕图不做遮挡消隐。

独立OpenCV投影核对最大差约3.98e−13显示像素；Blender投影与独立正交投影最大差约8.65e−5像素；重建TCP与采集位置最大差约1.59e−13 mm。9例预测短段均与冻结NPZ一致，4项源文件哈希不变。这里验证坐标、投影和资源完整性，不是新增训练、动力学或插接成绩；尚待用户评价展示效果。

[偏差最大案例对照](/data/shapeforge/runtime/runs/hier_s1_assets_20261125_v1/case_02_comparison.png) · [九位置总图](/data/shapeforge/runtime/runs/hier_s1_assets_20261125_v1/all_cases.jpg) · [三维场景](/data/shapeforge/runtime/runs/hier_s1_assets_20261125_v1/case_02.blend) · [证据清单](../../../../manifests/system1_asset_visualization_20261125.json)

生成入口 `scripts/perception/render_system1_assets.py`（omi_sim_train环境，调用Blender），传入 `--transfer`、`--probes`、新 `--output`，默认生成全部9例；`--cases`可选0～8的子集。`--compose-only --output <已有输出>`可重新排版。独立检查使用具备OpenCV的环境运行 `scripts/perception/audit_system1_assets.py <输出目录>`。

## 原始训练与短段展示

2026-11-25，用户要求先训练System1，查看二维图像或三维视图上的预测轨迹，并讨论完整／短段输出及监督来源。沿用独立原型，在新目录训练60轮，固定权重后评估未参与训练或选权重的回合，输出腕图叠加、三维局部短段与视频。

[实现](../../../../scripts/perception/render_system1_paths.py) · [验证清单](../../../../manifests/system1_path_visualization_20261125.json) · [独立系统背景](hierarchical-insertion.md)

完整接续入口：[2026-11-25 System1与System0当前交接](../../../chronicles/2026-11-25-system1-system0-handoff.md)。优先扩充System1不同接近位置的覆盖；60轮权重尚未与System0重新闭环评估。

同日后续完成[九个实际机器人起点检查](../../../../manifests/system1_nine_positions_20261125.json)：固定插座，孔口前约8 mm，左右／上下各−3、0、+3 mm；普通IK／PhysX动作到位后读取实际双RGB，由冻结第47轮模型生成路径。九例准备位姿误差均小于0.035 mm，未执行预测路径。位姿预测误差约2.02～7.43 mm，说明原正常路径附近的训练覆盖不足，不能把此前小扰动测试均值当作该范围泛化精度。

九位置的位姿误差均值为4.41218 mm。此为不同初始位置下的冻结模型诊断，不能与原1074帧同域均值合并，也不代表已完成接触控制测试。

产物位于 `/data/shapeforge/runtime/runs/hier_s1_nine_20261125/`：`nine_positions.png`逐位置腕图／三维对比，`paths_3d.png`将九个起点放到同一插座坐标系，`samples.npz`和逐例JSON保留图像、预测与实际准备轨迹。脚本：[probe_system1_positions.py](../../../../scripts/perception/probe_system1_positions.py)。橙色预测未被替换为绿色GT，所有失败偏差保留；本阶段没有针对九个测试位置追加训练。

路径与轨迹的接口建议保持：System1输出三维位姿path与名义速度／速度上限，System0依据反馈产生实际时间参数化。接触后允许暂停和倒退，不强迫按固定时间戳追赶路径。空中接近可以使用平滑的带速度轨迹，但不能据此把同样的严格时间要求延伸到插孔接触阶段。

## 实际训练与结果

使用原三条腕力采集回合：121000／121001训练，共720帧；121002验证357帧。独立双RGB CNN从新初始化训练60轮，每批32，随机种子5，CUDA；验证损失选择第47轮，未按测试结果追加训练或选权重。旧3轮模型保留。

验证平移均值约0.16671 mm；独立测试120000／120001／120002共1074帧，平移均值约0.22825 mm，P90约0.48313 mm，最大约2.20677 mm，旋转均值约0.00891°。这里衡量的是TCP相对插座位姿；同一资产、同一路径家族和小范围插槽随机化，不能推广为任意姿态、遮挡或真机精度。

## 可视化表达的内容

当前网络直接预测插座相对TCP位姿，参考路径由既有几何解码器生成。图中的“预测路径”是预测位姿经解码后的路径，不是网络直接输出的自由轨迹，也不是System0已经执行的动作。

橙色实线为预测，绿色虚线为相同几何规则下的真值参考，紫色圆点为当前模块尖端。亮线显示当前8个参考点，深色虚线显示名义剩余参考。三维主窗以当前尖端附近为中心、三轴等比例；孔口轮廓仅为几何示意。图上画的是模块尖端运动，已按固定夹持变换从TCP参考转换，不能把TCP原点直接叠在插接头上。

腕图使用实际128×128策略观测并放大；按原1920×1080鱼眼内参、766／566起始的389像素ROI及worker实际采样位置投影。射线与像素回代检查5个代表位置最大误差0。参考线穿过遮挡区域仍绘制，并在画面中说明。

视频取测试回合120000的完整观察序列，每3帧取一帧、10fps，共120帧／12秒，标明3×回放。静态图选择最差帧、孔口附近帧及中段帧。短段尖端参考差均值约0.06527 mm，但路径投影与截断会消除部分轴向误差，不能拿该数值替代位姿精度或插接成功率。

早期两版展示保留在review／review_v2目录，交付采用final：已修正进入通道后的背景参考线，避免把返回孔外的线段误画成未来计划；新增局部放大并隔开图形与标注。未改System0或运行新的策略闭环。

## 动作空间与老师来源的讨论

当前可解释基线为“预测几何位姿＋确定性路径解码”。建议下一版继续向System0发送短段三维位姿参考，同时保留插入轴和终点条件；先以8点作为起点，输出端使用绝对参考位姿序列或相对当前TCP的位姿序列，不能将其误当8次增量命令直接累加。位置和朝向都需要表达，图上的线只展示位置。

若改为直接学习路径，可比较少数控制点与8点位姿序列。应先用一致采样定义生成标签，路径长度不足时使用有效长度／mask，而不是把重复端点当作多次动作；当前原型的端点截断重复行为需在正式动作合同中进一步决定。暂不把任意长、固定时间到达的轨迹定为目标。

“GT位姿”和“专家路径”应分开：仿真提供几何真值，规划或规则给出一条可行参考，通常不代表唯一最优轨迹。针对当前任务，建议用规则定义孔外准备位姿、入口轴线和朝向约束；局部简单通路使用解析几何／平滑插值并核验IK与碰撞；自由空间接近及有障碍时使用规划器生成候选并筛选平滑、可达路径。此项规划升级尚未实施，当前仍是规则几何解码。

人类干预适合补充难以建模的意图与接触经验。受阻后的倒退、试探和再进入既然交给System0，应主要作为下层恢复示范，不能无区别混入上层名义接近路径。若规划器给同一场景生成多条路线，需固定选择原则、标明路线条件或使用多模态模型，避免对不同绕行路径直接求平均。

几何规划只能在其几何／运动学约束下检查可行性，不能把“无碰撞路径”当成接触插入的动力学真值。插槽内部预期接触需要独立任务合同与物理验证。参见[OMPL规划器分类](https://ompl.kavrakilab.org/planners.html)和[MoveIt规划与约束](https://moveit.picknik.ai/main/doc/concepts/motion_planning.html)。

## 运行资源

训练：`/data/shapeforge/runtime/runs/hier_s1_visual_20261125_train60/`。

交付：`/data/shapeforge/runtime/runs/hier_s1_visual_20261125_final/`，含 `system1_paths.mp4`、`overview.jpg`、`worst.png`、`entry.png`、`middle.png`、`evaluation.json`及逐帧`predictions.npz`。

复现入口是 `render_system1_paths.py --checkpoint <system1.pt> --dataset <独立测试目录> --transfer <传递包> --output <新目录>`。程序检查检查点／数据哈希及训练验证种子排除，使用固定网络输出重新生成参考与可视化。
