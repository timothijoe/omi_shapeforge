# 本地资源与恢复契约

机器可读清单为 [resources.json](../../../manifests/resources.json)，字段和恢复方法见[说明](../../../manifests/README.md)。其中根目录与路径模板是描述元数据，不是自动下载／展开程序。

本机布局：源码位于工作区；`/data/omi_runtime` 存 envs、models、cache、inputs、assets、tools 和 runs；`/data/nov_19_folder` 保留上传 ZIP、清单及交接。主项目 `.venv` 是轻量控制环境，也被 Git 忽略。

- 原始 ZIP 和解压包用于输入，先校验哈希与清单；输入内容保持。
- 新结果写入 runs 的新目录，不覆盖历史结果。
- GPU 环境重新建立，不从旧机器复制 venv 或混入 Isaac 自带 Python。
- 大网格、模型、厂商 SDK、录包、权重、安装包和缓存不进入主 Git。
- 01 工程包包含旧自定义代码与结果；02、03 是数据；04 是旧二进制环境，不应把它当成本机已验证环境。00／05 与 portable／quick 不能替代全部主体包。

`omi_proj` 的 local/assets、local/models 和 local/vendor 现已从 OMI 包恢复到外部基线，当前 local 符号链接指向该资源树。其源码和 .git 未被旧快照覆盖；本机以 .git/info/exclude 屏蔽这个外部资源链接。完整迁移须保留 MJCF／URDF 引用的网格及相邻布局，仅有脚本、SDK 或文档不够。

历史验证清单含绝对路径，作为当时来源保留。人类运行命令使用新的资源根和参数；不要批量改冻结 JSON 以制造“已经迁移”的表象。

## 完整迁移包当前状态

00–05 现已全部到达并解压，两个工程的 data／DATA 均为基线中的实际数据目录，见[完整清单](../../../manifests/extracted_archives.json)。04 的 Linux 环境保存在同一基线的 environment_runtime/foundation_stereo，内部链接校验通过；它尚未执行 conda-unpack 前缀重定位，也未作为默认运行时或做兼容性验收。当前 envs/ 中已验证开发环境不变，使用历史环境前须单独核对修复与运行条件。
