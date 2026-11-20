# 当前总览

核对日期：2026-11-20。ENG-001～003 已完成：源码基线、统一合同和共用运行层；本轮新跑两项 GPU smoke 与 MuJoCo 2×2 场景，并完成资产名称及可视化整理。没有运行训练或硬件控制。

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

主 CLI 现有 doctor、两种 smoke 和 simulate mujoco；doctor 的 ready 只代表路径检查。便携配准、Blender 和 Isaac 仍走独立脚本，详见[能力表](capabilities.md)和[教程](../tutorials/README.md)。

## 当前工作与下一步

用户已确定 **V3（Blender）为主模型，V2 为辅助参考与对比**。V3-r01 对应现有连通槽几何，已建立冻结副本与独立工作副本；未改变几何和精度结论。具体见[资产版本](asset-versions.md)与[ADR 002](agent/simulation/decisions/002-blender-v3-primary.md)。

ENG-001 已完成：仿真、知识库和基线记录纳入本地 `dev`；两个后端适配分别提交在 `feature/local-runtime-baseline`，四仓库源码 bundle 均成功恢复。原工作区与恢复副本各 4 项控制层测试通过，两项 GPU smoke 通过；见[基线说明](design/source-baseline.md)和[新阶段记录](chronicles/2026-11-20-source-baseline.md)。未推送，远端默认分支仍不含这些本地提交。

ENG-002 已完成[运行与产物合同 v1](agent/interfaces/run-contract.md)：三项流程规则、11 个合成示例、27 个反例及严格 JSON 检查通过，现有 4 项控制层测试通过。该阶段只读核对旧报告；后续 ENG-003 已接入运行层，旧报告转换器仍待实现。原阶段见[记录](chronicles/2026-11-20-run-contract.md)。

ENG-003 已完成，14 项控制层测试通过，两个 smoke 与 MuJoCo 2×2 的执行／产物／验收均通过，见[验证清单](../manifests/workflow_validation_20261120.json)。资产另已建立[版本名称](asset-versions.md)及[完整图册入口](visual-results.md)，模型原文件哈希保持不变。

1. 下一项 ENG-004：将 CPU 回归与合同检查纳入自动流程，并规范 GPU／仿真证据关联。
2. 选择机器人／工具配置，核对轴、TCP、限位、惯量、夹具与精细碰撞，然后接入当前场景。
3. 分别推进完整重建、Blender 生成、Isaac RTX／GUI 和 OMI Actor／数据合同检查，保留每项独立证据。
4. 历史环境是否需要启用单独决定，不作为继续使用当前环境的前置条件。

运行层最新干净版本与中断回收补强后的复验见[最终验证](../manifests/workflow_final_validation_20261120.json)。

资产查看器另修复了桌面 Chrome 无 WebGL 时的空白问题，已加入 CPU 网格渲染并核对真实桌面画面；详见[兼容性验证](../manifests/viewer_compatibility_validation_20261120.json)，资产几何与能力精度结论不变。

进展形成过程见[全局快照](chronicles/README.md)、[感知编年](agent/perception/chronicles/README.md)和[仿真编年](agent/simulation/chronicles/README.md)。

原电脑的 Open3D 原生查看器也已在本机打开，实际显示历史 V2 mesh；启动方式与 V1／点云切换范围见[原生查看教程](../tutorials/native_mesh_viewer.md)。这不是当前 V3（旧别名 GROOVE-r01） 的几何更新。
