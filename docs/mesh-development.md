# Mesh开发记录：建模、修订、导出与几何验证

PCG-01已补全[开发纪传体](agent/perception/evolution/pointcloud-geometry-pcg01.md)和[阶段编年体](agent/perception/chronicles/2026-11-23-pointcloud-geometry.md)：记录来源部件、排除范围、无颜色导出、原顶点／三角面一致性、文件与数组内存、可视化及可复制交付。

2026-11-23新增[PCG-01点云匹配纯几何版](agent/perception/evolution/pointcloud-geometry-pcg01.md)：无颜色／纹理，模块主体＋插口上部，源尺寸不变；已在Downloads交付可直接复制的文件夹与ZIP。

2026-11-23：[光模块与插口全部主要版本及尺寸速查](agent/simulation/evolution/module-socket-dimensions.md)，区分完整外形、模块插入截面、金属净孔、白框与底座，当前组合为V4-r08＋M1888／SIM-r06。

2026-11-23：[连续导向碰撞代理候选](agent/simulation/evolution/smooth-guide-contact.md)从冻结transfer另建，比较六个凸网格与六个原生盒形状；保留18.8×8.8 mm名义通道。视觉mesh及WG-r10／OM-r08源资产不改。这是碰撞表示实验，局部通过但完整机器人未验收，不是新的已接受外观版本。

夹持修订查看后已归档：GC-r01交互窗口已打开，用户反馈“感觉好很多”。本方面统一从[黑胶垫双面接触修订](agent/simulation/evolution/wrist-contact-closure.md)阅读，含接触验证、对比图、启动命令及对应编年记录；尚未验证接触插槽后的稳定性。

接触问题已确认并另建[GC-r01黑胶垫双面接触修订](agent/simulation/evolution/wrist-contact-closure.md)：WVA-01原左右间隙约0.046／0.602 mm；新场景以自由模块＋可闭合双指产生真实接触，5种初态及半步长通过保持／移动／释放。源mesh和WVA-01保留；这是局部夹持验证，非插入或训练验收。

用户已认可并命名 **[WVA-01「腕部实拍对齐版」](agent/simulation/evolution/wrist-visual-wva01.md)**：当前腕部视觉基线固定WG-r15＋OM-r08及SIM-r06插槽参考场景，保留真实／鱼眼仿真对比和依赖哈希。源mesh、历史版本和既有训练任务不变；接受范围为视觉。

新增[r15真实腕部采集／仿真鱼眼对比](agent/simulation/evolution/wrist-logo.md#r15真实腕部采集仿真对比)：同像素区域展示原始采集与新标志版，保留材质／拉环／背景差异；未重新拟合或训练。

新增[WG-r15 DAIMON表面标志版](agent/simulation/evolution/wrist-logo.md)：按实拍增加两侧红色图标与黑色字样，朝向相反；49件几何保持r14不变，Blender／GLB与MuJoCo贴图显示检查通过，旧版保留。

新增[WG-r14实拍比例复核候选](agent/simulation/evolution/wrist-tip-photo-review.md)：以原始实物照片收窄前端、缩短根部平段；红线只表达结构。两份银壳修改，前端齐平及其他47件保留；照片比例估计不是尺寸标定。

新增[WG-r13红线轮廓候选](agent/simulation/evolution/wrist-marked-tip.md)：银色外缘改为斜边接根部平段，继承前端齐平，仅修改两份银壳；47件及所有旧版本保留。

新增[WG-r12梯形齐平指尖候选](agent/simulation/evolution/wrist-trapezoid-tip.md)：按用户确认的伸出方向对齐银壳与胶皮前端，包边后退0.2 mm；四边梯形主轮廓、胶皮及间隙保留，旧版不改。

新增[WG-r10＋OM-r08的Isaac接入](agent/simulation/evolution/wrist-bundle-isaac.md)：只在独立场景装配与转译，源mesh不改，新U形件仍仅视觉。

新增[WG-r11宽钝头倒角候选](agent/simulation/evolution/wrist-fingertip-chamfer.md)：依据实物照片加宽两侧银色指尖前段，保留黑垫、间隙及其他47件；r10原资产和固定交接清单不变。

历史r10复用与继续编辑入口：[历史视觉资产交接](agent/simulation/evolution/wrist-assets-handoff.md)。WG-r10保留47件、修改两侧内沿；OM-r08保留16件主体、粗补连续U形件。新清单固定路径、哈希、米制坐标和17／18件映射，编辑从新副本开始；本轮没有重新改mesh。

新增[WG-r10主体轮廓修正与OM-r08粗补U形拉环](agent/simulation/evolution/wrist-primary-refinement.md)：保留r09相机／夹持变换，只改两侧内沿；最终三单元黄色外缘约10.9→6.2 px、黑臂基本不变，旧任务与资产保留。

新增[Isaac视觉转译复核](agent/simulation/evolution/isaac-contact-visual-review.md)：几何不变，源法线直映候选被拒绝，修正r07纯色纹理/PBR绑定；没有新建或缩放光模块mesh。

此前[固定r09位姿与开度试验](agent/simulation/evolution/wrist-pose-study.md)：镜头微调只改善部分指标，未替换主版本；模块相对位置随单元变化，且当时绿色件缺U形连接，不能仅靠全局相机位姿解决。

新增[Isaac碰撞转换与烘焙审计](agent/simulation/evolution/isaac-contact.md)：源mesh不变，以顶点/prim反向缩放改善毫米级凸包烘焙；部分曲面仍有引擎近似，不能将同源导入当作几何完全一致。

新增[WG-r09多视角点云约束候选](agent/simulation/evolution/wrist-pointcloud-refinement.md)：r08已完整冻结保留；11视角点云支持修改8件局部mesh，镜头和夹持变换不变，黑臂轮廓改善明显，黄色与相机残差仍保留。

新增[WG-r08腕部投影对齐候选](agent/simulation/evolution/wrist-alignment.md)：调整镜头安装、同步移动相机壳／短颈和参考夹持变换，夹爪几何保留；4个留出单元选定边缘约16～18→3 px，完整画面和绿色拉环仍未一致。

最新[尺寸与腕部图像核对](agent/simulation/evolution/wrist-camera-consistency.md)：网格尺寸符合建模参数，但真实尺寸未认证；当前针孔与真机不一致，同位姿鱼眼候选仍有黄色区域、掌部遮挡和绿色拉环差异，尚未完成外参／夹持关系校准。

历史阶段的[WG-r07照片轮廓修正版](agent/simulation/evolution/wrist-tool-photo-profile.md)：双峰黄色衬垫、中央凹口与收窄指臂，侧视复核衬垫厚度27→12 mm；49件检查通过，基体／相机保持r06不变，旧资产保留。

历史阶段的[WG-r06黄色衬垫修正版](agent/simulation/evolution/wrist-tool-refinement.md)：按用户反馈去掉偏红色调，49件几何保持r05不变；旧资产保留。

新增[腕部相机／夹爪WG-r05精修记录](agent/simulation/evolution/wrist-tool-refinement.md)：49件、局部双目尺寸估计、指尖凸起黑垫与真实衬垫开孔、分体导出、拓扑与重开校验。原WG-r04和光模块r07保留。

2026-11-22状态：[完整开发汇总](chronicles/2026-11-22-simulation-mesh-visual-progress.md)。当前r07只去除r06新增颗粒，保留色调和18件几何；已交付真机／r07对比，未更新碰撞或训练资产。

核对日期：2026-11-22。本页是光模块mesh开发的专门入口，记录几何本身如何形成、如何组织和验证。Blender管线实现事实维护在[资产管线](agent/simulation/evolution/asset-pipeline.md)，逐版详细纠正见[V4记录](agent/simulation/evolution/module-v4.md)，仿真系统接入状态见[simulation.md](simulation.md)。

## 当前暂定基线

最新为 **V4-r07纯色银灰材质候选**：保留r06色调，按用户反馈去除全部新增颗粒纹理。历史r06：按用户要求另存新资产，修改金属、绿色拉手和胶塞的材质／贴图，18件几何与r05精确一致。未替换下面的暂定基线；[材质开发、对照和导出记录](agent/simulation/evolution/module-material-r06.md)。

**V4-r05「双窗尾槽版」**（`OM-001/V4`，修订`r05`）已由用户暂定采用。名称固定绑定现有r05文件和哈希，V3及各历史修订保留；后续几何修改另存新修订。

资产目录：`/data/omi_runtime/assets/optical_module_v4/r05/`。命名状态由[暂定采用登记](../manifests/module_v4_r05_designation_20261121.json)维护，几何来源和部件由[构建清单](/data/omi_runtime/assets/optical_module_v4/r05/asset_manifest.json)维护。构建清单中“待复核”是命名前的历史状态，后续用户暂定采用以命名登记为准。

## 几何开发过程

| 阶段 | mesh层面的操作 | 保留的问题或纠正 |
| --- | --- | --- |
| V2／V3复核 | 检查实际顶点、部件包络和插入截面；区分头部总高度与插入段厚度 | 确认旧尺寸未完全对应实测；截图大小不能代替毫米尺寸 |
| MEASURED-r01 | 以V3求值网格为来源调整横向／厚度；重建下部薄板，前伸段下表面上翘0.2 mm | 保留槽、头盖、拉手等结构；斜面长5.19 mm沿用旧几何，未实测 |
| V4-r01 | 对头盖和下方盖板同时做布尔差，形成尾缘长方形缺口；增加侧片缺口 | 黑色件被简化为固定盲凹块，后被照片纠正 |
| V4-r02 | 删除固定黑块；用横梁和两条胶脚的布尔并集构成独立连通胶件；加入三个金属片和容纳空间 | 用户指出高度偏高 |
| V4-r03 | 将胶件和金属片下沉1.5 mm，同时重建内部空间 | 只改位置仍不够；正视照片暴露胶件端面过矮、底框余量过大的问题 |
| V4-r04 | 胶件端面高改为7.1 mm、底框余量约1.2 mm；金属端改为宽短矩形；上侧真实开窗 | 错把两个暗窗口填成上部胶脚延伸，虽拓扑检查通过，但语义不符合实物 |
| **V4-r05** | 删除错误的上部胶件填充，保留较低双脚；17个主体部件与r04顶点几何一致 | **三个金属端之间同高度的两个区域为空腔**，用户暂定采用 |

逻辑演进是V3→MEASURED-r01→V4-r01～r05；但r05构建脚本实际读取的是V4-r01 Blender，再按脚本重建后续胶件、金属端及空腔参数。不能把逻辑版本顺序误写成每次都直接加载前一版文件。完整用户反馈及来源见[开发编年](chronicles/2026-11-21-v4-double-window-baseline.md)。

## 当前部件与空腔组织

| 部件组 | 数量 | 名称／处理方式 |
| --- | --- | --- |
| 壳体、下板、侧壁、上槽及抬高头盖 | 5 | `01`上槽、`02`下板、两件`03`侧壁、`11`头盖；保留独立部件 |
| 板件、接触金属区、内部暗块 | 3 | `08`、`09`、`10`；内部不可见结构仍含简化假设 |
| 左右侧弹片 | 2 | 两件`13`；包含侧下沿小缺口 |
| 绿色拉手 | 2 | 两件`14`；作为静态外观网格，未模拟柔性 |
| 装饰折缝 | 2 | 两件`15 Estimated folded seam`，开放表面，仅作外观 |
| 左／中／右金属端 | 3 | 三件`16 Rear metal tongue`，当前为宽短端面，非先前深Z形支架假设 |
| 可取下双脚胶件 | 1 | `17 Removable black twin-leg plug`，横梁与两脚为同一连通实体 |

合计18个mesh：17个`main_module`部件和1个`removable_plug`。部件之间没有统一做成一个布尔并集；不可将“16个部件闭合”理解为整套装配已经是单一无交叠实体。

两处上侧窗口位于三个金属端之间。胶件最高Z=4.2 mm，金属端位于Z=4.25～4.9 mm，同高度区域没有胶件；空腔深处仍有模型背壁，不宣称整件贯穿。胶脚接收空间与上盖开口使用实际几何差集，不能用黑色贴图或外观遮挡代替。

## 尺寸来源与坐标合同

| 尺寸／结构 | 当前值 | 依据 |
| --- | --- | --- |
| 模块参考插入截面，含侧弹片 | 18.1 × 8.2 mm | 用户实测／允许值；在模块源坐标Y=5 mm切片复核，不代表全长每处都相同 |
| 下部前伸段尖端厚度 | 8.0 mm | 用户补充；指下唇前端，上唇保留更靠前的错位结构 |
| 下板上翘与斜面长度 | 上翘0.2 mm，长约5.19 mm | 厚度差来自用户约束，斜面长度沿用旧结构 |
| 胶件端面／底框余量 | 高7.1 mm／约1.2 mm | 正视照片比例建模估计 |
| 三个金属端宽度／高度 | 1.8／3.2／1.8 mm；高0.65 mm | 照片建模估计 |
| 尾槽、胶脚和隐藏内部空间 | 见构建清单参数 | 可见结构受照片和用户指认约束，毫米值及深部形状未标定 |

Blender与OBJ使用**米**；文档和几何验证报告通常使用**毫米**。X为横向，Z向上，−Y为模块插入方向，+Y朝拉手及胶件拔出方向。导出顶点应用对象变换到模块公共坐标，保存的模型为胶件装入状态。GLB导出关闭自动Y-up转换（`export_yup=False`）；加载时核对轴向，避免再次换轴或重复应用变换。

## 网格操作、导出与已验证范围

Blender构建使用求值网格、布尔差／并、独立薄板和短端面建模、局部倒角。修改后的实体执行三角化、重合顶点合并、退化面移除及法向重算。r04布尔合并曾产生微小三角边界，做过专门修复；r05去掉上部胶件延伸后通过其自身验证，不应把r04修补步骤不加区别地重跑到r05。

导出保留逐部件OBJ、整件OBJ／MTL、无胶件主体OBJ／MTL、单独胶件OBJ／MTL以及GLB。OBJ顶点按米制保留10位小数；GLB有颜色／金属度／粗糙度等材质信息，OBJ／MTL不承诺完整复现Blender材质。

| 检查 | r05实际结果 | 不代表什么 |
| --- | --- | --- |
| 实体拓扑 | 16件闭合、法向一致、正体积、无退化面；2件折缝仅作外观 | 不代表所有部件相互之间无交叠，也不是实物精度验收 |
| 胶件连通性 | 一个连通实体，双脚存在且脚间为空 | 未验证真实胶皮变形或内部截面 |
| 上侧空腔 | 两窗共280点无实体占据，同高度正面射线不碰胶件 | 背壁深度仍为假设，不是贯穿孔认证 |
| 尺寸与导出 | 主体／下唇切片通过；Blender与各OBJ／GLB重开、包络一致 | 不代表相机标定或真实图像重投影精度 |
| 胶件拔出 | 0～15 mm每0.5 mm取样，共31点无胶件／主体表面碰撞 | 不是连续路径、MuJoCo动力学或真实夹持力验证 |
| 版本保护 | 构建r05时686个旧文件哈希未变；命名未改r05模型 | 不把新模型结论回写到旧版实验 |

证据：[验证报告](/data/omi_runtime/assets/optical_module_v4/r05/validation.json)、[Blender重开](/data/omi_runtime/assets/optical_module_v4/r05/blender_reopen.json)、[来源与哈希](/data/omi_runtime/assets/optical_module_v4/r05/asset_manifest.json)。

## 代码和资产入口

- [构建脚本](/data/omi_runtime/assets/optical_module_v4/r05/build_scripts/build_r05.py)：Blender执行，实际读取V4-r01，按参数重建r05；不是任意输入模型通用编辑器。
- [几何验证脚本](/data/omi_runtime/assets/optical_module_v4/r05/build_scripts/validate_r05.py)：`omi_mesh_audit`环境，使用trimesh及碰撞查询核验上述内容。
- [原生查看脚本](/data/omi_runtime/assets/optical_module_v4/r05/build_scripts/view_r05.py)：`foundation_stereo`环境，Open3D只读显示；装入／拔出／旁置仅调整显示变换。
- [Blender源文件](/data/omi_runtime/assets/optical_module_v4/r05/OM-001-V4-r05.blend) · [整件OBJ](/data/omi_runtime/assets/optical_module_v4/r05/OM-001-V4-r05.obj) · [GLB](/data/omi_runtime/assets/optical_module_v4/r05/OM-001-V4-r05.glb)。
- [无胶件主体OBJ](/data/omi_runtime/assets/optical_module_v4/r05/OM-001-V4-r05-module-without-plug.obj) · [胶件OBJ](/data/omi_runtime/assets/optical_module_v4/r05/OM-001-V4-r05-removable-plug.obj)。

已归档脚本包含固定输入／输出路径，构建器以`exist_ok=False`拒绝覆盖现有目录。后续修改应在新的工作副本、输出目录和修订编号中进行，同时调整配套导出／验证脚本中的路径；不能直接重跑构建命令覆盖暂定基线。原生查看命令见[基线恢复入口](chronicles/2026-11-21-v4-double-window-baseline.md#来源文件与恢复)。

## 后续mesh工作与接口

### 新增独立末端工具资产

2026-11-22新近照确认：白色指尖壳内侧的黑色圆凸面才是本次实际夹持部位，橙黄色内衬位于后方。已在[真实像素混合预览](agent/simulation/evolution/hybrid-wrist-preview.md)中补回黑色接触面；本轮只修正图像掩码／遮挡呈现，没有将此近照转换为新的接触面mesh或力学模型。后续精修夹爪接触几何时应据此区分部件归属，并另做尺寸、摩擦与柔性校准。

依据`飞书20261121-212005.qt`另建 **WG-DAIMON-VIS-r04**：法兰／壳体9件、相机及安装座5件、双指及指尖14件、接头／线缆3件，共31件闭合外观mesh。Blender中另放18件V4参考模块用于握持展示，工具GLB只包含31件工具。r03完成倒角退化面清理和线缆端盖；r04工具几何不变，将参考模块固定位置改到TCP Z=195 mm，避免名义到位时与插座／PCB相交。

这是按视频比例、参考旧URDF法兰的外观候选，未核对具体型号或厂家CAD。摄像头镜片与MuJoCo光学位置已绑定，几何／坐标／双指对称运动检查通过；工具动态碰撞、真实抓取和触觉仍未建模。独立资产、版本过程和证据见[腕部相机／夹爪记录](agent/simulation/evolution/wrist-camera-gripper.md)，光模块V4-r05暂定基线保持不变。

### 光模块后续工作

最新接入进展：已从该外观基线创建 **SIM-OM001-OS001-r06**，插槽净开口18.8 × 8.8 mm、正面窄边6.9 mm（口径待进一步确认）。模块156个碰撞代理，插座335个；CoACD代理膨胀曾阻挡入口，现按源部件外包络逐平面裁剪并通过回归／动态检查。18份模块外观OBJ与基线逐字节相同；[新尺寸接触仿真](agent/simulation/evolution/measured-v4-simulation.md)已通过局部及机械臂3/3规则循环。

1. **实物几何**：测量尾槽、金属端、胶件及插孔局部尺寸，校准相机视角下的轮廓与遮挡；每次保留来源及估计标记。
2. **视觉特征**：为三个金属端、双空窗边界、头盖台阶等建立有可见性约束的3D点／线；版本变化后重新绑定，不能假设跨修订顶点索引稳定。真实定位改善需独立对照。
3. **碰撞资产**：SIM-r06已独立生成凸代理；两件开放折缝仍仅用于外观。对凹形孔口直接取单个凸包会封孔，CoACD也可能越出源外包络；后续修改仍需保孔、约束包络并重验接触，当前通过不代表所有局部凹面误差已标定。
4. **训练接入**：新几何规则装配验证已通过，但旧BC／RL直接迁移各0/2。SIM-r03历史成绩保留，新几何尚未重采示范或重训；必须另建新场景训练合同，不能继续使用旧replay。

后续mesh进展同步本页、[Blender资产管线](agent/simulation/evolution/asset-pipeline.md)、[V4能力记录](agent/simulation/evolution/module-v4.md)及相关索引；发生仿真接入变化时再同步[仿真器记录](simulation.md)。
