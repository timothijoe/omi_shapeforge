# 当前总览

核对日期：2026-11-20。ENG-001 已保存源码基线，并新跑控制层测试、官方双目和 BundleSDF 组件 smoke；其他能力沿用已有证据，未复跑物理场景或训练。

完整交接见[当前全部进展快照](chronicles/2026-11-20-workspace-handoff.md)，具体能力以领域纪传体为准。

## 已完成范围

| 领域 | 当前已验证状态 | 详细入口 |
| --- | --- | --- |
| 项目基础 | 本地 Git 与公开远端建立；main 空分支；主 CLI、两种 smoke 及控制层测试有记录 | [架构](design/project-architecture.md) · [CLI](agent/interfaces/cli.md) |
| 感知 | 官方双目与原生组件检查、已圈选目标 CPU 配准、V2 冻结几何回放通过 | [领域摘要](agent/perception/current.md) · [双目](agent/perception/evolution/stereo-and-backends.md) · [配准](agent/perception/evolution/confirmed-registration.md) |
| 数据与恢复 | 00–05 及 OMI／portable／quick 共 9 包均已校验解压，两个 data／DATA 目录完整恢复 | [数据与回放](agent/perception/evolution/data-and-replay.md) · [解压索引](../manifests/extracted_archives.json) |
| 仿真 | Blender 模型与导出、单模块／2×2 的 MuJoCo 渲染及 PhysX CPU 测试通过 | [领域摘要](agent/simulation/current.md) · [资产](agent/simulation/evolution/asset-pipeline.md) · [场景](agent/simulation/evolution/engine-scenes.md) |
| 机器人资源 | 模型、网格与夹爪 URDF 已到达；MuJoCo 3.15 静态编译、预检和渲染通过 | [机器人资产](agent/simulation/evolution/robot-assets.md) |

## 当前状态边界

数据恢复完成与算法全链路复现是不同状态。光模块真实录制尚未在本机重新执行完整双目／59 帧尺寸／在线重建流程；组件检查、条件配准或冻结几何回放不能替代这些验收。

机械臂与夹爪资源已齐，但尚未组合到光模块场景；当前碰撞是包围盒，质量／摩擦为假设。Isaac RTX、GUI 交互、实物位姿精度、夹持／插接及真机动作均未验收。

04 的 Python 3.11.18／Torch 2.7.1+cu128 原环境已恢复，但未执行 conda-unpack 或兼容性验收；当前 envs 中已验证的开发环境保持不变。OMI 包的完整逐样本／Actor 校验、BC／RL 重新训练也未执行。

主命令只有 doctor 和两种 smoke；doctor 的 ready 只代表路径检查。便携配准和仿真仍走独立脚本，详见[能力表](capabilities.md)和[教程](../tutorials/README.md)。

## 当前工作与下一步

ENG-001 已完成：仿真、知识库和基线记录纳入本地 `dev`；两个后端适配分别提交在 `feature/local-runtime-baseline`，四仓库源码 bundle 均成功恢复。原工作区与恢复副本各 4 项控制层测试通过，两项 GPU smoke 通过；见[基线说明](design/source-baseline.md)和[新阶段记录](chronicles/2026-11-20-source-baseline.md)。未推送，远端默认分支仍不含这些本地提交。

1. 下一项 ENG-002：定版任务记录、产物合同及旧报告适配；随后实现共用运行层，再接入真实样本。
2. 选择机器人／工具配置，核对轴、TCP、限位、惯量、夹具与精细碰撞，然后接入当前场景。
3. 分别推进完整重建、Blender 生成、Isaac RTX／GUI 和 OMI Actor／数据合同检查，保留每项独立证据。
4. 历史环境是否需要启用单独决定，不作为继续使用当前环境的前置条件。

进展形成过程见[全局快照](chronicles/README.md)、[感知编年](agent/perception/chronicles/README.md)和[仿真编年](agent/simulation/chronicles/README.md)。
