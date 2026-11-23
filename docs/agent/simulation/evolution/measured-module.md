# 实测截面光模块独立修订

2026-11-21 按用户新测量创建 **OM-001/MEASURED-r01**，从V3另存派生，未覆盖V2、V3、插座或SIM-r03。目录：`/data/omi_runtime/assets/optical_module_measured/r01/`。资产登记见[清单](../../../../manifests/measured_module_20261121.json)，仍未替换训练场景默认资产。

## 尺寸与斜面

用户允许插入段厚度8.1或8.2 mm，本版选择8.2 mm；横向最大宽度18.1 mm，包含侧弹片。前端下表面上翘0.2 mm，下部前伸段尖端厚度8.0 mm，中间线性过渡到8.2 mm。上下方向在文件中为Z，插入方向为−Y，长度单位为米。

斜面长度暂沿用V3下唇前端到侧壁前缘的5.193792 mm，对应约2.205°，**不是用户实测值**。厚度8.0 mm标在下部前伸段最前端；上唇仍比下唇再伸出约3.158 mm，那里没有下唇，不能把8.0 mm理解成整件最前方的局部材料厚度。

保留上方连通槽、头部台阶、板件与拉手；轴向位置不变。主体横向缩放、厚度校准；高于主体上表面的头部区域作平移以保持其原厚度。下板重建为封闭等厚薄板，前伸段上翘，不保留原来细小的边角倒圆。主壳比含侧弹片的最大包络窄，前伸段横向宽度并非处处18.1 mm。

## 实际验证

| 检查位置 | mesh切片高度 |
| --- | --- |
| 主体参考截面Y=5 mm | 8.200000 mm；横向18.100001 mm |
| 斜面接平直段 | 8.200000 mm |
| 斜面中点 | 8.100000 mm |
| 下唇尖端内移0.0001 mm | 8.000004 mm |

101个斜面切片验证下表面单调向前上翘。13个实体部件通过闭合性、法向一致、正体积及非退化三角面检查；2个历史装饰折缝仍为开放外观mesh，不宣称可直接作实体碰撞。新副本清理了侧弹片的重合顶点／退化面。

Blender独立重开确认15个mesh及米制单位；OBJ／GLB重新加载、坐标与包络一致。503个受保护旧文件逐个哈希核对未变，涵盖V2、V3工作／冻结文件、插座和SIM-r03资产目录。

本版交付是分部件几何资产，未做布尔并集或新的碰撞分解；未调整插座，未重跑动态插入或BC／RL。此前成功率仍属于旧资产。

## 文件与复现

- [Blender](/data/omi_runtime/assets/optical_module_measured/r01/OM-001-MEASURED-r01.blend) · [OBJ](/data/omi_runtime/assets/optical_module_measured/r01/OM-001-MEASURED-r01.obj)（米制，配套MTL）· [GLB](/data/omi_runtime/assets/optical_module_measured/r01/OM-001-MEASURED-r01.glb)。
- [整体预览](/data/omi_runtime/assets/optical_module_measured/r01/preview.png) · [前端侧视](/data/omi_runtime/assets/optical_module_measured/r01/tip_side.png) · [实际mesh尺寸投影](/data/omi_runtime/assets/optical_module_measured/r01/dimensions.png)。
- [资产来源、参数和文件哈希](/data/omi_runtime/assets/optical_module_measured/r01/asset_manifest.json) · [切片与拓扑验证](/data/omi_runtime/assets/optical_module_measured/r01/validation.json)。
- `build_scripts/`保留构建、精度OBJ导出、验证和尺寸图脚本；构建脚本拒绝已有输出目录。重建需指定新的目录并保持相应脚本路径一致，不能直接覆盖此版。

后续先确认斜面轴向长度及实物测量位置，再在新装配修订中校准18.8 × 8.8 mm插孔，生成新的碰撞代理并重验动态接触。
