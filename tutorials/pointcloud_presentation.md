# 查看与复现分层点云展示

当前默认约定见[能力说明](../docs/agent/perception/evolution/pointcloud-presentation.md)：完整普通面稀疏、任务面加密，同一点径，灰阶普通面与橙／绿重点。此页不启动新网络或物理实验。

当前采用r10冷银灰色表：模块普通面RGB(216,221,228)，配色采用时策略为`layered-points-v2-cool-silver`；[已认可视频](/home/linux/Downloads/机器人插接_WG-r15_冷银灰点云_r10_20261125.mp4)。新合成默认使用这一版本。

用户随后指定腕部RGB只叠加橙色尖端／绿色孔口；当前v3默认`--wrist-overlay focus-only`，右侧三维点云仍完整。此选项不删除源普通点，也不改变相机／姿态；`--wrist-overlay all`可恢复r10腕部叠加范围，r10色表保持。

## 查看点云

本机会话入口：[分层点云查看器](http://127.0.0.1:8911/fixed.html?v=2)。可切换普通层／加密层、整体／关键附近，拖动旋转、滚轮缩放。服务器不在线时，先检查8911端口，未监听再运行：

```bash
python3 -m http.server 8911 --bind 127.0.0.1 \
  --directory /home/linux/omi_folder/work/pointcloud-density-20261125
```

离线可直接双击`/home/linux/Downloads/光模块与插座_稀疏加密点云_20261125.html`。正式冻结副本和兼容验证同时位于`/data/shapeforge/runtime/runs/insertion_layered_points_20261125_r9/viewer/`；该目录中的`fixed.html`可直接独立打开，不依赖work目录或原端口。

## 按同一格式制作插接视频

以下命令在`omi_shapeforge`仓库根运行，输出必须使用新目录。现有r6捕获包含完整470状态；本任务无需重跑物理或RTX。

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  /data/omi_runtime/envs/foundation_stereo/bin/python \
  scripts/perception/render_alignment_film.py \
  --capture /data/shapeforge/runtime/runs/insertion_asset_upgrade_20261124_r6/fixture_capture \
  --templates /data/shapeforge/runtime/runs/insertion_asset_upgrade_20261124_r6/fixture_templates \
  --output <NEW>/film \
  --palette component-grays --point-style layered --playback-rate 3
```

先只生成代表帧可加`--preview`。当前默认已是`component-grays`＋`layered`；颜色、采样约定和显示约束在[`configs/pointcloud_presentation.json`](../configs/pointcloud_presentation.json)。影片中的腕部点和三维点均按最终输出1像素绘制，无屏幕网格额外抽稀、无2×2膨胀；相机可见性与像素深度测试仍保留。点间距是三维几何采样间距，投影后可能小于1像素而合并，放大检查更容易看清真实网格。

恢复旧版请配套使用该运行的归档源码和配置：r9／r10采用前的`source_snapshot/configs/pointcloud_presentation.json`保留模块原深灰；r8的`component-grays`＋`legacy`和r7的`component-tones`＋`legacy`也必须配合相应旧源码／色表。单独切回`legacy`不会撤销当前v2默认配色。更旧方案依照其当时清单恢复；新默认不覆盖历史影片。

## 核查

源模板模块42,441点、插座212,308点，普通／重点层分别18,923／23,518及167,239／45,069。不要误拿旧训练紧凑模板或旧日期模板冒充这次交付。

确认采样文件／相机／实际姿态的来源哈希、图例色表、统一点径、所有源状态顺序、全片解码和编码代表帧。三维面板完整模板与腕部可见表面范围不同；片中“几何位姿估计”标题不证明运行了网络。当前仍是r15固定夹持插入，不能写成自由接触夹持移动已通过。
