# 光模块候选特征与鱼眼跟踪原型

当前展示的是特征跟踪与遮挡状态，不是已认证的精确六维插入定位。默认仅更新相机 X/Y，深度与角度来自给定先验。实验六维分支因绑定不确定和漂移尚未采用。

## 查看现有结果

根目录：`/data/omi_runtime/runs/mesh_feature_tracking_20261121/feature_preview/`。

- `feature_atlas_review.png`：鱼眼特征与候选模型表面对应。
- `occlusion_mechanism_review.png`：前端遮挡、全遮挡、重现的状态检查。
- `real_episode_review.png`：128×128 实际 episode 的先验辅助和丢失情况。
- `full_fisheye_tracking_h264.mp4`、`controlled_occlusion_tracking_h264.mp4`：可播放对比视频。
- 各 case 的 `feature_atlas.json`、`reference_features.npz`、`tracking.json`：候选特征包和逐帧输出。

标贴外观对照在上一级 `label_identity_review.png`；这项人工选四角的外观比较没有被用于当前跟踪器求解位姿。

## 复跑已准备的输入

在仓库目录执行，指定新的结果子目录，拒绝覆盖已有跟踪结果：

```bash
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 \
  /data/omi_runtime/envs/video_to_data_trial/bin/python \
  scripts/perception/run_mesh_feature_tracking.py \
  --run /data/omi_runtime/runs/mesh_feature_tracking_20261121 \
  --track --controlled-occlusion --result-subdir review_new
```

`--prepare --segment-episodes` 用于新的 run 根目录，会从原视频和三段已导出的 episode 建立输入并调用现有 V2D SAM2 small；不要对现有根目录重复 prepare。源视频、内参、模型和 episode 路径目前在脚本中显式固定，适用范围仅为这批试验数据。

跟踪部分用 OpenCV/NumPy/SciPy/Open3D；SAM2 分割在 GPU 环境预处理。记录的跟踪耗时不包含完整在线采集、分割、IO 和渲染，不能解释为端到端帧率。

## 输入与输出约定

初始化需要固定单位为米的刚体 `T_camera_from_model`、正确的图像像素域及面向先验。原始鱼眼局部图使用 K/D 和裁剪原点；episode 使用已确认的采样表映回原图，不把插值放大当作增加了分辨率。

逐帧需要检查：

- `state`、`measurement_update`、`measurement_dof_count`。
- `pose_update_mode`：二维校正时为 `xy_only_fixed_depth_rotation`。
- `T_camera_from_model`：丢失时为空，其余状态也必须结合更新来源读取。
- `prediction_for_display_only`：仅供画出最后的几何假设，不能当新观测。
- `physical_pose_accuracy_validated=false`：本批数据没有独立位姿真值。

`--experimental-se3` 会启用近初值六维求解，用于诊断；当前数据已有漂移反例，不作为可用精密控制结果。

遮挡测试通过不代表真实物体的任何遮挡程度都可定位。可见特征不足、头部也被遮挡、参考外观发生变化、夹持滑移或绑定错误时，应报告不确定/丢失，而不是固定输出一个看似稳定的位姿。
