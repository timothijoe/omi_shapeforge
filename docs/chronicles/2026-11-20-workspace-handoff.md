# 2026-11-20：工作区完整进展与交接快照

本页汇总截至本次核对的全部工作。依据已保存报告、现有文件及 Git 工作树补录；本轮没有重新运行 GPU 推理、物理批次或训练。后续现状以[当前总览](../current.md)为准。

## 1. 项目、仓库与分支

主项目名、目录与 Python 包统一为 `omi_shapeforge`，展示名 OMI ShapeForge，采用 MIT 许可证。自有仓库远端为 `git@github.com:timothijoe/omi_shapeforge.git`。

`main` 保留为空提交，`dev` 保存初始开发代码。仿真实现已在本地 `feature/optical-simulation` 提交 `a12c225`；当前文档工作基于该提交，位于 `docs/project-knowledge-base`。当前一批文档及后续资源元数据尚未本地提交，也未推送，不能假定远端 dev 已含这些工作。

| 目录／仓库 | 当前职责与状态 |
| --- | --- |
| omi_shapeforge | 轻量调度、配置、证据、资产和仿真脚本；主命令为 doctor 与两种 smoke |
| 同级 FoundationStereo | 自有 fork；HEAD 为 `6e8806816b533e4d13ddbb95ffa907b797060a62`，有 3 处已跟踪修改及未跟踪样例入口 |
| 同级 BundleSDF | 自有 fork；HEAD 为 `ffa67d425240b5b76d2e387a7dd3d3735a7cf1a1`，有 7 处已跟踪修改及未跟踪组件入口 |
| 同级 omi_proj | 保留现有 Git 代码，local 指向外部资源基线；已用于离线仿真预检，不调用硬件控制 |

两个算法 fork 的本地适配包括兼容当前依赖、原生编译和样例入口；HEAD 本身不包含全部实际代码。后续共享前应分别提交这些修改，不能把差异哈希当作补丁。架构见[仓库与运行时](../design/project-architecture.md)。

## 2. 当前运行环境

本次只读取各已用环境的 Python／发行包元数据，未导入 Torch 运算或启动归档旧环境。报告使用的本机 GPU 为 RTX 4090，当前只读查询驱动为 550.107.02。

| 环境／工具 | 版本及用途 |
| --- | --- |
| 主项目 .venv | Python 3.11.15，omi-shapeforge 0.1.0，控制层仅标准库 |
| envs/foundation_stereo | Python 3.11.15，Torch 2.6.0+cu124，torchvision 0.21.0+cu124，NumPy 1.26.4、SciPy 1.17.1、Open3D 0.19.0 |
| envs/bundlesdf | 同上；另有 Kaolin 0.18.0、PyTorch3D 0.7.8、Warp 1.19.0+cu12 和已编译 mycuda／BundleTrack |
| envs/simulation | Python 3.11.15，MuJoCo 3.3.7、OpenUSD 26.11、NumPy 1.26.4，用于光模块场景 |
| envs/omi_assets | Python 3.12.7，MuJoCo 3.15.0、NumPy 2.5.3、Gymnasium 1.4.0，用于较新机械臂模型预检 |
| Blender | 官方 4.5.16 LTS，同原包版本；命令 blender，安装在外部 tools 目录 |
| Isaac Sim | 已安装 5.1.0 和 6.0.1；当前场景只验证过 5.1.0 自带 Python 的 PhysX CPU 路径 |
| 04 历史快照 | Python 3.11.18、Torch 2.7.1+cu128／CUDA 12.8；只解包和静态校验，未 conda-unpack、激活或兼容性验收 |

运行资源根为 `/data/omi_runtime`，主配置仍选择 envs 中现有环境，不会因为 04 到达而切换。Blender 命令链接和应用菜单入口已建立；图形界面操作尚未验收。

## 3. 全部上传包与恢复结果

当前 9 个包均已解压，原压缩包保留在 `/data/nov_19_folder`。完整目录和报告见[解压索引](../../manifests/extracted_archives.json)。

| 包 | 内容和检查结果 |
| --- | --- |
| 00_migration_tools_and_manifests.zip | 恢复工具、清单、环境说明和旧验证记录；87 个解压文件与包内内容复核一致 |
| 01_projects_and_results.zip | 旧 BundleSDF_trial／FoundationStereo 代码、权重、模型、文档与结果；整包 SHA256 及 81,042 个成员恢复校验通过 |
| 02_BundleSDF_trial_data.zip | BundleSDF data：9 份原始录包、28 帧基线、59 组近距光模块及缓存；2,121 个成员、约 39.32 GiB 全量恢复校验通过 |
| 03_FoundationStereo_DATA.zip | FoundationStereo DATA：录制、标定与重建／匹配输入；397 个清单成员、约 42.19 GiB 校验通过，另补齐 1 个大小写别名 |
| 04_foundation_stereo_linux_environment.zip | 历史 Conda-pack 快照；61,829 个条目、约 8.36 GiB 校验通过，1,154 个内部链接无缺失目标 |
| 05_developer_handoff.zip | 交接及文档覆盖记录；2 个解压文件复核一致 |
| optical_module_portable_20261119.zip | 独立 CPU 配准小工程，含照片、10 万点点云、ROI、模型与脚本；内部清单及 ZIP 校验通过 |
| optical_module_quick_20261119.zip | 快速查看／编辑交付；5 个主要结果与 portable 对应文件逐字节一致 |
| omi_transfer_20261120_004618.tar.gz | 机器人资源、示范、BC 权重与离线代码快照；gzip CRC、7,361 项包内 SHA256 和 7,321 项源文件记录通过 |

原始采集的少量丢帧属于已有数据情况：02 近距录制记录左／右／颜色／深度为 900／899／895／900 帧，选出 59 个完整时间组。归档完整并不等于原采集零丢帧或深度／标定为物理真值。

## 4. 数据、资产和结果的实际位置

以下以 `/data/omi_runtime` 为根；完整位置以解压索引及[资源清单](../../manifests/resources.json)为准。

```text
baselines/
  reconstruction_20261119/
    workspace/
      BundleSDF_trial/                  旧自定义工程与 02 data
      FoundationStereo/                旧工程与 03 DATA
    environment_runtime/
      foundation_stereo/               04 原环境快照，未重定位
    migration_support/                 恢复支持工具
  omi_transfer_20261120_004618/
    omi_proj/local/                    资产、示范与权重
inputs/optical_packages_20261120_001316/
  optical_module_portable_20261119/
  optical_module_quick/
assets/
  optical_module_sim_20261120/          15 部件 OBJ 和 asset.json
  optical_scene_v2_20261120/            单模块 MJCF／USD
  optical_array_2x2_20261120/            方阵 MJCF／USD
runs/                                  各次验证日志、报告和图像
```

当前工作区 `omi_proj/local` 是指向 OMI 基线 local 的符号链接，使用本地 Git exclude 保护；源代码与 .git 未被包内快照覆盖。重建基线与当前算法开发仓库是独立目录。

压缩包、模型、数据、安装包、缓存、环境和输出都留在 Git 外。此时点 `/data` 约剩 55 GiB；本轮没有删除原包。历史 JSON 的原机器绝对来源路径保留，不能直接当作新机器运行路径。

## 5. 感知与旧结果复现

| 验证 | 已取得的本机证据 | 不能推导的结论 |
| --- | --- | --- |
| 主项目调度 | 两种 smoke 实际执行通过；已有 4 项控制层测试记录 | 不是完整流水线或所有依赖诊断 |
| 官方双目 | 960×540、32 次迭代，470,018 点；两次进程的视差和深度数组一致 | 不是光模块原始录包的重新推理或深度真值精度认证 |
| BundleSDF 组件 | C++ 绑定、CUDA 采样／编码及梯度、PyTorch3D、Kaolin、Warp、真实 LoFTR 检查通过；LoFTR 2,893 组匹配 | 不是全视频在线跟踪和最终 textured mesh 重建通过 |
| 便携光模块配准 | 10 万点场景，486 原始选点、472 过滤点、121 检查点；固定尺度刚体拟合和独立复查通过 | 已知 ROI，头尾／正反仍有近似多解，不是自动检测或绝对位姿精度 |
| V2 冻结几何回放 | 64 个源文件核对；粗／细几何最大差约 1.83e-9／1.77e-9 m，面数组一致 | 不是从新的传感器录制重新估计几何 |

便携配准检查点中位距离约 0.147922 mm、P90 约 0.731328 mm，两项与参考差为 0；全部原始选区 P90 约 2.770541 mm，需一起报告。它们都是表面残差，不是实物位姿误差；检查区的选取和初始化也依赖整体观测。

01 还恢复了 V1／V2／V2.1 与 candidate_03 带孔对象的 161 个分件及来源。原版本继续保留，没有自动替换便携模型或仿真原型，也未将原机的尺寸／插入检查冒充当前重新执行。旧错误目标已撤回，后续只使用已确认目标的证据。

详细现状见[双目与组件](../agent/perception/evolution/stereo-and-backends.md)、[配准](../agent/perception/evolution/confirmed-registration.md)及[数据与回放](../agent/perception/evolution/data-and-replay.md)。

## 6. Blender 和两套仿真

Blender 4.5.16 LTS 的官方包已按 SHA256 验证。四份保存模型已后台重开，内嵌照片、库依赖和单位检查通过；当前连通槽模型实际渲染了一张 1400×1000 图像，并求值导出 15 个外观部件。

单模块和 2×2 场景都已生成 MJCF／USD：

- MuJoCo 3.3.7：实际加载、EGL 离屏图像、240 步／2 秒落台、稳定与接触检查通过。
- Isaac Sim 5.1.0：实际本地 USD 加载、PhysX CPU 的 240 步落台和支撑检查通过；无 RTX 相机图像。

当前碰撞是刚性配准模型的包围盒，不保留凹槽接触；质量 20 g、摩擦 0.6 为演示假设；拉手刚性附着，支撑轨道为示意结构。不能据此宣称夹持、插接、柔性或跨引擎物理精度通过。

Blender 原照片／metric／groove 完整生成阶段尚未在本机复跑，59 帧尺寸也未重新估计。详细边界与结果见[资产管线](../agent/simulation/evolution/asset-pipeline.md)和[引擎场景](../agent/simulation/evolution/engine-scenes.md)。

## 7. 机械臂、夹爪和 OMI 示范

OMI 包补齐了完整双臂 MJCF、相邻 MarvinCCS、Stand 派生模型与厂商资源。原 MuJoCo 3.3.7 拒绝新 compiler 语法，因此另建 MuJoCo 3.15 环境，保留源 XML，不改旧光模块环境。

本机已完成默认双臂 MJCF 的编译、forward、A 臂项目 preflight 和 EGL 静态渲染。两份完整 URDF 各有 27 links／26 joints，含 14 个臂旋转关节和 4 个滑动指关节；各 54 处网格引用均存在。指关节声明 velocity=0、工具/TCP 和惯量等仍需核对。

默认 MJCF 仍是灵巧手／刀具旧场景，不能直接等同于当前触觉夹爪。Stand 方向修正版仍仅为派生可视化对照，旧限位与坐标问题不因文件恢复而解决。机器人尚未组合进当前光模块场景，也未完成 Isaac 机器人导入。

OMI 示范保留原采集 10 回合中的 9 个正常回合，排除 1 个断连回合；元数据为 41 个片段、1499 条样本，训练／验证 1174／325。动作是 6 维末端增量，no_gripper=true，不能直接作为 7 维仿真关节动作或夹爪动作标签。历史 BC6148 使用过全部 1499 条，其旧验证划分不是这个权重的独立测试集。

本机已完成包内文件校验、模型预检和索引检查；没有执行包内完整的逐样本／Actor 推理验证，没有重新 BC／RL 训练，也没有连接 ROS、控制器或真机。详见[机器人资源](../agent/simulation/evolution/robot-assets.md)。

## 8. 入口和证据

主命令只包含 `doctor`、`smoke stereo`、`smoke bundlesdf`。doctor 检查路径和 Git 状态，不运行模型，不验证 GPU、旧环境或机器人。便携配准、Blender 和两套仿真仍是独立脚本；按任务运行的前提、命令和预期结果见[教程导航](../../tutorials/README.md)。

| 事项 | 证据索引 |
| --- | --- |
| 主项目初次控制／GPU 样例 | [initial_validation](../../manifests/initial_validation.json) |
| 便携 CPU 配准 | [portable_validation](../../manifests/portable_validation.json) |
| Blender 和光模块场景 | [simulation_validation](../../manifests/simulation_validation.json) |
| 01／OMI 恢复、V2 和机器人 | [transfer_validation](../../manifests/transfer_validation.json) |
| 02 压缩包校验与数据检查 | [data02_validation](../../manifests/data02_validation.json) |
| 02 全量恢复 | [restored_data02](../../manifests/restored_data02.json) |
| 03／04 校验、恢复与链接 | [data03_04_validation](../../manifests/data03_04_validation.json) |
| 全部包的最终解压状态 | [extracted_archives](../../manifests/extracted_archives.json) |

旧 JSON 反映记录当时状态：例如早期 simulation 记录机器人尚未到达，早期 data02 记录尚未解压。它们保留原值，当前资源状态使用最终解压索引与当前资源清单，不回写旧报告制造一致。

## 9. 未验收事项和下一步

1. 先把后端未提交适配保存为可共享版本，再把旧工程中需要的流程按当前路径逐项接入。
2. 针对已恢复真实录制，选择一个固定样例重新计算双目和配准，再推进完整 SDF／跟踪流程；不能因数据到齐就宣布算法复现完成。
3. 核对机器人／夹爪配置、轴向、TCP、限位、惯量和真实夹具几何，再组合 optical 场景并重建精细碰撞模型。
4. 若确实需要历史 04 环境，独立完成前缀修复和运行兼容性验收；它不是继续使用当前环境的前置条件。
5. 分别验证 Isaac RTX、GUI 交互、完整 Blender 生成阶段、OMI Actor／数据合同与训练，不相互替代证据。
6. 真实尺寸、真实六自由度位姿、抓取／插接及真机性能均需要独立验收。

本快照只记录现有实现和证据，没有宣布这些后续工作已完成；本轮未创建新的本地提交或执行 push。
