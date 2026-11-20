# 同源 MuJoCo 与 Isaac 场景

## 生成结构

`build_scenes.py` 读取 `asset.json` 和部件 OBJ，复制网格到新目录，生成 `scene.xml`、`scene.usda` 和 `scene_manifest.json`。两个格式共享模块初始位置、桌面、示意轨道、重力及物理假设。

默认 1×1；`--rows`／`--columns` 均须为正整数，总数 1–16。摆放为规则网格，X 间距 0.12 m、Y 间距 0.14 m、初始 Z 为 0.055 m；桌面 Z=0。该布局是合成原型，没有使用点云配准矩阵恢复真实现场。

外观采用部件三角网格；动力学使用单个碰撞盒，质量 0.02 kg、摩擦 0.6、重力 9.81 m/s²、步长 1/120 s。盒内均匀质量是假设；不保留槽接触或拉手柔性。设计原因见 [ADR 001](../decisions/001-visual-and-collision.md)。

## MuJoCo

使用独立 Python 3.11 环境和 MuJoCo 3.3.7，默认 240 步。脚本编译 MJCF，导出初始／末态 EGL 图像、状态样本、NPZ 和报告；检查状态有限、实际下落、最终接触、速度和台面穿透。

单模块与 2×2 方阵均通过本机运行。最新方阵报告绑定脚本与 XML 哈希，见[仿真验证索引](../../../../manifests/simulation_validation.json)。测试阈值只服务原型运行检查，不是精细接触精度标准。

## Isaac Sim

当前验证使用已安装的 Isaac Sim 5.1.0 自带 Python，显式加载本地 PhysX／USD 扩展并关闭扩展注册表下载。CPU PhysX 阶段直接 attach USD stage、simulate／fetch results，并把变换回写到 USD；不依赖 RTX 渲染器或机器人框架。

单模块和 2×2 均实际执行 240 步，检查下落、稳定及台面支撑，输出 `states.json`、`settled.usda` 和 `report.json`。安装目录另有 6.0.1，但本轮没有用它验收这些场景。

通用 no-render 启动的首次探针曾因扩展下载超时；当前本地扩展启动是已验证入口。不能将 `omni.kit.loop-default`、普通 main-loop 或无 stage attach 的尝试写为通过方案，操作命令以[Isaac 教程](../../../../tutorials/isaac_scene.md)为准。

## 未验证边界

未运行 Isaac RTX 相机或 GUI 交互。两引擎结果只证明局部同源资产可加载且简化接触能运行，不证明动力学一致、质量／摩擦正确、现场复现、夹持或插接成功。当前光模块场景尚未接入机械臂／夹爪，也没有实机接口；新到达资源的离线预检见[机器人资产](robot-assets.md)。

数据格式见[接口](../../interfaces/data-formats.md)，操作见[MuJoCo 教程](../../../../tutorials/mujoco_scene.md)。
