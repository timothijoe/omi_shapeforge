# WG-r07：照片轮廓与双峰黄色衬垫修正

新增[WG-r08腕部投影对齐候选](wrist-alignment.md)：调整镜头安装、同步移动相机壳／短颈和参考夹持变换，夹爪几何保留；4个留出单元选定边缘约16～18→3 px，完整画面和绿色拉环仍未一致。

最新[尺寸与腕部图像核对](wrist-camera-consistency.md)：网格尺寸符合建模参数，但真实尺寸未认证；当前针孔与真机不一致，同位姿鱼眼候选仍有黄色区域、掌部遮挡和绿色拉环差异，尚未完成外参／夹持关系校准。

2026-11-22，用户提供`/home/linux/Downloads/img/20261122-113448.jpg`，指出夹爪尺寸及黄色衬垫形状仍需按照片调整。新建 **WG-DAIMON-REFINED-r07「双峰衬垫轮廓修正版」**，保留WG-r06黄色及相机资产。此WG-r07是工具版本，与光模块OM-001/V4 r07不同。

## 观察与建模改动

旧黄色衬垫近似等宽长条，实际内缘有两处向内凸起、中间凹口、根部收窄和指尖下的窄条延伸；新图同时显示黑色指臂较旧模型窄，银色壳与黑色接触垫比例需要调整。

先在原图局部ROI内用HSV提取黄色外轮廓，再用平滑曲线建立镜像名义轮廓，避免把孔洞、照明噪声和锯齿全部做成轮廓。黑色指臂和银色壳采用人工边界点。采用6.9 px/mm及模块轴向斜率0.045作为弱透视拟合近似，结合此前模块宽度及双目指臂长度约束；这是本照片的轮廓建模比例，不是独立相机标定或精确尺寸测量。

| 项目 | r06 | r07名义值／变化 |
| --- | --- | --- |
| 指臂外侧跨度 | 约81 mm | 约75.4 mm，重建弧形轮廓 |
| 指臂根部至指尖 | 120 mm | 约119.6 mm |
| 银色指尖轴长 | 40 mm | 约37.9 mm |
| 凸起黑色接触垫轴长 | 29 mm | 24 mm，随照片比例微调位置 |
| 名义黑垫最小间隙 | 18.8 mm | 18.4 mm；示意值，非真实夹持标定 |
| 黄色衬垫内缘 | 等宽近直条 | 双峰、中央凹口、两端细窄延伸 |
| 黄色衬垫厚度 | 27 mm | **12 mm**，位于TCP X=3.5～15.5 mm |
| 六角孔／横筋 | 旧密度及直边分布 | 约2.6 mm节距、孔半径0.85 mm，随新内缘排列 |

27 mm旧厚度是此前错误的厚实体近似。用已有232640录制sample_07侧视RGB和本轮前一阶段的双目深度，局部平面加三段边界选点得到约11.17、11.77、12.04 mm，采用12 mm建模。该估计仍有遮挡、曲面和边界选点误差，不能写成卡尺实测。指臂／指尖的深度方向厚度沿用r06，相机及基体未因这张俯视照片缩放。

证据：[黄色轮廓提取](/data/omi_runtime/runs/wrist_tool_profile_20261122/yellow_contour_reference.png)、[目标轮廓叠加](/data/omi_runtime/runs/wrist_tool_profile_20261122/target_profile_overlay.png)、[设计参数](/data/omi_runtime/runs/wrist_tool_profile_20261122/design_profiles.json)、[侧视厚度估计](/data/omi_runtime/runs/wrist_tool_profile_20261122/liner_thickness_evidence.json)。

## 几何、导出和装配检查

49件工具部件中22件夹指相关部件重新生成，27件基体／相机OBJ与r06逐字节相同；独立相机GLB也完全相同。全部49件闭合、法向一致、正体积、无退化面；Blender重新打开后与OBJ顶点一致，完整及独立GLB包络检查通过。

首次按新俯视轮廓仍保留27 mm厚衬垫时，与参考光模块侧壁／头盖和绿色拉环相交，失败稿保存在运行目录`draft_full_depth/`。补做侧视厚度估计并修正为12 mm后，名义参考装配**无网格相交**，黑垫距模块表面约0.150 mm，仍不是实际接触抓取。参考光模块显示位置由TCP Z=235改为217 mm以对齐照片中的头部位置；模块原几何不改，此变换也未作真机标定。

MuJoCo可加载49个mesh与两个滑动关节；每侧向外12 mm后名义间隙42.4 mm。腕部针孔视图640×480下左右指各可见5236像素，相机外壳未挡住镜头。工具关闭碰撞，质量／惯量仍为展示占位。新增俯视相机便于检查照片轮廓，未改变腕部相机的外观安装参数。

同一拟合照片的黄色填充轮廓IoU约从0.173升至0.797。它只检查本次平面拟合改善，**不是独立照片评估或三维精度**。实际照片仍有透视、非对称遮挡及材质光照差异。

验证：[网格、导出、名义装配与相机](/data/omi_runtime/assets/daimon/wrist_gripper_refined_r07/validation.json)、[Blender重开](/data/omi_runtime/assets/daimon/wrist_gripper_refined_r07/blender_reopen.json)、[拟合照片轮廓检查](/data/omi_runtime/runs/wrist_tool_profile_20261122/photo_outline_check.json)。102个直接受保护旧文件哈希未变。未重新执行机器人插入、动力学抓取或策略训练。

## 当前交付

- [实物／r06／r07对比图](/data/omi_runtime/runs/wrist_tool_profile_20261122/photo_profile_comparison.png)
- [r07完整Blender](/data/omi_runtime/assets/daimon/wrist_gripper_refined_r07/WG-DAIMON-REFINED-r07.blend) · [完整工具GLB](/data/omi_runtime/assets/daimon/wrist_gripper_refined_r07/WG-DAIMON-REFINED-r07.glb)
- [独立夹爪](/data/omi_runtime/assets/daimon/wrist_gripper_refined_r07/gripper.glb) · [独立相机（未改）](/data/omi_runtime/assets/daimon/wrist_gripper_refined_r07/wrist_camera.glb)
- [登记](../../../../manifests/wrist_tool_profile_20261122.json) · [操作](../../../../tutorials/refined_wrist_tool.md)

脚本、参数和验证证据随资产保存在`build_scripts/`与`evidence/`；完整运行目录为`/data/omi_runtime/runs/wrist_tool_profile_20261122/`。下一步先由用户复核轮廓，再验证新工具在插槽附近的路径、真实夹持深度和相机外参；不能直接沿用旧WG-r04的插入成功或净空结论。

## 查看器交互修正

用户反馈无法拖动，原因是初始使用固定俯视相机。已将运行窗口切回自由视角，并将启动脚本默认改为自由视角、仅在快捷键切换时设置相机；1恢复自由查看，2／3为固定相机。该修正不改变mesh或动力学参数。
