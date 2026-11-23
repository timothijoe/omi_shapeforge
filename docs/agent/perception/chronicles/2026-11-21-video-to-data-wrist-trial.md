# 2026-11-21：实际运行 Video to Data 腕部试验

用户要求运行此前讨论的 NVIDIA `video_to_data`，查看真实结果。此前只有代码评估；本记录为本机实际推理，不把两者混为一谈。

## 运行范围与输入

- 项目 `/data/omi_runtime/external/video_to_data`，固定提交 `1e862a8984bf28474c324c1b49db99b2da7ece80`。运行其 SAM2、MoGe、FoundationPose Python 模块；未运行人体动作、机器人重定向或 RL 阶段。
- 输入 `/home/linux/Downloads/img/腕部相机_插口接近_6秒.mp4`，原始 1920×1080、180 帧，按每 3 帧采样并补末帧，得到 61 帧。相对运动小，不能代表不同 episode 大俯仰泛化。
- 使用用户提供的 `wrist_intrinsics_1920x1080.json`（opencv_fisheye）。构造以原图 `(970,750)` 射线为光轴的 960×960 虚拟针孔视图，fx=fy=900、cx=cy=479.5；记录虚拟相机旋转。最终真实 V3 mesh 按该变换逆转换，重新投影回原始鱼眼图。
- 使用当前 V3 的 9 个刚性主体部件，保持米制尺寸，排除绿色拉环／挂件、拉手座、简化内部和开口折边。没有用缩放模型来迁就预测深度。
- **尚无头部点云到腕部的已验证外参**，所以此轮初值用既有单图 PnP 粗解，不是 HTML 点云姿态转移。不能声称完成了头部点云初始化的整条链。

## 环境与兼容处理

RTX 4090 24 GB、驱动 550.107.02。Docker socket 无访问权限（提升请求后同样失败）；改用 `/data/omi_runtime/envs/video_to_data_trial` 原生环境，读取既有 bundlesdf 环境的 Torch 2.6.0+cu124 和几何依赖，新依赖仅安装在试验环境。没有升级系统驱动或修改既有环境。

复用 SAM2.1 small 和 NVLabs FoundationPose 官方权重；下载 MoGe `Ruicheng/moge-2-vitl-normal` 的 `model.pt`（1323815904 bytes），校验 SHA256 `280741fd09bc3f403ccff9967784c2a391b52d2c0742ae3efdb21d9f90cc1a01`。MoGe 源码固定在 V2D 指定提交 `925b8ed835a7a9cdb7578ba15c658a0afc969030`。nvdiffrast 和 V2D 内的 mycpp 在本机编译，FoundationPose 使用项目提供的 `nvlabs_pytorch` 后端。

首次 MoGe 推理在保存 uint16 深度时因 Pillow 13 的 mode 行为失败。试验环境单独固定 Pillow 11.3.0 后成功，算法源码没有因此修改。SAM2 可选 CUDA 孔洞填充扩展不可用，神经网络推理与传播正常完成；该限制保留在报告中。

注意 V2D 的 PNG 深度编码是 `65535/(depth_m+1)`，通过其 `DepthImage` 解码，**不是毫米深度 PNG，不能简单除以 1000**。

## 实际执行的三条分支

1. **V2D SAM2**：首帧 2 个前景点、4 个背景点为人工视图提示，随后在 61 帧传播。首帧金属主体被分出，绿色挂件和两侧夹爪未被纳入主体。没有把人工 mask 当作网络输出。
2. **V2D MoGe＋FoundationPose**：61 帧生成单目预测深度。用真实固定 mesh、SAM2 mask 和相机 K，分别测试从既有粗解精修及全局注册，之后各在 7 个代表帧进行跟踪。两条分支均实际执行完，无运行异常，但目视 mesh 明显偏移，未通过贴合检查。首帧主体预测深度中位数约 0.660 m，与已有几何初值约 0.19 m 明显不一致；无实测深度真值，不能把差值直接当传感器误差。
3. **V2D SAM2＋自编像素精修**：这是额外的本地适配层，**不是 FoundationPose 的成功结果，也不是 V2D 原生功能**。采用 nvdiffrast 可微轮廓、固定 mesh、既有初始位姿，在六维小范围内优化投影掩码与 SAM2 掩码的误差，加入弱初值惩罚。每个旋转增量分量限制约 ±11.5°、平移分量 ±6/6/15 mm，220 次 Adam 迭代；61 帧各自从同一初值优化，没有用时序平滑隐藏失败。

## 结果与边界

| 分支 | 帧数 | 与 SAM2 掩码的 IoU 均值 |
| --- | ---: | ---: |
| 初始 mesh | 61 | 0.657 |
| SAM2＋自编像素精修 | 61 | 0.914 |
| V2D FoundationPose 从初值精修＋预测深度 | 7 | 0.106 |
| V2D FoundationPose 全局注册＋预测深度 | 7 | 0.072 |

像素精修 IoU 范围 0.871–0.953，优化本身中位耗时约 0.815 s/帧（不含完整 IO、分割和显示），不能据此宣称实时系统。IoU 是优化所用 SAM2 掩码上的**拟合指标**，不是独立分割准确率，更不是实际六维位姿精度。没有真实位姿 GT，未证明毫米级距离、俯仰或插接精度。

目视检查首帧及代表帧对比：像素精修后的主体边界明显更贴近真实模块；直接 V2D＋预测深度结果存在严重错位／投影过小。保留失败分支。结论支持继续使用“可靠几何初值＋图像主体约束”，但当前单目预测深度不能直接替代可靠 RGB-D；下一步需接上外参和更丰富的跨 episode 视角验证。

## 产物与复现

目录：`/data/omi_runtime/runs/v2d_wrist_trial_20261121/`。

- `first_frame_comparison.png`：SAM2、原初值 mesh、直接 V2D 失败结果、像素精修四列对比；已打开桌面图片查看器。
- `keyframes_comparison.png`：原视频 0、90、179 帧对比。
- `foundationpose_failure_comparison.png`：两种官方位姿分支失败对照。
- `comparison_h264.mp4`：已验证可解码 61 帧的 H.264 视频（1080×640）；`comparison.mp4` 为原始编码版。内容为 61 帧 SAM2／初始 mesh／像素精修对比。
- `pixel_poses.csv`：精修后原始腕部相机坐标下平移 mm、旋转向量 rad 及掩码拟合指标。
- `foundationpose_results.json`、`pixel_refinement_results.json`、`pixel_refinement_all_frames.json`：完整候选变换和实际运行结果。
- `summary.json`、`inputs.json`、`provenance.json`、`geometry_validation.json`：范围、内参映射、权重与版本、验证边界。
- `sam2.log`、`moge_first.log`、`moge_video.log`、`foundationpose_trial.log`：包含首次兼容问题和成功运行记录。

本项目脚本：`prepare_v2d_wrist_trial.py` 准备校正输入与初值；V2D `v2d.sam2.lib.video_to_masks` 使用 `CONFIG_FILE=configs/sam2.1/sam2.1_hiera_s.yaml`、`CHECKPOINT_FILE=sam2.1_hiera_small.pt`；`v2d.moge.lib.video_to_depth` 使用已知虚拟 K 提供水平 FOV 先验；`run_v2d_pose_trial.py` 调用官方 tracker 两种入口；`refine_v2d_silhouette.py --all-frames` 执行自编适配；`render_v2d_wrist_results.py` 回投原鱼眼图。

所有这些实验脚本位于 `scripts/perception/`。初始数据、模型尺寸和此前结果保留；未连接机器人或运行 RL。
