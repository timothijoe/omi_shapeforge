# ShapeForge 资产迁移与恢复

本批迁移包保存当前机器上 Git 仓库之外的模型、场景、标定、特征数据、预训练权重及已完成训练状态。四个开发仓库的当前源码由用户另行提交和上传；本包不能代替这些源码提交。

交付目录：`/data/omi_migration/shapeforge_assets_20261121T051808Z/`。该目录中的 `README.md` 是本教程的副本。压缩包采用 gzip，成员路径保留原机器布局，但没有开头的 `/`。它们可先解压到任意空目录检查。

## 文件组成

| 文件 | 用途 |
| --- | --- |
| `01_assets_scenes.tar.gz` | Blender、OBJ/PLY/GLB、碰撞分解、MJCF/USD、机器人与夹爪、历史资产、感知特征及选定实验输入/报告 |
| `02_weights_dependencies.tar.gz` | FoundationStereo、LoFTR、MoGe、SAM2、FoundationPose、SERL 权重；V2D/MoGe/SAM2 外部源码；原 OMI BC 权重 |
| `03_completed_training.tar.gz` | 已完成首轮接管 RL、BC 候选和示范，以及上一阶段接触训练的模型、replay 与续训状态；可选下载 |
| `*.manifest.json` | 每个归档成员的路径、字节数、权限、修改时间和 SHA256；符号链接单独记录目标 |
| `archives.json`、`SHA256SUMS` | 压缩包大小及交付文件校验值 |
| `selection.json` | 实际选入根目录与排除项 |
| `source_versions.json` | 打包时四个开发仓库及外部源码的版本、分支和工作树状态 |
| `environment_snapshots/` | 七套当前环境的 Python 版本、已安装包版本、安装位置与 editable 来源；不是可直接照搬的环境 |
| `scene_dependencies.json` | 五个主要场景的外部文件引用清单 |
| `verification.json`、`scene_load_verification.json` | 逐文件归档验证与另一路径恢复后的场景加载结果 |
| `verify_package.py` | 重新检查压缩包和全部成员哈希，检查主要场景网格是否包含在交付中 |

三份压缩包分别为 **5.21 GiB、2.48 GiB、4.74 GiB**，合计 **12.43 GiB**，共 **45,619 个成员**。资产和权重两个包合计约 **7.69 GiB**。精确字节数以交付目录的 `archives.json` 为准。三个包按顺序去重：一个文件只放在一个包内；恢复完整训练时三个包都需要。资产包包含部分旧 SDF 训练权重，因为它们属于完整历史建模结果目录。

## 资产具体保存在哪里

以下路径中的 `R` 表示 `/data/omi_runtime`，`B` 表示 `R/baselines/reconstruction_20261119/workspace`，`L` 表示 `R/baselines/omi_transfer_20261120_004618/omi_proj/local`。

资产包包含：

- `R/assets/` 全部当前资产：光模块 V3 的工作副本与发布版、插座 r01–r04、SIM 接触资产 r01–r03、单模块及阵列场景。当前接触训练使用 `assets/sim_insertion/r03/`。
- `R/inputs/` 中 portable/quick 小型交付包。保留模型、手工 ROI、配置、来源、脚本与少量配准样例数据。
- `B/BundleSDF_trial/assets/`、`results/`、`references/`、`scan_asset_lab/releases/`，以及旧自定义脚本、文档和 manifests。这里包含 V1/V2/V2.1、原始插座建模、编辑几何和历史 SDF 结果。
- `B/FoundationStereo/output/` 中除旧 `checkpoints/` 与 `foundationpose_runtime_20261116/` 以外的历史结果。后者所需 FoundationPose 权重单独进入权重包；旧二进制环境不迁移。
- `L/assets/`、`L/models/`、`L/vendor/optical_module_pu/source/` 及厂商来源记录。保留机器人 URDF、网格和相邻目录；没有再复制重复的 922 MB 厂商原 ZIP。
- 仿真必需的 `runs/robot_urdf_mvp_20261120T090059Z/`、`dual_camera_scene_20261121_final/`、`contact_robot_scene_20261121_final/`、`mesh_insertability_20261121/`、V3 插入检查输入，以及规则示范和接触验证结果。
- 感知使用的点云配准、`body_mesh.npz`、腕部位姿先验、V2D 输入和结果、episode 派生结果、`mesh_feature_tracking_20261121/` 中的特征图谱及 `reference_features.npz`。完整选择见 `selection.json`。
- `/home/linux/Downloads/img/wrist_intrinsics_1920x1080.json`。
- `/home/linux/omi_folder/local_setup/` 中的环境说明和后端编译脚本。

`omi_proj/local` 原来只是指向 `L` 的符号链接；本包保存的是对应实体文件。恢复后需要重新建立该链接。

权重包另包含两处容易遗漏的内容：

```text
B/BundleSDF_trial/runtime/sam2_source/checkpoints/
B/FoundationStereo/output/foundationpose_runtime_20261116/FoundationPose/weights/
```

这些权重不在 `R/models/` 内。FoundationStereo 的完整 `.pth` 与 `cfg.yaml` 一起保存；未完成下载的 `.part`、`.download` 不保存。

## 训练快照范围

`03_completed_training.tar.gz` 保存：

```text
R/runs/contact_intervention_study_20261121/
  initial_actor.pt
  protocol.json
  contract.json
  selection.json
  additional_control_plan.json
  demonstrations/
  bc_plain/
  bc_rotation10/
  rl/

R/runs/contact_visual_training_20261121_final/
```

首轮 `rl/` 已完成 20 回合，独立测试报告记录 BC 3/4、RL 4/4，测试时没有接管。这是固定仿真任务的小样本结果。训练中使用规则接管，不能当作真人数据或真机精度验收。

打包不停止训练进程。正在推进的 `rl_bounded/`、其 pilot 和新的等数据/旋转对照不属于本次快照，即使它们在打包过程中产生了新文件，也不会自动进入归档。若要接续这些后续实验，需要结束后另做快照。

仅执行策略可以读取相应 `actor.pt`；继续首轮训练还依赖 `learner.pt`、replay、示范集和协议。本次保留完整已选目录，避免仅保存 actor 后丢失优化器及经验池。

## 原始采集数据出处

大规模原始数据不重复打包。下表原始压缩包均保存在旧机 `/data/nov_19_folder/`。

| 数据 | 原始文件及恢复位置 |
| --- | --- |
| BundleSDF 录制和处理数据 | `02_BundleSDF_trial_data.zip` → `B/BundleSDF_trial/data/` |
| FoundationStereo 扫描数据 | `03_FoundationStereo_DATA.zip` → `B/FoundationStereo/DATA/` |
| OMI 真实示范回合 | `omi_transfer_20261120_004618.tar.gz` 内 `omi_proj/local/rl_episodes/` |
| portable 配准样例 | `optical_module_portable_20261119.zip`；本次另保留其小型解压副本 |
| 旧自定义工程与结果完整基线 | `01_projects_and_results.zip`；包含代码和资产，不能整体视为原始采集数据 |
| 腕部原视频 | 旧机 `/home/linux/Downloads/img/腕部相机_插口接近_6秒.mp4` |
| 补充实物照片 | 旧机 `/home/linux/Downloads/img/` 中的 JPG |

02 包 SHA256：`9641eec7babb03856f0b06b383cdac3b498ce826eacc4ab1ab93586ad4de9156`。

03 包 SHA256：`6284db3e34438356cbed97f0ecc503ca47695624dec20aaab6840911ace8a597`。

OMI 包已计算 SHA256：`aa2f86ae3f00c8cfaeb2b429326ae8248cfcde2decfc9c3e91c88e7f4956d765`。

其他原包来源和校验见仓库 `manifests/extracted_archives.json`、`manifests/resources.json`。本次不包含完整 MCAP/真实 episode 数据库，但保留派生特征、规则示范、训练 replay 和少量样例；厂商源码的 `bag_test/` 中两个小型 MCAP 测试样例也随目录保留。所以不能按扩展名删除所有图像、NPZ 或点云。

## 在新机器恢复

### 1. 校验与解压

复制整个交付目录后，先在该目录执行：

```bash
sha256sum -c SHA256SUMS
python3 verify_package.py
```

验证器使用 Python 3.11 及以上版本的标准库，不需要 GPU；默认只报告结果，不覆盖随包保存的验收记录。会读取所有包，因此需要一定时间。若只下载前两个包，可先仅核对对应 SHA256；完整验证器要求三个包及 manifests 齐全。

建议先解到新建空目录，检查实际结构：

```bash
RESTORE_ROOT=/data/shapeforge_restore_20261121
mkdir "$RESTORE_ROOT"
tar -xzf 01_assets_scenes.tar.gz -C "$RESTORE_ROOT" --keep-old-files
tar -xzf 02_weights_dependencies.tar.gz -C "$RESTORE_ROOT" --keep-old-files
# 需要已有训练成果及续训时再解第三个包。
tar -xzf 03_completed_training.tar.gz -C "$RESTORE_ROOT" --keep-old-files
```

此时文件位于 `$RESTORE_ROOT/data/omi_runtime/` 等子目录。`--keep-old-files` 会对同名已有文件报错，避免悄悄覆盖。归档中的日志、进程锁、浏览器临时配置和 Python 缓存已排除。

### 2. 恢复目录布局与源码

最省改动的方式是在新机器使用 `/data/omi_runtime` 作为资源根，将暂存目录下的 `data/omi_runtime` 移至该位置；先确认目的地不存在。将暂存的 `home/linux/Downloads/img/wrist_intrinsics_1920x1080.json` 和 `home/linux/omi_folder/local_setup` 放到实际使用位置。

四个仓库 `omi_shapeforge`、`omi_proj`、`FoundationStereo`、`BundleSDF` 保持同级。拉取用户此次提交后的相应分支，不要使用空的 ShapeForge `main`。`source_versions.json` 仅说明归档时的源码状态，不包含未提交代码，也不会替用户提交。

在新 `omi_proj` 仓库中，确认 `local` 尚不存在后建立：

```bash
ln -s /data/omi_runtime/baselines/omi_transfer_20261120_004618/omi_proj/local local
```

场景 XML 包含绝对网格路径；若改变资源根，需要重新构建场景或在新副本中重定位路径。部分感知脚本还硬编码了 Downloads、模型输入和旧 run 路径，修改 `configs/local.toml` 并不能覆盖所有位置。不要批量改写历史来源 manifests。

### 3. 重建环境

不迁移 `.venv`、`R/envs/`、旧 conda 环境、Blender/Isaac 安装目录和通用缓存。使用仓库教程及以下清单重建：

- `omi_shapeforge/requirements/`、`manifests/environments/`。
- `omi_proj/requirements/sim-train-cu124.txt`。
- `local_setup/README.md` 和构建脚本。
- 已保存实验中的 `environment.txt`，包括 `runs/mesh_insertability_20261121/environment.txt`。
- 交付目录的 `environment_snapshots/`，覆盖七套实际环境；其中本地 URL 和平台相关扩展需要重新安装，不能直接把清单视为安装器。
- V2D 的 `runs/v2d_wrist_trial_20261121/provenance.json`；本机曾固定 Pillow 11.3.0，并从 BundleSDF 环境复用依赖，不能将 V2D 视为独立环境。

原环境常用 Python 3.11、PyTorch 2.6.0+cu124；Blender 为 4.5.16，Isaac PhysX 记录为 5.1.0。它们是已验证版本记录，目标机器仍需检查驱动和平台兼容。BundleSDF、PyTorch3D、nvdiffrast 等原生扩展需要适合目标 GPU 的编译；旧构建脚本包含 RTX 4090 的 SM 8.9 参数。

### 4. 验证恢复

按 `environment_setup.md` 设置 `configs/local.toml`，先运行 `doctor`，再按所需功能运行双目/BundleSDF smoke。`doctor` 通过仅代表路径检查。

仿真先按 `contact_simulation.md` 做局部接触及机器人循环验证，使用新的输出目录；随后再加载 actor 或续训。当前 SIM-r03 是等效柔顺接触模型，原 V3/r04 的刚体阻挡结论不因此改变。

## 本次校验边界

打包器逐文件记录 SHA256，并检查源文件在归档期间是否发生大小或修改时间变化；验证器重新读取每个压缩包，核对全部成员内容与符号链接。

主要场景的引用会检查是否包含在交付包中，并将对应 XML/网格从压缩包恢复到另一目录，重定位副本后使用现有 MuJoCo 环境加载。该检查证明归档与主要网格依赖完整；不代表已在另一台机器重新编译 GPU 后端或运行训练。
