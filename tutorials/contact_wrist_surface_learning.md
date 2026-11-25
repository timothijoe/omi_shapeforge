# 接触版腕部表面学习：操作与恢复

> 本机迁移提示（2026-11-24）：运行资源实体已迁至 `/data/shapeforge/runtime`；本文中的 `/data/omi_runtime` 是保留的兼容入口，指向同一份内容。目录映射与恢复要求见[当前资源契约](../docs/agent/interfaces/local-resources.md)。

运行根：`/data/omi_runtime/runs/contact_wrist_surface_20261123_r01/`。能力与局限见[接触版训练记录](../docs/agent/perception/evolution/contact-wrist-surface-learning.md)。

结果窗口：`http://127.0.0.1:8893`。默认方案一，顶部可切换方案二；“逐帧查看点云”可旋转和缩放，“查看最大误差帧”直接跳到test_0002／第5张图。

服务恢复：

```bash
python3 -m http.server 8893 --bind 127.0.0.1 --directory /data/omi_runtime/runs/contact_wrist_surface_20261123_r01
```

## 进度入口

- `capture_0.log`至`capture_3.log`：四个数据采集分片；保留拒绝原因。
- `pipeline_v2.log`：审核修正后的合并、审计、训练、旧新对照和完整forward检查。原`pipeline.log`保留首次审核失败。
- `shards/shard_*/episodes/`：各配置腕部视频／JPEG／实际物理状态。
- `data/`：合并后的训练数据入口，episode目录是指向分片的符号链接；迁移须一起保留`shards/`和替代配置目录`repair_visible_gate/`。
- `data/label_audit.json`：独立重放标签、接触轨迹、可见表面记录和源几何核查。
- `network_templates/`：方案一的完整规则模板。
- `train/`：新训练配置、日志、检查点、测试预测与指标。
- `transfer_evaluation/`：旧冻结模型、新模型在相同新测试帧上的对照。
- `full_forward_check/`：从RGB调用完整网络、完整点云与位姿展开核对。

不要重复运行固定目录脚本覆盖已有数据。新实验使用新目录；`train_smoke/`仅检查流程，不能作为效果结论。

## 新运行复现

在仓库根，用`omi_mesh_audit`环境运行`generate_contact_wrist_dataset.py --output <新运行>/shards/shard_i --shards 4 --shard-id i`，i为0到3，默认192／32／32段。可设置`MUJOCO_GL=egl OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1`。

四个分片均完成后，用相同环境运行`audit_contact_wrist_dataset.py --run <新运行>`。检查`data/label_audit.json`通过且每帧包含可见表面gate。

将已登记的规则模板恢复到新运行`network_templates/`，核对manifest哈希。在`foundation_stereo`环境中运行：

```bash
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 /data/omi_runtime/envs/foundation_stereo/bin/python \
  scripts/perception/train_sim_wrist_surface.py \
  --data <新运行>/data --templates <新运行>/network_templates \
  --output <新运行>/train --epochs 25 --batch-size 16 --workers 4 \
  --init-checkpoint /data/omi_runtime/runs/sim_wrist_surface_20261122_r01/train/best.pt
```

`--init-checkpoint`是新数据微调；同一数据训练中断才用`--resume <新运行>/train/last.pt`，两者互斥。完整审核状态不通过时不要启动训练。

## 结果文件与单图推理

`train/report.json`为主测试指标，`transfer_evaluation/report.json`为同图旧新对照，`failure_analysis.json`记录最大误差及训练姿态覆盖诊断，`approach_clearance.json`记录仍在孔口前的距离。旧模型不变，旧8892结果窗口保留。

`results/surface_schemes_v1/`保存两方案视频、384帧投影和浏览器检查；`transfer_evaluation/visual/old_vs_contact_finetuned.mp4`是旧新模型同图视频。图像投影作屏幕抽样，3D使用完整点集。

```bash
/data/omi_runtime/envs/foundation_stereo/bin/python scripts/perception/infer_trained_surface.py   --checkpoint /data/omi_runtime/runs/contact_wrist_surface_20261123_r01/train/inference.pt   --image /data/omi_runtime/runs/contact_wrist_surface_20261123_r01/data/episodes/test_0000/0000.jpg   --output /data/omi_runtime/runs/contact_inference_NEW
```

复现显示依次运行`render_sim_surface_results.py`、`render_surface_scheme_results.py`、`render_contact_transfer_comparison.py`，均提供`--run <新运行>`；第二步额外提供`--templates /data/omi_runtime/runs/regular_surface_schemes_20261122/templates_v2 --output <新运行>/results/surface_schemes_v1`。输出目录须未存在。失败诊断JSON在第一次渲染前准备，可在页面显示失败入口。

机器清单与源码版本入口：`manifests/contact_wrist_surface_learning_20261123_r01.json`。采集初版和可见胶垫门控修复版分别留存，不覆盖历史快照。
