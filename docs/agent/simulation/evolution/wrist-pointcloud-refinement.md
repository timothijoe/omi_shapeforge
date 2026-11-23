# WG-r09：多视角点云约束的夹爪局部优化

后续[固定r09位姿与开度试验](wrist-pose-study.md)：镜头微调只改善部分指标，未替换主版本；模块相对位置随单元变化，且现有绿色件缺U形连接，不能仅靠全局相机位姿解决。

2026-11-22，用户要求利用已提供的腕部／夹爪扫描继续优化，并保留当前结果。已完整冻结WG-r08，另建 **WG-DAIMON-CLOUD-r09「多视角点云约束候选」**。相机内外参及模块参考夹持变换保持r08不变，本次只修改有点云支持的指臂／衬垫几何。

## 当前结果保留

WG-r08原目录不改，另存完整字节副本`/data/omi_runtime/assets/daimon/releases/wrist_gripper_aligned_r08_frozen_20261122/`，82个文件逐一哈希一致，包含Blender、GLB、网格、脚本、证据及原对比图。名称为“WG-r08 · 图像对齐保留版”，不是实物精度认证。

[保留版登记](../../../../manifests/wrist_tool_r08_preservation_20261122.json)。冻结副本的历史清单保留原绝对路径，移机恢复时需要路径映射，不应改写其历史哈希。

## 点云来源与处理

在用户的nov_22备份中核对到头腕采样点云，以及两段专门扫描工具的MCAP、同步左右IR／RGB／原生深度和标定。原备份说明明确专门工具扫描当时尚未融合最终点云。本轮从这些扫描记录已保存的QC同步帧取15组，4组复用前阶段深度，11组新跑FoundationStereo ViT-S／32次迭代，使用本录制约49.975 mm双目基线，不采用模型尺寸去重定标。

用静态场景SIFT＋双目3D对应进行刚体RANSAC与位姿图优化，没有拟合全局尺度。曾检查背景标板检测，但未把标板检测结果作为最终配准约束，也没有把模块marker写成模型纹理或策略监督。

15个视角中11个连通，4个因对应不足暂不融合：232640_00／02／04／07。位姿图对应残差中位约1.94 mm、P90约4.17 mm。通过参考232055_03中的银色指尖平面与角点，将点云近似锚定到工具TCP坐标，六点刚体锚定RMS约2.2 mm；它不是已知真值坐标标定。

用SAM2的模型辅助框／点提示提取工具部位，检查彩色覆盖图；剔除明显混入机械臂的相机掩码，对黄色表面另用局部颜色和空间区域提取。相机部分只使用5个通过审阅的视角。模型辅助提示和空间裁剪带来先验偏差，不能称作无提示分割或真值点云。

获得545,594个有来源的表面观测，0.8 mm体素下采样后168,762点，保存为[tool_scan_reference.ply](/data/omi_runtime/runs/wrist_pointcloud_refinement_20261122/tool_scan_reference.ply)。这是已配准的多视角观测叠加，**不是闭合融合mesh或完整隐藏面重建**。本次没有重新解码／校验整个MCAP。

证据：[配准](/data/omi_runtime/runs/wrist_pointcloud_refinement_20261122/registration.json) · [坐标锚定](/data/omi_runtime/runs/wrist_pointcloud_refinement_20261122/tool_anchor.json) · [点云数量与分割范围](/data/omi_runtime/runs/wrist_pointcloud_refinement_20261122/cloud_report.json) · [掩码审阅图](/data/omi_runtime/runs/wrist_pointcloud_refinement_20261122/mask_review.jpg)。

## 几何修改

点云支持旧黑臂中后段偏窄、根部上表面抬高而非恒定挤出。根据逐段包络建立变化截面：外侧最大名义跨度约89.2 mm（原75.4 mm），根部上表面TCP X约25 mm，向指尖平滑回到13.5～14.5 mm。根部与端部遮挡较多，采用保守补全，不能把每个参数都标成直接测量。

黄色衬垫的外侧包络按点云扩展，顶面从X=15.5降至12.5 mm、底面从3.5降至0.5 mm，厚度仍12 mm。黑色内侧改成上沿与下部内壁不同的截面，为内凹衬垫留出层次；内部未观测区域仍属建模近似。双峰内缘保留，六角孔和横筋重新生成。

总计49件工具中8件（两侧黑臂／背缝／衬垫／筋）修改，41件保持原OBJ字节。独立相机GLB、相机参数、参考夹持变换均与r08完全相同。没有用再次移动相机来抵消新的轮廓差异。

[点云与截面证据图](/data/omi_runtime/runs/wrist_pointcloud_refinement_20261122/pointcloud_profile_evidence.png) · [形状参数与原始包络估计](/data/omi_runtime/runs/wrist_pointcloud_refinement_20261122/cloud_profile_design.json)。

## 三维复核

用6个视角求解形状参数，其余5个视角做表面复核；复核视角此前仍参与配准和质量检查，因此不是完全独立的真值测试。两版对比使用相同点子集，测量观测点到模型表面的单向距离。

| 复核视角 | r08中位／P90 | r09中位／P90 |
| --- | --- | --- |
| 黑臂 | 0.88／6.30 mm | **0.66／1.90 mm** |
| 黄色衬垫 | 0.59／4.23 mm | **0.46／2.21 mm** |
| 相机区域 | 4.82／6.44 mm | 保持不变 |

相机区域的复核统计仅来自1个通过掩码审阅的复核视角，不能与指臂的5个视角覆盖等同。相机区域尚有明显残差、部分关键侧面视角未能配准，本轮不依据这些不足的覆盖继续修改相机壳或外参。表面距离不包含隐藏面错误，也受到深度、配准、掩码和TCP锚定误差影响，不能解释为实物尺寸达到亚毫米精度。

[逐视角表面评估](/data/omi_runtime/runs/wrist_pointcloud_refinement_20261122/surface_evaluation.json)。

## 腕部图像复核

保持r08镜头、K／D、夹持变换和名义插槽位姿，纯仿真渲染，不叠加真实手部像素。沿同一真实腕部图的5行采样黑臂外缘，平均绝对偏差约 **30.8→7.2 px**；靠腕部y=980处每侧偏差由54／49 px变为5／8 px，新版略偏宽。该图没有参与形状参数求解，但属于前阶段已查看的开发样本，不能称为完全未见测试。

黄色外缘5行平均约11.3→10.9 px，仅小幅改善；部分行略变差，y=980处仍约21／12 px。绿色拉环形状／姿态和光照材质仍未匹配。当前证据支持黑臂主轮廓的改进，不支持“完整相机画面已经一致”。

[真机／r08／r09对比](/data/omi_runtime/runs/wrist_pointcloud_refinement_20261122/cloud_refinement_comparison.png) · [轮廓图](/data/omi_runtime/runs/wrist_pointcloud_refinement_20261122/outer_contour_comparison.png) · [逐行像素统计](/data/omi_runtime/runs/wrist_pointcloud_refinement_20261122/contour_report.json)。

## 导出与范围

49件闭合、法向一致、正体积、无退化面；完整和独立GLB包络、Blender重开与OBJ一致、MuJoCo加载及镜头／关节绑定通过。参考模块无网格相交，黑垫到模块最近间隙维持约0.046／0.602 mm，仍不是实际双侧夹紧。视觉组件连接处可有装配重叠，闭合网格检查不等于真实工具碰撞模型验收。

- [r09 Blender](/data/omi_runtime/assets/daimon/wrist_gripper_cloud_r09/WG-DAIMON-CLOUD-r09.blend) · [完整GLB](/data/omi_runtime/assets/daimon/wrist_gripper_cloud_r09/WG-DAIMON-CLOUD-r09.glb)
- [夹爪GLB](/data/omi_runtime/assets/daimon/wrist_gripper_cloud_r09/gripper.glb) · [相机GLB（保持r08）](/data/omi_runtime/assets/daimon/wrist_gripper_cloud_r09/wrist_camera.glb)
- [几何与装配验证](/data/omi_runtime/assets/daimon/wrist_gripper_cloud_r09/validation.json) · [登记](../../../../manifests/wrist_pointcloud_refinement_20261122.json)

未改变旧机器人／训练场景，未重新验证新外形的插槽路径、真实接触、惯量或训练策略。下一步优先补足相机侧面点云的可靠配准，复核黄色可见轮廓和绿色拉环，再考虑新的机器人安装与训练验证。

脚本与主要证据随资产保存在`build_scripts/`和`evidence/`，完整点云／深度／掩码／渲染在`/data/omi_runtime/runs/wrist_pointcloud_refinement_20261122/`。操作见[教程](../../../../tutorials/refined_wrist_tool.md)。
