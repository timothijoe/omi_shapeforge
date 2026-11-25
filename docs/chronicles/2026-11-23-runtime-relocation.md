# 2026年11月23日 runtime实体归拢与兼容验证

用户确认保留runtime与storage各自内容，以保证完整性，并要求将runtime实体统一到ShapeForge目录、同步docs说明。本阶段承接[此前四批导入与交付迁移](2026-11-23-storage-layout.md)；前一阶段记录中的“runtime未搬迁”属于当时状态，原记录保留。

## 当前位置

运行资源实体从`/data/omi_runtime`迁至`/data/shapeforge/runtime`，与`/data/shapeforge/storage`并列。旧`/data/omi_runtime`现在是指向新实体的兼容链接，原本位于`/data/shapeforge/runtime`的导航链接已由实体目录替代。资产、权重、环境、工具、缓存、实验、基线和附带历史文档一起迁入，未拆散内部目录。

统一入口中的assets、models、experiments、snapshots、releases、environments、tools七个导航链接已改为直接指向新位置。runtime与storage按实体根登记；副本、压缩包、旧环境和失败实验均保留，没有执行去重或数据删除。

当前规则见[本地资源契约](../agent/interfaces/local-resources.md)，机器映射见[runtime迁移登记](../../manifests/runtime_relocation_20261123.json)。源码工作区及用户明确排除的home目录未搬迁。

## 完整性检查

本次在同一ext4文件系统内重命名目录，没有复制运行数据。迁移前后完整比对590,054个普通文件、55,774个目录、2,015个符号链接和1个遗留socket条目，未发现差异。核对内容包括设备号、inode、类型、权限、所有者、大小、实际分配块、硬链接数、修改时间；普通文件的ctime也一致。符号链接文本保留，解析目标在归一化新旧前缀后相同。

另对选定的不超过1 MiB的说明和元数据计算完整SHA-256，共10,585个路径、10,464个不同inode，前后一致。模型、数据集及其他二进制大文件没有重新全量哈希，其验证依据是原inode及元数据保持、迁移过程没有内容写入。普通文件按唯一inode计的实际分配量为215,232,589,824字节；不能把含硬链接或稀疏数组的表观大小当成额外复制空间。

预检发现的旧实验socket没有监听进程，已作为特殊条目原样保留；原有6个失效符号链接也未清理，前后状态一致。不存在越出runtime树的相对符号链接。首次预检在遇到socket时停止，尚未移动任何数据；补充特殊条目核对后重新执行，过程证据一并保留。

## 环境与旧命令

7套环境的解释器在迁移前、迁移后旧入口及迁移后新入口均完成检查：omi_sim_train、video_to_data_trial、omi_mesh_audit、omi_assets、simulation、foundation_stereo、bundlesdf。各环境中已安装的NumPy、MuJoCo、PyTorch可导入，版本与模块位置在归一化路径前缀后匹配迁移前。检查禁用字节码写入，没有启动GPU工作负载、仿真或训练。

现有`configs/workspace.toml`保留`/data/omi_runtime`作为稳定逻辑前缀，资源登记则注明新的实际根。旧环境脚本、场景、源码链接和历史命令继续依靠兼容入口；不批量改写冻结文件。换机时须先恢复实体，再恢复兼容链接与外部依赖。完整运行流程仍按各自教程验收，解释器导入检查不替代训练或场景运行验收。

迁移后另核对WVA-01的677项静态依赖完整SHA-256、3个共享数据链接及omi_proj/local资源入口，均通过；CLI doctor的配置路径与启动入口检查返回ready。结果随本次机器登记保存，未据此宣称完成GPU工作负载验收。

## 记录位置

本机证据位于`/data/shapeforge/maintenance/migrations/20261123T153023Z_runtime/`，包括压缩的迁移前后逐项清单、空差异清单、环境比较、导航变更和阶段记录。主项目文档和资源登记已同步；旧编年、原包清单与runtime中的历史说明保持原字节。以[机器登记](../../manifests/runtime_relocation_20261123.json)中的证据位置和哈希追溯本阶段。
