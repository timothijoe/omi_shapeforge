# 2026-11-26：清晰腕部相机视角

用户在初始偏移／倾斜demo后要求能看清腕部图像。选用已完成的初始俯仰+2°案例（训练种子341000、测试360004），复用同一对策略的实际关节状态和reset第0步。路径组387步成功，无路径组108步后接触保护终止；本次不重新执行策略，不新增成功率结果。

相机保持冻结transfer的wrist_rgb安装变换与原始OpenCV鱼眼K/D，跟随夹爪，不追踪或重新瞄准插口。主视图使用原1920×1080像素域的固定ROI `[740,550,1220,838]`，直接从高密度射线重投影到900×540；完整腕图在下方显示该ROI边框，另配同状态外部近景。原训练资产与夹持关系保留。

局部所需cubemap面为1536×1536，外围上下文面为256×256，完整鱼眼输出仍覆盖1920×1080像素域。清晰局部与上下文采用同一个相机模型；这不是均匀采样的原始传感器录像，也不声称是actor原始输入像素。本轮actor使用GT几何条件和历史，显示用途不会增加模型输入。

按每个控制步捕获，10 fps、仿真时间原速；真实初态先停留3秒，结束后停留2.5秒，较早终止的一侧保持末帧。此前3倍速外部视角视频保留。

运行根：`/data/shapeforge/runtime/runs/s0_wrist_view_20261126/`。选择与状态来源见`selection.json`，逐帧相机外参见`capture/<mode>/<step>/wrist_pose.json`。`source_snapshot/`及`source_hashes.json`保存当前实现。完整回放已完成，共44.3秒，497帧腕部状态已核对；最终验证与交付由`delivery_manifest.json`记录。交付：`/home/linux/Downloads/Wrist_View_Demo_20261126/Wrist_View_Pitch_Demo.mp4`。

为降低外围小窗渲染开销，首次全部六面1536分辨率的部分捕获主动停止，原输出以`full_faces_`前缀保留。新版本主放大区域仍保持1536来源面，未改变轨迹、相机位姿、投影或模型；`render_revision.json`记录调整。该停止是本次主动渲染调整，不是策略或物理失败。

实现：`scripts/simulation/capture_path_ablation_video.py --wrist`，合成使用`compose_path_ablation_video.py --wrist-layout`，最终核查入口为`audit_wrist_policy_view.py`。源姿态／模型哈希、原始相机安装关系、固定ROI投影、全部视频解码均纳入核查。轻量98项中29通过、69跳过。

[初态实验与边界](../agent/simulation/evolution/system0-initial-pose-robustness.md)。相机参数沿用冻结仿真记录，不新增真机标定或物理准确性认证。

最终检查：相机相对TCP安装矩阵最大误差3.33e-16，相机世界位置回放误差最大0.000465 mm，原始鱼眼参数及固定ROI一致。模型／状态哈希保持，443帧视频完整解码通过。
