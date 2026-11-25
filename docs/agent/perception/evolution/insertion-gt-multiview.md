# 连续插入与同步 GT 点云视频

后续用户要求更清楚的未对准起点和参考截图样式，已另交付[51.5秒未对准→对准→插入版本](alignment-insertion-film.md)。该版画面称“几何位姿估计”，实际仍用仿真位姿参考；本文39.8秒旧片保留。

2026-11-24，用户澄清需要的是同一次动作从未插入到完成插入的连续录像，同时展示机器人第三人称、腕部相机叠加点云、特殊部位着色的三维点云；允许先用 GT 展示效果。此前56秒结果介绍片保留，但不作为本次过程视频交付。

## 当前交付

[完整视频](/home/linux/Downloads/机器人完整插入_三视图_GT点云_1080p_20261124.mp4) · [封面](/home/linux/Downloads/机器人完整插入_三视图_封面_20261124.png) · [实际编码帧分镜](/home/linux/Downloads/机器人完整插入_三视图_分镜_20261124.jpg)。39.8秒，1920×1080，30fps容器，1194帧，H.264。运行根为 `/data/shapeforge/runtime/runs/insertion_multiview_20261124_v1/`。

视频全程维持同一布局和时间线：左侧机器人第三人称、左下同步插接近景；右上腕部相机与可见GT点云，附完整鱼眼视野小窗；右下模块与插座通道的点云近景。青色标记模块尖端，橙色标记孔口。阶段从孔口前对准、进入孔口、持续插入推进到绿色落座状态，没有介绍片段或跨回合拼接。

## 轨迹与渲染

唯一动作来源是 `isaac_fast5_20261124/async5/client/cases/normal/trajectory.jsonl`，种子91000，规则控制的成功PhysX回合，358个控制状态、10Hz。第一条记录在孔口前4.9135mm，末条深度51.2811mm、`is_success=true`，具有原入口资格和稳定落座记录。完整358条均按原顺序显示，每状态重复3个成片帧，保持原速；另有首帧1.5秒、末帧2.5秒停留。没有图像插帧、姿态插值、跳步或重排。

使用该回合的实测关节位置，经原冻结传递包 `staged_contact_20261123/robot_transfer` 的独立FK恢复刚体位姿，再在Isaac RTX中重新渲染高分辨率第三人称、近景及腕部六面相机。每次渲染时间增量为0，未重新推进物理；三个视图及点云使用同一状态。RGB是仿真轨迹重渲染，不是再次动力学成功试验。

该传递包使用WG-r10＋OM-r08固定模块插入模型；不将本片称作WVA-01／GC-r01动态夹持验收，不改源资产或既有接触任务合同。

腕部960×540鱼眼从原1920×1080投影按像素中心规则缩放内参，保留原D参数，并由6个640×640方形相机重投影。视频主窗显示固定像素裁剪 `[270,250,690,473]` 的任务近景，另保留完整视野小窗；不是更换腕部相机位置或光学模型。

## 点云含义

本片**没有运行网络估计**，主标题和第三视图均明确标为GT。表面点直接取本次传递包当前可见mesh，不替换既有网络训练模板：普通0.8mm平面网格、尖端／孔口0.2mm加密，模块42,441点、插座212,308点；活动绿色附件不属于刚性模块目标。`gt_templates/manifest.json`保留原三角形重建和网格审核。

腕部叠加使用物体表面朝向和RTX径向深度处理夹爪等遮挡，深度容差1.2mm，显示时只抽稀原始点ID。右下三维近景显示模块及插座cage／通道，省略支架、外壳和PCB以便看清插接；保留被遮挡部分的GT几何，画面注明这一含义。该三维视图不表示相机看到了隐藏表面，也不表示网络遮挡补全或置信度已经验证。

## 验证与恢复

- 全部358条源关节位置、步号和顺序一致；重放TCP相对源测量最大位置差约0.467微米。
- 从本片模块／插座变换独立重算插入深度，最大差约0.000319mm；这是回放一致性检查，不是实物精度。
- 成片1194帧来源映射连续，所有控制状态均出现，三视图共用同一状态；源传递包和原轨迹／报告SHA256保持一致。
- FFprobe确认尺寸、时长、帧数和编码；FFmpeg全片解码无错误。抽查0.5／3／7／12／20／28／35／37.5／39秒实际编码帧，与同状态重新合成的RGB平均绝对差约1.16–1.21／255，均保留青／橙重点点云。
- 轻量测试84项：25通过、59项因可选依赖跳过、0失败；实际RTX三帧预览与整段358状态捕获另行完成。首次预览的pad关节命名解析错误已修复，失败产物保留在 `preview/`，成功预览在 `preview_r2/`。

证据：运行根 `quality_check.json`、`trajectory_validation.json`、`capture/capture_report.json`、`film/film_manifest.json`及源码快照。[仓库清单](../../../../manifests/insertion_gt_multiview_20261124.json)。

在仓库根使用新目录复现，依次执行：

```bash
/data/isaac-sim-5.1.0/python.sh -u scripts/simulation/capture_insertion_multiview.py \
  --transfer /data/shapeforge/runtime/runs/staged_contact_20261123/robot_transfer \
  --case /data/shapeforge/runtime/runs/isaac_fast5_20261124/async5/client/cases/normal \
  --worker /data/shapeforge/runtime/runs/isaac_fast5_20261124/async5/worker \
  --output /data/shapeforge/runtime/runs/insertion_multiview_NEW/capture

OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  /data/omi_runtime/envs/foundation_stereo/bin/python scripts/perception/render_insertion_multiview.py \
  --capture /data/shapeforge/runtime/runs/insertion_multiview_NEW/capture \
  --templates /data/shapeforge/runtime/runs/insertion_multiview_NEW/gt_templates \
  --output /data/shapeforge/runtime/runs/insertion_multiview_NEW/film
```

捕获追加 `--indices 0 179 357` 可先检查三个时刻；合成追加 `--preview` 可只看布局。当前能力是完整插入轨迹的同步GT可视化；未新增网络、BC／RL或真机训练与精度成绩，14,549张严格网格数据仍未因此训练。
