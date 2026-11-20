# 已有资产与可视化结果

核对日期：2026-11-20。本次找到 **2496 个可视化文件、78 个分组**，覆盖本机运行、便携包和恢复的旧机实验 results 目录。原始采集数据帧、第三方软件素材不纳入此展示目录。未去除重复图或失败试验，方便回溯。

完整清单：[CSV](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/files.csv>) · [JSON](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/inventory.json>)。图片、模型和逐组图册均在外部资源目录；本仓库仅维护入口。

## 当前资产状态

| 资产 | 状态 | 边界 |
| --- | --- | --- |
| 光模块 Blender | 照片稿、米制修正版、连通槽、V2 参考共四份；本机重开检查通过 | 完整重新生成和实物精度未验收 |
| 仿真外观网格 | 已导出 15 个部件 | 复杂材质和柔性未完整保留 |
| 单模块／2×2 场景 | MuJoCo 有初末态图；Isaac PhysX CPU 有状态和 USD | 盒碰撞、假设质量／摩擦；Isaac 没有已验收 RTX 图像 |
| 机器人／夹爪 | 双臂 MJCF 静态加载与图像通过；两份完整 URDF 资源齐全 | 旧灵巧手／刀具不是当前夹爪配置，尚未接入光模块任务 |
| 点云配准 | 已确认 ROI 配准可复验 | 人工先验，低残差不等于真实位姿精度 |

能力与证据见[仿真现状](agent/simulation/current.md)、[感知现状](agent/perception/current.md)。

## 建议先看的图

| 内容 | 原图 |
| --- | --- |
| 照片与早期模型对比（历史照片稿） | [查看](</data/omi_runtime/inputs/optical_packages_20261120_001316/optical_module_portable_20261119/results_reference/previews/photo_vs_model.png>) |
| 连通槽模型本机渲染 | [查看](</data/omi_runtime/runs/blender_validation_20261120/reference_0001.png>) |
| 目标选区修正与配准（历史对比） | [查看](</data/omi_runtime/inputs/optical_packages_20261120_001316/optical_module_portable_20261119/results_reference/previews/annotation_vs_corrected_overlay.png>) |
| 单模块落台末态 | [查看](</data/omi_runtime/runs/mujoco_optical_v3_20261120/settled.png>) |
| 2×2 场景落台末态 | [查看](</data/omi_runtime/runs/mujoco_optical_array_v2_20261120/settled.png>) |
| 机器人旧场景总览 | [查看](</data/omi_runtime/runs/omi_robot_asset_review_20261120/robot_scene_overview.png>) |
| 官方双目点云预览 | [查看](</data/omi_runtime/runs/stereo_official_20261119/cloud_preview.png>) |
| LoFTR 匹配 | [查看](</data/omi_runtime/runs/omi_shapeforge/20261120T014828_903620Z_bundlesdf/loftr_matches.jpg>) |

## 交互查看与模型源文件

HTML 保留原文件；本次只确认文件存在，未声称所有旧页面的交互或依赖均可用。

- [本机配准叠加](</data/omi_runtime/runs/optical_portable_20261120_001316/overlay.html>)

- [官方点云交互预览](</data/omi_runtime/runs/stereo_official_20261119/cloud_preview.html>)

- [便携包点云与模型](</data/omi_runtime/inputs/optical_packages_20261120_001316/optical_module_quick/view/pointcloud_mesh_overlay.html>)

- [photo_unscaled.blend](</data/omi_runtime/inputs/optical_packages_20261120_001316/optical_module_portable_20261119/models/photo_unscaled.blend>)

- [stereo_refined.blend](</data/omi_runtime/inputs/optical_packages_20261120_001316/optical_module_portable_20261119/models/stereo_refined.blend>)

- [connected_groove.blend](</data/omi_runtime/inputs/optical_packages_20261120_001316/optical_module_portable_20261119/models/connected_groove.blend>)

- [v2_reference.blend](</data/omi_runtime/inputs/optical_packages_20261120_001316/optical_module_portable_20261119/models/v2_reference.blend>)

- [v2_reference.glb](</data/omi_runtime/inputs/optical_packages_20261120_001316/optical_module_portable_20261119/models/v2_reference.glb>)

## 完整分组图册

每个图册直接展示该组所有图片，HTML／视频以原文件链接提供。大型逐帧图册加载可能较慢。旧机组只表示文件已恢复，不等于本机重算或最终结论。

| 分组 | 文件数 | 图册 |
| --- | --- | --- |
| 光模块便携包 / optical_module_portable_20261119 | 15 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/01.md>) |
| 光模块便携包 / optical_module_quick | 2 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/02.md>) |
| 旧机实验归档 / aperture_crosschecks_20261117_v1 | 1 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/03.md>) |
| 旧机实验归档 / aperture_detail_rebuild_20261119_v2 | 48 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/04.md>) |
| 旧机实验归档 / aperture_dimension_insertion_20261119_v1 | 11 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/05.md>) |
| 旧机实验归档 / aperture_edges_development_20261117_v1 | 8 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/06.md>) |
| 旧机实验归档 / aperture_human_reference_20261117_v1 | 11 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/07.md>) |
| 旧机实验归档 / aperture_joint_20261117_v1 | 119 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/08.md>) |
| 旧机实验归档 / aperture_prior_rebuild_20261119_v1 | 162 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/09.md>) |
| 旧机实验归档 / body_aperture_audit_20261117_v1 | 40 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/10.md>) |
| 旧机实验归档 / box_clear_outward_20261116_v1 | 1 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/11.md>) |
| 旧机实验归档 / box_clear_preview_20261116_v1 | 1 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/12.md>) |
| 旧机实验归档 / cleared_pose_trial_20261116_v1 | 346 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/13.md>) |
| 旧机实验归档 / comparison_v1 | 6 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/14.md>) |
| 旧机实验归档 / comparison_v2 | 6 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/15.md>) |
| 旧机实验归档 / dual_geometry_export_v1 | 8 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/16.md>) |
| 旧机实验归档 / dual_geometry_trial_20261116_v1 | 178 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/17.md>) |
| 旧机实验归档 / fixed_comparison | 6 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/18.md>) |
| 旧机实验归档 / fixed_user_template_registration_20261117_v1 | 10 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/19.md>) |
| 旧机实验归档 / fixed_user_template_registration_20261117_v2 | 10 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/20.md>) |
| 旧机实验归档 / fixed_user_template_registration_20261117_v3 | 73 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/21.md>) |
| 旧机实验归档 / horizontal_front_review_20261116_v1 | 1 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/22.md>) |
| 旧机实验归档 / manual_aperture_review_20261116_142544 | 6 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/23.md>) |
| 旧机实验归档 / manual_reference_matching_20261117_v1 | 105 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/24.md>) |
| 旧机实验归档 / manual_reference_matching_right_20261117_v2 | 106 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/25.md>) |
| 旧机实验归档 / mesh_noise_audit_20261116_v1 | 11 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/26.md>) |
| 旧机实验归档 / mesh_pose_trial_v1 | 514 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/27.md>) |
| 旧机实验归档 / multiview_joint_20261117_v1 | 25 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/28.md>) |
| 旧机实验归档 / multiview_joint_20261117_v2 | 25 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/29.md>) |
| 旧机实验归档 / multiview_joint_20261117_v3 | 28 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/30.md>) |
| 旧机实验归档 / new_cloud_box_20261117_v1 | 49 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/31.md>) |
| 旧机实验归档 / new_cloud_user_box_20261117_v2 | 49 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/32.md>) |
| 旧机实验归档 / observation_filter_trial_20261116_v1 | 8 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/33.md>) |
| 旧机实验归档 / observation_filter_trial_20261116_v2 | 234 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/34.md>) |
| 旧机实验归档 / observed_fuzz_audit_20261116_v1 | 1 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/35.md>) |
| 旧机实验归档 / optical_close_fs_registration_v1 | 1 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/36.md>) |
| 旧机实验归档 / optical_module_v1_dimensions_20261119 | 1 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/37.md>) |
| 旧机实验归档 / optical_prior_fit_20261119_v1 | 4 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/38.md>) |
| 旧机实验归档 / optical_prior_fit_20261119_v2 | 126 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/39.md>) |
| 旧机实验归档 / optical_prior_fit_20261119_v3_recess | 5 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/40.md>) |
| 旧机实验归档 / optical_prior_fit_20261119_v4_symmetric | 5 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/41.md>) |
| 旧机实验归档 / optical_prior_fit_20261119_v5_inner_groove | 7 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/42.md>) |
| 旧机实验归档 / optical_prior_fit_20261119_v6_left_groove | 7 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/43.md>) |
| 旧机实验归档 / optical_prior_fit_20261119_v7_no_side_tabs | 7 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/44.md>) |
| 旧机实验归档 / optical_prior_fit_20261119_v8_photo_candidate | 8 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/45.md>) |
| 旧机实验归档 / optical_shape_prior_20261119_v1 | 1 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/46.md>) |
| 旧机实验归档 / optical_shape_prior_20261119_v2 | 1 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/47.md>) |
| 旧机实验归档 / optical_shape_prior_20261119_v3 | 1 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/48.md>) |
| 旧机实验归档 / optical_shape_prior_20261119_v4_recess | 1 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/49.md>) |
| 旧机实验归档 / optical_shape_prior_20261119_v5_symmetric | 1 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/50.md>) |
| 旧机实验归档 / optical_shape_prior_20261119_v6_inner_groove | 1 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/51.md>) |
| 旧机实验归档 / optical_shape_prior_20261119_v7_left_groove | 1 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/52.md>) |
| 旧机实验归档 / optical_shape_prior_20261119_v8_no_side_tabs | 1 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/53.md>) |
| 旧机实验归档 / optical_shape_prior_20261119_v9_photo_candidate | 1 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/54.md>) |
| 旧机实验归档 / optical_top_audit_20261118_v1 | 7 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/55.md>) |
| 旧机实验归档 / optical_v1_photo_projection_20261119 | 2 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/56.md>) |
| 旧机实验归档 / optical_v1_photo_review_20261119 | 3 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/57.md>) |
| 旧机实验归档 / optical_v2_dimension_refinement_20261119 | 3 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/58.md>) |
| 旧机实验归档 / pose_offset_diagnosis_20261116_v1 | 5 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/59.md>) |
| 旧机实验归档 / rgb_depth_correspondence_20261117_v1 | 3 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/60.md>) |
| 旧机实验归档 / shared_aperture_geometry_20261117_v1 | 1 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/61.md>) |
| 旧机实验归档 / three_view_annotation_audit_20261117_v1 | 1 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/62.md>) |
| 旧机实验归档 / tsdf_review | 6 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/63.md>) |
| 旧机实验归档 / visible_housing_audit_20261117_v1 | 40 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/64.md>) |
| 本机运行结果 / blender_validation_20261120 | 1 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/65.md>) |
| 本机运行结果 / bundlesdf_components_20261119 | 1 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/66.md>) |
| 本机运行结果 / mujoco_optical_array_20261120 | 2 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/67.md>) |
| 本机运行结果 / mujoco_optical_array_v2_20261120 | 2 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/68.md>) |
| 本机运行结果 / mujoco_optical_v2_20261120 | 2 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/69.md>) |
| 本机运行结果 / mujoco_optical_v3_20261120 | 2 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/70.md>) |
| 本机运行结果 / omi_robot_asset_review_20261120 | 2 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/71.md>) |
| 本机运行结果 / omi_shapeforge / 20261119T151446_852822Z_stereo | 1 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/72.md>) |
| 本机运行结果 / omi_shapeforge / 20261119T151448_014730Z_bundlesdf | 1 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/73.md>) |
| 本机运行结果 / omi_shapeforge / 20261120T014811_666235Z_stereo | 1 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/74.md>) |
| 本机运行结果 / omi_shapeforge / 20261120T014828_903620Z_bundlesdf | 1 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/75.md>) |
| 本机运行结果 / optical_portable_20261120_001316 | 1 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/76.md>) |
| 本机运行结果 / stereo_official_20261119 | 3 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/77.md>) |
| 本机运行结果 / stereo_repeat_20261119 | 1 | [打开图册](</data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/albums/78.md>) |
