# V4-r05「双窗尾槽版」：暂定基线与开发过程

2026-11-21，用户确认“暂时先定这一个版本”，本轮将 **OM-001/V4 r05** 命名为 **「双窗尾槽版」**，正式显示名为 **V4-r05 · 双窗尾槽版**。名称指尾端上侧凹槽中，三个金属端之间的两个空窗口。此名称固定对应r05，后续r06等修订不能沿用这个名称来悄悄指向新文件。

本次只命名、登记和整理文档，未重新生成mesh、改材质或重命名原文件。用户暂定采用的是当前外观结构；已有训练仍使用SIM-OM001-OS001-r03，V4没有自动替换训练资产。

## 版本演进与纠正

| 阶段 | 实际改动／发现 | 当时问题与后续处理 |
| --- | --- | --- |
| V2／V3尺寸复核 | 用户测得插孔18.8 × 8.8 mm、模块18.1 × 8.2 mm；复查发现旧仿真通道19.0 × 9.6 mm、模块参考截面18.1741 × 7.8383 mm | 旧仿真间隙偏大，旧插入／策略成绩不能直接代表实测尺寸下的表现 |
| MEASURED-r01 | 从Blender V3另建独立模块，采用18.1 × 8.2 mm参考截面；下部前端上翘，尖端厚度8.0 mm | 斜面长5.19 mm沿用原结构，未实测；上下壳按用户要求使用相同金属外观 |
| V4-r01 | 依据视频补尾端上盖长方形缺口、侧片下沿缺口和黑色尾件凹面 | 上盖缺口落实为真实几何；黑色件却被错误简化成固定盲凹块 |
| V4-r02 | 两张新照片显示胶件可取下且有双脚；改成独立连通双脚胶件，补三个金属凸片及内部容纳空间 | 用户指出胶件和金属片太高；未采用这个高度 |
| V4-r03 | 用户明确应向下沉，胶件与三个金属片整体下移1.5 mm，内部空间同步调整 | 新正视图表明问题不只在位置：胶件端面仅高3.95 mm，下方余量4.9 mm，仍不符合实物比例 |
| V4-r04 | 胶件端面加高至7.1 mm、底部余量收至约1.2 mm；三个金属端改宽短，形成两处上侧窗口 | 将暗窗口错误解释为胶件上部延伸，用户明确这些同高度区域应为空 |
| **V4-r05「双窗尾槽版」** | 删除两条错误的上部胶件填充；保留下方端面、较低的双胶脚和三个金属端 | 两个窗口确认为空；用户暂定采用此版，V3与全部旧修订保留 |

这轮修正的主要教训是：单一斜视角会混淆高度、端面尺寸和遮挡关系；暗区也不能直接当成黑色实体。最后分别用视频侧面、胶件装入／取下照片、尾端正视图和用户指认约束结构，再用几何检查确认实际空腔。

## 暂定版本的内容

- 18个mesh：主体17件，另1件可单独显示、移开的连通双脚胶件。
- 模块参考插入截面18.1 × 8.2 mm，横向包含侧弹片；下部前伸段尖端厚度8.0 mm。
- 上侧尾缘有真实长方形缺口，左／中／右三个宽短金属端之间留有两个空窗口。**与金属端同高度的窗口内没有胶件填充。**
- 黑色胶件端面高7.1 mm、底框余量约1.2 mm；三个金属端可见宽度1.8／3.2／1.8 mm。胶件的内伸双脚保留在较低区域。
- 上下壳同种银色金属；胶件黑色，拉手绿色。查看器中的装入、拔出和旁置只是显示状态，保存的Blender模型为装入状态。

18.1 mm和8.2／8.0 mm来自用户尺寸约束或允许值；尾槽、胶件端面、金属端、内部空间的具体毫米值及5.19 mm斜面长度仍是建模估计。暂定外观基线不等于这些尺寸都已实物标定。

## 已完成验证与范围

- 16个实体通过闭合性、法向一致、正体积及非退化三角面检查；另2个历史开放折缝只作外观。
- 胶件是一个连通实体，左右两脚和中间空隙检查通过；主体参考截面和下唇尖端尺寸检查通过。
- 两个窗口内共280个采样点无实体占据；同高度正面射线不命中胶件，在空腔深处才遇到金属背壁。背壁深度是假设，未宣称整件贯穿孔。
- 胶件向外拔出0–15 mm、每0.5 mm取样，共31个位置未发现胶件／主体表面碰撞。不是连续路径保证，也未模拟橡胶变形、接触力或真实卡扣机构。
- Blender、整件OBJ／GLB、无胶件主体OBJ及单独胶件OBJ均已重开核对。r05形成时686个旧文件哈希不变；此次命名再次核对r05已有文件哈希，未改变构建产物。
- 尚未用V4重建MuJoCo碰撞资产、校准插座或重训策略，也没有真实视频定位误差的V3／V4对照结果。

## 来源、文件与恢复

视频：[飞书20261121-193612.qt](/home/linux/Downloads/飞书20261121-193612.qt)。照片：[胶件装入](/home/linux/Downloads/img/20261121-194740.jpg)、[胶件取下](/home/linux/Downloads/img/20261121-194745.jpg)、[尾端正视](/home/linux/Downloads/img/20261121-200216.jpg)。

资产目录：`/data/omi_runtime/assets/optical_module_v4/r05/`。

- [Blender模型](/data/omi_runtime/assets/optical_module_v4/r05/OM-001-V4-r05.blend) · [整件OBJ](/data/omi_runtime/assets/optical_module_v4/r05/OM-001-V4-r05.obj) · [GLB](/data/omi_runtime/assets/optical_module_v4/r05/OM-001-V4-r05.glb)。
- [无胶件主体OBJ](/data/omi_runtime/assets/optical_module_v4/r05/OM-001-V4-r05-module-without-plug.obj) · [单独胶件OBJ](/data/omi_runtime/assets/optical_module_v4/r05/OM-001-V4-r05-removable-plug.obj)。
- [构建清单](/data/omi_runtime/assets/optical_module_v4/r05/asset_manifest.json) · [验证报告](/data/omi_runtime/assets/optical_module_v4/r05/validation.json) · [模型窗口](/data/omi_runtime/assets/optical_module_v4/r05/evidence/window_empty.png)。
- [命名与暂定采用登记](../../manifests/module_v4_r05_designation_20261121.json)，资产目录内也有同内容的[version_name.json](/data/omi_runtime/assets/optical_module_v4/r05/version_name.json)。它记录原Blender与构建清单哈希，覆盖构建时清单中旧的“待外观复核”状态说明，而不修改原清单。

查看：

```bash
/data/omi_runtime/envs/foundation_stereo/bin/python \
  /data/omi_runtime/assets/optical_module_v4/r05/build_scripts/view_r05.py
```

后续以此版为只读参考，另建新修订再改；不覆盖r05或V3，不改写旧实验结果。下一步若进入视觉／仿真验证，应先绑定可见结构特征、做相同帧集对照，并为新尺寸另建碰撞与插座资产。

持续事实见[V4能力记录](../agent/simulation/evolution/module-v4.md)，仿真系统现状见[仿真器专门记录](../simulation.md)。

mesh本身的部件、坐标、几何操作、导出和验证接口另维护于[Mesh开发专门记录](../mesh-development.md)，对应实现事实已同步[Blender资产管线](../agent/simulation/evolution/asset-pipeline.md)。
