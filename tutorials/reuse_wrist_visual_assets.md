# 其他Agent复用腕部视觉资产

> 本机迁移提示（2026-11-24）：运行资源实体已迁至 `/data/shapeforge/runtime`；本文中的 `/data/omi_runtime` 是保留的兼容入口，指向同一份内容。目录映射与恢复要求见[当前资源契约](../docs/agent/interfaces/local-resources.md)。

当前已接受腕部视觉基线为[WVA-01「腕部实拍对齐版」](../docs/agent/simulation/evolution/wrist-visual-wva01.md)，读取[新清单](../manifests/wrist_visual_wva01_20261122.json)。下文保留WG-r10历史复现步骤；不要用下文旧路径替代WVA-01的r15资产。

先读[接入合同与边界](../docs/agent/simulation/evolution/wrist-assets-handoff.md)。固定版本入口是[机器可读清单](../manifests/wrist_visual_asset_handoff_20261122.json)，其路径及哈希优先于历史页面里的“最新”。

## 只读校验与加载参数

以下只使用Python标准库，不改模型或原输出：

```bash
python3 - <<'PYCODE'
from pathlib import Path
import hashlib, json
entry = Path('/home/linux/omi_folder/omi_shapeforge/manifests/wrist_visual_asset_handoff_20261122.json')
bundle = json.loads(entry.read_text())
for name, item in bundle['assets'].items():
    manifest = Path(item['manifest'])
    assert hashlib.sha256(manifest.read_bytes()).hexdigest() == item['manifest_sha256']
    delivery = Path(item['delivery_manifest'])
    assert hashlib.sha256(delivery.read_bytes()).hexdigest() == item['delivery_manifest_sha256']
    files = json.loads(delivery.read_text())['files']
    base = Path(item['directory'])
    for relative, digest in files.items():
        assert hashlib.sha256((base / relative).read_bytes()).hexdigest() == digest, relative
    print(name, item['identity'], len(files), 'files verified')
PYCODE
```

哈希不同先查版本／来源；不要更新期望哈希来掩盖差异。其他机器可从清单中的目录恢复资源，使用读入时路径映射；不要直接重写冻结清单。

## 查看

完整静态组合，支持自由旋转：

```bash
MUJOCO_GL=glfw /data/omi_runtime/envs/omi_mesh_audit/bin/python /data/omi_runtime/runs/wrist_primary_refinement_20261122/view_primary_scene.py
```

1自由视角，2针孔检查视角；默认隐藏侧栏。该程序不进行物理步进。鱼眼对照图：

```bash
/data/omi_runtime/envs/omi_mesh_audit/bin/python /data/omi_runtime/runs/wrist_primary_refinement_20261122/view_comparison.py
```

Blender、完整／独立GLB从bundle的`assets.*.files`加载。独立相机与夹爪保留TCP公共坐标；工具Blender有参考模块，工具GLB不含它。

## 在自己的新目录复现鱼眼渲染

原脚本含固定输出路径。以下复制脚本与试验配置，仅把**副本中的本轮运行目录**改到新目录，源资产引用保持只读；这是已实际验证的隔离方式。

```bash
/data/omi_runtime/envs/omi_mesh_audit/bin/python - <<'PYCODE'
from pathlib import Path
from datetime import datetime, timezone
import json, os, shutil, subprocess, uuid
entry = Path('/home/linux/omi_folder/omi_shapeforge/manifests/wrist_visual_asset_handoff_20261122.json')
bundle = json.loads(entry.read_text())
source_run = Path(bundle['reproduction']['source_run'])
suffix = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + uuid.uuid4().hex[:8]
work_run = Path('/data/omi_runtime/runs') / ('wrist_consumer_' + suffix)
work_run.mkdir(exist_ok=False)
shutil.copy2(bundle['reproduction']['trial_config'], work_run / 'trials.json')
script = Path(bundle['reproduction']['script']).read_text()
(work_run / 'render_final.py').write_text(script.replace(str(source_run), str(work_run)))
subprocess.run(
    [bundle['reproduction']['python'], str(work_run / 'render_final.py'), 'final'],
    env={**os.environ, 'MUJOCO_GL': 'egl'}, check=True,
)
print('New outputs:', work_run / 'final')
PYCODE
```

产物包括`audit_scene.xml`、`asset_same_pose_fisheye_1920.png`、分割图数组和`camera_render_report.json`。检查输出尺寸1080×1920×3、部件可见性、相机／模块变换及来源路径。不同机器的光栅边界可能有微小差异，不以PNG文件字节一致作为跨GPU唯一验收。

参考复现已运行于`/data/omi_runtime/runs/wrist_asset_handoff_check_20261122_181528/isolated_render/`，没有覆盖原结果。若要更改姿态或内沿方案，只修改自己的`trials.json`和脚本；显式记录新合同和差异。

## 自己加载静态XML时的初始状态

只加载XML不会执行展示脚本中的状态设置。若自行建立`MjModel/MjData`，应把插入关节设到登记的−2 mm，再`mj_forward`，否则模块与固定工具的相对位置会与对比图不同：

```python
import json, mujoco
from pathlib import Path
scene_info = bundle['static_inspection_scene']
model = mujoco.MjModel.from_xml_path(scene_info['path'])
data = mujoco.MjData(model)
physical = json.loads(Path(scene_info['physics_manifest']).read_text())
data.joint('insertion').qpos[0] = (
    scene_info['initial_insertion_depth_mm'] - physical['start_depth_mm']
) / 1000
mujoco.mj_forward(model, data)
```

这里是静态视觉状态，没有调用`mj_step`或机器人控制。显示时关闭geom group 3～5以隐藏碰撞代理，与已有渲染一致。

## 读取坐标约定

在有NumPy的`omi_mesh_audit`环境中：

```python
import json, numpy as np
from pathlib import Path
bundle = json.loads(Path('/home/linux/omi_folder/omi_shapeforge/manifests/wrist_visual_asset_handoff_20261122.json').read_text())
kit = json.loads(Path(bundle['assets']['tool']['manifest']).read_text())
T_tcp_from_module = np.eye(4)
T_tcp_from_module[:3, :3] = kit['tool_to_module']['rotation']
T_tcp_from_module[:3, 3] = kit['tool_to_module']['position_m']
cam = kit['camera']
T_tcp_from_camera_cv = np.eye(4)
T_tcp_from_camera_cv[:3, :3] = np.column_stack([
    cam['xyaxes_tcp'][:3], -np.asarray(cam['xyaxes_tcp'][3:]), cam['optical_forward_tcp']
])
T_tcp_from_camera_cv[:3, 3] = cam['optical_position_m']
T_camera_cv_from_module = np.linalg.inv(T_tcp_from_camera_cv) @ T_tcp_from_module
```

读取K／D用`kit['observation_projection']`。这不是每条真实样本的位姿标签；跨头部／腕部坐标还需对应样本的外参候选。

## 接入机器人或训练前

按[接入说明第4～7节](../docs/agent/simulation/evolution/wrist-assets-handoff.md)适配组件／颜色映射、IK／TCP、相机和17件模块索引。原`wrist_tool_scene.py`不能直接处理r10新增的相机组件。物理接触、工具惯量和新策略测试要在独立场景完成；本教程的静态复现不提供这些验收。
