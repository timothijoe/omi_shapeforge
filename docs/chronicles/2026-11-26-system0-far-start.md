# 2026-11-26：初始前后间距再增加2～3 cm

用户在腕部视角视频后指出起点仍太近。本轮将夹爪及模块沿插接轴再后退20／30 mm，相对于原名义10 mm起点变为30／40 mm；插口保持+0.5／+0.5 mm、yaw=0，保留俯仰及组合偏差。没有改镜头来替代真实距离变化。

原初始化直接求IK被每控制步0.1 rad关节连续性限幅拒绝，改为离线数值continuation更新种子，再一次性放置初态；所有原厂限位继续有效，物理准备动作0。六个目标离线核验约0.003 mm误差后，实际worker完成左右同初态、无初始穿模的测试。

| 条件 | 实际初始间隙 | 比10 mm版增加 | 路径组 | 无路径组 |
| --- | --- | --- | --- | --- |
| 正对 | 30.002 mm | 20.000 mm | 成功／457步 | 成功／462步 |
| 俯仰+2° | 30.262 mm | 20.000 mm | 成功／500步 | entrance_not_qualified／227步 |
| 横移+2 mm／抬高+1 mm／俯仰与偏航+2° | 30.319 mm | 20.000 mm | 成功／507步 | entrance_not_qualified／235步 |
| 正对 | 40.002 mm | 30.000 mm | 成功／511步 | 成功／516步 |
| 俯仰+2° | 40.262 mm | 30.000 mm | 成功／557步 | entrance_not_qualified／275步 |
| 横移+2 mm／抬高+1 mm／俯仰与偏航+2° | 40.319 mm | 30.000 mm | 成功／568步 | entrance_not_qualified／280步 |

路径6/6、无路径2/6，teacher requests全部0。只是同一对冻结模型、六个单次条件，不重训，也不更改原成功判据。源模型、任务目标和左右源码／初态核验通过。相关29项测试通过；轻量29通过、70跳过。

- [能力与完整初态实验](../agent/simulation/evolution/system0-initial-pose-robustness.md)
- 评估：`/data/shapeforge/runtime/runs/s0_far_start_20261126/summary.json`
- 初始化求解说明：同根`initialization_adjustment.json`、`offline_ik_audit.json`
- 展示：`/data/shapeforge/runtime/runs/s0_far_wrist_videos_20261126/`
- 初态对照：`initial_gap_comparison.jpg`及对应JSON，使用原外部相机和原俯仰角，实测10.26／30.26／40.26 mm。

30／40 mm腕部原速视频已完成，沿用同一物理执行记录；完整腕图的小窗保留原视野但降低上下文像素量，高清局部仍从高分辨率面采样。旧数据、视频和资产均保留。

最终交付：30 mm版55.6秒、40 mm版61.3秒，带章节合集116.9秒，全部解码通过。1563帧腕部状态的安装关系、原始鱼眼投影和固定ROI均核验通过；初态对照的外部相机参数与两个影片相同。`/home/linux/Downloads/Farther_Starts_Demos_20261126/Farther_Starts_30_40mm.mp4`。
