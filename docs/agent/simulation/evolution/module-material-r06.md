# 光模块材质开发：r07纯色银灰，r06历史候选

## 当前修订：V4-r07（2026-11-22）

用户反馈“颜色差不多”，明确要求去掉额外颗粒感。已另存 **V4-r07 · 纯色银灰材质候选**：保留r06的银灰／绿色／暗灰底色及金属度、粗糙度参数，将三张颗粒色纹理替换为空间恒定的2×2纯色图，颗粒幅度为0。后续沿用此要求，不再给该模块人为添加颗粒纹理。

Blender已重新保存，GLB、整件及逐件OBJ／MTL同步导出；MuJoCo材质适配与独立混合腕部预览均使用新目录。18件OBJ顶点／面与r06一致，GLB重开为18件，三张纹理全部像素恒定，1397个受保护旧文件哈希未变。原几何、旧版资产和r05暂定基线保留。只完成静态材质预览，未替换实时训练场景或重新训练。

- [真机与r07无颗粒版对比](/data/omi_runtime/runs/module_v4_plain_material_20261122/real_vs_r07_plain_comparison.png)：同一区域裁剪，不额外调色；右侧为仿真模块与真实夹爪像素的静态合成。
- [r07预览](/data/omi_runtime/runs/module_v4_plain_material_20261122/r07_plain_material_preview.png)
- [Blender](/data/omi_runtime/assets/optical_module_v4/r07/OM-001-V4-r07.blend) · [GLB](/data/omi_runtime/assets/optical_module_v4/r07/OM-001-V4-r07.glb)
- [验证](/data/omi_runtime/assets/optical_module_v4/r07/validation.json) · [登记](../../../../manifests/module_material_r07_20261122.json)

## r06历史阶段（颗粒处理已被用户否定）

2026-11-22，用户指出合成图中光模块颜色与真机不同，要求改色并生成新mesh，不污染旧资产。已从V4-r05「双窗尾槽版」派生 **V4-r06 · 银灰材质候选**，新目录为`/data/omi_runtime/assets/optical_module_v4/r06/`。r05仍是已暂定采用的基线，r06尚待用户外观复核。

## 改动及不变项

| 项目 | r06处理 |
| --- | --- |
| 金属壳、上下板、头盖、金属端等 | 中性银灰底色、细微颗粒色纹理，PBR金属度0.88、粗糙度0.50；上下壳同一材质 |
| 绿色拉手 | 改为更暗、更低饱和度的绿色，粗糙度0.68 |
| 黑色胶塞 | 从渲染中的近纯黑调整为有层次的暗灰，粗糙度0.84 |
| 板件、接触金属区、内部暗块 | 原材质保留 |
| 几何 | 18件顶点、面索引、对象变换与r05完全一致；尺寸、前端斜面、双空窗和低位双胶脚均不变 |
| 新增数据 | UV、3份程序生成贴图、MTL／PBR信息与显式MuJoCo材质适配 |

程序颗粒使用固定随机种子2206、16 mm贴图周期，是微小表面变化的外观近似，不是重建出的真实金属微结构。贴纸／marker没有写入材质。

## 同视角外观对照

主参考为原始腕部帧中未覆盖贴纸的金属区域`(949,695)～(988,724)`，同时查看用户手机照片。手机照片与腕部图像的照明／曝光不同，没有将不同照片的RGB直接当成同一物理反射率。

新旧MuJoCo预览使用相同相机、灯光、鱼眼K／D、位姿先验及真实夹爪掩码，只更换模块视觉mesh的UV／材质。黑色夹爪接触面的修正也保留。

| 8位RGB统计 | 真机参考 | r05旧材质 | r06候选 |
| --- | --- | --- | --- |
| 金属区域中位数 | (199,203,208) | (191,207,226) | (199,204,207) |
| 胶塞区域中位数 | (37,33,42) | (3,3,4) | (37,33,42) |
| 金属区域RGB均值的平均通道差 | — | 9.56 | 1.15 |

上述金属区域同时用于拟合和检查，**不是独立色彩验证、色卡标定或跨光照真实性证明**。相较旧材质，当前样例的偏蓝和纯色块问题有所减轻；绿色拉手只比较颜色分布，其真实与模型轮廓仍有差异。

- [真机／旧版／新版对照](/data/omi_runtime/runs/module_v4_material_20261122/module_material_comparison.png)。
- [r06混合腕部预览](/data/omi_runtime/runs/module_v4_material_20261122/hybrid_r06/hybrid_detail.png) · [对照统计](/data/omi_runtime/runs/module_v4_material_20261122/appearance_comparison.json)。

## 输出、材质兼容与验证

- [Blender](/data/omi_runtime/assets/optical_module_v4/r06/OM-001-V4-r06.blend)：18件原几何、PBR材质、已内嵌贴图；预览使用新文件内的中性灯光，未修改r05灯光或文件。
- [GLB](/data/omi_runtime/assets/optical_module_v4/r06/OM-001-V4-r06.glb)：18件几何及嵌入材质贴图。
- [OBJ](/data/omi_runtime/assets/optical_module_v4/r06/OM-001-V4-r06.obj)：与同目录MTL、`textures/`一起使用；`meshes/`内逐件OBJ另带本地MTL／贴图副本，避免加载器拒绝跨目录纹理引用。
- [MuJoCo材质适配](/data/omi_runtime/assets/optical_module_v4/r06/mujoco_appearance.json)及同目录`mujoco_materials.xml`：显式纹理与颜色调制。MuJoCo的简单材质和Blender／GLB的PBR不是同一个BRDF，不能只复制旧`rgba`便假设贴图已经生效。

验证已通过：逐件OBJ的顶点／面索引与r05精确相同；独立重开Blender后18件坐标、面及对象变换仍完全一致；OBJ／GLB均可重开且包络一致，逐件贴图可读取，Blender三份材质图已打包。1348个受保护旧文件哈希未变。

证据：[几何验证](/data/omi_runtime/assets/optical_module_v4/r06/geometry_validation.json) · [Blender验证](/data/omi_runtime/assets/optical_module_v4/r06/blender_validation.json) · [交付清单](/data/omi_runtime/assets/optical_module_v4/r06/delivery_manifest.json) · [登记](../../../../manifests/module_material_r06_20261122.json)。构建、贴图生成、打包、验证及对照脚本保存在新资产`build_scripts/`。

本轮未覆盖原模型、物理碰撞资产、运行中的实时场景或旧合成图片，也未训练策略。新材质只在独立预览场景中接入；当前暂定基线仍固定为r05。后续若采用r06，应显式应用新材质配置并重新检查不同视角／照明，不把当前拟合区的颜色改善扩展成物理或策略收益结论。
