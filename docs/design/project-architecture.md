# 项目和运行时架构

## 仓库职责

`omi_shapeforge` 维护任务流程、配置、接口、配准评估和资产／仿真脚本。自有 FoundationStereo、BundleSDF 仓库维护网络、跟踪、重建及原生扩展。`omi_proj` 提供机器人资产、接口资料及已执行的离线仿真预检；本项目不调用其 ROS 或硬件控制系统。

```mermaid
flowchart LR
    CLI[ShapeForge CLI] --> FS[FoundationStereo 独立进程]
    CLI --> BS[BundleSDF 组件独立进程]
    PKG[光模块便携包] --> CPU[包内 CPU 配准脚本]
    BL[Blender] --> OBJ[求值外观 OBJ 与资产清单]
    OBJ --> GEN[独立场景生成脚本]
    GEN --> MJ[MuJoCo MJCF]
    GEN --> USD[USD 与 Isaac PhysX]
```

主 CLI 已通过共用运行层覆盖两种 smoke，并可调用已有 MJCF 的 MuJoCo 检查；配准、Blender、场景生成与 Isaac 仍保留独立入口。当前没有双目结果自动转为完整重建／机器人任务的一键流水线。

## 环境和版本

主环境仅依赖标准库。两个 GPU 后端、MuJoCo／OpenUSD、Blender 及 Isaac 使用各自解释器。进程边界避免同名模块与二进制依赖串用，决定见[感知 ADR 001](../agent/perception/decisions/001-backend-processes.md)。

`backends.lock.json` 是初始化快照，不是运行时强制锁定器。新 v1 `run_manifest.json` 记录实际 Git HEAD、dirty、入口文件哈希与输入／产物身份；旧清单和 doctor 的 Git 快照还包含 tracked diff 哈希。哈希不是补丁副本，不能恢复未提交修改。ENG-001 已将现有算法适配提交到各自仓库，并保存可独立恢复的 bundle；当前版本见[源码基线](source-baseline.md)。远端尚未同步，资源恢复仍需使用指定版本及外部资源。

## 分支

`main` 保持为空，`dev` 为开发基线，后续任务从本地 `dev` 建新分支。ENG-001 将已有仿真／文档历史经 `chore/source-baseline` fast-forward 汇入本地 `dev`；保留原功能／文档分支。两个算法仓库的适配位于各自 `feature/local-runtime-baseline`，原 master 不变。尚未推送，不能假定远端 `dev` 已含这些更新。

## 资源与配置

源码在工作区，运行资源由[资源接口](../agent/interfaces/local-resources.md)管理。当前配置路径选择仅有 `--config`／`OMI_SHAPEFORGE_CONFIG`；运行根路径来自 TOML。外部便携包和仿真脚本接受自己的参数，不会自动读取主配置。
