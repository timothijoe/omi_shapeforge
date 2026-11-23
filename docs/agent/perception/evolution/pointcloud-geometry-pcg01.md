# PCG-01：点云匹配纯几何版

本页是PCG-01的**能力纪传体和主阅读入口**；按时间记录的需求、处理和交付经过见[编年体](../chronicles/2026-11-23-pointcloud-geometry.md)。本次归档涵盖版本核对、文件／内存口径、纯几何提取、可视化、独立打包及复用范围。

## 需求与版本关系

用户要求从现有模块／插口资产中单独提取点云匹配几何，不带颜色，并在看到三维可视化后要求保存为可以直接复制的文件。

前置版本／物理尺寸清点见[模块与插口尺寸速查](../../simulation/evolution/module-socket-dimensions.md)。随后用户澄清“大小”指内存空间，因此不能再用毫米尺寸回答：原完整V4-r08 GLB为747,044字节，M1888-r01 GLB为1,948,136字节，合计2,695,180字节；这只是磁盘文件大小，不是运行时RAM或显存。PCG-01按新的纯几何范围单独导出，既去掉外观字段，也排除指定附件；体积降低不能全部归因于去颜色。

| 名称 | 作用 | 与本版关系 |
| --- | --- | --- |
| OM-001/V4-r08 | 带外观和U形拉环的光模块资产 | 提供15件刚性匹配主体，原资产不改 |
| SIM-OM001-OS001-r06 | 插槽视觉／碰撞仿真组合 | 只提取112件固定上部视觉几何，不带碰撞代理 |
| WVA-01 | 已接受的腕部视觉组合 | 保留，PCG-01不替换其带材质场景 |
| GC-r01 | 双黑胶垫接触夹持场景 | 保留，PCG-01不是新的夹持或动力学版本 |
| PCG-01 | 独立、无颜色的匹配几何文件 | 当前可复制交付包 |

## 交付与保留范围

已交付[独立文件夹](/home/linux/Downloads/PCG-01)和[ZIP压缩包](/home/linux/Downloads/PCG-01.zip)。ZIP约0.915MB，含两个无颜色mesh、压缩几何数组、灰色预览、便携查看脚本、说明及哈希；复制后不依赖原工程或原资产路径。查看脚本需要Python／Open3D环境，PLY可直接交给其他支持该格式的软件。详见[包内说明](/home/linux/Downloads/PCG-01/README.md)。

| 对象 | 保留范围 | 顶点／三角面 | PLY文件 | 顶点＋索引数组内存 |
| --- | --- | --- | --- | --- |
| 光模块 | V4-r08刚性主体15件，排除绿色U形拉环及假设内部阴影块 | 2019／3954 | 75,876字节 | 71,676字节 |
| 插口 | SIM-r06固定上部112件，保留框架、金属槽、PCB、小支柱，排除下方大支架 | 12992／25628 | 489,316字节 | 463,440字节 |

插口按本轮明确说明的默认范围去除大支架，保留的是“上部装配”，并非只剩金属孔口。未打包夹爪、相机、机器人、真实采集照片或原始扫描点云。

## 几何与数据合同

这里只提取现有几何，不做减面、平滑或新建模；保留每个对象原始米制坐标、原点和尺寸。两份PLY只含float32 XYZ与三角面索引，无RGB、UV、法向、材质和纹理。NPZ只含`vertices_m`和`faces`；需要法向时由几何计算。数组内存合计535,116字节，不含运行环境、采样点、KD-tree或渲染器。

PLY采用binary little-endian；NPZ中`vertices_m`为N×3 float32，`faces`为M×3 int32。它们仍是网格，不是均匀点云模板。两个文件分别位于各自原始物体坐标系，未做装配／配准；不能直接叠放就认为模块已插入插口。复用时应用对应的`T_camera_from_object`或`T_world_from_object`。

## 存储与内存

| 项目 | 精确字节数 | 十进制MB |
| --- | ---: | ---: |
| 两份PLY | 565,192 | 0.565 |
| 两份NPZ压缩文件 | 178,636 | 0.179 |
| 两对象加载为顶点＋三角面数组 | 535,116 | 0.535 |
| 可复制文件夹，含预览／脚本／说明 | 1,335,147 | 1.335 |
| ZIP交付包 | 914,836 | 0.915 |

数组字节数按dtype和shape计算，不能当作整个Python／Open3D进程的RSS或显存实测。PLY与NPZ是同一几何的两种保存方式，通常选择一种加载即可，无需同时加载以重复占用内存。

## 验证与可视化

原文件的选中顶点／三角面逐项核对通过，只有float32坐标表示的舍入，最大坐标差低于0.000004mm；源mesh哈希不变，Blender导入确认没有颜色属性或材质槽。ZIP逐文件哈希与解压完整性通过。[登记](../../../../manifests/pointcloud_geometry_pcg01_20261123.json) · [验证](/data/omi_runtime/assets/pointcloud_matching/PCG-01/validation.json)。

已打开Open3D窗口，用户反馈已经看到。窗口用统一灰色光照显示；M网格、P临时采样点云、1模块、2插口、3两者。并排显示只平移显示副本，不修改文件；点云来自mesh采样，不是传感器实测点。

Open3D并排查看使用同一米制比例；P模式临时采样模块12,000点、插口30,000点，没有颜色，不写回交付文件。[预览图](/home/linux/Downloads/PCG-01/preview.png)则是两对象独立取景，不能据其画面大小比较物体实际比例。默认灰色是查看器光照，不是写入mesh的顶点色。

## 直接复制和读取

直接复制`/home/linux/Downloads/PCG-01.zip`，或整个`/home/linux/Downloads/PCG-01/`文件夹。包内11个文件：`module.ply`、`socket.ply`、`module.npz`、`socket.npz`、`preview.png`、`asset_manifest.json`、`validation.json`、`view_geometry.py`、`requirements-viewer.txt`、`README.md`、`SHA256SUMS.json`。

包内查看器用`Path(__file__).resolve().parent`定位PLY；原资产路径只在工程来源记录中使用，不是交付包的运行依赖。运行环境验证为Python3.11.15、NumPy1.26.4、Open3D0.19.0；直接读NPZ只需NumPy，可选交互查看器需要Open3D。

```python
from pathlib import Path
import numpy as np

package = Path('/复制后的目录/PCG-01')
with np.load(package / 'module.npz', allow_pickle=False) as data:
    vertices_m = data['vertices_m']
    faces = data['faces']
```

查看命令为`python /复制后的目录/PCG-01/view_geometry.py`。包内`SHA256SUMS.json`记录其他10个文件的哈希；整个ZIP的SHA256为`6215ae794b4b29d31e0a3640c9af6048ffba496632f057debb40cbea834c0d7f`。迁移后可按文件哈希核对，不要修改已登记版本来掩盖差异。

## 边界与接续

当前插口默认排除大支架，因此不同于以前包含支架的完整点云训练模板；没有自动替换旧模板、训练数据、网络或仿真场景。模块主体沿用既有匹配目标范围，旧带材质资产、WVA-01和GC-r01保持不变。没有新增ICP、点云匹配精度或训练验收。

这里的“没有新增训练”仅指PCG-01导出工作，不否定其他并行主线已完成的感知或BC／RL实验。若将本版换入现有模板／网络，需重新核对部件范围、坐标和点数合同；需要刚性配准时应单独保存配准实验，而非把导出一致性当作匹配精度。

源纯几何目录`/data/omi_runtime/assets/pointcloud_matching/PCG-01/`；提取、验证、预览与打包脚本在`/data/omi_runtime/runs/pointcloud_geometry_20261123/`。

本窗口完整接续上下文另见[外观／接触／纯几何交接](../../../chronicles/2026-11-23-mesh-contact-pcg-window-handoff.md)，包含WVA-01、GC-r01、PCG-01关系和恢复命令。
