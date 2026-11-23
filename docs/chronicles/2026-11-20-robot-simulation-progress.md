# 2026-11-20：插接资产与机械臂仿真阶段交接

用户要求先记录当前进展，稍后切换其他工作。本次停点是：**真实机械臂 URDF 仿真场景、6D 末端到达接口和交互查看已跑通；抓取、接触插入及 RL 学习尚未完成。**

这份记录承接当天早期[重启交接](2026-11-20-restart-handoff.md)，不回写其历史结论。恢复本轮工作优先读本文、[当前总览](../current.md)及[开发计划](../design/robot-rl-development-plan.md)。

## 1. 已确认的用户决定

- 光模块以 **Blender V3** 为主；V2 留作参考，不能用旧 V2 的插入结果代替 V3。
- 带孔装配体命名为“**光模块插接座**”，简称插接座，本地编号 OS-001；下部白色件称插接座支架。
- 用户看过背面实拍后确认保留后部两处凸出结构，r02 平背面方案不采用。
- 当前插接座工作候选为 **r04**：比 r03 略放宽，金属基本通道内宽 **19.00 mm**、白色孔口宽 **20.60 mm**。
- 19.00 mm 是用户要求下选择的候选值，**不是图像或点云独立测得值**。不能先把 V3 视为尺寸真值，再把全部误差归给插接座。
- 用户确认较深插入照片可按机械插到位理解：窄平段进入，较大头部台阶在孔口止挡，绿色拉手留在外面；电气就位未确认。
- 模型查看优先用 Open3D；整体机械臂场景已使用 MuJoCo 原生窗口。完整下部支架需要显示。
- 开发优先搭整体架构、尽快做简单版本，但第一版也必须使用已有机械臂 URDF；代理夹持体只用于回归测试。

## 2. 插接几何已完成的工作

原 TSDF、人工清孔 SDF、原始 RealSense 彩色帧与模型已分别核对。已从原 MCAP 提取与 28 帧 IR 精确同时间戳的设备原生深度，并与已有 FoundationStereo 深度缓存分别检查 21 项尺寸。它们的估计有差异，孔内沿／底面仍缺少稳定支持。

V3 主体名义宽 17.542 mm 来自旧 59 视角截面拟合；含侧弹片外包宽约 18.174 mm。已复算旧逐帧统计并比较“扩大模块”的假设，但没有重新执行完整 59 帧重建或获得独立计量认证。

当前模型平段高约 **7.838 mm**，基本通道高约 **9.600 mm**；r04 居中横向单侧名义间隙约 **0.413 mm**。这些数值没有扣除全部细接触件，也不证明实物厚度／高度准确。

实际 V3 的逐件表面相交、双向采样包含、截面与采样距离已检查。模型尖端到头部台阶约 **51.282 mm**；全刚体会在约 **4.21 mm** 与孔口弹片相交。仅在诊断统计中排除细接触件后，才到约 51.28 mm 的台阶止挡。没有删掉弹片来冒称物理插入通过，也没有模拟弹性或插入力。

模型均另存新修订，原 V3、r01～r03 和历史报告保留。当前 r04：

- [Blender 文件](/data/omi_runtime/assets/optical_socket/revisions/r04/OS-001-r04.blend)
- [几何示意](/data/omi_runtime/runs/v3_socket_r04_20261120T082303Z/insertion_geometry.png)
- [相对位姿与检查记录](/data/omi_runtime/runs/v3_socket_r04_20261120T082303Z/insertion_contract.json)
- [版本／验证清单](../../manifests/socket_r04_20261120.json)
- [完整能力说明](../agent/simulation/evolution/v3-insertion.md)

## 3. 当前机械臂仿真与架构

采用 **MuJoCo 3.15.0＋Python＋Gymnasium 1.4.0**，运行环境为 `/data/omi_runtime/envs/omi_assets`。ShapeForge 的 `.venv` 仍是轻量控制环境，模拟依赖通过可选依赖组声明。

从厂商 `marvin_stand.urdf` 导入完整双臂／夹爪：27 个 link、18 个活动关节（14 旋转＋4 滑动）、18 个位置执行器、2 个 mimic 等式。只在派生副本中去掉两个零体积 TCP 标记的 visual/collision，坐标架与原 URDF 保留。

场景包含机器人、圆桌、插接座 r04 和 V3 共 150 个参考可视分件，布局参照用户全景照片，尚未做照片到世界坐标的米制标定。

| 组件 | 代码入口 | 当前状态 |
| --- | --- | --- |
| URDF 导入与场景装配 | `src/omi_shapeforge/sim/robot_scene.py` | 可生成独立 MJCF、来源清单与参考资产 |
| 真实机器人 Gym 环境 | `sim/robot_env.py` | `RobotReachEnv`：6D TCP 增量 → DLS IK → 7 关节伺服 |
| 明确任务选择 | `sim/factory.py` | `robot_reach`、`insertion_proxy`；`robot_insertion` 明确未实现 |
| 交互显示 | `sim/robot_viewer.py` | MuJoCo 原生 3D；只查看，不步进物理或运行策略 |
| 回归夹具 | `sim/insertion_env.py`、`config.py`、`scene.py` | 简化几何用于接口与回合语义测试 |
| 回归输出 | `sim/smoke.py` | 场景、合同、transition JSONL、图像与报告 |

真实 URDF 到达检查在两种重置种子下均为 31 步，TCP 误差由约 17.4 mm 降至 2.65 mm／2.64 mm。Gymnasium checker、非法动作拒绝及非主动臂保持检查通过。控制层 14 项测试通过；4 项可选仿真行为测试在仿真环境通过，在控制 `.venv` 中明确跳过。

**当前边界：**机器人接触关闭、重力补偿开启、伺服参数为假设；URDF TCP 尚非已校准工具中心。光模块和插接座仍是静态参考，模块没有绑定到夹爪。没有接通现有 Actor/Learner/Replay，没有运行 RL 训练，没有连接或控制硬件。代理夹具的插入成功不能算作机械臂插入成功。

## 4. 关键产物与恢复入口

| 内容 | 路径 |
| --- | --- |
| 机器人场景 | `/data/omi_runtime/runs/robot_urdf_mvp_20261120T090059Z/scene/scene.xml` |
| URDF 来源与映射 | 同目录 `robot_manifest.json` |
| 到达与接口验证 | `/data/omi_runtime/runs/robot_urdf_mvp_20261120T090059Z/reach_smoke.json`、`interface_validation.json` |
| 场景预览 | [robot_final.png](/data/omi_runtime/runs/robot_urdf_mvp_20261120T090059Z/robot_final.png) |
| 汇总清单 | [robot_rl_mvp_20261120.json](../../manifests/robot_rl_mvp_20261120.json) |
| 简化夹具结果 | `/data/omi_runtime/runs/sim_mvp_20261120T085558Z/report.json` |
| 原始插入照片副本 | `/data/omi_runtime/runs/v3_socket_insertion_20261120T073119Z/photos/` |
| 原 mesh／原生深度审计 | `/data/omi_runtime/runs/socket_flat_rear_20261120T064745Z/` |
| 宽度来源复核 | `/data/omi_runtime/runs/width_evidence_20261120T081118Z/` |

重新打开整体机器人场景：

```bash
cd /home/linux/omi_folder/omi_shapeforge
MUJOCO_GL=glfw PYTHONPATH=src /data/omi_runtime/envs/omi_assets/bin/python \
  -m omi_shapeforge.sim.robot_viewer \
  --scene-dir /data/omi_runtime/runs/robot_urdf_mvp_20261120T090059Z/scene
```

重新打开 V3／插接座 r04 的局部插入检查：

```bash
/data/omi_runtime/envs/foundation_stereo/bin/python \
  scripts/simulation/view_v3_insertion.py \
  --run /data/omi_runtime/runs/v3_socket_r04_20261120T082303Z
```

查看器进程不承载唯一模型状态；关闭后按命令重开，不依赖旧 PID。当前展示窗口没有运行策略或训练。详细操作见[机器人教程](../../tutorials/robot_sim_mvp.md)与[局部插入教程](../../tutorials/v3_socket_insertion.md)。

## 5. Git 与资源状态

当前分支：`feature/socket-rear-observation-review`，从本地 `dev` 基线继续，基础 HEAD 为 `66ff11720e5dc4327041d709b661dec73c83f605`。本轮新增代码、文档和清单已写入工作区，**尚未提交或推送**；实际状态以 `git status --short --branch` 为准。`omi_proj` 只读使用，没有改其代码。

当天早期重启备份／Git bundle **不包含本轮未提交改动**。二进制资产、照片副本、环境和运行输出在 `/data/omi_runtime`，也不会自动随 Git 保存。后续不要用早期 bundle、reset 或 clean 覆盖当前工作。

## 6. 接续顺序

1. 按[开发计划](../design/robot-rl-development-plan.md)继续 M1：核对主动臂、真实工具／夹爪与 TCP，建立 `tool_to_module`、`socket_to_world`。
2. 将静态模块参考变成与夹爪绑定的仿真对象，先验证到孔口前的姿态和可达性。
3. 分阶段开启自碰撞、台面与插接接触；解决凹孔碰撞体和弹片代理，不以穿模或删除接触件获取成功。
4. 再接现有 RL 框架。当前状态观测与旧十帧图像／触觉历史合同不同，6D TCP 动作也不能冒充旧 7D 关节动作；需要显式适配与新的 replay 合同。
5. 小规模学习器冒烟之后，再谈长训练、多种子评估、随机化与迁移。

本次按用户要求记录停点，不继续扩展任务或启动训练；后续由用户的新任务决定工作方向。
