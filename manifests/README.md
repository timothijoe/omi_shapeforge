# 资源与证据清单

本目录只保存小型元数据、环境包清单和验证索引。数据、模型、权重、SDK、软件、venv、网格和输出本体保留在外部目录。

| 文件 | 职责 |
| --- | --- |
| [resources.json](resources.json) | 根目录、资源路径、用途、来源、必需功能、恢复方法和检查日期 |
| [visual_catalog_20261120.json](visual_catalog_20261120.json) | 资产可视化图册范围与完整文件目录；不改变能力验收状态 |
| [optical_assets.json](optical_assets.json) | 光模块模型名称、源文件哈希、版本关系、部件及场景实例身份 |
| [viewer_compatibility_validation_20261120.json](viewer_compatibility_validation_20261120.json) | 实际桌面无 WebGL 导致空白的原因、CPU 后备渲染及验证 |
| [backends.lock.json](backends.lock.json) | 后端初始化 Git HEAD、工作树和入口快照；不强制检出 |
| [source_baseline_20261120.json](source_baseline_20261120.json) | ENG-001 本地源码版本、原变更清单、bundle 恢复及控制层／GPU smoke 证据 |
| [contract_validation_20261120.json](contract_validation_20261120.json) | ENG-002 Schema／示例／反例检查、原报告只读核对；不是新增运行验收 |
| [workflow_validation_20261120.json](workflow_validation_20261120.json) | ENG-003 共用运行层、14 项测试与两个 smoke／MuJoCo 的实际运行证据 |
| [workflow_final_validation_20261120.json](workflow_final_validation_20261120.json) | 中断回收补强后的最终干净版本复验；保留上一份验证 |
| [initial_validation.json](initial_validation.json) | 主项目初始化与两条 GPU 调度的历史验证 |
| [portable_validation.json](portable_validation.json) | 本机已确认 ROI 配准的复验结果与包哈希 |
| [simulation_validation.json](simulation_validation.json) | Blender 和两引擎测试报告索引 |
| [robot_assets.json](robot_assets.json) | omi_proj 机器人资源需求、当前恢复位置和模型核对 |
| [transfer_validation.json](transfer_validation.json) | 新到达的 01／OMI 包校验、恢复、V2 回放与机械臂离线预检 |
| [data02_validation.json](data02_validation.json) | 02 包解压前的完整性和数据契约验证快照 |
| [restored_data02.json](restored_data02.json) | 02 数据全量恢复校验报告 |
| [extracted_archives.json](extracted_archives.json) | 当前 9 个已上传压缩包的解压位置、状态及最后检查 |
| [data03_04_validation.json](data03_04_validation.json) | 03／04 整包与成员恢复、落盘、符号链接和别名校验；旧环境未激活 |
| [documentation_validation.json](documentation_validation.json) | 本轮文档、入口和链接检查结果 |
| environments/ | 两个 GPU 环境的历史要求与 freeze；当前仿真 lock 位于 requirements/ |

## 资源格式与恢复

`resources.json` 的 `root` 指向 `roots` 中的目录，`path` 为该根下的相对位置。相对根以仓库根目录解释；绝对根是本机配置示例。`availability` 是检查当时的状态，不是永久保证，也不由 CLI 自动更新。

清单不是安装器，路径变量不自动注入代码。主配置迁移仍按[配置接口](../docs/agent/interfaces/configuration.md)填写，外部脚本用显式参数。恢复前核对 source、expected_sha256 和当前资料；expected hash 来自此前验证，是否重新哈希以各阶段记录为准；最新迁移阶段已核对 01 整包及恢复成员和 OMI 全部清单。

GPU 环境快照如下：

- [Stereo requirements](environments/requirements-stereo.txt) 与 [freeze](environments/stereo-freeze.txt)。
- [BundleSDF requirements](environments/requirements-bundlesdf.txt) 与 [freeze](environments/bundlesdf-freeze.txt)。
- [本机版本约束](environments/constraints-host.txt)。

它们与相应源码／原生扩展共同构成恢复依据；freeze 的本地 URL 或 editable 路径不能直接在新机器照装，不能复制旧 venv 冒充恢复完成。当前尚无完整可移植 GPU 一键安装器。依赖安装与已知缺口见[环境教程](../tutorials/environment_setup.md)。

历史验证 JSON 保留当时的绝对位置、哈希与限制。资源后来移动时更新当前目录映射与新记录，不篡改旧报告以掩盖来源。
