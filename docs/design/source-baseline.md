# 源码与分支基线（ENG-001）

2026-11-20 完成首轮源码整理。版本和检查证据见 [source_baseline_20261120.json](../../manifests/source_baseline_20261120.json)。本页描述可恢复源码及现有环境复验，不代表全新机器上的依赖安装或原生扩展重新编译已通过。

## 已保存版本

| 仓库 | 整理前 | 已保存版本 | 保存内容 |
| --- | --- | --- | --- |
| ShapeForge | `a12c225` 加 80 个修改／新增文件 | `eb8da4289cad327cf61c5cc03e90d188df65f19b` | 现有仿真代码、知识库、资源元数据、PROMPTS 原文与开发方案；随后仅补充基线文档和证据 |
| FoundationStereo | `6e88068` 加 4 个文件 | `e46fa7098730674bfc9f96047b4d2ffe9a87e1b4` | 本地 DINOv2、checkpoint 兼容、避免重复下载初始权重、GPU smoke 入口 |
| BundleSDF | `ffa67d4` 加 8 个文件 | `b1a55878264e8c28841507bb578835c94a63d475` | PCL／CMake／pybind11／CUDA 适配、LoFTR 通道修复、组件 smoke 入口 |
| omi_proj | 干净工作树 | `963a7c29f8e39bff59ba4eb285693976b224961e` | 保留原分支与代码，仅备份源码 |

两个后端提交位于各自的 `feature/local-runtime-baseline`，原 `master` 不变。主项目先保存 `docs/project-knowledge-base`，再从 `dev` 建立 `chore/source-baseline`，以 fast-forward 接入现有仿真与文档历史；验收后将该整理分支 fast-forward 汇入本地 `dev`。`main` 仍为空树，历史分支保留，没有重写提交或推送。

后续从本地 `dev` 创建功能分支。远端分支尚未更新，新机器只克隆 GitHub 默认分支仍缺本轮提交；需使用下面的 bundle 或另行发布这些版本。原 `backends.lock.json` 保留为初始化快照，新的基线清单不改变 CLI 的版本选择行为。

## 恢复材料与实测

外部目录：

```text
/data/omi_runtime/baselines/source_baseline_20261120T014740Z/
  before.json                     整理前分支、HEAD、文件清单和哈希
  <仓库>/before.bundle            整理前 Git 引用及可达历史
  <仓库>/working-tree.patch       整理前已跟踪文件差异
  <仓库>/index.patch              整理前暂存差异
  <仓库>/changed-files.tar.gz     修改和新增文件原文
  <仓库>/source.bundle            下表验证使用的源码提交和历史
  restored-sources.json           bundle 哈希及恢复核对结果
  restore-check/                  从四份 source.bundle 实际克隆的副本
  validation/                     原工作区／恢复副本测试及 smoke 调用日志
```

四份 `source.bundle` 均通过 `git bundle verify` 和独立目录克隆，恢复 HEAD 与清单一致。恢复后的主项目使用恢复副本的 `src` 运行 4 项控制层测试，通过。两个未跟踪后端入口已纳入提交；主项目 6 个 CLI／调度／仿真文件也检查了跟踪状态和哈希。

从源码备份恢复的示例（目标目录须尚不存在；`/path/to/recovery` 替换为新位置）：

```bash
snapshot=/data/omi_runtime/baselines/source_baseline_20261120T014740Z
git clone --branch chore/source-baseline "$snapshot/omi_shapeforge/source.bundle" /path/to/recovery/omi_shapeforge
git clone --branch feature/local-runtime-baseline "$snapshot/FoundationStereo/source.bundle" /path/to/recovery/FoundationStereo
git clone --branch feature/local-runtime-baseline "$snapshot/BundleSDF/source.bundle" /path/to/recovery/BundleSDF
git clone --branch oct_26_branch "$snapshot/omi_proj/source.bundle" /path/to/recovery/omi_proj
```

这些 bundle 恢复的是已验证源码时点；最终文档交付另存 `omi_shapeforge/delivery.bundle`，对应提交由外部 `delivery.json` 记录，避免在清单中自引用当前提交哈希。bundle 克隆的 `origin` 是本地 bundle；需要使用远端时按清单中的地址重新配置。

bundle 不包含外部数据、模型权重、环境、生成资产、原生编译产物及 `omi_proj/local` 本地资源链接。恢复运行时须按[资源清单](../../manifests/README.md)和[环境教程](../../tutorials/environment_setup.md)配置；这里没有把“能恢复源码”写成“能在任意机器立即运行”。旧工作树恢复材料仅用于追溯，不应覆盖已经整理好的目录。

## 验证结果

| 检查 | 结果与证据范围 |
| --- | --- |
| 控制层 | 原工作区 4 项、恢复副本 4 项均通过 |
| doctor | 配置的路径、解释器、入口、权重与 nvcc 检查通过 |
| 官方双目 smoke | `20261120T014811_666235Z_stereo`：960×540、32 次迭代、470,018 点 |
| BundleSDF 组件 smoke | `20261120T014828_903620Z_bundlesdf`：C++、CUDA、PyTorch3D、Kaolin、Warp、LoFTR 检查通过；2,893 组匹配 |

两次 smoke 的运行清单均记录干净的主项目 `eb8da42` 及上述后端提交，输出位于 `/data/omi_runtime/runs/omi_shapeforge/` 的新目录。主项目后续交付修改限于文档和元数据，运行代码与该验证版本一致。

本轮没有重编译 BundleSDF 原生模块，报告另外记录了使用中的 `my_cpp` 文件哈希；没有进行完整视频在线重建、光模块原始录制重算、仿真场景复验或训练。历史环境与已有实验保持原样。

## 下一步

ENG-001 完成。下一项为 ENG-002：先定版运行记录、产物合同和旧报告适配规则，再开展共用运行层实现。具体顺序见[统一开发方案](unified-development.md)。
