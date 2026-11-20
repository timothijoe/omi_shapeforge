# OMI ShapeForge

OMI 的光模块感知、资产化与仿真开发主项目，Python 包名为 `omi_shapeforge`。

接续会话先读 [交接文档](HANDOFF.md)，再进入当前状态和能力文档。

当前已验证：官方双目样例、BundleSDF 组件检查、已圈选光模块 CPU 配准、Blender 资产导出，以及 MuJoCo／Isaac PhysX 的单模块与 2×2 场景。完整在线重建、机器人接入和实物精度仍未验收，见[能力总表](docs/capabilities.md)。

## 最短入口

在已有本机配置的仓库根目录执行：

```bash
.venv/bin/omi-shapeforge doctor
```

`doctor` 是路径与版本体检，不运行模型，也不证明 GPU 和所有依赖已通过。实际样例使用 `smoke stereo` 或 `smoke bundlesdf`，会生成新结果目录。

| 阅读目的 | 入口 |
| --- | --- |
| 操作者安装与运行 | [教程总目录](tutorials/README.md) · [快速运行](tutorials/quickstart.md) |
| 当前能力、证据与限制 | [当前总览](docs/current.md) · [能力总表](docs/capabilities.md) |
| Agent 接续开发 | [知识库入口](docs/agent/README.md) |
| 架构与维护规则 | [设计索引](docs/design/README.md) |
| 数据、权重、环境和机器人资产 | [资源清单说明](manifests/README.md) |

## 开发与分支

`main` 保持为空；本地 `dev` 已整理仿真、知识库和源码基线，后续从 `dev` 创建功能分支。远端尚未同步，版本与恢复步骤见[源码基线](docs/design/source-baseline.md)。

主项目维护流程、接口、配准评估和文档；同级 `FoundationStereo`、`BundleSDF` 自有仓库维护对应算法实现。后端适配已分别保存为本地提交并通过 smoke；仅拉取尚未同步的 GitHub 默认分支仍不能还原当前环境，见[架构说明](docs/design/project-architecture.md)。

```bash
.venv/bin/python -m unittest discover -s tests -v
```

大资源放在配置的外部根目录，本机为 `/data/omi_runtime`。原始输入与历史结果保留，新实验使用新输出目录。

## 许可证

本仓库采用 [MIT License](LICENSE)。第三方代码、模型、权重和厂商资源遵循各自许可。
