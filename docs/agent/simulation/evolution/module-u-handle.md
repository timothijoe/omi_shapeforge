# OM-001/V4 r08：U形拉环粗补全

2026-11-22，用户要求先补全拉环，但明确拉环不是主要矛盾。另建 **V4-r08 · U形拉环补全候选**：原两侧分离拉臂替换为一个连续U形带体，16份非绿色部件OBJ逐字节保持r07原样；总计17件。r05暂定基线及r07原件均保留。

拉环仅按照片作粗略补全：中性中心线从Y≈35.9至76 mm，带体厚约2 mm、主体宽约2.6 mm，根部渐收至1.2 mm。根部等宽初稿与黑色夹持面相交，已缩窄；旧失败稿保存在运行目录。未对拉环像素相似度持续调参，主体轮廓工作见[WG-r10](wrist-primary-refinement.md)。

新U形mesh闭合、法向一致、单连通、正体积；Blender／OBJ／GLB重开及包络验证通过。默认资产为中性姿态，组合展示采用假设铰点下−35°。0／−25／−35°的局部模块／工具相交检查通过，−40°与黑色胶塞相交，已明确不用。它不是已标定铰链行程、弹性结构或新碰撞资产；原2个开放装饰折缝仍按历史外观件保留。

- [Blender](/data/omi_runtime/assets/optical_module_v4/r08/OM-001-V4-r08.blend) · [GLB](/data/omi_runtime/assets/optical_module_v4/r08/OM-001-V4-r08.glb) · [预览](/data/omi_runtime/assets/optical_module_v4/r08/preview.png)
- [验证](/data/omi_runtime/assets/optical_module_v4/r08/validation.json) · [显式MuJoCo视觉替换说明](/data/omi_runtime/assets/optical_module_v4/r08/mujoco_visual_patch.json)
- [联合登记](../../../../manifests/wrist_primary_refinement_20261122.json)

继承r07纯色材质，无新增颗粒纹理。新manifest保留16个原件的source_part_index，旧绿色索引8／10移除、改加U形件；不能直接把新17件列表按旧18件顺序覆盖。当前只在独立静态视觉场景接入，未替换旧训练或物理接触资产。
