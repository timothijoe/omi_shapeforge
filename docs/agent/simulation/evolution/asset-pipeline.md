# Blender 与外观资产管线

## 当前工具和输入

用户已将 Blender 路线命名为 V3，作为后续编辑和导出的主资产；V2 为辅助参考与对比，见[ADR 002](../decisions/002-blender-v3-primary.md)。默认编辑 V3 工作副本，迁移原件和 V3-r01 冻结副本留作追溯。

便携包指定原机 Blender 4.5.16 LTS。本机从官方发布目录取得 Linux 包，并核对官方 SHA256；版本、下载来源及本地位置记录在[仿真验证索引](../../../../manifests/simulation_validation.json)。软件、原模型、OBJ 和渲染图均在外部资源目录。

保存模型包含：未定标照片稿、米制尺寸修正版、连通槽版本和 V2 参考。前三者照片资源内嵌；没有外部 `.blend` 库依赖。照片稿的单位是 NONE，其余米制模型 scale_length 为 1。

## 实际实现

`scripts/simulation/export_blender_asset.py` 必须由 Blender 自带 Python 执行。它读取指定集合的求值 MESH／CURVE，把 `matrix_world` 应用到顶点，三角化后逐部件输出 OBJ；颜色取自材质或 Principled Base Color。复杂着色和纹理不完整导出。

当前导出 15 个外观部件，模型总体约 0.10 m 量级。`asset.json` 记录源 `.blend` 哈希、Blender 版本、部件清单和 bounds。源 `rigid_match_mesh.npz` 的 bounds 提供碰撞盒；导出不把修改保存回输入 `.blend`。

## 验证和限制

本机已实际重开四份模型、检查图片打包和单位，完成当前连通槽模型的一张 1400×1000 后台图像，以及求值几何导出。报告与图像由[资源清单](../../../../manifests/README.md)索引。

包内有 `rebuild_blender.py --stage photo|metric|groove`，但这些完整生成阶段尚未在本机复跑。metric 阶段使用冻结参数，不从 59 帧重新估计尺寸。旧机槽重建／拓扑检查记录是背景，不能作为本机新验收。

导出器依赖当前模型集合名称和固定资产结构，不是通用任意 Blender 文件转换器。柔性拉手被转换为刚性附着外观，精度未认证。操作见[Blender 教程](../../../../tutorials/blender_assets.md)，历史见[本阶段](../chronicles/2026-11-20-blender-and-scenes.md)。

## 资产身份与交互对照

初始目录中的 `OM-001/GROOVE-r01` 现为 `OM-001/V3` 的兼容别名，V3 是主模型；`OM-001/REF-V2` 为辅助对比，PHOTO／METRIC 为历史阶段；具体映射、父版本与实例身份见[资产版本说明](../../../asset-versions.md)。新名称仅是本地资产目录标识，不是厂家型号，也不改变物理精度验收状态。

本次为对照展示重新读取四份 Blender 的可见求值几何；隐藏构造刀具排除，原模型哈希保持不变。展示中分别适配模型大小，材质为示意，不用截图尺寸代替物理测量。

桌面兼容性补充：原浏览器检查使用启用了软件 WebGL 的无头 Chromium，未覆盖实际桌面 Chrome 无 WebGL 的配置。用户打开后出现空画布，已增加 CPU 逐像素深度渲染后备路径；禁用 WebGL 的检查覆盖四网格、旋转、缩放和部件选择，并在真实桌面刷新核对。网格数据未改变，见[兼容性验证](../../../../manifests/viewer_compatibility_validation_20261120.json)。

另已恢复原机 Open3D 原生 GUI，按旧启动记录加载历史 V2／V1 资产；本机桌面窗口及 V2 网格实际可见。它不依赖网页，支持原有模型选择和点云叠加入口；启动方法见[原生查看教程](../../../../tutorials/native_mesh_viewer.md)，证据见[原生窗口验证](../../../../manifests/native_viewer_validation_20261120.json)。本次没有重建或修改几何，也没有把旧界面的“当前 V2”改写成新资产目录的默认版本。
