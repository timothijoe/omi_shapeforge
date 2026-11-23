# Blender 与外观资产管线

新增[PCG-01纯几何提取与便携导出记录](../../perception/evolution/pointcloud-geometry-pcg01.md)：直接保留原OBJ顶点／三角面，剥离外观字段，float32二进制PLY／NPZ另存；Blender仅用于无材质导入检查及灰色预览，没有重新建模、减面或覆盖源资产。

2026-11-23：[入口受阻、内部顺滑候选](smooth-guide-contact.md)通过独立transfer生成解析碰撞代理，不修改Blender／视觉mesh。原生形状与凸包的接触对照保留；完整机械臂验收未通过，不能由外观保真或局部通行推定动力学有效。

接触问题已确认并另建[GC-r01黑胶垫双面接触修订](wrist-contact-closure.md)：WVA-01原左右间隙约0.046／0.602 mm；新场景以自由模块＋可闭合双指产生真实接触，5种初态及半步长通过保持／移动／释放。源mesh和WVA-01保留；这是局部夹持验证，非插入或训练验收。

用户已认可并命名 **[WVA-01「腕部实拍对齐版」](wrist-visual-wva01.md)**：当前腕部视觉基线固定WG-r15＋OM-r08及SIM-r06插槽参考场景，保留真实／鱼眼仿真对比和依赖哈希。源mesh、历史版本和既有训练任务不变；接受范围为视觉。

新增[WG-r15 DAIMON表面标志版](wrist-logo.md)：按实拍增加两侧红色图标与黑色字样，朝向相反；49件几何保持r14不变，Blender／GLB与MuJoCo贴图显示检查通过，旧版保留。

新增[WG-r14实拍比例复核候选](wrist-tip-photo-review.md)：以原始实物照片收窄前端、缩短根部平段；红线只表达结构。两份银壳修改，前端齐平及其他47件保留；照片比例估计不是尺寸标定。

新增[WG-r13红线轮廓候选](wrist-marked-tip.md)：银色外缘改为斜边接根部平段，继承前端齐平，仅修改两份银壳；47件及所有旧版本保留。

新增[WG-r12梯形齐平指尖候选](wrist-trapezoid-tip.md)：按用户确认的伸出方向对齐银壳与胶皮前端，包边后退0.2 mm；四边梯形主轮廓、胶皮及间隙保留，旧版不改。

新增[WG-r10＋OM-r08的Isaac装配](wrist-bundle-isaac.md)，读取已发布OBJ/PBR，不修改原Blender或冻结清单。

新增[WG-r11宽钝头倒角候选](wrist-fingertip-chamfer.md)：依据实物照片加宽两侧银色指尖前段，保留黑垫、间隙及其他47件；r10原资产和固定交接清单不变。

新增[WG-r10主体轮廓修正与OM-r08粗补U形拉环](wrist-primary-refinement.md)：保留r09相机／夹持变换，只改两侧内沿；最终三单元黄色外缘约10.9→6.2 px、黑臂基本不变，旧任务与资产保留。

新增[Isaac视觉转译复核](isaac-contact-visual-review.md)：原Blender/GLB保留，读取r07材质与纯色纹理，验证USD物理属性/绑定不变。

新增[Isaac USD与碰撞烘焙审计](isaac-contact.md)：从既有求值网格派生，原Blender与OBJ不改，外观和碰撞验证分开记录。

新增[WG-r09多视角点云约束候选](wrist-pointcloud-refinement.md)：r08已完整冻结保留；11视角点云支持修改8件局部mesh，镜头和夹持变换不变，黑臂轮廓改善明显，黄色与相机残差仍保留。

新增[WG-r08腕部投影对齐候选](wrist-alignment.md)：调整镜头安装、同步移动相机壳／短颈和参考夹持变换，夹爪几何保留；4个留出单元选定边缘约16～18→3 px，完整画面和绿色拉环仍未一致。

最新工具为[WG-r07照片轮廓修正版](wrist-tool-photo-profile.md)：双峰黄色衬垫、中央凹口与收窄指臂，侧视复核衬垫厚度27→12 mm；49件检查通过，基体／相机保持r06不变，旧资产保留。

最新工具外观为[WG-r06黄色衬垫修正版](wrist-tool-refinement.md)：按用户反馈去掉偏红色调，49件几何保持r05不变；旧资产保留。

新增[WG-r05腕部工具精修](wrist-tool-refinement.md)：Blender参数化49件，真实六角孔布尔、圆角凸接触垫、统一米制TCP坐标，工具／相机／夹爪三份GLB及逐件OBJ。四帧双目只提供局部尺寸证据，未完成扫描融合。

产物／验证／接续总表见[2026-11-22完整进展](../../../chronicles/2026-11-22-simulation-mesh-visual-progress.md)。r07真机对比沿用原图坐标裁剪，没有额外色调修正，生成脚本与来源JSON保存在独立运行目录。

最新[光模块r07纯色材质候选](module-material-r06.md)：用恒定色图替换r06颗粒贴图，色调及PBR参数不变，保留r05几何和原文件；导出带内嵌材质的Blender／GLB及完整OBJ／MTL贴图包，并提供MuJoCo显式外观适配。实时场景和碰撞资产不自动切换。

新增末端工具资产：[视频参考腕部相机与夹爪](wrist-camera-gripper.md)，31件独立外观mesh、镜头坐标、双指运动绑定和GLB／Blender重开均已检查，已挂载独立MuJoCo场景。它不覆盖V4-r05模块，也不是匹配型号的厂家CAD或已标定抓取碰撞资产。

最新碰撞接入：V4-r05外观保持不变，已派生SIM-r06及独立插槽OS-001/M1888-r01，使用18.8 × 8.8 mm孔口和暂按正面窄边口径的6.9 mm偏置；局部与机械臂规则循环通过。模型导出与碰撞代理仍分别维护，详见[实测尺寸仿真记录](measured-v4-simulation.md)。

## 当前工具和输入

Blender仍是建模工具。2026-11-21用户暂定采用 **V4-r05「双窗尾槽版」**，后续从该只读基线另建新修订；V3及全部历史模型保留，V2用于辅助对比。原V3命名决定见[ADR 002](../decisions/002-blender-v3-primary.md)，最新采用状态见[命名登记](../../../../manifests/module_v4_r05_designation_20261121.json)。mesh层面的开发入口为[专门记录](../../../mesh-development.md)。

便携包指定原机 Blender 4.5.16 LTS。本机从官方发布目录取得 Linux 包，并核对官方 SHA256；版本、下载来源及本地位置记录在[仿真验证索引](../../../../manifests/simulation_validation.json)。软件、原模型、OBJ 和渲染图均在外部资源目录。

历史便携包包含未定标照片稿、米制尺寸修正版、连通槽版本和V2参考；前三者照片资源内嵌，没有外部`.blend`库依赖。照片稿单位是NONE，其余米制模型scale_length为1。后续另存MEASURED-r01和V4各修订，当前r05已独立重开核验18个mesh及米制单位。

## 当前V4-r05实际管线

运行归档位于`/data/omi_runtime/assets/optical_module_v4/r05/build_scripts/`，代码和生成资产均保存在外部资源目录。`build_r05.py`实际读取V4-r01 Blender，移除旧固定黑块，重建较低的双胶脚／加高端面、三个短矩形金属端以及真实容纳槽／上侧空窗。r05没有r04错误的上部胶件填充；17个主体部件与r04保持相同顶点几何。

构建使用Blender精确布尔差／并；对修改实体进行三角化、`1e-9 m`范围的重合顶点合并、退化面移除和法向重算。胶件横梁与双脚合并成一个连通实体；整套装配保留部件组织，不做全局布尔并集。18件分为17件主体和1件可移开胶件，其中16件实体、2件开放外观折缝。

逐件OBJ与整件OBJ／MTL使用公共模块坐标和米制顶点，保留10位小数；另输出无胶件主体、单独胶件及GLB，GLB关闭自动Y-up转换。Blender保存胶件装入状态；Open3D查看时的毫米显示比例、移开胶件等不改文件顶点。

`validate_r05.py`在`omi_mesh_audit`环境中检查闭合性、法向、体积、退化面、胶件连通性、空腔、截面和导出包络。两处窗口280点检查及同高度正面射线确认无胶件填充；胶件0～15 mm的31个离散拔出位置无主体表面碰撞。结果见[验证报告](/data/omi_runtime/assets/optical_module_v4/r05/validation.json)。这些是几何验证，不是实物标定、橡胶力学或当前MuJoCo插入任务验收。

构建脚本拒绝已有输出目录，且包含固定输入／输出路径；不是将输入换成任意Blender文件即可运行的通用编辑器。复现或继续开发需复制脚本／工作文件到新位置，并统一调整修订、输出和验证路径。V4的18件外观后来在SIM-r06中派生156个模块凸碰撞件，两件开放折缝不作实体碰撞。部件表、尺寸依据与逐版修改见[mesh开发记录](../../../mesh-development.md)和[V4持续事实](module-v4.md)。

## V3历史导出实现

`scripts/simulation/export_blender_asset.py` 必须由 Blender 自带 Python 执行。它读取指定集合的求值 MESH／CURVE，把 `matrix_world` 应用到顶点，三角化后逐部件输出 OBJ；颜色取自材质或 Principled Base Color。复杂着色和纹理不完整导出。

该V3导出共有15个外观部件，模型总体约0.10 m量级。`asset.json`记录源`.blend`哈希、Blender版本、部件清单和bounds。源`rigid_match_mesh.npz`的bounds提供旧碰撞盒；导出不把修改保存回输入`.blend`。这些数量和碰撞表示不代表后续V4-r05。

## V3及便携包的历史验证和限制

本机已实际重开四份模型、检查图片打包和单位，完成当前连通槽模型的一张 1400×1000 后台图像，以及求值几何导出。报告与图像由[资源清单](../../../../manifests/README.md)索引。

包内有 `rebuild_blender.py --stage photo|metric|groove`，但这些完整生成阶段尚未在本机复跑。metric 阶段使用冻结参数，不从 59 帧重新估计尺寸。旧机槽重建／拓扑检查记录是背景，不能作为本机新验收。

导出器依赖当前模型集合名称和固定资产结构，不是通用任意 Blender 文件转换器。柔性拉手被转换为刚性附着外观，精度未认证。操作见[Blender 教程](../../../../tutorials/blender_assets.md)，历史见[本阶段](../chronicles/2026-11-20-blender-and-scenes.md)。

## 资产身份与交互对照

初始目录中的`OM-001/GROOVE-r01`为`OM-001/V3`的兼容别名，V3保留为原Blender主线及旧场景来源；当前暂定外观基线为V4-r05。`OM-001/REF-V2`为辅助对比，PHOTO／METRIC为历史阶段；映射、父版本与实例身份见[资产版本说明](../../../asset-versions.md)。名称是本地目录标识，不是厂家型号，也不改变物理精度验收状态。

本次为对照展示重新读取四份 Blender 的可见求值几何；隐藏构造刀具排除，原模型哈希保持不变。展示中分别适配模型大小，材质为示意，不用截图尺寸代替物理测量。

桌面兼容性补充：原浏览器检查使用启用了软件 WebGL 的无头 Chromium，未覆盖实际桌面 Chrome 无 WebGL 的配置。用户打开后出现空画布，已增加 CPU 逐像素深度渲染后备路径；禁用 WebGL 的检查覆盖四网格、旋转、缩放和部件选择，并在真实桌面刷新核对。网格数据未改变，见[兼容性验证](../../../../manifests/viewer_compatibility_validation_20261120.json)。

另已恢复原机 Open3D 原生 GUI，按旧启动记录加载历史 V2／V1 资产；本机桌面窗口及 V2 网格实际可见。它不依赖网页，支持原有模型选择和点云叠加入口；启动方法见[原生查看教程](../../../../tutorials/native_mesh_viewer.md)，证据见[原生窗口验证](../../../../manifests/native_viewer_validation_20261120.json)。本次没有重建或修改几何，也没有把旧界面的“当前 V2”改写成新资产目录的默认版本。
