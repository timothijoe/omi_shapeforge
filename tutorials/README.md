# 操作教程

- [感知细网格数据 v1：查看、主集使用、标注导出与恢复](grid_perception_data_v1.md)：8895窗口，主集与辅助数据分开，当前为孔口前静态仿真样本。
- [接触版腕部表面训练的查看与恢复](contact_wrist_surface_learning.md)：既有8893训练结果，与细网格数据采集分开。

- [仿真腕部点云训练结果与单张推理](sim_wrist_surface_learning.md)：8892窗口、实际模型检查点、视频和复现入口。

- [尖端与插孔局部精细点云](interaction_surface_representation.md)：8891窗口，薄唇／孔口／内壁分色，密集表面、真实棱边与训练预算对照。

- [WG-r10＋OM-r08的Isaac查看与重建](wrist_bundle_isaac.md)

- [查看完整表面点云与图像输入网络原型](image_to_complete_surface.md)：独立8890窗口；点数对比、真实前向输出格式，网络未训练。

- [其他Agent复用当前腕部／模块视觉资产](reuse_wrist_visual_assets.md)：只读校验、新目录重渲染、静态初态与接入边界。

- [Isaac Sim同源插接实验](isaac_contact_insertion.md)：独立USD、PhysX、双相机和回归命令。

- [头部点云与腕部图像：逐数据XYZ／RPY调节、结构点精修和保存](head_wrist_pose_review.md)。

- [精修腕部相机与夹爪：独立模型及MuJoCo预览](refined_wrist_tool.md)。

- [查看带相机与夹爪外观候选的仿真](wrist_camera_gripper.md)：原生窗口播放规则插入，切换全景／腕部／头部／末端，查看新资产。

- [V4与实测尺寸插槽：接触仿真、视频和新训练入口](measured_v4_simulation.md)：当前SIM-r06候选，18.8 × 8.8 mm孔口、机械臂规则3/3，旧策略直接迁移未通过。

- [资产迁移包与恢复步骤](asset_migration_20261121.md)：三份外部资源压缩包、逐文件校验、原始数据出处和跨机器恢复。

- [旧SIM-r03接触资产：模型、视频、验证、训练和续训](contact_simulation.md)：保留原实验和旧策略训练入口，新尺寸仿真见上方。

- [实际mesh插入检查与碰撞导出修复](mesh_insertability.md)：保留孔形、定位入口弹片阻挡，当前完整接触未通过。

- [观看仿真、生成规则示范并辅助训练](rule_demonstrations.md)：三视图视频、分阶段老师、BC 初始化和混合 SAC。

- [双相机 MuJoCo → OMI 视觉训练与续训](dual_camera_training.md)：真实渲染输入、padding、经验池和梯度更新全链路。

- [机械臂 URDF 仿真原型](robot_sim_mvp.md)：真实双臂／夹爪模型的 IK 与小幅到达接口；接触插入尚未开放。
所有命令从仓库根目录执行；输出使用新目录。首次操作先看前提和预期，不把缺资源的入口当作已验收流程。

1. [环境安装与配置](environment_setup.md)
2. [最短可运行案例](quickstart.md)
3. [双目与 BundleSDF 组件样例](stereo_sample.md)
4. [光模块 CPU 配准](portable_registration.md)
5. [Blender 打开、检查与导出](blender_assets.md)
6. [单模块和方阵场景生成](scene_generation.md)
7. [MuJoCo 离屏仿真](mujoco_scene.md)
8. [Isaac PhysX 后台仿真](isaac_scene.md)
9. [故障排查、停止和恢复](troubleshooting.md)

当前没有本项目录制或真机执行能力，因此没有对应操作教程。能力边界见[能力表](../docs/capabilities.md)，资源状态见[清单](../manifests/README.md)。

- [Open3D 原生桌面 mesh 查看器](native_mesh_viewer.md)：插接座扫描／模型对照及历史 V2／V1 查看。
- [V3 与插接座的插入关系](v3_socket_insertion.md)：实际 V3、孔宽候选、可调深度及台阶限位检查。

- [重启后恢复工作](restart_resume.md)：Blender V3 会话、原生 V2 查看、现有环境与代码接续。

- [光模块候选特征与鱼眼跟踪](mesh_feature_tracking.md)：原图特征、模型候选映射、遮挡/重现检查与实验模式边界。
