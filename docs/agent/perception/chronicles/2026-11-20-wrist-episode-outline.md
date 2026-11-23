# 2026-11-20：腕部视频与真实 episode 轮廓初检

用户提供 6 秒腕部视频和 1920×1080 OpenCV fisheye 内参，要求查看光模块轮廓；首帧已做人工初始化的可见轮廓预览。该阶段没有估计三维模型位姿，也没有生成完整三维投影视频。随后用户要求改看 omi_proj 的真实 episode，寻找更大的俯仰变化，并关注对应六维坐标。

本机可用源为 `omi_proj/local/rl_episodes/spacepilot_response_20261017_213359/periodic_episodes/`。扫描得到 9 个有观测的回合，按原格式读取最新历史槽位并校验单帧内容哈希；训练片段数／有效动作样本数与这里的原始观测数不混用。

优先选择 **8083942d4ead4367aa334198e7a9890f**，记录的末端固定轴 XYZ Euler 俯仰跨度约 15.25°；另取 **19c7887c59f34dcb9d53bd1d8bc9b950** 作对照。各取四个关键帧，生成半自动轮廓预览：固定人工 ROI／种子先验、逐图 GrabCut 主体分割、HSV 绿色拉手区域及保守上边界筛选。

- [8 帧轮廓与记录末端位姿](/data/omi_runtime/runs/episode_wrist_outline_20261120T102752Z/selected_episode_outlines_v2.png)
- [9 回合概览](/data/omi_runtime/runs/episode_wrist_outline_20261120T102752Z/episode_overview.jpg)
- [原始记录对应的末端六维 CSV](/data/omi_runtime/runs/episode_wrist_outline_20261120T102752Z/recorded_eef_poses.csv)
- [结果与限制](/data/omi_runtime/runs/episode_wrist_outline_20261120T102752Z/review.json)

**边界：**保存的腕部图是 128×128 预裁剪 ROI，孔口遮挡会改变可见前端，拉手可能被图像边界裁断；轮廓在相似金属／孔口区域存在明显不确定性，不能作为标注真值或可靠的 6D 输出。

图中的 XYZ／RPY 来自 `observation_status.eef_xyz_xyzw`，并与最新观测帧 `state[7:]` 核对一致。源合同要求 `base_link`、四元数 xyzw；CSV 平移换算为 mm，RPY 使用固定轴 XYZ Euler 度。它是**记录的机器人末端位姿，不是光模块相对腕部相机的位姿**，也不证明其为独立测得的真实 TCP。图像和末端的原 header 时间差已另存。

腕部相机和被夹持模块共同运动，末端在 base_link 中俯仰变化并不意味着模块在相机中等量俯仰。必须区分夹持变化、遮挡变化与物体相对相机运动。

采集代码为 ROI `(0.500, 0.704, 0.36)`、nearest-rint-linspace 到 128。若源图确为 1920×1080，裁剪框为 `(766, 566, 389, 389)`；已保存条件映射，**尚未确认新提供的内参版本和该分辨率适用于 10 月回合**。相机系模块位姿字段暂为空，等待这一确认以及足够的 2D–3D 对应／可见性约束；不能把末端位姿替代物体位姿。

原 episode、原视频、原内参未修改；未加载训练权重、连接 ROS 或控制硬件。当前轮廓拼图已在桌面图片查看器打开。
