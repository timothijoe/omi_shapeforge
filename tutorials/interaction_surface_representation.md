# 查看尖端、插孔的精细点云

新窗口：`http://127.0.0.1:8891`。旧8890整体点数／网络原型窗口仍保留。

**当前默认是“整体＋重点加密（训练模板）”**：完整光模块和插座的全局点与加密区域在同一坐标中显示，整体采用材质色，重点区采用结构色。每个大视图右下角的小窗仅放大对应局部，不改变点的位置。网络点集未变，仍为模块22528、插座43008点，各包含2048全局点。

左侧能看到完整模块到尖端的关系，蓝色为上薄唇、橙色为下薄唇、灰色为侧壁、黄色为原mesh锐边／开放边界。“放大关键部位”可临时只看尖端，再切换正视、侧视或最前6mm；“看整体”返回完整形状。

右侧显示完整插座／PCB／下支架与加密孔口的关系。孔口局部蓝色为金属侧壁、橙色为底面／导向筋、紫色为口沿、绿色为白框。小窗正对孔口；可“放大关键部位”后查看内壁及2～24mm深度。深度过滤只作用于重点点层，不裁掉完整背景，不新增封口面。

两侧下拉框都可切换：

- 整体＋重点加密（训练模板），默认包含全局和局部全部点。
- 整体＋超密局部（几何参照），在完整背景上查看更细的局部。
- 整体＋旧局部点，模块局部590点、插孔局部2008点；背景去掉同一ROI内的重复旧点。
- 重点区域仅表面、仅真实棱边；整体背景可独立开关。

“整体脉络”和“局部小窗”开关只影响显示，不修改模型／网络模板。局部放大时小窗自动隐藏，避免重复。旧的仅局部页面保存在运行目录的`whole_context_20261122/index_local_before.html`。

拖动旋转，滚轮缩放；点大小可调。结构颜色是辅助说明，不是RGB相机观测；这些点来自已有mesh，而非新扫描。

运行目录：`/data/omi_runtime/runs/interaction_surface_representation_20261122/`。

- `templates/`：高密度局部表面、边缘、逐面来源、覆盖统计及包含全局背景的密集组合。
- `network_templates/`：模块22528点、插座43008点的训练配置，分为全局／局部／棱边三层。
- `prototype/`：新模板实际未训练网络输出与前向／合成梯度报告；不是识别结果。
- `viewer_old_local.png`、`viewer_dense_front.png`、`viewer_dense_oblique.png`：旧／新同视角对照。

恢复查看服务：

```bash
python3 -m http.server 8891 --bind 127.0.0.1 \
  --directory /data/omi_runtime/runs/interaction_surface_representation_20261122
```

新生成（输出目录必须不存在）：

```bash
/data/omi_runtime/envs/foundation_stereo/bin/python \
  scripts/perception/build_interaction_surface.py \
  --output /data/omi_runtime/runs/interaction_surface_NEW/templates

/data/omi_runtime/envs/foundation_stereo/bin/python \
  scripts/perception/build_interaction_surface.py \
  --compact-from /data/omi_runtime/runs/interaction_surface_NEW/templates \
  --output /data/omi_runtime/runs/interaction_surface_NEW/network_templates

/data/omi_runtime/envs/foundation_stereo/bin/python \
  scripts/perception/render_interaction_surface.py \
  --run /data/omi_runtime/runs/interaction_surface_NEW
```

网络沿用[图像原型入口](image_to_complete_surface.md)，将`--templates`改为新`network_templates`，输出另选新目录。`test_interaction_surface.py`验证ROI不封孔、边缘来源和损失分层；`test_image_to_surface.py`保留网络几何回归。

[表示设计与验证边界](../docs/design/interaction-surface-representation.md)。
