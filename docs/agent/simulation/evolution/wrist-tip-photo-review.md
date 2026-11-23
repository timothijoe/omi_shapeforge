# WG-r14：按原始实拍复核银色指尖比例

用户明确红线只是示意，最终需与真实照片看齐。因此将r13作为历史候选保留，另存WG-DAIMON-PHOTO-r14「实拍比例复核指尖候选」。原始依据为`20261122-000200.jpg`近景和`20261122-113448.jpg`俯视实拍；`20261122-222136.jpg`是模型截图标注，本轮不作为尺寸或坐标目标。

## 实拍依据及几何变化

两张照片各人工选择根部内外角、前端内角，作三锚点弱透视平面归一化。前端外角及肩部转折点用于比例复核：前端／后端宽度约16%～23%，平台／轴向长度约19%～21%。r13的对应比例约34%／31%，偏大。本次选取约21%／20%，只修改两个银壳。

| 参数（名义建模值） | r13 | r14 |
| --- | --- | --- |
| 前端短边 | 6.3 mm | 3.8 mm |
| 根部平段轴向长度 | 11.3 mm | 7.5 mm |
| 根部宽度 | 18.3 mm | 18.3 mm |
| 轴向长度 | 约36.8 mm | 约36.8 mm |
| 倒角 | 0.6 mm | 0.6 mm |

原照片包含透视、倒角边缘和手选点误差；归一化的三个锚点本身按定义对齐，不能当作独立验证。照片比例也不是毫米实测。既有立体参考的银壳根部边长约19.1～19.2 mm，锚点／配准误差约2 mm，只提供粗尺度背景；本轮未据此再改绝对尺度。镜像生成两侧；继续保留前端短面、斜边、根部平段和倒角。

[原始照片／r13／r14对比](/data/omi_runtime/runs/wrist_tip_photo_review_20261122/photo_comparison.png) · [两张原图上的比例轮廓叠加](/data/omi_runtime/runs/wrist_tip_photo_review_20261122/original_photo_overlays.png) · [人工点与方法](/data/omi_runtime/runs/wrist_tip_photo_review_20261122/photo_proportion_review.json)。照片和渲染视角不同；叠加图采用同一三锚点归一化，只比较轮廓比例，不是整机同位姿投影结果。

## 验证及接入

49件工具网格闭合、法向一致、正体积、无退化面；Blender重开逐顶点与OBJ一致，GLB包络一致，MuJoCo加载及双指开合通过。银壳与胶皮最大TCP Z均为210.5000019 mm，差0；黑包边仍退后约0.2 mm。47份其他OBJ及相机GLB字节不变，相机和夹持变换不变；76个直接受保护父版文件哈希通过。

当前参考模块无网格相交，左右胶皮至模块最小距离约0.046／0.602 mm，仅是参考装配间隙检查，不证明真实夹持。工具仍是视觉资产；本轮没有更新碰撞／惯性、重新标定相机、跑机器人插入或训练，也未复测整幅腕部像素误差。其他部分和手机照片的视觉差异仍然存在，不能把局部比例改善当作全图匹配。

- [独立候选登记](../../../../manifests/wrist_tip_photo_review_20261122.json)
- [Blender](/data/omi_runtime/assets/daimon/wrist_gripper_photo_r14/WG-DAIMON-PHOTO-r14.blend) · [完整GLB](/data/omi_runtime/assets/daimon/wrist_gripper_photo_r14/WG-DAIMON-PHOTO-r14.glb)
- [资产清单](/data/omi_runtime/assets/daimon/wrist_gripper_photo_r14/asset_manifest.json) · [验证](/data/omi_runtime/assets/daimon/wrist_gripper_photo_r14/validation.json)

其他Agent显式读取r14登记，再按[坐标／组件接入说明](wrist-assets-handoff.md)加载。固定WG-r10＋OM-r08交接清单不变，所有旧版保留；新增指尖形状不能自动继承旧像素拟合成绩。资产内build_scripts／evidence包含本轮生成及复核脚本，完整运行目录`/data/omi_runtime/runs/wrist_tip_photo_review_20261122/`。
