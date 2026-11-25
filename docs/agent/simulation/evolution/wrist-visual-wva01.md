# WVA-01「腕部实拍对齐版」

2026-11-25后续：[r16原图域外观候选](wrist-photo-refinement-r16.md)独立修订银壳和橙色，并追溯真实腕图与裁剪链；未自动替代本WVA-01／r15认可版本，不将新开发帧拟合扩大为实机标定或RL验收。

2026-11-25：[独立Isaac插入展示已接入r15原网格／UV标志](wva01-isaac-insertion.md)，组合SC-WVA01-ISAAC-FIXTURE-r01采用GC-r01闭合参考的固定夹持合同。旧训练r10默认不自动迁移，自由接触夹持移动未验收，WVA-01原接受范围不扩大。

> 本机迁移提示（2026-11-24）：运行资源实体已迁至 `/data/shapeforge/runtime`；本文中的 `/data/omi_runtime` 是保留的兼容入口，指向同一份内容。目录映射与恢复要求见[当前资源契约](../../interfaces/local-resources.md)。

**后续接触勘误**：本版原装配有左右约0.046／0.602 mm间隙，视觉接受不代表已经夹住。用户指出后新增[GC-r01双胶垫接触修订](wrist-contact-closure.md)，以动态闭合和自由模块接触保持；原WVA-01文件仍保留，使用夹持功能请读取新修订清单。

2026-11-22，用户在查看真实腕部采集与r15鱼眼仿真对比后认可当前结果，要求固定版本并命名。**WVA-01「腕部实拍对齐版」现作为这条腕部视觉资产工作的已接受基线。**“对齐”表示已进行实拍参考下的外形、安装关系和投影调整，不代表完整像素一致或计量级标定。

后续其他Agent从本页及[固定版本清单](../../../../manifests/wrist_visual_wva01_20261122.json)接入；旧WG-r10＋OM-r08交接清单及旧Isaac场景保留历史身份。此次命名不修改底层mesh，不把r15重命名为r16，也不自动切换已有机器人或训练任务。

## 版本组成

| 对象 | 固定身份 | 本版内容 |
| --- | --- | --- |
| 腕部相机与夹爪 | WG-DAIMON-LOGO-r15，49件 | 点云约束的黑色指臂／衬垫，r14实拍比例银壳，r15两侧DAIMON印刷标志 |
| 光模块 | OM-001/V4 r08，17件 | 纯色无新增颗粒的主体、双窗尾槽、黑胶塞、连续U形拉环；参考拉环角−35° |
| 插槽／参考装配 | SIM-OM001-OS001-r06 | 孔口18.8×8.8 mm；窄边6.9 mm仍依赖此前测量口径假设 |
| 观测 | 1920×1080 OpenCV鱼眼 | 6面cubemap映射、既有K／D、既有相机及模块夹持变换 |
| 对比数据 | unit_001真实wrist_rgb | 此前拟合参考帧，不是独立留出评估集 |

夹爪采用米制TCP公共坐标，+Z朝指尖、+X为相机／银壳标志面，夹指沿Y运动。银壳前端与黑胶皮前端齐平；名义闭合间隙18.4 mm。标志是无厚度UV材质，不改变碰撞形状。OM-r08在本组合中固定使用，单独光模块原暂定基线V4-r05「双窗尾槽版」的历史身份不变。

## 开发过程与已验证内容

- r09：多视角扫描约束指臂和衬垫外形，保留r08；r10：修正内沿遮挡，维持相机／夹持关系。
- r11～r13：探索银壳倒角、前端齐平及斜边接根部平段，保留各次结果。
- r14：回到两张原始实拍，前端短边6.3→3.8 mm、根部平段11.3→7.5 mm；这些是照片比例驱动的建模值，非官方尺寸。
- r15：按实拍添加相反阅读方向的DAIMON标志。全部49件顶点／三角面与r14相同，只有两个银壳OBJ增加UV／材质，其他47份OBJ字节不变。
- 当前通过网格闭合／法向／正体积、Blender重开、GLB包络、MuJoCo加载／开合及实际标志渲染检查。当前参考模块无网格相交；左右胶皮到模块最小距离约0.046／0.602 mm，这不是接触夹持验收。

详细mesh依据见[r14比例复核](wrist-tip-photo-review.md)、[r15标志与腕部对比](wrist-logo.md)，原始扫描和相机过程见[点云修订](wrist-pointcloud-refinement.md)、[相机对齐](wrist-alignment.md)。此次版本登记额外固定场景677个外部文件依赖的哈希；旧资产和旧清单不变。

## 查看与复用

[真实／仿真完整对比](/data/omi_runtime/releases/wrist/WVA-01/evidence/real_vs_sim_wrist_r15.png) · [夹持细节放大](/data/omi_runtime/releases/wrist/WVA-01/evidence/wrist_detail_r15.png)。同尺寸、同像素区域裁剪，真实图未调色或单独拉伸，仿真未混入真实手部像素。

版本快照位于`/data/omi_runtime/releases/wrist/WVA-01/`，包含版本清单、对比证据、候选内参、静态MJCF、依赖哈希和渲染脚本。**资产本体通过绝对路径及哈希引用，快照不是可单独搬走的完整资产包。**恢复到其他机器时还须恢复清单中的资产和场景依赖。

打开对比：

```bash
/data/omi_runtime/envs/omi_mesh_audit/bin/python /data/omi_runtime/releases/wrist/WVA-01/evidence/view_comparison.py
```

只加载静态场景时，需将`insertion`关节设置为`(-2 - physics_manifest['start_depth_mm']) / 1000`后调用`mj_forward`，并隐藏geom group 3～5。不调用`mj_step`；XML里的`asset_pinhole`是针孔检查相机，完整鱼眼图由cubemap映射产生。

重现或继续开发时，在新运行目录复制快照中的`reproduction/render_r15.py`和`trials.json`，把脚本中`reproduction.embedded_source_run_to_replace`对应的旧运行路径替换为新目录，再运行`MUJOCO_GL=egl <python> <新目录>/render_r15.py r15`。源资产路径保持只读。配置中`historical_parent_metrics_not_r15_evaluation`仅保存历史数值，不能引用为本版准确率。

导入r15必须保留OBJ的vt／面UV、MTL及PNG，或使用内嵌贴图的Blender／GLB。MuJoCo绑定2D texture＋material，并使用白色geom rgba避免二次染色；只替换mesh路径并沿用纯色材质会丢失标志。坐标解释与组件映射可参考[历史接入合同](wrist-assets-handoff.md)，但版本路径以WVA-01清单为准。

## 已知差异与下一版方向

当前仍存在衬垫偏亮黄、黑臂偏黑、金属反光、拉环形态、插槽相对位置及背景差异。手机照片／点云只提供近似尺寸；内参文件与本次采集硬件、模式的绑定未确认，插槽尚未逐帧拟合。标志是照片描摹，不是官方矢量稿，额外marker贴纸按用户要求不建模。

本版接受范围是视觉资产和当前静态对比。未新增真实相机标定、抓取接触／惯性、机器人碰撞或策略训练验证，不能继承旧资产的BC／RL成功率或r10轮廓误差。后续可分别改善材质光照、拉环／夹持姿态及逐帧插槽投影；变化另存WVA-02或新的资产修订，保留本版可复现结果。

## 当前能力结论与记录位置

**仿真视觉资产已经具备**：模型和纹理、可加载的静态MuJoCo组合、腕部鱼眼渲染、真实采集对比、版本哈希与接续说明均已交付。已有碰撞资产／控制训练仍按各自版本验收；WVA-01不自动替换当前r10 Isaac训练场景。

本页为按资产能力维护的纪传体；开发顺序和用户确认保存于[领域编年体](../chronicles/2026-11-22-wva01-assets.md)。最新索引同步在[项目当前总览](../../../current.md)、[仿真当前摘要](../current.md)、[仿真器专门记录](../../../simulation.md)、[Mesh开发记录](../../../mesh-development.md)和[能力总表](../../../capabilities.md)。命名阶段的[独立验证报告](/data/omi_runtime/runs/wva01_designation_20261122/verification.json)包含快照／677项依赖哈希、场景加载和相机位置核对。
