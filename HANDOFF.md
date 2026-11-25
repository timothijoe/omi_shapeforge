# OMI ShapeForge 交接文档

当前System1／System0主线：[2026-11-25完整交接](docs/chronicles/2026-11-25-system1-system0-handoff.md)。含最新分工、直接动作与腕力、60轮System1训练、九位置泛化不足、可视化和下一步；当前先处理System1接近位置覆盖。

存储接续：运行资源实体已迁入`/data/shapeforge/runtime/`，原`/data/omi_runtime`为兼容链接；导入与交付资料位于同级storage。当前布局以[本地资源契约](docs/agent/interfaces/local-resources.md)为准，分别见[runtime迁移](docs/chronicles/2026-11-23-runtime-relocation.md)和[此前四批资料迁移](docs/chronicles/2026-11-23-storage-layout.md)。下方历史命令中的旧runtime前缀继续有效。

当前Isaac插入／规则反馈RL窗口已收尾：[专项交接](docs/chronicles/2026-11-23-isaac-rule-rl-window-handoff.md)。含固定WG-r10＋OM-r08、旧BC／RL结果、新规则8/8与恢复4/4、视频恢复、源码快照、实仿缺项及接续注意事项；不替代并行感知／资产交接。

当前感知任务交接：[三变量采样、细网格数据与后续预训练](docs/chronicles/2026-11-23-perception-grid-pretraining-handoff.md)。含已确认目标、数据入口、验证、历史模型区别、恢复和接续事项；不替代并行资产／控制任务交接。

本窗口专项交接：[外观资产、GC-r01接触与PCG-01纯几何交付](docs/chronicles/2026-11-23-mesh-contact-pcg-window-handoff.md)。最近可复制产物是Downloads/PCG-01.zip；文档包含版本区别、窗口恢复、验证和接手注意事项，不替代并行主线状态。

[感知细网格数据v1](docs/agent/perception/evolution/grid-perception-data-v1.md)已完成：16490候选全部检查，16251张物理有效图；严格三变量主集14549张（训练12463／验证987／测试1099），辅助1702张，未收录239个。窗口8895，模块和插座范围／步长、有效区域及标注均可查看；当前仅孔口前静态样本，未训练新网络。推荐入口`grid_perception_20261123_v1/data_strict/`。


纯几何资产导出专项已归档：用户看过PCG-01三维展示后要求复制走，交付`/home/linux/Downloads/PCG-01/`及`PCG-01.zip`。先读[PCG-01纪传体](docs/agent/perception/evolution/pointcloud-geometry-pcg01.md)和[编年体](docs/agent/perception/chronicles/2026-11-23-pointcloud-geometry.md)；文件不带颜色、沿用原坐标，插口排除大支架，与旧完整模板范围不同。此项不改并行感知／控制训练状态。

用户已查看可视化并确认光模块相对夹爪只采样**前后、上下、俯仰**，左右居中、偏转和侧倾固定。[三变量预览](docs/agent/perception/evolution/three-variable-grasp-preview.md)已完成27组静态夹持检查，窗口8894；三变量含义与可视化表达已获认可，正式采样范围／步长另议，未开始新训练。

2026-11-23：GC-r01接触版感知训练已完成。256段／3072帧经接触与可见网格筛选，方案一模板续训25轮；同一新测试集尖端误差旧模型12.26mm→新模型0.98mm，P90为1.38mm，最差仍10.97mm。窗口8893；仅接近阶段仿真，非插入／真机验收。 [完整记录](docs/agent/perception/evolution/contact-wrist-surface-learning.md) · [恢复](tutorials/contact_wrist_surface_learning.md)。

腕部夹持专项最新：[GC-r01双胶垫接触修订](docs/agent/simulation/evolution/wrist-contact-closure.md)已保存。旧WVA-01有左右间隙；新场景模块不焊死，双指闭合产生接触，5例移动／释放及半步长通过。源mesh、WVA-01和当前r10训练场景保持原样。

最新仿真资产专项状态：**WVA-01「腕部实拍对齐版」已具备并获用户接受**。复用先读[版本纪传体](docs/agent/simulation/evolution/wrist-visual-wva01.md)、[阶段编年](docs/agent/simulation/chronicles/2026-11-22-wva01-assets.md)和[固定清单](manifests/wrist_visual_wva01_20261122.json)。固定r15夹爪／相机＋r08模块及插槽参考场景；视觉基线与下方感知／r10训练进度分别管理，不改变其他主线任务优先级。

历史首轮训练：[仿真腕部视频→完整点云](tutorials/sim_wrist_surface_learning.md)，窗口`http://127.0.0.1:8892`。数据256配置／3072帧，25轮3600更新，最佳第19轮；独立测试尖端相对误差均值1.92mm，对比平均位姿基线21.42mm。模型在`/data/omi_runtime/runs/sim_wrist_surface_20261122_r01/train/best.pt`，含视频、完整点云和复现记录。旧“未训练”页面是历史原型；当前训练也尚未完成真机／插接精度验收。

8891显示后续：按用户要求保留整体脉络，默认完整材质色点云＋原位重点加密，并提供局部小窗。没有改变点集或位姿，仍为模块22528／插座43008点。[操作](tutorials/interaction_surface_representation.md)。

表征后续：用户重点改为模块尖端和插孔接触几何。已新增[局部精细点云窗口](tutorials/interaction_surface_representation.md)，地址`http://127.0.0.1:8891`；密集参照和网络模板分开，后者模块22528／插座43008点，包含全局／局部／棱边三层。源mesh不改，旧8890点数窗口保留；当时网络未训练；现有已训练结果见本页顶部。

历史未训练原型：[图像→完整表面点云原型](tutorials/image_to_complete_surface.md)，独立窗口`http://127.0.0.1:8890`。模块2048／插座8192点、共享图像编码器／自动局部裁剪／双位姿头／模板刚体解码已实现并检查前向和梯度；网络尚未训练，当前数值输出不可当定位结果。8876人工调节与原标注保留。

历史r10视觉资产专项交接（2026-11-22）：[WG-r10＋OM-r08接入说明](docs/agent/simulation/evolution/wrist-assets-handoff.md)、[机器清单](manifests/wrist_visual_asset_handoff_20261122.json)、[独立复现教程](tutorials/reuse_wrist_visual_assets.md)。已核对哈希、依赖和隔离重渲染，原结果不变。旧挂载助手的组件／颜色映射尚需适配；本项不改变下方感知／Isaac任务的优先级。

初始化与颜色后续：[四点结构引导＋密集彩色点云](docs/agent/perception/chronicles/2026-11-22-guided-initialization-color.md)已接入。原图按序点四角，结合双目深度求初值；原始RGB／选区辅助色可切换，目标邻域密集保留。首条有待审阅建议，用户原调整已保存；两组调节仍独立，真实精度未认证。前后端点云布局同步更新为八列，重启服务后刷新页面。

位姿窗口后续：点云与像素拟合已拆成左右视图下方各六轴的独立调节栏，互不覆盖；外参只在显式应用时才替换投影。28项隔离／保存恢复浏览器检查通过，正式标注不改。[操作](tutorials/head_wrist_pose_review.md)。

2026-11-22新增可操作入口：[头部点云＋腕部位姿审阅窗口](tutorials/head_wrist_pose_review.md)，本机`http://127.0.0.1:8876`。支持287条数据、模块／插座独立六轴滑条、按需双目点云、鱼眼线框、手工结构点精修、逐条外参候选及历史保存。首条仅为待审阅演示初值，插座仍偏；[能力边界](docs/agent/perception/evolution/head-wrist-pose-review.md)。

当前任务优先级（2026-11-22用户重新指定）：**腕部相机中的光模块位姿估计与头部双目点云几何约束优先**。从新备份的287组四图和已有五组点云接续，先核查相机标定／坐标关系，再做结构约束与mesh回投影；详见[感知接续决定](docs/chronicles/2026-11-22-perception-priority.md)。Isaac图像对照和RL仿真作为后续工作，以下旧优先级按历史阶段理解。

真实视觉接续（2026-11-21）：先读[感知开发完整交接](docs/chronicles/2026-11-21-perception-progress-handoff.md)。当前主线不使用附加 marker，已完成模块/夹爪归属过滤，右侧可疑头部线停用，保留四组结构；精确六维、遮挡定位和到位判断尚未验收。当前感知源码/文档及主要证据另存于 `/data/omi_runtime/baselines/perception_handoff_20261121T092928Z/`。这与下方仿真策略结果分开评价，当前工作树修改尚未提交。

最新策略试验：已完成10个BC训练回合、两组各20回合接管RL和关闭接管的独立测试／新初态确认，合计BC 7/8、第一轮RL 8/8；另一个组合及等数据额外BC失败。资产仍是一套包含模块／插座／7触点的装配包，额外marker贴纸可忽略。全部进展、失败和限制见[汇总](docs/chronicles/2026-11-21-contact-policy-improvement.md)，数据／源码快照见[新清单](manifests/contact_policy_study_20261121.json)。

最新交付：用户要求不改现有mesh、创建新仿真资产，已建立 **SIM-OM001-OS001-r03** 并完成局部／机械臂规则接触插入退出、双相机和实际训练续训。见[观看与操作](tutorials/contact_simulation.md)、[交付记录](docs/chronicles/2026-11-21-contact-asset-completed.md)。视觉闭环仍未成功，不能把规则通过当作策略成功；原mesh与旧失败证据保留。

当前优先级（2026-11-21）：用户要求先检测mesh并保证插入。已完成[原网格／碰撞体／实际接触检查](docs/agent/simulation/evolution/mesh-insertability.md)，原完整模型在4.212mm被入口弹片阻挡；主体51.282mm通路仅为排除细件的诊断。不能声称插入成功。拓扑修复和孔形分解已另存，下一步复核弹片与横向卷边，见[教程](tutorials/mesh_insertability.md)。

规则示范接续（2026-11-21）：已新增预插入规则老师、16段成功示范、三视图回放、视觉BC与规则／在线混合训练，见[教程](tutorials/rule_demonstrations.md)和[能力边界](docs/agent/simulation/evolution/rule-demonstrations.md)。独立规则来源和BC设置随新训练目录恢复；旧无示范结果保留。

2026-11-21 最新接续：[双相机仿真与 OMI 视觉训练](docs/agent/simulation/evolution/visual-training.md)已跑通，累计 300 条经验／20 次 SAC 更新并完成续训。见[启动教程](tutorials/dual_camera_training.md)与[本次编年](docs/agent/simulation/chronicles/2026-11-21-dual-camera-training.md)。本次同时修改 `omi_proj` 的独立仿真训练入口，代码未提交；下面旧基线关于“没有修改 OMI／没有训练”的描述是历史范围。

最新开发方向：用户要求优先搭建**包含真实机械臂 URDF 的仿真与 RL 架构**，先做简单可运行版本。已完成完整双臂／夹爪 URDF 导入、圆桌和插接资产参考场景、6D TCP→IK→伺服的 Gym 小幅到达检查；当前关闭接触、未建立抓取关系、未训练 RL。后续按[开发计划](docs/design/robot-rl-development-plan.md)推进工具 TCP／夹持模块／预插入到达；[启动教程](tutorials/robot_sim_mvp.md)。纯笛卡尔夹具只作回归，不是主场景。

最新插接座工作：当前为 **OS-001/r04 孔宽检查候选**，金属通道内宽 19.00 mm、白色孔口宽 20.60 mm，相对当前 V3 单侧名义间隙约 0.41 mm。按用户要求比 r03 略放宽，保留背面结构和完整下部支架，V3 未缩放。默认使用 [Open3D 插入查看器](tutorials/v3_socket_insertion.md)；[当前证据与边界](docs/agent/simulation/evolution/v3-insertion.md)、[r04 清单](manifests/socket_r04_20261120.json)。这些尺寸不是独立实测结果；约 51.28 mm 台阶限位已有几何检查，弹片让位和物理插装仍未验收。r01～r03 及历史报告保留。

交接更新日期：2026-11-20。主项目为本文所在的 `omi_shapeforge` 仓库，展示名 OMI ShapeForge。ENG-001 已保存本地源码基线并复验控制层与两项 GPU smoke；后续 ENG-002～003 已定版并接入[统一合同 v1](docs/agent/interfaces/run-contract.md)，两项 smoke 和 MuJoCo 2×2 复验通过。资产名称见[版本目录](docs/asset-versions.md)，全部既有图像见[可视化目录](docs/visual-results.md)。训练未重跑。原始完整交接快照保留不变。

## 重启接续入口（本次最新）

先读[重启前完整交接](docs/chronicles/2026-11-20-restart-handoff.md)，操作按[重启后恢复教程](tutorials/restart_resume.md)。本轮已经保存当前 Blender 未保存会话为独立副本，成功后台重开，原 V3 工作文件未覆盖；记录见[重启清单](manifests/restart_handoff_20261120.json)。

持久备份：`/data/omi_runtime/baselines/restart_handoff_20261120T043105Z/`。需要恢复当前会话时打开其中 `V3-live-session.blend`；正常主编辑文件为 `/data/omi_runtime/assets/optical_module_v3/work/OM-001-V3.blend`。快照之后的新编辑需另行保存。

当前决定：**Blender／V3 为主，V2 辅助参考与对比**。ENG-001～003 已完成；下一工程项 ENG-004。最终代码提交与四库 bundle 哈希由上述目录 `delivery.json` 记录。所有提交仍在本地，未推送；本轮没有执行重启。重启后的窗口、PID 和 `/tmp` 标记不可沿用。

## 1. 接手先读

1. [AGENTS.md](AGENTS.md)：分支、资源与验证约定。
2. [当前总览](docs/current.md)：全项目当前状态的唯一摘要。
3. [最新重启交接](docs/chronicles/2026-11-20-restart-handoff.md)：工程进展、V3／V2、会话保存、恢复命令和待办；[早期完整快照](docs/chronicles/2026-11-20-workspace-handoff.md)保留迁移数据细节。
4. [能力总表](docs/capabilities.md)：已运行、未接入和未验收的区别。
5. [教程目录](tutorials/README.md)及[资源清单](manifests/README.md)：按任务定位真实命令和输入。

本文是接续工作的导航与注意事项。能力细节由领域纪传体维护，后续变化更新 current／evolution 并追加阶段记录，不回写旧报告或旧编年。

## 2. 用户目标与开发分工

目标是继续光模块感知、模型与点云配准，并在 Isaac Sim 和 MuJoCo 中建立可追溯仿真场景，逐步接入已有机械臂、夹爪和夹具资产。

主项目承载流程、配置、评估、文档及仿真脚本；同级自有 FoundationStereo／BundleSDF 仓库承载对应算法实现。`omi_proj` 提供机器人资产、资料及离线预检；本项目没有调用其硬件控制系统。

用户偏好中文交流，希望助手实际执行建模、验证和可视化。用户已正式指定 Blender 建模路线为 V3，后续以 Blender／V3 为主，V2 只作辅助参考与对比；工作文件和旧名映射见[资产版本](docs/asset-versions.md)。HTML 操作采用左键旋转、Shift+左键平移和滚轮缩放，不要求鼠标中键；新四模型对照的视角、部件选择及操作已做浏览器检查，并核对实际桌面显示；旧包内 HTML 页面仍未逐一验收。

## 3. Git 状态与可恢复基线

- `main` 继续保持空树；本地 `dev` 已整合原仿真、知识库及本轮源码基线，后续从 `dev` 建功能分支。
- ShapeForge 的最新运行代码验证时点为 `b3aa2fb`；其后已完成显示修复、原生查看、V3 指定及交接文档。交接前功能基线为 `9e14cbe`，准确最终交付 HEAD 用 `git rev-parse dev` 或本轮备份 delivery.json 查看。三项实跑证据见[最终工作流清单](manifests/workflow_final_validation_20261120.json)，早期 `eb8da42` 仅是 ENG-001 时点。
- FoundationStereo 的适配与入口保存为 `e46fa7098730674bfc9f96047b4d2ffe9a87e1b4`；BundleSDF 保存为 `b1a55878264e8c28841507bb578835c94a63d475`，均位于各自 `feature/local-runtime-baseline`。
- omi_proj 保持 `963a7c29f8e39bff59ba4eb285693976b224961e`，没有修改其代码。
- 原有未提交文件已保存为本地提交，包含 PROMPTS 原文；四个仓库另有 Git bundle，且已独立克隆核对。整理前补丁、原文件与 Git 历史保存在外部备份中。
- 尚未 push，不能假定远端 dev／后端默认分支包含本轮提交。首次恢复使用[基线清单](manifests/source_baseline_20261120.json)与 bundle，再配置外部环境和资源。

当前状态以 `git status --short --branch` 为准；保留后续用户工作树，不执行 reset／clean。旧交接中的“未提交”描述属于当时快照，不能继续用作当前结论。

## 4. 数据已经齐全恢复，不要再按“缺包”处理

目前 00–05 加 OMI／portable／quick 共 9 个上传包均已解压，原包实际保留在 `/data/shapeforge/storage/imports/reconstruction_2026-11-19`；`/data/nov_19_folder`是兼容入口。[原解压索引](manifests/extracted_archives.json)保留当时路径和校验结论，当前位置映射见[存储登记](manifests/storage_layout_20261123.json)。早期报告中的“未到达／未解压”仅代表当时状态。

```text
/data/omi_runtime/
  baselines/reconstruction_20261119/
    workspace/BundleSDF_trial/                 旧自定义工程、模型及 02 data
    workspace/FoundationStereo/               旧工程与 03 DATA
    environment_runtime/foundation_stereo/     04 旧 Conda 环境，未重定位
  baselines/omi_transfer_20261120_004618/
    omi_proj/local/                           机器人资产、示范和权重
  inputs/optical_packages_20261120_001316/
    optical_module_portable_20261119/
    optical_module_quick/
  envs/                                       当前使用的独立环境
  assets/                                     导出的光模块及单模块／方阵场景
  tools/                                      Blender 等工具
  runs/                                       日志、报告、渲染图与新实验输出
```

当前工作区的 `omi_proj/local` 指向上述 OMI 基线 local。恢复内容没有覆盖现有 Git 源码。重建基线与当前算法开发目录独立；历史 JSON 的旧机器来源路径保留，实际运行应使用显式输入参数或受控路径映射。

02 的 2,121 个成员、03 的 397 个成员、04 的 61,829 个条目全部恢复校验通过。04 的 1,154 个内部链接无缺失目标，03 补齐一个大小写别名。检查时 `/data` 剩余约 55 GiB，未删除源包。

## 5. 环境与最小接续检查

以下相对 envs 目录均位于 `/data/omi_runtime`：

| 用途 | 环境／版本 |
| --- | --- |
| 主调度器 | 仓库 .venv；Python 3.11.15；标准库控制层 |
| 双目／BundleSDF 组件 | envs/foundation_stereo、envs/bundlesdf；Python 3.11、Torch 2.6.0+cu124 |
| 光模块仿真 | envs/simulation；Python 3.11、MuJoCo 3.3.7、OpenUSD 26.11 |
| 机械臂资产预检 | envs/omi_assets；Python 3.12、MuJoCo 3.15.0、NumPy 2.5.3 |
| Blender | 4.5.16 LTS；已建立 blender 命令和应用菜单入口 |
| Isaac | 5.1.0 自带 python.sh 验证过；另装有 6.0.1，但未用其验收场景 |

**04 不等于当前开发环境。** 它是 Python 3.11.18／Torch 2.7.1+cu128 的历史快照，尚未执行 conda-unpack、激活或运行兼容性验收；继续使用当前 envs 不以适配旧环境为前置条件。

从仓库根目录先做只读检查：

```bash
git status --short --branch
.venv/bin/omi-shapeforge --help
.venv/bin/omi-shapeforge doctor
```

doctor 仅检查路径、解释器、权重／nvcc 是否存在并显示 Git 信息，不检查全部动态库、GPU 运算、仿真或机器人。主配置为 `configs/workspace.toml`，机器覆盖可用忽略的 local.toml。真正运行前按[教程](tutorials/README.md)选择对应环境和新输出目录。

## 6. 已有本机验证与关键限制

- 官方双目样例：960×540、32 次迭代，470,018 点；两进程视差和深度一致。不是光模块原始录制的重算。
- BundleSDF 组件：C++、CUDA 采样／编码与梯度、PyTorch3D、Kaolin、Warp、真实 LoFTR 检查通过；LoFTR 2,893 组匹配。不是完整视频在线跟踪／重建验收。
- 已确认 ROI 配准：10 万点场景，486 原始点／472 过滤点／121 检查点；检查残差中位数约 0.148 mm、P90 约 0.731 mm，全部原始点 P90 约 2.771 mm。残差不是实物位姿精度，方向仍有近似多解；旧误选目标已撤回。
- V2 回放：64 个源文件及冻结几何检查通过，粗／细差约 1.83e-9／1.77e-9 m。回放参数和保存位移，不是从新传感器重新估计。
- Blender：四份模型后台重开、内嵌资源／单位检查，一张后台渲染及 15 部件导出通过；V3 已在本机 GUI 实际显示，并保存重启会话副本。完整 photo／metric／groove 生成和 59 帧尺寸重估未在本机复跑。
- 光模块仿真：单模块及 2×2 在 MuJoCo 完成 EGL 渲染与 240 步落台，Isaac 5.1 完成对应 PhysX CPU 测试。碰撞是盒，20 g／摩擦 0.6 为假设，拉手刚性附着，轨道为示意；不证明精细夹持／插接。
- 机器人：双臂 MJCF 编译、A 臂 preflight 和静态渲染通过；两份完整 URDF 各有 27 links／26 joints，含四个滑动指关节，网格引用齐全。旧 MJCF 的灵巧手／刀具不等于当前夹爪配置；指关节 velocity=0、TCP、轴、惯量和限位仍需核对。
- OMI 数据：9 个正常原始回合、41 片段、1499 样本，原划分 1174／325；动作是 6 维末端增量且 no_gripper=true，不可直接当 7 维关节／夹爪动作标签。BC6148 用过全部 1499 条，旧验证划分不是该权重的独立测试。

机器人尚未接入光模块场景或 Isaac 机器人任务；本机未运行完整 OMI 数据／Actor 验证与重新训练。Isaac RTX／GUI、真实精度及真机动作均未验收；Blender 实际显示和新对照查看器交互已有独立验证。

主要证据：[初始化](manifests/initial_validation.json)、[便携配准](manifests/portable_validation.json)、[仿真](manifests/simulation_validation.json)、[旧工程／OMI／V2](manifests/transfer_validation.json)、[02 恢复](manifests/restored_data02.json)、[03／04](manifests/data03_04_validation.json)。旧报告保持原样，当前资源状态由最终解压索引和资源清单说明。

## 7. 建议接续顺序

1. 先读源码基线和对应能力文档，检查实际工作树；数据已到齐，不必继续等待 03／04 或重复整包解压。
2. ENG-001～003 已完成；下一项 ENG-004 推进 CPU 与合同自动检查，并关联 GPU／仿真证据。
3. 复现路线：从一个固定真实双目样本开始，核对输出和坐标，再推进局部重建、59 帧尺寸或完整跟踪，各项单独验收。
4. 仿真路线：先选择准确机器人／工具配置，核对关节与 TCP，再组合光模块和真实夹具，重建能保留槽接触的碰撞体；不能直接把示意轨道和单盒当最终任务场景。
5. Isaac GUI／RTX、完整 Blender 生成、OMI Actor／数据合同及训练是独立待办；Blender V3 以后按新修订保存、导出与验证。

所有新实验使用新目录；保留 V1／V2／V2.1 和原始数据。用户已授权将 Blender 模型线命名为 V3；这是资产版本决定，不升级全项目包版本，也不改写历史试验编号。没有连接硬件或执行真实控制的授权记录，不从其他仓库顺手启动控制脚本。本轮基线已本地提交，尚未推送。
