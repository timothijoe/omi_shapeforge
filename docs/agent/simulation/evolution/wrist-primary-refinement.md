# WG-r10：以主体轮廓为重点的内沿遮挡修正

> 本机迁移提示（2026-11-24）：运行资源实体已迁至 `/data/shapeforge/runtime`；本文中的 `/data/omi_runtime` 是保留的兼容入口，指向同一份内容。目录映射与恢复要求见[当前资源契约](../../interfaces/local-resources.md)。

2026-11-22，用户要求补全拉环后继续试验，同时强调优先把其他主体部分做好。本轮交付 **WG-r10 · 内沿遮挡修正版**及独立[OM-r08 U形拉环候选](module-u-handle.md)。最终版本保留r09相机几何、内外参、开度及模块参考夹持变换，不把拉环作为主要拟合指标。所有旧资产保留。

## 主体修改与取舍

固定r09点云约束的黑臂外轮廓和黄色件，测试黑色上沿向外让出0.8／1.2／1.6 mm，以减少对黄色衬垫的遮挡。变化只作用于中段，靠近根部和银色指尖渐变回原值。选择1.6 mm候选，最终只修改左右两份黑臂OBJ，其他47份工具OBJ不变；相机独立GLB保持原字节。

曾同时尝试前阶段“镜头微调”候选，像素黑臂误差较低，但相机区域点云P90由约6.22升到7.41 mm，因此拒绝作为正式镜头修改。该中间稿存为draft_camera_micro，不是正式资产入口。最终明确回到r09相机，而不是继续为图像相似度移动镜头。

主黑臂点云复核P90约1.90 mm，整体基本不变。局部内沿点集P90约0.71→1.00 mm、中位约0.23→0.36 mm，是可见外缘改善与局部表面贴合之间的小幅折中，不能写成“所有点云误差都改善”；该差异低于既有配准／锚定不确定性，但仍完整记录。

[方案选择](/data/omi_runtime/runs/wrist_primary_refinement_20261122/selected_candidate.json) · [整体点云比较](/data/omi_runtime/runs/wrist_primary_refinement_20261122/lip_surface_evaluation.json) · [局部与相机取舍](/data/omi_runtime/runs/wrist_primary_refinement_20261122/local_cloud_tradeoff.json)。

## 图像复核

主要指标只比较黑臂／黄色外缘，拉环不进入优化目标。原图1920×1080，真实侧用局部颜色连通区域，仿真侧用几何ID；沿5行测量外侧包络，因此不是完整图像准确率。

| 数据集合 | r09黑臂／黄色平均偏差 | 最终候选黑臂／黄色平均偏差 |
| --- | --- | --- |
| 确认单元002／006／009／013 | 7.43／11.73 px | 7.63／6.98 px |
| 参数锁定后的单元004／007／011 | 7.33／10.93 px | **7.53／6.17 px** |

前一组参与了固定／微调镜头方案的确认，不能称作完全独立最终测试；后一组未用于参数选择。后一组逐帧黄色误差4.9、4.8、8.8 px，仍有差异。黑臂变化约0.2 px，属于基本保持原水平，不能继续引用微调镜头方案的3.4 px作为最终成绩。

[最终三单元报告](/data/omi_runtime/runs/wrist_primary_refinement_20261122/final_check_evaluation.json) · [真实掩码复核图](/data/omi_runtime/runs/wrist_primary_refinement_20261122/final_check_frame_review.png) · [确认单元报告](/data/omi_runtime/runs/wrist_primary_refinement_20261122/fixed_camera_new_check.json)。

[真机／r09／最终组合图](/data/omi_runtime/runs/wrist_primary_refinement_20261122/primary_refinement_comparison.png)保持相同原图坐标裁剪，没有真实手部像素覆盖。最终导出模型的黑臂／黄色分割图与选定试验完全一致，见[最终渲染一致性](/data/omi_runtime/runs/wrist_primary_refinement_20261122/final_render_equivalence.json)。

## 交付与验证

- [WG-r10 Blender](/data/omi_runtime/assets/daimon/wrist_gripper_observation_r10/WG-DAIMON-OBS-r10.blend) · [完整工具GLB](/data/omi_runtime/assets/daimon/wrist_gripper_observation_r10/WG-DAIMON-OBS-r10.glb)
- [独立夹爪](/data/omi_runtime/assets/daimon/wrist_gripper_observation_r10/gripper.glb) · [独立相机（不变）](/data/omi_runtime/assets/daimon/wrist_gripper_observation_r10/wrist_camera.glb)
- [工具验证](/data/omi_runtime/assets/daimon/wrist_gripper_observation_r10/validation.json) · [Blender重开](/data/omi_runtime/assets/daimon/wrist_gripper_observation_r10/blender_reopen.json)
- [新光模块及U形件](module-u-handle.md) · [登记](../../../../manifests/wrist_primary_refinement_20261122.json)

49件工具拓扑／GLB／Blender／MuJoCo加载验证通过；Blender另含17件新模块的参考展示。当前−35°拉环展示姿态下工具与模块无网格相交，黑垫间隙仍约0.046／0.602 mm，不能视为真实双侧夹紧。模块主体16件原始几何未改，保留金属材质、尾槽空窗、黑塞结构和尺寸依据。

当前改进集中在主要可见轮廓。模块相对夹爪的状态仍随采集样本变化；本次没有生成全批次可靠6D标签。材质、环境、部分遮挡和拉环真实柔性仍不一致，拉环只粗补全，不再作为主要调参对象。

未改原MuJoCo／Isaac任务场景、控制、碰撞资产或权重，未新增策略训练成绩。新资产需要另行验证机器人安装路径与接触，不能自动继承旧成功率。

## 查看与复现

- 对比图窗口：`/data/omi_runtime/envs/omi_mesh_audit/bin/python /data/omi_runtime/runs/wrist_primary_refinement_20261122/view_comparison.py`
- 独立静态组合场景：`MUJOCO_GL=glfw /data/omi_runtime/envs/omi_mesh_audit/bin/python /data/omi_runtime/runs/wrist_primary_refinement_20261122/view_primary_scene.py`。默认自由视角；1自由、2针孔检查视角。没有进行物理步进；鱼眼结果看对比图。
- 重渲染：`MUJOCO_GL=egl /data/omi_runtime/envs/omi_mesh_audit/bin/python /data/omi_runtime/runs/wrist_primary_refinement_20261122/render_final.py final`。

完整运行目录`/data/omi_runtime/runs/wrist_primary_refinement_20261122/`。脚本和关键证据随两份新资产保存；Rejected／draft目录只作中间证据，不替代正式版本。
