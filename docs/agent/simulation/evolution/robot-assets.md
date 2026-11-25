# 机械臂、夹爪与夹具资源状态

> 本机迁移提示（2026-11-24）：运行资源实体已迁至 `/data/shapeforge/runtime`；本文中的 `/data/omi_runtime` 是保留的兼容入口，指向同一份内容。目录映射与恢复要求见[当前资源契约](../../interfaces/local-resources.md)。

新增[Isaac Sim同源机器人插接实验](isaac-contact.md)，独立记录PhysX导入、IK/驱动、接触和RTX双相机，不替代本文历史MuJoCo阶段。

## 当前新增：视频参考相机／夹爪外观候选

已建立[WG-DAIMON-VIS-r04](wrist-camera-gripper.md)，共31个独立闭合外观部件，按视频拟合相机、安装座、弯指、橙色内衬和白色指尖组件，具体硬件SKU／CAD尚未确认。工具绑定到原URDF框架，实际腕部相机位置与镜头一致；最终安装在名义路径上无工具／插座相交，两个初态模块插入退出通过。

当前仍继承URDF惯量和关节，用固定变换附着光模块，未将新夹爪几何启用为接触抓取模型，也未仿真触觉或真实鱼眼。光模块／插槽接触来自[SIM-r06](measured-v4-simulation.md)。相机与夹爪外观候选、真实机器人动力学和现场已标定硬件三者不能等同。

## 以下为原URDF导入及迁移阶段记录

2026-11-21：在下述真实 URDF 原型上派生了[双相机预插入训练场景](visual-training.md)，V3 固定附着到 TCP、两路 RGB 进入 OMI 视觉 SAC，训练与续训通过。原静态参考场景保留；固定附着不代表已校准抓取，接触仍关闭。

## 新增：真实 URDF 原型场景

用户明确第一版也使用机械臂后，已把完整厂商 `marvin_stand.urdf` 导入 MuJoCo，保留 27 links 对应坐标架、18 个活动关节和 2 个 mimic 等式；零体积 TCP 显示标记只在派生副本中移除，TCP 框架仍在。场景加入圆桌和 150 个 r04／V3 参考外观分件。实际 URDF 的 L 臂通过 6D TCP→DLS IK→位置伺服完成小幅到达检查。

这是接触关闭、重力补偿开启的软件阶段：模块尚未夹持，工具 TCP、实际主动臂身份和动力学未校准。不能把到达成功当成插入成功。旧 MJCF 和派生可视化 URDF 均保留。架构与后续验收见[开发计划](../../../design/robot-rl-development-plan.md)，产物在 `/data/omi_runtime/runs/robot_urdf_mvp_20261120T090059Z/`。

## 当前可用资源

2026-11-20 后续到达的 `omi_transfer_20261120_004618.tar.gz` 补齐了此前缺少的 Git 外资源。解压后 7,361 项包内 SHA256 与 7,321 项源文件记录校验通过，见[迁移验证](../../../../manifests/transfer_validation.json)。原先缺少资源的阶段记录保留，当前现状以本页为准。

数据位于外部基线，`omi_proj/local` 是指向该基线 local 目录的符号链接。当前 omi_proj 的源码和 .git 保留；包内另含离线代码快照，未覆盖现有仓库。

| 资源 | 相对 omi_proj 的位置 | 当前验证 |
| --- | --- | --- |
| Marvin 双臂 MJCF | `local/assets/robot_assets/mujoco/right_chopping_scene.xml` | MuJoCo 3.15 编译、forward、项目 preflight、EGL 静态图像通过 |
| Arm／base 网格 | `local/assets/MarvinCCS/` | 完整校验，与 robot_assets 保持相邻 |
| Stand 派生 URDF | `local/models/omi_marvin_stand_axis_corrected_v1/` | 原件、15 份网格和来源已恢复；仍仅作派生可视化模型 |
| 完整厂商资源 | `local/vendor/optical_module_pu/` | 两份完整 URDF 和相应 meshes／meshes_pro 已找到，引用齐全 |

两份完整 URDF 各含 27 links、26 joints，其中左右臂共 14 个旋转关节，另有四个滑动指关节 `Arm_L10/11_Joint`、`Arm_R10/11_Joint`；各 54 处 mesh 引用均能解析。声明的指关节限位上限为 0.04、velocity 为 0，仍须核对实际控制含义，不能按声明直接开展接触任务。

## 运行时与限制

现有机械臂 MJCF 使用 compiler conflict 等较新语法，原光模块环境的 MuJoCo 3.3.7 会拒绝。为保留原资产，新建独立 Python 3.12／MuJoCo 3.15 环境做检查，没有删改 XML 属性，也没有替换旧光模块环境。

默认 MJCF 是旧双臂场景，含灵巧手、刀具与工作台；它不自动等于现场触觉夹爪配置。完整厂商 URDF 的惯量、工具/TCP、限位与现场安装仍未标定；本机已完成上述 MuJoCo 无接触原型导入，尚未完成 optical 接触任务或 Isaac 机器人任务。

Stand 修正版保留原来的可视化用途和未解决项，不能作为真机控制模型。当前光模块仿真仍使用示意轨道；01 包虽已提供更多带孔对象几何，尚未自动替换原型中的碰撞结构。

## 后续接入

先选择所需机器人／工具配置并核对坐标、网格、关节、惯量和碰撞，再离线导入光模块场景。Git 自带 surrogate 仍只供接口测试。来源和恢复记录见[机器人清单](../../../../manifests/robot_assets.json)，新到达阶段见[编年](../chronicles/2026-11-20-robot-resources-arrived.md)。本轮没有连接硬件或运行控制脚本。
