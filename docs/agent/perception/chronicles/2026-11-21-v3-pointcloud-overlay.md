# 2026-11-21：当前 V3 与用户指定点云叠加

用户指定 `/home/linux/Downloads/pointcloud.html`，并圈选双孔插座下方、夹爪上方的光模块。输入 SHA256 为 `efdf00062690651d2123d57f4eac48abc0bfca2c2a49ef5de29fc53d2201ee85`，与 portable 包的源 HTML 完全相同；新截图和原包圈选相同，因此复用已核对的 ROI。不是重新进行全场景目标检测。

HTML 自述为红外双目 OpenCV SGBM 点云、单位米，未读取设备深度；不能把它当作已标定的头部相机原生深度或机器人坐标。原始 100000 点逐元素核对保留。ROI 原始 486 点，平面过滤后 472 点，121 个检查点不参与 ICP，但 ROI 和初始化仍使用整体观测，不构成独立位姿真值。

从当前 `OM-001-V3.blend` 对应的 15 个已评估部件重新导出米制网格，模型源 SHA256 为 `016ac93da1f252e2f13325ac20454d1a02b82e31a840ac4f95bffa4218d0b8d2`。9 个刚性主体部件参与 36 个初始条件的稳健点到面 ICP；显示全部 15 个部件（4044 个三角形），包括拉手、拉手座和折边。9 部件的顶点和三角面与旧 portable 刚体网格逐元素一致，故本次是当前 V3 的条件配准重跑及完整显示，不是新的资产修订。

无先验最低分会把拉手指向插座；与另一头尾解的分数接近（约 0.618 对 0.630）。依据插接场景采用“插入端朝插座、拉手端朝夹爪”先验选择默认解；正反面仍不唯一。下拉框保留其他候选，不能以低表面距离认定真实 6D 朝向已确定。

默认解：模型原点在 HTML 点云坐标中的平移约 `[9.136, -78.807, 707.882] mm`。旋转行列式 1，正交误差约 `1.8e-15`，没有缩放或变形。检查子集表面距离中位数 0.155 mm、P90 0.728 mm；全部原始 ROI 中位数 0.159 mm、P90 2.752 mm。这些为几何相容性，不是物理位姿精度；拉手没有独立几何配准验证。

产物：`/data/omi_runtime/runs/pointcloud_v3_overlay_20261121_0140/`。

- `report.json`：输入、模型和各部件哈希、选解先验、4×4 位姿和统计。
- `registration/overlay.html`：自包含交互页面，已打开桌面 Chrome；橙色完整 V3、绿色 ROI、灰色原点云。
- `registration/fit/unconstrained_results.json`：原始无头尾先验结果，保留供检查。
- `registration/fit/confirmed_target_results.json`：按场景先验排序的候选与默认解。
- `registration/delivery/matched_v3_full.ply`：变换后的完整 V3。
- `v3_cloud_context.png`、`v3_cloud_closeup.png`、`v3_cloud_alternative_face.png`、`v3_cloud_annotation_view.png`：浏览器实际渲染截图。

已实际用 Chrome WebGL 检查页面加载、局部显示、候选切换、标注视角恢复，并目视核对默认模型位于用户所圈细长区域。WebGL 错误码 0，页面包含完整 100000 点；截图中拉手向夹爪延伸，主体与目标点大致相容。未验证独立外参、原始双目标定或真实位姿精度。

复现入口：`scripts/perception/pointcloud_v3_overlay.py`。在 `foundation_stereo` 环境运行，传入 `--html`、`--package`、`--model-inputs`、新的 `--output`。该入口对 HTML 哈希做严格检查，不允许将本 ROI 静默套用到其他点云；输出拒绝覆盖已有目录。原始 HTML、模型和 portable 包未修改。

## 桌面显示纠正

用户随后反馈原 Chrome 窗口没有内容。此前成功的 WebGL 截图来自独立无头浏览器，不能代表用户原浏览器窗口正常。已启动独立可见 Chrome 配置 `browser-visible`，使用 `--use-angle=swiftshader --enable-unsafe-swiftshader` 软件渲染；通过该可见窗口的 DevTools 验证 100000 点、WebGL 错误码 0，捕获并目视检查 `visible_browser_verified.png`，切到目标局部并将窗口激活到前台。另用图片查看器打开局部预览。原窗口空白的具体原因没有独立确诊；模型、位姿和点云未修改。

## 用户纠正正反面

用户指出模型正反面倒置，已采用槽面朝采集相机的另一候选，并在同一数据上重新执行条件配准；不对调插入端和拉手端。相对前一默认解旋转变化 179.914°、长轴变化 1.255°、原点平移变化 0.334 mm（翻面后局部贴合微调）。原模型与点云不变。新结果目录 `/data/omi_runtime/runs/pointcloud_v3_overlay_20261121_face_corrected`，包含 `report.json`、`registration/overlay.html`、`registration/delivery/matched_v3_full.ply` 和 `preview.png`。新检查子集 P90 1.111 mm，全部原始 ROI P90 1.296 mm；选择来自用户正反面先验，不是自动消除几何歧义。`--face-prior toward-camera` 可复现；旧结果保留。已在独立可见软件渲染 Chrome 中验证默认槽面朝相机、10 万点、WebGL 错误码 0，并截图核对。
