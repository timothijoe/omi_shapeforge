# 光模块插接座

> 本机迁移提示（2026-11-24）：运行资源实体已迁至 `/data/shapeforge/runtime`；本文中的 `/data/omi_runtime` 是保留的兼容入口，指向同一份内容。目录映射与恢复要求见[当前资源契约](../../interfaces/local-resources.md)。

用户将带孔白色框架、金属内槽及 PCB 的装配体命名为“光模块插接座”，简称“插接座”；大型白色下部件称“插接座支架”。本地资产号 OS-001，独立于光模块 OM-001/V3。目录见 [socket_assets.json](../../../../manifests/socket_assets.json)。

## 当前采用结构与孔宽候选

用户查看背面实拍后确认保留两处凸出结构；**r02 平背面不采用**，r01 为保留背面结构的基准。针对孔宽偏大先保存 r03/18.60 mm，随后按用户“略放宽”要求另存当前 **r04-width-review**：金属基本通道宽 **19.00 mm**、白色孔口宽 **20.60 mm**，V3 和背面结构保留，单侧名义间隙约 **0.41 mm**。孔宽仍是待核实候选，不是图像／点云独立测得值。实际 V3 插入路径、51.28 mm 台阶限位及弹片刚体接触见[V3 插入记录](v3-insertion.md)。

默认桌面查看已按用户要求改为 **Open3D**。上部网格双视图保留原 TSDF 与 r01 对照；当前实际 V3／r04 插入组合使用[专用查看器](../../../../tutorials/v3_socket_insertion.md)，可调插入深度并显示完整下部。Blender 继续保留为编辑工具。

## 历史 r02 平背面检查候选（未采用）

当时生成 **r02-flat-rear**，父版本为 r01。用户用黄色圈指出两整块后凸体，并要求核对原始 mesh 和 RealSense 尺寸；后续看过背面实拍后改为保留原结构。以下保留该阶段证据，不能作为当前采用状态。

- [r02 独立插接座](/data/omi_runtime/assets/optical_socket/revisions/r02/OS-001-r02.blend)
- [r02 V2 插入场景](/data/omi_runtime/assets/optical_socket/revisions/r02-insertion-v2/OS-001-r02-insertion-V2.blend)
- [原 TSDF／历史 SDF／r01／r02 同尺度对照](/data/omi_runtime/runs/socket_flat_rear_20261120T064745Z/original_mesh_fixed_scale_comparison.jpg)
- [同尺度 Blender 对照](/data/omi_runtime/runs/socket_flat_rear_20261120T064745Z/socket_mesh_review.blend)
- [21 项尺寸对照 CSV](/data/omi_runtime/runs/socket_flat_rear_20261120T064745Z/dimension_comparison.csv)
- [完整新证据](/data/omi_runtime/runs/socket_flat_rear_20261120T064745Z/final_review.json)

r02 仅裁去两部件超出既有白色壳体背面（body Y=−64 mm）的部分，原外沿 Y=−73 mm，缩去约 9 mm；切口封闭，保留内部范围及黑／银色平面。其余 133 个装配 mesh 的几何与材质引用不变，组合场景中其余 135 个 mesh（含两版光模块）不变。135 个装配部件闭合、无退化面，两份 Blender 重开通过，GLB 零错误零警告。原件与 r01 均保留。

**平背面约束来自用户明确修正，不是本轮深度拟合结果。** 原始 TSDF 后部是低矮、模糊且部分超出白壳背面的结构，没有现模型那样规则的两个 9 mm 方盒；但原网格及原生深度也不能独立证明整个背面完全齐平。因此 r02 是待查看候选，不是传感器认证的最终几何。

## 原始网格与采集尺寸复核

原 mesh 是 `assets/dual_geometry_v1/registration_mesh.ply`（28 帧 TSDF）；`display_target_mesh.ply` 则是人工清孔后的 SDF，分开对照。对照使用原 object／body 米制坐标，未做独立 ICP、缩放或居中拟合。展示仅裁取插接座上部；Blender 并排场景的横向位移是展示偏移，记录在对象属性中。

对应原录制为 `FoundationStereo/DATA/recordings/20261114_203053_613923_marker_scan/`，MCAP 仍在。本轮从 `/camera/camera/depth/image_rect_raw` 提取与 28 个 IR 帧 **header 时间戳完全一致**的原生 `16UC1` 深度，按毫米换算；录制的 depth-to-infra1 为单位变换，裁剪与相机位姿沿用 baseline_28。另独立复跑已有 FoundationStereo 冻结缓存的尺寸检查，未重新推理。

| 白色壳体项目 | Blender 名义值 mm | 原 TSDF 局部面估计 mm | RealSense 原生深度两种门限 mm | 已有双目缓存两种门限 mm |
| --- | ---: | ---: | --- | --- |
| 宽度 | 62.00 | 60.89 | 62.92／63.49 | 63.94／64.60 |
| 长度 | 65.00 | 64.37 | 65.52／65.88 | 65.32／66.29 |
| 高度 | 17.00 | 未可靠确定两定义面 | 底面支持不足 | 底面支持不足 |
| 白色孔口宽度 | 22.50 | 不据平滑网格宣称实测 | 两内沿支持不足 | 两内沿支持不足 |
| 金属孔内宽度 | 20.90 | 不据平滑网格宣称实测 | 两内沿支持不足 | 两内沿支持不足 |

TSDF 数值来自固定局部区域、颜色／法向筛选、面积加权的面坐标，受融合平滑与孔洞影响，不是包围盒真值。深度列分别是 2 mm／4 mm 可见面门限下逐帧面坐标中位数的差，**不是置信区间或真实尺寸上下界**；门限仍依赖当前近似模型。21 项尺寸均未满足两个定义面同时稳定支持的既定规则；历史 23／5 分组已用于开发，不是独立测试。不能仅挑某一列给模型做确定毫米改版。本轮除了用户圈出的两部件裁剪，没有更改外壳、PCB 或孔口名义尺寸。

原生深度提取、两套审计、原 mesh 可视化与尺寸估计脚本及报告均在新运行目录。读取 MCAP 的依赖只安装于该目录 `reader_deps/`；没有修改当前算法环境。几何复现脚本为 `scripts/simulation/flatten_socket_rear.py`，输入源、body frame、证据、新输出目录；组合场景用 `--insertion`，渲染用 `--render`。

## 历史 r01 端面清理

`r01-rear-review` 是首次以 OS-001 登记的检查候选，父版本是迁移资产 `aperture_detail_rebuild_20261119_v2/candidate_03`，不是光模块 V3 的新修订。

- [插接座 Blender](/data/omi_runtime/assets/optical_socket/revisions/r01/OS-001-r01.blend)
- [修正后的 V2 插入对齐场景](/data/omi_runtime/assets/optical_socket/revisions/r01-insertion-v2/OS-001-r01-insertion-V2.blend)
- [原始 RGB／修改前／修改后对照](/data/omi_runtime/runs/socket_rear_review_20261120T063929Z/rear_evidence_before_after.jpg)
- [28 帧原始 RGB 局部图册](/data/omi_runtime/runs/socket_rear_review_20261120T063929Z/native_rgb_contact.jpg)

本次检查 RealSense `20261114_203053_613923_marker_scan` 采集对应的 28 帧原始彩色图，后部参考重点为第 15–21 帧。两块一黑一银的后部连接器均有多视角支持，保留其主体。删除历史脚本补画的两块黑色端面覆盖片和共 24 个金色触点：银色件外侧端面在原始图像中呈金属外观，不能按旧模型统一画成带 12 针的黑色面板；现有图像也不能确认两组针脚的布局。

这是一项保守的端面细节修正，未整体重建后部。孔内后方的黑色件、横梁和两块连接器的包络仍保留原几何，其隐藏细节未因此得到验证。

### r01 当时的深度与验证范围

同时检查第 12–23 帧的已有浮点深度。这些是 RealSense IR 对经 FoundationStereo 处理后的冻结缓存，**不是原始硬件深度，也不是本轮新推理**。反光银色件上有明显空洞／背景回落及帧间变化，不能由这些采样可靠改写连接器尺寸。原相机位姿和临时 RGB 标定保持，彩色重投影误差仍存在；未重新配准、标定或拟合毫米尺寸。

插接座从 161 个 mesh 减为 135 个；保留件的顶点、面、对象变换和材质引用逐项保持。135 件均闭合、坐标有限、无退化面。两份新 Blender 文件独立重开通过；GLB 验证零错误、零警告，另有未使用 UV 等信息提示。组合场景保留 V2／V2.1 几何及原对齐关系，默认仅显示 V2；没有将 V3 自动替换进去。

原 candidate_03、原插入场景及 V3 资产保留。新场景默认从后方观察，隐藏下部支架以便检查，支架几何仍在文件中。尚未重新验收碰撞、精细插装、电气布局或实物精度。

复现脚本为 `scripts/simulation/revise_socket_rear.py`，由 Blender Python 运行，参数为 `--source`、全新的 `--output`、`--evidence`；组合场景需加 `--insertion`，生成同视角对照需加 `--render`。脚本拒绝已有输出目录，检查 26 个指定对象，保留其余几何并回读校验。证据和输入哈希保存在上述运行目录的 `evidence.json`，修订检查在各输出目录 `revision.json`。
