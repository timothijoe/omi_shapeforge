# 本地资源与恢复契约

机器可读清单为 [resources.json](../../../manifests/resources.json)，字段和恢复方法见[说明](../../../manifests/README.md)。其中根目录与路径模板是描述元数据，不是自动下载／展开程序。

## 当前本机布局

统一查找入口为[/data/shapeforge/README.md](/data/shapeforge/README.md)。源码与本仓库说明仍位于`/home/linux/omi_folder`；运行资源实体已迁入`/data/shapeforge/runtime`，原`/data/omi_runtime`为兼容链接。2026-11-23两阶段迁移后的实体与旧入口如下。

| 用途 | 当前实际位置 | 旧兼容路径 |
|---|---|---|
| 运行资源、环境、实验和历史基线 | `/data/shapeforge/runtime` | `/data/omi_runtime` |
| 原始工程、数据和环境迁移包 | `/data/shapeforge/storage/imports/reconstruction_2026-11-19` | `/data/nov_19_folder` |
| 采集数据和采集机备份 | `/data/shapeforge/storage/imports/capture_session_2026-11-22` | `/data/zt-think-d1-data/nov_22` |
| 资产和训练交付包 | `/data/shapeforge/storage/exports/shapeforge_assets_2026-11-21` | `/data/omi_migration/shapeforge_assets_20261121T051808Z` |
| 交付包恢复检查副本 | `/data/shapeforge/storage/restore_checks/shapeforge_assets_2026-11-21` | `/data/omi_migration/shapeforge_assets_20261121T051808Z_restore_check` |

每批内部的原文件名、目录结构、README、校验清单和内容均保留。原`omi_migration`与`zt-think-d1-data`父目录现在作为兼容容器使用。机器可读映射见[存储迁移登记](../../../manifests/storage_layout_20261123.json)，操作经过和验证范围见[迁移编年](../../chronicles/2026-11-23-storage-layout.md)。

runtime整体保留envs、models、cache、inputs、assets、tools、runs及历史baselines，内部硬链接、符号链接和目录关系保持。主项目`.venv`仍位于源码工作区。`configs/workspace.toml`保留`/data/omi_runtime`兼容前缀，已有环境、场景和脚本可继续使用该路径；它指向新的实体，不表示另有一份运行资源。详见[路径解析说明](configuration.md)、[runtime迁移编年](../../chronicles/2026-11-23-runtime-relocation.md)与[机器登记](../../../manifests/runtime_relocation_20261123.json)。

## 存储与版本原则

### 集中范围与外部依赖

本次实体迁移覆盖原runtime与四批导入／交付资料，它们已集中到`/data/shapeforge`。这不表示本机所有相关软件都位于该目录：Isaac Sim安装仍在`/data/isaac-sim-5.1.0`，BundleSDF所用CUDA工具链仍在`/usr/local/cuda-12.4`。它们是当前配置使用的外部运行依赖，未纳入本次搬迁；用户排除的home目录也保持原位置。

当前维护页面中引用旧runtime前缀的说明已补迁移提示。历史编年、复制进来的原说明和冻结清单保留原文，由导航索引及迁移映射解释当前位置。不能把“入口和路径兼容检查通过”理解成“所有历史文档都已改写”，也不能把集中目录当成包含外部软件依赖的独立完整备份。

### 资源保留规则

- 原始 ZIP 和解压包用于输入，先校验哈希与清单；输入内容保持。
- 新结果写入 runs 的新目录，不覆盖历史结果。
- GPU 环境重新建立，不从旧机器复制 venv 或混入 Isaac 自带 Python。
- 大网格、模型、厂商 SDK、录包、权重、安装包和缓存不进入主 Git。
- 01 工程包包含旧自定义代码与结果；02、03 是数据；04 是旧二进制环境，不应把它当成本机已验证环境。00／05 与 portable／quick 不能替代全部主体包。

`omi_proj` 的 local/assets、local/models 和 local/vendor 现已从 OMI 包恢复到外部基线，当前 local 符号链接指向该资源树。其源码和 .git 未被旧快照覆盖；本机以 .git/info/exclude 屏蔽这个外部资源链接。完整迁移须保留 MJCF／URDF 引用的网格及相邻布局，仅有脚本、SDK 或文档不够。

历史验证清单含绝对路径，作为当时来源保留。人类运行命令使用新的资源根和参数；不要批量改冻结 JSON 以制造“已经迁移”的表象。

新接收的完整批次放在`storage/imports/<用途>_<日期>`；新交付物放在`storage/exports/<用途>_<日期>`；恢复检查副本放在`storage/restore_checks/<对应批次>`。工作流程的小型输入、资产修订和实验输出分别放在`/data/shapeforge/runtime/inputs`、`assets`、`runs`的新目录中。

逻辑资产版本与实际存放位置分开登记。同一版本的工作稿、冻结副本和预校验目录各有用途；同名或内容相同不自动意味着可以删掉其中一个。WVA-01仍引用外部资产，细网格数据的`data`与`data_strict`共享`shards`和模板，训练恢复仍依赖learner、replay、示范与协议。目录归类未替代这些恢复关系。

## 索引维护与兼容恢复

旧名称快捷入口集中在`/data/_catalog/90_legacy_paths`。根目录的`omi_runtime`、`nov_19_folder`、`omi_migration`、`zt-think-d1-data`转接到这个目录，最终仍访问同一批实体；旧根目录名称尚未移除。入口路由见本机[index_config.json](/data/shapeforge/index_config.json)的`compatibility_routes`和[调整记录](/data/shapeforge/shortcut_routing.json)。环境启动脚本及场景仍使用旧前缀，不能仅移动链接就取消原地址。

资源来源和恢复要求维护在本仓库`manifests/resources.json`及对应版本清单；当前说明维护在本页和领域文档。本机`/data/shapeforge`的表格是派生索引，更新原清单后运行：

```bash
python3 /data/shapeforge/refresh_catalog.py
python3 /data/shapeforge/refresh_catalog.py --check
```

刷新只生成索引和导航链接；`--check`只检查，不搬迁文件、不重新哈希全部数据、不运行仿真或训练。原脚本中仍使用旧路径的入口由兼容链接支持，不能在依赖仍存在时移除这些链接。

交付包中的`run_validation.py`和`load_scenes.py`会根据解析后的脚本位置推导相邻的`*_restore_check`目录。因此还保留`/data/shapeforge/storage/exports/shapeforge_assets_2026-11-21_restore_check`链接，指向独立的`restore_checks`实体；它不是第二份副本。原脚本及历史验证报告未改写。

换机时先按清单恢复runtime与storage实体，再恢复上述兼容关系，尤其是`/data/omi_runtime`到新runtime的链接，保留符号链接、硬链接和稀疏文件语义。仅复制导航目录不等于完整备份：源码、未提交工作、部分照片与标定、PCG-01便携交付物还位于`/home/linux`，环境也可能依赖外部解释器。完整步骤见本机[恢复指南](/data/shapeforge/RESTORE.md)；本机索引不可用时，可从仓库内的存储登记和原资源清单确定映射与恢复范围。

## 完整迁移包当前状态

00–05 现已全部到达并解压，两个工程的 data／DATA 均为基线中的实际数据目录，见[完整清单](../../../manifests/extracted_archives.json)。04 的 Linux 环境保存在同一基线的 environment_runtime/foundation_stereo，内部链接校验通过；它尚未执行 conda-unpack 前缀重定位，也未作为默认运行时或做兼容性验收。当前 envs/ 中已验证开发环境不变，使用历史环境前须单独核对修复与运行条件。
