# WG-r15：DAIMON表面标志版

用户接受r14实拍比例后要求增加DAIMON标志。另存WG-DAIMON-LOGO-r15，保留r14和所有旧版，固定WG-r10＋OM-r08交接组合不替换。

## 标志制作与资产变化

从原始近景`20261122-000200.jpg`选取银壳平面锚点，做近似仿射展开；在局部ROI分离红色图标、黑色DAIMON字形，轮廓简化为SVG再生成抗锯齿贴图。只提取图形形状，没有复制金属照片纹理、加入颗粒或位移。它是照片描摹的近似字形，不是厂家矢量原稿。

依据`20261122-113448.jpg`的俯视实拍，标志放在两侧银壳靠根部位置，正俯视下上侧正常阅读、下侧转180度，字形不镜像。标志包络约18.9×5.3 mm，属于现有模型尺度下的近似位置和大小。

49件工具顶点及三角面连接与r14一致。只为两份银壳增加UV与材质；47份OBJ、相机GLB字节不变。标志只作用于工具+X方向银壳宽面，其余面UV落到纯银色区域；没有贴片厚度或新增碰撞几何。原银壳Blender底色／粗糙度保留，标志像素设为非金属。颜色仍会随光照和渲染器变化。

## 验证与接入

Blender重开顶点与OBJ一致，GLB包络检查通过；UV接缝合并后49件均闭合、法向一致、正体积、无退化面。MuJoCo加载49mesh、双指开合及实际渲染检查通过，两侧标志朝向正确。参考模块无相交，胶皮间隙和银壳前端齐平继承r14；相机／夹持变换未改，76个直接受保护父版文件哈希不变。本轮没有新增动力学、训练或腕部全图匹配结论。

- [独立候选登记](../../../../manifests/wrist_logo_20261122.json)
- [真实照片／r15对比](/data/omi_runtime/runs/wrist_logo_20261122/logo_comparison.png)
- [Blender](/data/omi_runtime/assets/daimon/wrist_gripper_logo_r15/WG-DAIMON-LOGO-r15.blend) · [完整GLB](/data/omi_runtime/assets/daimon/wrist_gripper_logo_r15/WG-DAIMON-LOGO-r15.glb)
- [MuJoCo独立预览场景](/data/omi_runtime/assets/daimon/wrist_gripper_logo_r15/preview_scene.xml) · [MuJoCo标志渲染](/data/omi_runtime/runs/wrist_logo_20261122/mujoco_logo_top.png)
- [几何验证](/data/omi_runtime/assets/daimon/wrist_gripper_logo_r15/validation.json)

其他Agent接入需保留`textures/`及银壳OBJ的vt／面UV索引；只复制顶点或沿用旧纯色材质会丢失标志。Blender／GLB已内嵌贴图，OBJ配套MTL／PNG；MuJoCo需要加载2D texture＋material、保留mesh UV，银壳geom rgba为白色以避免二次染色，参考本版preview_scene.xml。其他坐标和组件关系沿用[接入说明](wrist-assets-handoff.md)。主机器人场景未自动切换。

运行目录`/data/omi_runtime/runs/wrist_logo_20261122/`；资产build_scripts和evidence收录生成脚本、轮廓SVG、照片来源与对比证据。

## r15真实腕部采集／仿真对比

新增[完整画面与同区域放大](/data/omi_runtime/runs/wrist_r15_capture_compare_20261122/real_vs_sim_wrist_r15.png)及[夹持部位细节](/data/omi_runtime/runs/wrist_r15_capture_compare_20261122/wrist_detail_r15.png)。真实来源是nov22备份中的unit_001、sample_20261121_212334_434186_62cb90/wrist_rgb.png，属于此前相机／夹持参考位姿拟合帧，不是新留出集评估。

本次独立场景加载WG-r15＋OM-r08＋SIM-r06插槽，显式绑定银壳UV和2D标志纹理。用6面cubemap和既有K／D生成1920×1080鱼眼图；相机与模块夹持变换保持既有候选，插槽采用−2 mm参考预插入状态，没有按本帧另拟合。新采集与内参文件的硬件／模式绑定仍未确认。

左右采用同尺寸、同像素坐标裁剪；真实照片未调色或单独几何拉伸，仿真未混入真实夹爪像素。夹爪／模块大致位置接近，但衬垫偏亮黄、黑臂偏黑、银色反光、拉环形态、插槽相对位置及背景仍明显不同。标志可见不代表完整像素匹配。marker贴纸按既有要求未建模。

[来源／哈希／对比登记](../../../../manifests/wrist_r15_capture_compare_20261122.json)，运行与渲染脚本在`/data/omi_runtime/runs/wrist_r15_capture_compare_20261122/`。r15资产文件及固定WG-r10交接清单未修改，无新训练结论。
