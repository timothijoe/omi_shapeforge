# WG-r08：镜头安装与模块夹持位置的投影对齐候选

新增[WG-r09多视角点云约束候选](wrist-pointcloud-refinement.md)：r08已完整冻结保留；11视角点云支持修改8件局部mesh，镜头和夹持变换不变，黑臂轮廓改善明显，黄色与相机残差仍保留。

后续[整块轮廓诊断](wrist-contour-diagnosis.md)确认：约3 px只适用于选定边缘；靠腕部黑臂每侧仍偏内约49～54 px，黄色外缘约18～28 px。优先查局部mesh／装配并联合复核相机，未将诊断探测相机作为新资产。

2026-11-22，用户确认缺少官方尺寸，授权依据已有采集核对并调整镜头位置／倾角和模块夹持关系。已另建 **WG-DAIMON-ALIGNED-r08「腕部投影对齐候选」**。结论是选定几何边缘投影明显改善，**不是完整真机图像一致或硬件计量标定**。旧WG-r07、光模块r07、全部原采集保留。

## 本次调整方式

固定WG-r07夹爪几何、光模块mesh及用户已有鱼眼K／D，不优化尺度、焦距或畸变。使用unit_001中间腕部帧，人工选择六个银色指尖几何角点和掌部前缘；不使用marker、文字或logo作为对应。先拟合镜头相对工具的6D位姿，再用模块壳体／头盖几何点拟合一个参考夹持变换，带位置／角度边界及弱先验。

俯视照片和既有双目尺寸用于冻结的几何先验；本轮没有将新拟合外参回写成独立测量。单次安装和近似固定夹持的画面不能充分区分所有几何与外参误差。

| 参数（工具TCP系） | WG-r07 | WG-r08候选 |
| --- | --- | --- |
| 镜头光学中心X／Y／Z | (78.02,0,47.38) mm | (86.35,−0.19,55.48) mm |
| 向下倾角参数 | 约6.89° | 约11.15°，另有很小的偏航／滚转 |
| 相机壳局部尺寸 | 42×40×28 mm | 保留，刚体移动／转动 |
| 夹爪及基体 | r07几何 | **39份逐件OBJ字节不变，独立gripper.glb也不变** |
| 相机与支架 | 原安装 | 刚体移动9件相机mesh，重建1件短颈连接座 |
| 参考模块平移 | (0,0,217) mm | (−6.94,−0.65,237.65) mm，另含小角度转动 |

也就是镜头相对原候选约抬高8.33 mm、沿指尖方向前移8.10 mm。相机壳与镜片一起移动，光学中心仍位于镜片中心前0.6 mm，没有只挪虚拟视点却保留旧外壳。短颈同时延伸，与底脚及壳体都相交连接；支架新尺寸用于装配补全，不是厂家参数。

二维夹持拟合初稿与一侧黑垫相交。保持其他拟合量不变，小范围横向搜索后移动0.15 mm去除相交；最终左右黑垫最近表面间隙约0.046／0.602 mm。它只保证名义参考装配不穿插，并不代表两侧已真实夹紧或力学抓取成立。模块原mesh未改变。

## 留出样本复核

unit_003／008／012／014各取一个中间帧，没有用这些帧优化参数。以梯度模板跟踪相同几何边缘，并人工检查对应；unit_008一个被绿色拉环遮挡的角点跟踪错误，已明确剔除。掌部是近水平边界，只评价垂直误差，不能把沿边界的模板位置当成固定点。

| 留出单元 | 接受特征数 | 调整前平均误差 | 调整后平均误差 |
| --- | --- | --- | --- |
| 003 | 7 | 15.80 px | 3.36 px |
| 008 | 6，另剔除1个遮挡角点 | 17.61 px | 3.01 px |
| 012 | 7 | 16.07 px | 2.96 px |
| 014 | 7 | 15.65 px | 2.82 px |

掌部前缘垂直误差约从88～91 px降到1～2 px。该表是少量选定边缘的误差，**不是全图相似度、独立标定真值或毫米精度**；这些单元仍来自同一安装，姿态覆盖有限。

另外对标点施加假设的2 px角点／4 px掌部扰动，40次拟合的5～95百分位镜头X约83.89～88.16 mm、Z约54.03～56.89 mm。这只是标点敏感性，未计入mesh误差或内参误差，不能解释成真实尺寸置信区间。

证据：[拟合参数及3D约束](/data/omi_runtime/runs/wrist_alignment_20261122/constrained_fit_report.json)、[留出复核与剔除原因](/data/omi_runtime/runs/wrist_alignment_20261122/heldout_reviewed_report.json)、[留出对应点图片](/data/omi_runtime/runs/wrist_alignment_20261122/heldout_edge_review.png)、[标点敏感性](/data/omi_runtime/runs/wrist_alignment_20261122/pose_sensitivity.json)。

## 真机／前后对比与仍有差异的部分

[真机／r07／r08对比图](/data/omi_runtime/runs/wrist_alignment_20261122/alignment_comparison.png)保持新旧两图采用相同鱼眼内参、相同原图裁剪区域；均为纯MuJoCo几何渲染，不叠加真实夹爪像素。可见掌部遮挡和衬垫的纵向可见范围改善，指尖与模块的投影更接近参考帧。

绿色拉环的几何／姿态和可见性仍与真实不同，部分指臂及衬垫可见宽度、材质光照也尚不一致。不同采集单元里模块／拉环的相对位置有变化，当前模块固定变换只拟合unit_001，不能直接作为全部样本的夹持真值。插槽仍是名义−2 mm预插入场景，未逐帧重建其位姿；背景也未重建。

已有`wrist_intrinsics_1920x1080.json`作为固定候选内参使用，新采集metadata仍未绑定该文件；本轮不优化它，也不宣称已认证为同设备同模式。后续应继续用几何／多视角约束校核，而非通过缩放夹爪消除所有图像差异。

## 资产与验证

49件工具网格、完整及独立GLB、Blender重开、镜头位置／开合绑定检查通过。39件夹爪／基体OBJ及独立夹爪GLB不变；120个直接受保护旧文件哈希保持。名义模块装配无相交，支架脚—颈—壳连接检查通过。未重新执行机械臂插入、物理抓取、自碰撞或策略训练。

- [r08 Blender](/data/omi_runtime/assets/daimon/wrist_gripper_aligned_r08/WG-DAIMON-ALIGNED-r08.blend) · [完整GLB](/data/omi_runtime/assets/daimon/wrist_gripper_aligned_r08/WG-DAIMON-ALIGNED-r08.glb)
- [相机及安装座](/data/omi_runtime/assets/daimon/wrist_gripper_aligned_r08/wrist_camera.glb) · [夹爪（几何未改）](/data/omi_runtime/assets/daimon/wrist_gripper_aligned_r08/gripper.glb)
- [网格与装配验证](/data/omi_runtime/assets/daimon/wrist_gripper_aligned_r08/validation.json) · [Blender重开](/data/omi_runtime/assets/daimon/wrist_gripper_aligned_r08/blender_reopen.json)
- [资产登记](../../../../manifests/wrist_alignment_20261122.json) · [查看与复现](../../../../tutorials/refined_wrist_tool.md)

资产`observation_projection`保存鱼眼K／D与分辨率；运行目录的`render_aligned.py`负责六面渲染和鱼眼重投影。MuJoCo原生查看器的“2”仍是针孔检查视角，**不能把它当成最终鱼眼图像**；看真实观测对比应使用上述图片／重投影脚本。尚未接入训练环境的实时_capture()。

构建、拟合、约束搜索、留出复核、敏感性、渲染、验证及查看脚本随资产保存于`build_scripts/`，证据在`evidence/`；完整实验目录为`/data/omi_runtime/runs/wrist_alignment_20261122/`。
