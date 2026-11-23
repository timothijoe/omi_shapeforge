# 2026-11-21：真实视觉位姿与结构特征开发交接

按用户要求整理本轮记录。**当前做成的是不使用额外 marker 的结构特征提取、归属过滤和位姿候选原型；尚未做成可靠的精确六维位姿、真实插入深度或到位判断。**

本页针对真实感知。仿真资产和 BC/RL 的并行结果看[全局交接](2026-11-21-current-progress-handoff.md)，不能用仿真策略成功证明真实视觉定位准确。本次仅整理文档、核对证据和保存快照，不重新训练或修改模型。

## 1. 用户目标和必须保留的决定

- 操作过程中即使模块部分插入/被遮挡，也希望借助 mesh、视觉结构和先验估计**模块相对插口**的局部位姿，用于对准、插入进度及后续结果判断。
- 正反面、朝上/朝前和粗位姿可以作为先验。重点是连续位置、角度以及台阶、端部的精细对齐，不把解决翻面当作主要成果。
- **黑白标贴是额外添加的，明确不使用。不要再询问标贴是否同一块或是否移动，也不要恢复其角点/纹理对应作为主线。**历史试验保留，不作为当前观测。
- 绿色挂件不用于刚体配准；刚性黑色端部壳体与它不同，可以作为结构候选。
- 使用模块本身的壳体、台阶、缺口和刚性边缘；不可见、被遮挡或对应不明的结构不强行匹配。
- 蓝色观测点必须先检查属于模块还是夹爪。归属不清就剔除，不能为凑足特征数保留可疑线。
- 保持现有 V3 尺寸；低像素残差、IoU 提升、数值收敛和稳定轨迹都不等于真实位姿精度。
- 用户偏好中文解释和直接打开结果，说明具体观察到了什么，而不是笼统说“跑通”。

## 2. 最新主线与结果

当前目录：`/data/omi_runtime/runs/structural_ownership_20261121/`。

先屏蔽 marker，再用 SAM2 分开金属模块、黑色端部、左右夹爪。首帧有明确前景/负点提示，随后传播；不是无提示全图识别。结构检测要求模块内部支持、夹爪及绿色附件排除，缺少归属 mask 时拒绝继续。通过检查的二维线与 V3 三维结构线对应，使用鱼眼标定求近先验刚体位姿候选。

| 项目 | 当前事实 |
| --- | --- |
| 输入 | 原 6 秒鱼眼视频，61 个采样帧，使用原始分辨率坐标 |
| 模型候选 | 杆身左右、头部左右、黑色端壳下沿，共五组 |
| 实际参与 | 杆身左右、头部左侧、黑色端壳下沿，共四组 |
| 被剔除 | `head_right`：全部61帧停用，归属/支持不足 |
| 首末帧旧候选 | 右侧头部各35个点，均未通过新归属检查 |
| marker 检查 | 首/中/末帧分别替换黑/白/噪声，9项在相同先验下不变 |
| 夹爪检查 | 固定语义mask，加入强夹爪纹理不改变接受的模块点 |
| 位姿结果 | 61个数值候选，**不是61帧识别正确** |
| 尚未验收 | 精确六维、可靠遮挡跟踪、两端相对深度及到位判断 |

分割本身不是物理真值。不要把“通过过滤”写成“所有点都已证实正确”，也不要把被排除的整组点都说成已证实位于夹爪内部；接触边界可存在归属不确定。

- [最新修正图](/data/omi_runtime/runs/structural_ownership_20261121/ownership_correction.png)：左红是旧候选，中间是分割辅助，右蓝是接受点。
- [逐帧结果](/data/omi_runtime/runs/structural_ownership_20261121/filtered/results.json)、[汇总](/data/omi_runtime/runs/structural_ownership_20261121/filtered/summary.json)、[验证](/data/omi_runtime/runs/structural_ownership_20261121/validation.json)。
- [当前来源清单](../../manifests/structural_edge_ownership_20261121.json)和[详细归属修正记录](../agent/perception/chronicles/2026-11-21-structural-edge-ownership.md)。

## 3. 模型、数据和坐标

| 内容 | 路径或范围 |
| --- | --- |
| 主光模块 | `/data/omi_runtime/assets/optical_module_v3/work/OM-001-V3.blend`；V3为主，V2仅参考 |
| 视觉插座参考 | OS-001/r04，局部尺寸仍未独立计量认证；不等于并行的新 SIM 接触资产 |
| 模块求值网格 | `/data/omi_runtime/runs/v3_socket_insertion_20261120T073119Z/inputs/` |
| 插座求值网格 | `/data/omi_runtime/runs/v3_socket_r04_20261120T082303Z/inputs/` |
| 网格单位 | 原求值数组为 mm；估计算法转为 m；不能混用 |
| 鱼眼视频 | `/home/linux/Downloads/img/腕部相机_插口接近_6秒.mp4`，1920×1080、180帧 |
| 腕部内参 | `/home/linux/Downloads/img/wrist_intrinsics_1920x1080.json`，OpenCV fisheye K/D |
| episode | 恢复的9个原始回合，已导出1682张不同腕部图 |
| episode 裁剪 | `image[566:955,766:1155]`，389×389，再以 `rint(linspace(0,388,128))` 采样到128×128 |
| 双目扫描 | `/data/omi_runtime/baselines/reconstruction_20261119/workspace/BundleSDF_trial/data/optical_close_fs_20261118_v1/`，59组完整抽取样本 |

该双目段记录左IR 900、右IR 899、RGB 895、native depth 900帧；本轮新推理测试11组，不是全部重建。episode 内参身份沿用用户“应该相同”的说明，未独立重标定。头部/双目到腕部的外参没有完成验证，不能把不同相机的位姿直接混用。

## 4. 历史结果与纠正

| 试验 | 有效进展 | 不代表 |
| --- | --- | --- |
| HTML 点云＋V3/插座 | 条件ROI配准、mesh叠加及正反面纠正 | 全场景识别、唯一朝向、物理精度 |
| 多 episode 回投影 | 9回合/72张代表图，发现错配插座与遮挡拒绝 | 低PnP残差就是正确识别 |
| Video to Data | SAM2、MoGe、FoundationPose实际运行；预测深度下位姿错位 | FoundationPose在当前输入上已成功 |
| 轮廓像素优化 | mask拟合有所改善 | 已接头部点云初值或达到精确六维 |
| 新双目＋像素 | 11组新深度/点云初值，联合约束试验 | 已通过真实精度；用户随后否定质量 |
| 局部结构复核 | 发现0885约75px跨帧错位，整体指标未排除错面 | 原“改善帧”均正确；marker路线现已停用 |
| 图像特征跟踪 | 候选记录、二维跟踪、丢失/重现；六维漂移保留 | 冻结深度/旋转后的稳定性就是六维准确 |
| 初版结构线 | 61帧五组候选、marker替换检查 | 右侧候选属于模块；最新已纠正归属 |

历史运行都在 `/data/omi_runtime/runs/`，关键目录：

- `pointcloud_v3_overlay_20261121_face_corrected`、`socket_module_cloud_20261121`：点云叠加。
- `episode_v3_mesh_batch_20261120T163456Z/batch`：episode导出和失败图册。
- `v2d_wrist_trial_20261121`：V2D实测及失败分支。
- `stereo_pixel_pose_20261121`：新双目与联合精修，已标记用户未验收。
- `stereo_pose_structure_audit_20261121`：局部结构反例。
- `stereo_fine_pose_prior_20261121`、`_r02`、`_r03`：固定面向细化，未达标。
- `mesh_feature_tracking_20261121`：特征/遮挡/低分辨率失败；其中 `feature_preview/` 当时默认仅二维，现不是主位姿路线。
- `local_insertion_geometry_20261121`：两端位姿到局部偏差/名义深度的纯几何换算，仅有合成坐标检查。
- `structural_features_20261121/wrist_lines`：未做实体归属过滤的旧结果。
- **`structural_ownership_20261121`：最新主线。**

`final`、`passed` 和低残差必须结合具体验证范围解释。历史详见[感知编年索引](../agent/perception/chronicles/README.md)。

## 5. 复现入口

核心源码在 `scripts/perception/`：

- `prepare_structural_ownership.py`：屏蔽marker后分割模块/黑端/夹爪。
- `structural_edge_pose.py`：模型结构线、归属过滤、鱼眼拟合、候选保护。
- `run_structural_edge_trial.py`：整段运行及反事实/遮挡检查；**必需 `--ownership`**。

复用已有mask重跑，必须使用新输出目录：

```bash
cd /home/linux/omi_folder/omi_shapeforge
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 \
  /data/omi_runtime/envs/foundation_stereo/bin/python \
  scripts/perception/run_structural_edge_trial.py \
  --ownership /data/omi_runtime/runs/structural_ownership_20261121 \
  --output /data/omi_runtime/runs/structural_ownership_review_NEW
```

重建mask（需已有SAM2/GPU环境），也要新目录：

```bash
/data/omi_runtime/envs/video_to_data_trial/bin/python \
  scripts/perception/prepare_structural_ownership.py \
  --source-run /data/omi_runtime/runs/structural_features_20261121/wrist_lines \
  --output /data/omi_runtime/runs/structural_ownership_masks_NEW \
  --weights /data/omi_runtime/baselines/reconstruction_20261119/workspace/BundleSDF_trial/runtime/sam2_source/checkpoints
```

`NEW` 是示例目录名，存在时换名。视频、搜索区域和首帧提示针对这套腕部场景固定，不是通用输入接口。无需重新下载模型或先解决Docker权限。

```bash
eog --new-instance /data/omi_runtime/runs/structural_ownership_20261121/ownership_correction.png
```

GUI PID不持久，恢复时重新打开。早期HTML曾在用户原Chrome中空白；已有独立软件渲染窗口的验证记录，图片查看器不依赖WebGL。

## 6. 下一步

1. 先复核四组保留边缘的实体归属与多帧稳定性，保留被拒点/理由，不让夹爪重新混入。
2. 核对真实端壳台阶/缺口与具体mesh边的对应，不能只因为“都有横线”就认定同一结构。
3. 增加部分插入时仍外露的独立刚性约束；隐藏结构只作模型预测，不作新测量。
4. 两端在同一相机/时间下都有可信位姿后，再用 `interaction_geometry.py` 计算相对偏移、角度和名义深度；不自动等于机械/电气到位。
5. 用未参与拟合的结构与独立参考评估。用户未给毫米/角度阈值，不以此阻止基础核查，也不擅自宣布达标。

## 7. 工作树与持久快照

记录时 ShapeForge 分支为 `feature/dual-camera-training`，HEAD `66ff11720e5dc4327041d709b661dec73c83f605`，含本轮感知及并行仿真/训练的未提交修改。FoundationStereo 为 `feature/local-runtime-baseline`，HEAD `e46fa7098730674bfc9f96047b4d2ffe9a87e1b4`，新运行脚本也仍在工作树。**本次没有提交、推送或切换分支。**恢复时以实际 `git status` 为准，保留并行工作。

感知范围持久快照：`/data/omi_runtime/baselines/perception_handoff_20261121T092928Z/`。

包含当前仓库感知源码、相关文档/清单、FoundationStereo新入口、最新主要证据与哈希。`previous_docs/` 保存整理前文档，Git状态分别保存于 `git_state_before.json`/`git_state_after.json`，`delivery.json` 为索引。

原始录制、模型、环境及全部历史运行目录仍使用上述外部路径，本次不重复复制。该快照不代表全部并行仿真工作也已由本次备份；旧11月20日Git bundle不包含本轮未提交修改。
