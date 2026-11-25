# 资源与证据清单

- [System1 与 System0 原型验证](hierarchical_insertion_20261125.json)：代码、原生过程、三种参考对照及默认兼容检查。

- [2026-11-25工作区源码快照](workspace_snapshot_20261125.json)：两个仓库的保存分支、训练源码版本、检查结果及BC6148历史数据缺口；本次System1／System0仅记录讨论。

- [runtime实体归拢登记](runtime_relocation_20261123.json)：新实体根、旧兼容前缀、文件身份与环境检查；此前导入／交付迁移登记保留原时点。

- [2026-11-23存储布局与迁移登记](storage_layout_20261123.json)：四批实体的新旧路径、脚本兼容链接及验证范围；当前目录规则见[本地资源契约](../docs/agent/interfaces/local-resources.md)。`resources.json`使用新的实际导入根；日期化的旧迁移、采集与解压验证清单保留原文。

- [PCG-01纯几何便携包登记](pointcloud_geometry_pcg01_20261123.json)：交付目录、ZIP哈希／字节数、源几何目录和验证；能力与使用方法见[纪传体](../docs/agent/perception/evolution/pointcloud-geometry-pcg01.md)。

- [Isaac规则反馈RL登记](isaac_rule_feedback_20261122.json)：完整链路验证与自主策略结果分开。

- [WVA-01当前已接受腕部视觉版本](wrist_visual_wva01_20261122.json)：WG-r15／OM-r08、场景依赖哈希及对比快照；旧WG-r10清单保留历史身份。

- [WG-r10＋OM-r08的Isaac接入登记](wrist_bundle_isaac_20261122.json)：固定来源、静态路径、开合和观察范围。

- [历史WG-r10腕部视觉资产交接清单](wrist_visual_asset_handoff_20261122.json)：固定WG-r10／OM-r08身份、路径、哈希、静态场景依赖、坐标合同及复现验证。

- [Isaac接触/图像复核登记](isaac_contact_visual_review_20261122.json)：任务结果与进程收尾状态分开。

- [Isaac同源插接验收登记](isaac_contact_20261122.json)：固定10项验收矩阵、来源保护、视频和限制。

本目录只保存小型元数据、环境包清单和验证索引。数据、模型、权重、SDK、软件、venv、网格和输出本体保留在外部目录。

| 文件 | 职责 |
| --- | --- |
| [module_material_r06_20261122.json](module_material_r06_20261122.json) | 独立V4-r06材质候选、18件几何不变、同视角颜色拟合及旧文件保护；r05仍为暂定基线 |
| [hybrid_black_contact_20261122.json](hybrid_black_contact_20261122.json) | 混合腕部图像的黑色夹持面归属修正、真实像素与图像邻接检查；不代表物理抓取验收 |
| [wrist_camera_gripper_20261121.json](wrist_camera_gripper_20261121.json) | 视频参考相机／夹爪31件外观、镜头绑定、工具名义间隙与两个规则循环；不代表厂家CAD或真实接触抓取 |
| [measured_v4_simulation_20261121.json](measured_v4_simulation_20261121.json) | V4-r05＋18.8×8.8mm新孔口／窄边6.9mm候选；SIM-r06局部／机器人／相机检查与旧策略迁移失败，保留失败候选及源码 |
| [module_v4_r05_designation_20261121.json](module_v4_r05_designation_20261121.json) | 固定命名V4-r05「双窗尾槽版」、用户暂定采用的范围及未改变的模型哈希；不代表训练或实物精度验收 |
| [perception_handoff_20261121.json](perception_handoff_20261121.json) | 真实感知最新交接、源码/文档/主要证据快照、未提交状态和恢复边界 |
| [contact_policy_study_20261121.json](contact_policy_study_20261121.json) | 10回合BC、两组20回合接管RL、无接管测试／新初态复验、失败对照和动作来源审计 |
| [simulation_assets.json](simulation_assets.json) | 新SIM资产族及r01/r02调试版、r03接触资产；与原V3/r04分开 |
| [contact_simulation_asset_20261121.json](contact_simulation_asset_20261121.json) | 新资产局部接触、机器人循环、双相机示范、训练／续训和原mesh不变的验证 |
| [mesh_insertability_20261121.json](mesh_insertability_20261121.json) | 当前完整mesh插入未通过；拓扑修复、凸包封孔、弹片阻挡和主体通路的独立检查 |
| [rule_demonstrations_20261121.json](rule_demonstrations_20261121.json) | 规则老师、三视图视频、824条示范、BC／混合SAC和续训的证据与来源 |
| [restart_handoff_20261120.json](restart_handoff_20261120.json) | 本轮重启前版本、Blender 会话快照、重开验证与持久备份 |
| [resources.json](resources.json) | 根目录、资源路径、用途、来源、必需功能、恢复方法和检查日期 |
| [visual_catalog_20261120.json](visual_catalog_20261120.json) | 资产可视化图册范围与完整文件目录；不改变能力验收状态 |
| [optical_assets.json](optical_assets.json) | 光模块模型名称、源文件哈希、版本关系、部件及场景实例身份 |
| [socket_assets.json](socket_assets.json) | 插接座 OS-001、保留背面结构的基准、未采用平背面及收紧孔宽候选 |
| [v3_socket_insertion_20261120.json](v3_socket_insertion_20261120.json) | 新插入照片、实际 V3 截面／台阶限位、r03 孔宽候选、碰撞及 Open3D 查看证据 |
| [socket_r04_20261120.json](socket_r04_20261120.json) | 当前 r04 通道 19.00 mm 候选、0.41 mm 单侧名义间隙、独立重开与插入复验 |
| [asset_v3_designation_20261120.json](asset_v3_designation_20261120.json) | 用户指定 Blender V3 为主、V2 为辅助；冻结／工作副本及实际桌面验证 |
| [viewer_compatibility_validation_20261120.json](viewer_compatibility_validation_20261120.json) | 实际桌面无 WebGL 导致空白的原因、CPU 后备渲染及验证 |
| [native_viewer_validation_20261120.json](native_viewer_validation_20261120.json) | 恢复的 Open3D 原生查看器启动与实际桌面网格显示 |
| [backends.lock.json](backends.lock.json) | 后端初始化 Git HEAD、工作树和入口快照；不强制检出 |
| [source_baseline_20261120.json](source_baseline_20261120.json) | ENG-001 本地源码版本、原变更清单、bundle 恢复及控制层／GPU smoke 证据 |
| [contract_validation_20261120.json](contract_validation_20261120.json) | ENG-002 Schema／示例／反例检查、原报告只读核对；不是新增运行验收 |
| [workflow_validation_20261120.json](workflow_validation_20261120.json) | ENG-003 共用运行层、14 项测试与两个 smoke／MuJoCo 的实际运行证据 |
| [workflow_final_validation_20261120.json](workflow_final_validation_20261120.json) | 中断回收补强后的最终干净版本复验；保留上一份验证 |
| [initial_validation.json](initial_validation.json) | 主项目初始化与两条 GPU 调度的历史验证 |
| [portable_validation.json](portable_validation.json) | 本机已确认 ROI 配准的复验结果与包哈希 |
| [simulation_validation.json](simulation_validation.json) | Blender 和两引擎测试报告索引 |
| [robot_assets.json](robot_assets.json) | omi_proj 机器人资源需求、当前恢复位置和模型核对 |
| [robot_rl_mvp_20261120.json](robot_rl_mvp_20261120.json) | 真实双臂／夹爪 URDF 导入、无接触 TCP 小闭环、Gym 与代理夹具回归；不是插入或 RL 训练验收 |
| [transfer_validation.json](transfer_validation.json) | 新到达的 01／OMI 包校验、恢复、V2 回放与机械臂离线预检 |
| [data02_validation.json](data02_validation.json) | 02 包解压前的完整性和数据契约验证快照 |
| [restored_data02.json](restored_data02.json) | 02 数据全量恢复校验报告 |
| [extracted_archives.json](extracted_archives.json) | 当前 9 个已上传压缩包的解压位置、状态及最后检查 |
| [data03_04_validation.json](data03_04_validation.json) | 03／04 整包与成员恢复、落盘、符号链接和别名校验；旧环境未激活 |
| [documentation_validation.json](documentation_validation.json) | 本轮文档、入口和链接检查结果 |
| environments/ | 两个 GPU 环境的历史要求与 freeze；当前仿真 lock 位于 requirements/ |

## 资源格式与恢复

`resources.json` 的 `root` 指向 `roots` 中的目录，`path` 为该根下的相对位置。相对根以仓库根目录解释；绝对根是本机配置示例。`availability` 是检查当时的状态，不是永久保证，也不由 CLI 自动更新。

清单不是安装器，路径变量不自动注入代码。主配置迁移仍按[配置接口](../docs/agent/interfaces/configuration.md)填写，外部脚本用显式参数。恢复前核对 source、expected_sha256 和当前资料；expected hash 来自此前验证，是否重新哈希以各阶段记录为准；最新迁移阶段已核对 01 整包及恢复成员和 OMI 全部清单。

GPU 环境快照如下：

- [Stereo requirements](environments/requirements-stereo.txt) 与 [freeze](environments/stereo-freeze.txt)。
- [BundleSDF requirements](environments/requirements-bundlesdf.txt) 与 [freeze](environments/bundlesdf-freeze.txt)。
- [本机版本约束](environments/constraints-host.txt)。

它们与相应源码／原生扩展共同构成恢复依据；freeze 的本地 URL 或 editable 路径不能直接在新机器照装，不能复制旧 venv 冒充恢复完成。当前尚无完整可移植 GPU 一键安装器。依赖安装与已知缺口见[环境教程](../tutorials/environment_setup.md)。

历史验证 JSON 保留当时的绝对位置、哈希与限制。资源后来移动时更新当前目录映射与新记录，不篡改旧报告以掩盖来源。

## 双相机训练新增记录（2026-11-21）

[dual_camera_training_20261121.json](dual_camera_training_20261121.json) 记录两个仓库的 MuJoCo 双相机视觉训练、300 条经验／20 次更新、独立进程续训、测试、产物哈希和外部源码快照。场景固定附着、接触关闭，策略评估未成功；[教程](../tutorials/dual_camera_training.md)。
