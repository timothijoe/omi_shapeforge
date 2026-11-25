# 查看与复现完整表面点云和网络原型

> 本机迁移提示（2026-11-24）：运行资源实体已迁至 `/data/shapeforge/runtime`；本文中的 `/data/omi_runtime` 是保留的兼容入口，指向同一份内容。目录映射与恢复要求见[当前资源契约](../docs/agent/interfaces/local-resources.md)。

窗口：`http://127.0.0.1:8890`。第一页可旋转模型并选择512／2048／8192／16384点；“显示加密区域”标出全表面／关键区分配。第二页展示输入图片与实际未训练网络输出，可勾选叠加观察；不代表识别成功。

运行根目录：`/data/omi_runtime/runs/image_to_complete_surface_20261122/`。

- `templates_v2/`：最终点集及来源、覆盖误差清单；`templates/`是早期没有最低部件覆盖配额的对照，保留。
- `point_count_comparison.png`：可导出的静态点数对比。
- `prototype/UNTRAINED_predictions.npz`及两个PLY：实际网络前向输出，**不是准确位姿**。
- `prototype/report.json`：输入／模板／标定哈希、动态参数、设备、输出尺寸与梯度检查。
- `index.html`、`viewer_templates.png`、`viewer_network.png`：交互页面及截图。

服务停止后：

```bash
python3 -m http.server 8890 --bind 127.0.0.1 \
  --directory /data/omi_runtime/runs/image_to_complete_surface_20261122
```

再打开上述地址。它与8876的人工位姿调节窗口独立，不会修改已有标注。

从仓库根目录生成一份新点集（输出目录必须不存在）：

```bash
/data/omi_runtime/envs/foundation_stereo/bin/python \
  scripts/perception/build_surface_representation.py \
  --output /data/omi_runtime/runs/surface_templates_NEW
```

网络实现：`scripts/perception/image_to_surface_network.py`。最小调用：

```python
model = ImageToCompleteSurface(template_dir, calibration).eval()
result = model(images)  # float RGB [B, 3, 1080, 1920] in [0, 1]
module_cloud = result['module']['points_m']  # [B, 2048, 3], meters
socket_cloud = result['socket']['points_m']  # [B, 8192, 3], meters
```

使用真实图片做前向／梯度流程检查，输出新目录：

```bash
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 \
  /data/omi_runtime/envs/foundation_stereo/bin/python \
  scripts/perception/run_image_to_surface_prototype.py \
  --templates /data/omi_runtime/runs/image_to_complete_surface_20261122/templates_v2 \
  --image /path/to/raw_wrist_rgb.png \
  --ignore-rects /path/to/this_image_marker_ignore_regions.json \
  --output /data/omi_runtime/runs/surface_prototype_NEW
```

忽略区域JSON格式为`{"rectangles_xyxy": [[x0,y0,x1,y1], ...]}`，坐标对应原始图像。本次首帧定义在`first_frame_ignore_regions.json`，不能无核查套用到所有图像。此预处理不使用位姿标签；网络的动态输入仍只是处理后的RGB图像。当前骨干和预测头均未训练，脚本不会下载预训练权重或执行优化器更新。

验证：

```bash
/data/omi_runtime/envs/foundation_stereo/bin/python \
  scripts/perception/test_image_to_surface.py -v
```

完整表示、坐标、网络、损失和训练接续见[设计文档](../docs/design/image-to-complete-surface.md)。
