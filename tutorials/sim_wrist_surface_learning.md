# 查看、恢复和复现仿真腕部点云训练

> 本机迁移提示（2026-11-24）：运行资源实体已迁至 `/data/shapeforge/runtime`；本文中的 `/data/omi_runtime` 是保留的兼容入口，指向同一份内容。目录映射与恢复要求见[当前资源契约](../docs/agent/interfaces/local-resources.md)。

最新结果窗口：`http://127.0.0.1:8892`。

默认使用已认可的方案一（完整结构＋重点加密）；方案二（仅尖端与孔口）保留为备选。

顶部“表面表达方案”可切换完整规则网格／仅尖端与孔口；“逐帧查看点云”中可旋转、滚轮放大。灰色为普通表面，绿色／橙色为重点真值／预测。当前视频在`results/surface_schemes_v1/{whole_grid,focus_only}/heldout_comparison.mp4`。此次表面重采样沿用原预测位姿，未重新训练。

- “测试视频对比”：当前默认同一帧、同一裁剪／尺度，左侧只画绿色真值，右侧只画橙色预测，避免重合处遮盖。完整输入通过“原始腕部视频”链接查看。
- “逐帧查看点云”：图像和3D点云均支持并排、仅真值、仅预测与叠加；3D并排使用共同相机视角／尺度。图像叠加采用绿色空心圈／橙色点。
- 页面还有原始腕部视频、机械臂运动预览、训练曲线和失败案例。

运行根目录：`/data/omi_runtime/runs/sim_wrist_surface_20261122_r01/`。旧8890是未训练原型历史，8891是模板表征，8876是人工标注，均与本页训练结果分开。

## 关键文件

| 文件／目录 | 用途 |
| --- | --- |
| `data/episodes/*/wrist.mp4` | 256段原始仿真腕部视频及对应JPEG |
| `data/records.jsonl` | 每帧仿真特权位姿／关节／图像哈希；不作为网络输入 |
| `data/label_audit.json` | 划分、图像、FK及mesh坐标核查 |
| `train/best.pt` | 验证集选择的第19轮模型及训练状态 |
| `train/inference.pt` | 相同模型权重的轻量推理包，不含优化器，不能用于恢复训练 |
| `train/last.pt` | 第25轮训练状态，供恢复／检查 |
| `train/report.json` | 独立测试结果与平均位姿基线 |
| `train/test_predictions.npz` | 全部384测试帧的预测／真值位姿及误差 |
| `full_forward_check/` | 从图片直接执行完整网络的点云、PLY和配对打乱对照 |
| `results/` | 视频、逐帧叠加、曲线、代表完整点云和查看器证据 |
| `results/color_compare_v2/heldout_gt_pred_separate.mp4` | 此前绿／橙左右对照视频；保留历史 |
| `inference_example/` | 单图片推理CLI实际输出 |

服务停止后：

```bash
python3 -m http.server 8892 --bind 127.0.0.1 \
  --directory /data/omi_runtime/runs/sim_wrist_surface_20261122_r01
```

## 单张图片推理

从`omi_shapeforge`根目录执行，输出必须为新目录：

```bash
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 \
  /data/omi_runtime/envs/foundation_stereo/bin/python \
  scripts/perception/infer_trained_surface.py \
  --checkpoint /data/omi_runtime/runs/sim_wrist_surface_20261122_r01/train/inference.pt \
  --image /data/omi_runtime/runs/sim_wrist_surface_20261122_r01/data/episodes/test_0000/0000.jpg \
  --output /data/omi_runtime/runs/surface_inference_NEW
```

产生`complete_surfaces.npz`、两个对象的PLY和`prediction.json`。点坐标为米，腕部光学坐标x向右／y向下／z向前。模型输入960×540完整图像，读取方式与训练一致为PIL RGB。其他分辨率默认拒绝；仅在确认同光学域、同长宽比时可显式`--resize-full-frame`。该开关不保证真机域适用。

移机时可用`--templates`提供恢复后的同一模板目录，模板清单哈希必须与检查点一致。默认路径为`/data/omi_runtime/runs/interaction_surface_representation_20261122/network_templates/`。不要把仅有actor/JSON位姿文件当作完整模型。

## 数据生成与训练复现

先读取[固定视觉资产接入说明](reuse_wrist_visual_assets.md)。本轮生成器用完整URDF装配，调用FK和渲染，不做物理夹持／插接步进。需要既有固定机器人场景及工具／模块资源。新输出目录例子如下：

```bash
MUJOCO_GL=egl OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 \
  /data/omi_runtime/envs/omi_mesh_audit/bin/python \
  scripts/perception/generate_sim_wrist_dataset.py \
  --output /data/omi_runtime/runs/surface_training_NEW/data \
  --train-clips 192 --val-clips 32 --test-clips 32 \
  --frames 12 --fps 6 --width 960 --height 540 --face-size 672

MUJOCO_GL=egl OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 \
  /data/omi_runtime/envs/omi_mesh_audit/bin/python \
  scripts/perception/audit_sim_wrist_dataset.py \
  --data /data/omi_runtime/runs/surface_training_NEW/data \
  --geometry-audit /data/omi_runtime/runs/sim_wrist_surface_20261122_r01/module_template_render_geometry_audit.json

OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 \
  /data/omi_runtime/envs/foundation_stereo/bin/python \
  scripts/perception/train_sim_wrist_surface.py \
  --data /data/omi_runtime/runs/surface_training_NEW/data \
  --output /data/omi_runtime/runs/surface_training_NEW/train \
  --epochs 25 --batch-size 16 --workers 4
```

上述几何比对文件只适用于当前固定的r05目标主体／r08渲染主体；更换资产必须重新核查，不能沿用旧比对结论。预训练骨干位于`/data/omi_runtime/models/vision/resnet18-f37072fd.pth`，哈希和来源记录在训练配置／资源清单。

训练只用训练集计算均值和归一化参数，只用验证集选择模型。`--resume`用于同一数据、同一总轮数的中断恢复，配合`last.pt`；延长训练不能不加说明地沿用旧余弦调度假设。当前模型已经完成25轮，无需再次启动相同训练覆盖结果。

随后用新运行根调用`verify_trained_sim_surface.py --run ...`及`render_sim_surface_results.py --run ...`生成完整输出核对和结果页。两者保留新输出，重复运行时需另选实验目录。

完整配置、效果与限制见[能力记录](../docs/agent/perception/evolution/sim-wrist-surface-learning.md)。

## 复现两种表面采样

用foundation_stereo环境的Python从仓库根依次运行（输出目录必须未存在）：

```bash
/data/omi_runtime/envs/foundation_stereo/bin/python scripts/perception/build_regular_surface_schemes.py --output /data/omi_runtime/runs/regular_surfaces_NEW
/data/omi_runtime/envs/foundation_stereo/bin/python scripts/perception/render_surface_scheme_results.py --run /data/omi_runtime/runs/sim_wrist_surface_20261122_r01 --templates /data/omi_runtime/runs/regular_surfaces_NEW --output /data/omi_runtime/runs/sim_wrist_surface_20261122_r01/results/surface_schemes_NEW
```

第二步会保存旧页面为`index_before.html`，然后更新8892服务根页面；训练和预测文件保持不变。具体点数、抽样规则与局限见能力记录末尾。源代码快照、验证和恢复路径汇总在`manifests/sim_surface_schemes_20261122.json`。
