# 点云展示与插接视频交接：r11腕部重点叠加版

记录日期：2026-11-25。用户已认可r10冷银灰配色，随后要求腕部相机画面只叠加橙色／绿色点云，其他位置保留原始图像，并确认将这部分写入docs。本页汇总当前展示约定、r11实际交付、验证和恢复入口；本次归档不重新渲染视频。

## 当前展示约定

| 视图 | 显示方式 |
| --- | --- |
| 左：机器人第三人称 | 仿真器原画面，连续展示未对准、对准、插入 |
| 中：腕部相机＋重点点云 | 仅叠加可见的橙色模块尖端、绿色插座孔口；其他位置保留原始RGB |
| 右：几何位姿估计 | 完整模块、插座和支架点云；普通区域稀疏、关键区域加密 |

后续多数新点云展示沿用这一分工：独立三维视图保留完整形状，RGB叠加视图只强调任务关键部位。RGB里不再绘制普通灰点；普通几何仍保留在模板和深度判断中，不因隐藏标记而错误暴露后方重点。

普通／重点层使用相同点径，当前影片为最终输出1像素。当前插接资产普通采样间距0.8 mm，尖端／孔口0.2 mm，平面单位面积密度约相差16倍。其他资产按实际尺度和任务定义ROI及间距，不照搬本任务零件编号。稀疏／加密是三维采样分配，不是PCA或特征嵌入降维。

| 点云区域 | RGB |
| --- | --- |
| 光模块普通面：冷银灰 | 216,221,228 |
| 插座上部普通面 | 176,181,188 |
| 底座／支撑普通面 | 194,205,218 |
| 模块尖端 | 255,166,68（橙） |
| 插座孔口 | 78,240,112（绿） |

普通面使用低饱和中性色，只有指定重点使用鲜亮橙绿。前三种普通色只用于独立三维视图；腕部画面中的普通区域直接显示相机原图。

## r11交付

- [完整视频](/home/linux/Downloads/机器人插接_WG-r15_腕部仅橙绿重点_r11_20261125.mp4)
- [封面](/home/linux/Downloads/机器人插接_WG-r15_腕部重点叠加_封面_20261125.png)
- [腕部前后对比：左r10／右r11](/home/linux/Downloads/腕部点云叠加_仅橙绿重点_前后对比_20261125.png)
- [九个编码时刻过程图](/home/linux/Downloads/机器人插接_WG-r15_腕部重点叠加_过程预览_20261125.jpg)
- [交付清单及文件哈希](../../manifests/insertion_wrist_focus_overlay_20261125_r11.json)

视频1920×1080、30fps、542帧、18.0667秒，3×连续回放；包含全部470个源状态，首尾各1.2秒停留。MP4为3,272,865字节，SHA256：`1ef1605949f7a5e0adfe8b6890cfe3d6a8a29f5313f660242267db6ca38ec9da`。

r10已认可版本及更早影片继续保留。r11只调整中间腕部卡片及对应字幕，左侧机器人、右侧完整冷银灰点云、源相机和运动轨迹均保持。

## 来源与验证

运行根：`/data/shapeforge/runtime/runs/insertion_wrist_focus_overlay_20261125_r11/`。

原回放和点云模板来自`/data/shapeforge/runtime/runs/insertion_asset_upgrade_20261124_r6/fixture_capture/`及`fixture_templates/`。资产为WG-r15／OM-r08，使用Isaac固定夹持插入回放；点云位置由仿真几何与参考姿态驱动，未运行新网络。固定夹持展示不代表自由接触夹持移动已经通过，完整模板也不等于相机看到了所有遮挡表面。

| 对象 | 普通点 | 重点点 | 完整点数 |
| --- | ---: | ---: | ---: |
| 光模块刚性主体 | 18,923 | 23,518 | 42,441 |
| 插座与支架 | 167,239 | 45,069 | 212,308 |

四个无损代表时刻检查通过：腕部非重点位置等于相同裁剪／缩放后的原始RGB；橙绿标记与r10一致；中间卡片外逐像素一致；显式`all`模式可恢复r10。原图相等指叠加结果本身，不包括圆角界面的遮罩边角，也不宣称有损MP4解码后逐字节相同。

全片542帧解码、参数和470状态顺序检查通过；九个编码时刻与同源合成图的RGB平均绝对差约1.565～1.672／255，腕部区域约1.289～1.531／255。原模板和r10交付文件哈希核对通过。既有轻量检查92项：29通过、63可选依赖跳过、0失败；本次仅补docs，没有新增物理、网络训练或性能成绩。

关键证据：`overlay_audit.json`、`quality_check.json`、`film/film_manifest.json`、`source_snapshot/`及`before/`。原始检查脚本与圆角范围修正过程也留存。

## 恢复与后续使用

当前策略为[`layered-points-v3-wrist-focus-only`](../../configs/pointcloud_presentation.json)。在仓库根使用新输出目录执行：

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  /data/omi_runtime/envs/foundation_stereo/bin/python \
  scripts/perception/render_alignment_film.py \
  --capture /data/shapeforge/runtime/runs/insertion_asset_upgrade_20261124_r6/fixture_capture \
  --templates /data/shapeforge/runtime/runs/insertion_asset_upgrade_20261124_r6/fixture_templates \
  --output <NEW>/film \
  --palette component-grays --point-style layered \
  --wrist-overlay focus-only --playback-rate 3
```

先看代表帧可加`--preview`。`--wrist-overlay all`恢复r10的完整腕部叠加范围；精确复现历史版本须同时使用对应源码与配置快照，不覆盖旧输出。

长期约定见[点云展示默认规范](../agent/perception/evolution/pointcloud-presentation.md)，影片沿革见[插接视频纪传体](../agent/perception/evolution/alignment-insertion-film.md)，操作细节见[点云展示教程](../../tutorials/pointcloud_presentation.md)。
