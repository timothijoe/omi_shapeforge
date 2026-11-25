# 点云估计展示视频

后续用户澄清需要连续插入过程，另已完成[39.8秒同步三视图GT视频](../evolution/insertion-gt-multiview.md)。本文56秒结果介绍片继续保留，不作为该连续过程请求的交付。

2026-11-24，按用户要求阅读[感知网格与预训练交接](../../../chronicles/2026-11-23-perception-grid-pretraining-handoff.md)，将已有点云估计制作成独立成片。用户消息中的参考图本轮仅显示 `Image #1`，无法读取具体画面；本版采用深色、中文排版、三维环绕、真值与预测并排和原创合成背景音乐。

## 交付

- [1080p 成片](/home/linux/Downloads/点云估计_展示视频_1080p_20261124.mp4)：56 秒，1920×1080，30fps，1680 帧，H.264／AAC，14,750,322 字节。
- [封面](/home/linux/Downloads/点云估计_展示封面_20261124.png) · [实际编码帧分镜](/home/linux/Downloads/点云估计_分镜预览_20261124.jpg)。
- 运行目录：`/data/shapeforge/runtime/runs/pointcloud_showcase_20261124_v1/`；无音乐画面为 `picture.mp4`。
- [渲染脚本](../../../../scripts/perception/render_pointcloud_showcase.py)；运行目录另存相同脚本快照、`manifest.json`、`source_frame_map.json`、`quality_check.json`、源码／原结果哈希。

内容依次为：0–6 秒点云环绕；6–14 秒 RGB 到预测几何；14–26 秒留出配置真值／预测；26–34 秒旧新模型同图比较；34–42 秒全部测试帧误差；42–49 秒最大误差案例；49–56 秒网格数据与后续预训练。

## 来源与表达范围

预测只来自 `contact_wrist_surface_20261123_r01/train/test_predictions.npz`，旧模型对照来自该运行 `transfer_evaluation/old_frozen_predictions.npz`。没有重新训练、调整预测或筛掉失败配置。使用原网络模板模块 37,895 点、插座 204,820 点；完整输出由双对象刚体位姿展开模板，不是自由形状生成。

三维运镜使用 `test_0000/frame06` 的静态实际预测，在同一预测插座坐标系下移动展示相机；没有改变模块与插座相对姿态。二维对照展示 `test_0000`、`test_0001`、`test_0003`，旧新对照另含 `test_0027`；原始 6fps 序列明确标注为 0.5× 慢放，通过重复帧呈现，不插值图像或预测。三维绘图按像素深度和展示相机朝向筛选完整模板；二维绘图抽稀投影点，不使用真值 mask 修正预测。

所有 384 帧参与统计与误差散点图。视频显示平均 0.982mm、P90 1.381mm、最大 10.974mm，旧冻结模型在同一测试集平均 12.260mm；最大误差 `test_0002/frame04`（ID 2716）单独保留。三维误差指固定尖端参考点在插座系中的误差，不是点云均值、实际插入精度或真机成绩。

新细网格严格主集重新计数为 14,549 张，只在片尾作为后续数据准备状态展示。该批数据尚未训练，不把旧接触数据成绩归给新数据。

## 检查

- FFprobe 确认成片尺寸、帧率、时长、1680 帧、H.264 与 48kHz 立体声 AAC；FFmpeg 全片音视频解码无错误。
- 在 3／10／16／23／28／32／39／45／52 秒抽取实际编码帧，与重新渲染比较，RGB 平均绝对差约 1.33–1.58／255，检查过文字、画面与最大误差点标记。
- 独立按预测／真值位姿与固定尖端参考点重算全部 384 帧，相对原始误差最大差约 0.0000272mm。
- 视频 1680 帧的来源映射保存为 `source_frame_map.json`，实际使用的 49 张不同源图 SHA256 全部与原记录一致。
- 检查点、报告、预测、记录与训练模板渲染前后 SHA256 一致；Downloads 副本与运行目录成片哈希一致。

复现须使用新输出目录，保留本次与全部历史产物：

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  /data/omi_runtime/envs/foundation_stereo/bin/python \
  scripts/perception/render_pointcloud_showcase.py \
  --run /data/shapeforge/runtime/runs/contact_wrist_surface_20261123_r01 \
  --output /data/shapeforge/runtime/runs/pointcloud_showcase_NEW
```

追加 `--preview` 只生成分镜。源码图像为仿真，范围仍是接近阶段视觉估计；未新增插入后遮挡、策略收益或 sim-to-real 验证。
