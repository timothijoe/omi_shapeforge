# 机械臂、夹爪与夹具资源状态

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

默认 MJCF 是旧双臂场景，含灵巧手、刀具与工作台；它不自动等于现场触觉夹爪配置。完整厂商 URDF 虽含滑动指结构，尚未完成其惯量、工具/TCP、限位与现场安装的标定，也未导入当前 optical 场景或 Isaac 机器人任务。

Stand 修正版保留原来的可视化用途和未解决项，不能作为真机控制模型。当前光模块仿真仍使用示意轨道；01 包虽已提供更多带孔对象几何，尚未自动替换原型中的碰撞结构。

## 后续接入

先选择所需机器人／工具配置并核对坐标、网格、关节、惯量和碰撞，再离线导入光模块场景。Git 自带 surrogate 仍只供接口测试。来源和恢复记录见[机器人清单](../../../../manifests/robot_assets.json)，新到达阶段见[编年](../chronicles/2026-11-20-robot-resources-arrived.md)。本轮没有连接硬件或运行控制脚本。
