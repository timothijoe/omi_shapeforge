# 腕部相机与夹爪：WG-r05双目参考精修版

> 本机迁移提示（2026-11-24）：运行资源实体已迁至 `/data/shapeforge/runtime`；本文中的 `/data/omi_runtime` 是保留的兼容入口，指向同一份内容。目录映射与恢复要求见[当前资源契约](../../interfaces/local-resources.md)。

最新工具为[WG-r07照片轮廓修正版](wrist-tool-photo-profile.md)：双峰黄色衬垫、中央凹口与收窄指臂，侧视复核衬垫厚度27→12 mm；49件检查通过，基体／相机保持r06不变，旧资产保留。

## 最新材质修订：WG-r06黄色衬垫

用户指出r05衬垫偏红，实物应为黄色。已另存 **WG-DAIMON-REFINED-r06「黄色衬垫修正版」**，只调整两侧穿孔衬垫及内侧横筋共4件的材质；49份逐件OBJ字节与r05相同，相机独立GLB也逐字节相同，完整／夹爪GLB重开包络和件数不变。原r05保留。

采用暖黄色sRGB `(245,190,20)`，Blender／GLB使用对应线性底色，MuJoCo显式使用该显示色RGBA，避免沿用偏红的旧材质值。照片曝光和渲染光照不同，此次按用户反馈修正色调，未做色卡标定。形状、尺寸、相机位置、开合设置及既有物理验证边界均不变。

- [实物／r05／r06颜色对比](/data/omi_runtime/runs/wrist_tool_yellow_20261122/yellow_liner_comparison.png)
- [r06 Blender](/data/omi_runtime/assets/daimon/wrist_gripper_refined_r06/WG-DAIMON-REFINED-r06.blend) · [独立夹爪](/data/omi_runtime/assets/daimon/wrist_gripper_refined_r06/gripper.glb) · [独立相机](/data/omi_runtime/assets/daimon/wrist_gripper_refined_r06/wrist_camera.glb)
- [验证](/data/omi_runtime/assets/daimon/wrist_gripper_refined_r06/validation.json) · [登记](../../../../manifests/wrist_tool_yellow_20261122.json)

以下为r05几何开发历史；其中“橙色”是旧版命名，后续显示颜色以本节黄色修订为准。


2026-11-22，按用户要求综合新采集的两段多视角录制、原视频和指尖照片，创建独立 **WG-DAIMON-REFINED-r05「双目参考精修版」**。原WG-DAIMON-VIS-r04和光模块r07保留；本轮不是全扫描融合，而是局部双目尺寸证据支持的Blender参数化精修。

## 输入与尺寸依据

- 新数据：`nov_22/session_backup_20261121_20261122_20261122_014108`中两段D435工具建模录制已有QC帧；使用232640的sample_00／07／12及232055的sample_03。
- 原视频：`/home/linux/Downloads/飞书20261121-212005.qt`及已有抽帧；指尖照片`20261122-000122.jpg`、`20261122-000200.jpg`。新旧照片共同约束外壳、短支架和黑色接触面形状，附加marker不建模。
- 对四组左右IR实际运行FoundationStereo ViT-S、32次迭代，使用本录制49.975 mm基线与相机标定，将深度按列主序外参重投影到RGB。不是拿旧相机内参直接套用。
- 人工选择平面内点，拟合局部平面，再把相邻轮廓端点投影到平面估算尺寸。局部残差不能代表绝对精度；黑色曲面、轮廓点、平面外推和双目系统误差仍存在。

| 项目 | 本轮局部估计 | 新资产采用值／解释 |
| --- | --- | --- |
| 指臂根部到指尖 | 120.1 mm | 120 mm名义轴向长度 |
| 银色指尖壳长度 | 39.5 mm | 40 mm，改为渐窄外壳 |
| 闭合指臂外侧跨度 | 81.1 mm | 约81 mm，平滑轮廓有轻微收缩 |
| 相机侧面高／厚 | 38.8／27.7 mm | 高40／厚28 mm |
| 相机正面宽 | 43.7 mm，较弱的斜视估计 | 宽42 mm；仍需实测 |
| 驱动体侧面截面高度／轴长 | 84.0／80.4 mm | 主体80×70×76 mm，黑色顶盖额外约4 mm |
| 顶面宽／轴长 | 71.0／75.4 mm | 宽70 mm、轴长76 mm支持 |
| 法兰直径 | 沿用URDF参考 | 72 mm，未用本轮数据重新计量 |
| 指尖黑垫名义最小间隙 | 显示装配设置 | 18.8 mm，并非新实测夹持开度 |

相机斜视前面还得到55.9 mm高度外推，与侧面证据不一致，**已拒绝采用**；不能挑选所有输出作为真实尺寸。完整选点、拟合残差和被拒绝的估计保存在[尺寸证据](/data/omi_runtime/runs/wrist_tool_refinement_20261122/dimension_evidence.json)，四帧推理记录在[双目报告](/data/omi_runtime/runs/wrist_tool_refinement_20261122/stereo/report.json)。

## 形状精修及拆分

共49个工具部件：驱动体、顶盖、法兰、滑块、左右平滑弯指、带真实六角开孔的橙色衬垫、内侧横向筋、渐窄银色指尖壳、独立凸起的圆角矩形黑色接触面、指尖线缆、侧接口／线缆及独立相机。

黑色夹持面向两指中间凸出，不能再把橙色衬垫当作直接夹持模块的面。相机包含脚座、短颈、圆角壳、前盖／接缝、镜框、镜片和紧固点。隐藏面与部分细节按对称／装配关系补全，不声称为厂家CAD。橙色开孔和筋是可见几何，不是给光模块重新加入颗粒；r07模块原件未改。

坐标统一为米制TCP法兰系：+Z指向指尖、+X指向相机／顶面、夹指沿Y开合。分别导出完整工具、相机（含安装座）、夹爪GLB，保留公共坐标便于直接装配。Blender另含18件r07参考模块，参考模块不计入49件，也不进入工具GLB。

## 产物与查看

- [新资产与实物参考图](/data/omi_runtime/runs/wrist_tool_refinement_20261122/refined_tool_review.png)：参考视角未做精确配准，仅作外形审阅。
- [完整Blender](/data/omi_runtime/assets/daimon/wrist_gripper_refined_r05/WG-DAIMON-REFINED-r05.blend) · [完整工具GLB](/data/omi_runtime/assets/daimon/wrist_gripper_refined_r05/WG-DAIMON-REFINED-r05.glb)。
- [独立腕部相机GLB](/data/omi_runtime/assets/daimon/wrist_gripper_refined_r05/wrist_camera.glb) · [独立夹爪GLB](/data/omi_runtime/assets/daimon/wrist_gripper_refined_r05/gripper.glb)。
- [MuJoCo开合／相机预览场景](/data/omi_runtime/assets/daimon/wrist_gripper_refined_r05/preview_scene.xml) · [操作教程](../../../../tutorials/refined_wrist_tool.md)。
- [资产清单](/data/omi_runtime/assets/daimon/wrist_gripper_refined_r05/asset_manifest.json) · [仓库登记](../../../../manifests/wrist_tool_refinement_20261122.json)。

## 验证与当前边界

49个工具网格均闭合、法向一致、正体积、无退化面；Blender重新打开后49件顶点与逐件OBJ一致，另有18件参考模块。完整与两份独立GLB重开包络一致。六角孔布尔最初在衬垫底面发生共面边界问题，已将切割体延伸穿过底面，重新生成并通过上述检查。

MuJoCo可加载49个mesh、两个滑动关节；示意闭合间隙18.8 mm，每指向外移动12 mm后的间隙42.8 mm。镜头坐标与清单一致，双指开合不移动相机。640×480镜头视图中左右指各可见5267像素，相机自身外壳未遮挡镜头，见[镜头可见性检查](/data/omi_runtime/runs/wrist_tool_refinement_20261122/wrist_view_check.json)。两指的0.05 kg质量和惯量只是独立运动展示的数值占位，全部工具几何关闭碰撞；本场景不作物理抓取测试。

r07参考模块采用固定变换，名义装配与工具无网格相交；黑色垫到模块表面最近约0.543 mm，**尚未接触，也未建立力学夹持**。本轮没有把它接回机械臂执行插入，不能沿用旧r04约1.961 mm路径间隙或2/2规则成绩来认证新尺寸工具。直接受保护的77个旧工具／模块文件哈希未变。

验证：[几何与MuJoCo检查](/data/omi_runtime/assets/daimon/wrist_gripper_refined_r05/validation.json) · [Blender重开](/data/omi_runtime/assets/daimon/wrist_gripper_refined_r05/blender_reopen.json)。

光学中心放在镜片前方0.6 mm以便渲染，方向为外观拟合；预览仍用90°针孔。没有把扫描D435标定当作腕部相机标定，也未完成真机相机外参、夹持变换、惯量、摩擦、触觉、动态混合图或新策略训练。下一步先审阅尺寸／轮廓，随后在新场景中重做工具安装、插槽路径净空与双相机验证，再接训练。

构建、四帧推理、选点测量、校验、对照图与查看脚本在资产`build_scripts/`；完整运行产物位于`/data/omi_runtime/runs/wrist_tool_refinement_20261122/`。旧候选保留，当前候选未替换任何既有实时训练场景。
