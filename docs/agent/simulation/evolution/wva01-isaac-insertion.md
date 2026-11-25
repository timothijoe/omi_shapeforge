# WVA-01新版夹爪的Isaac插入展示与资产核对

2026-11-25完成，工作始于2026-11-24。用户要求记录旧视频实际版本，使用新版夹爪，并检查其他资产是否遗漏更新。

**已交付r15外观／原UV标志纹理＋GC-r01闭合参考装配的固定夹持插入视频。自由接触夹持的完整PhysX移植仍未通过移动验证，不计入已验收版本。** 本组合身份为 `SC-WVA01-ISAAC-FIXTURE-r01`，不重命名原WVA-01、GC-r01或光模块版本。

## 成片与逐项核对

[新版视频](/home/linux/Downloads/机器人插接_WG-r15新版夹爪_三视图_20261125.mp4) · [封面](/home/linux/Downloads/机器人插接_WG-r15新版夹爪_封面_20261125.png) · [实际编码帧预览](/home/linux/Downloads/机器人插接_WG-r15新版夹爪_过程预览_20261125.jpg)。18.0667秒、1920×1080、30fps、542帧、2,569,757字节。三个主视图、深浅灰普通面、橙色尖端、绿色孔口及标注3×回放沿用用户认可的展示约定。

| 项目 | 原r2～r5视频 | 本版实际选择／核对 |
| --- | --- | --- |
| 夹爪 | WG-DAIMON-OBS-r10 | **WG-DAIMON-LOGO-r15**，WVA-01固定清单，49件原网格 |
| 标志材质 | 转译没有原UV／PNG | 两侧银壳原UV与DAIMON PNG接入USD，实际腕部与近景渲染已查看 |
| 模块 | OM-001/V4-r08 | 已是当前组合使用版，保留原几何和U形拉环 |
| 插座 | SIM-r06／M1888来源 | 与当前采用组合一致；保留staged／smooth-guide碰撞和任务判据 |
| 相机 | 既有TCP安装、OpenCV鱼眼K／D | 与r15清单逐项相同，保留；没有新标定结论 |
| 机器人 | 原URDF | 与工作区当前同名URDF SHA256一致，保留 |
| 夹持装配 | 旧固定参考变换 | 更新为GC-r01 `gravity_hold`实际闭合参考及对应夹指位置；**仍是固定插入夹持** |
| 点云模板 | 当前模块／插座可见mesh采样 | 从选定新packet重新生成，点坐标／法向／重点等级与原模板一致，因为对象几何已是当前版 |

PCG-01是另一个匹配用途的纯几何交付范围，去掉支架和外观，不是本片完整视觉／碰撞模型的新替代版。不能按目录日期或编号盲换。光模块独立r05暂定外观基线的历史身份也不因组合使用r08而重写。

## 实际数据链与验证

运行根：`/data/shapeforge/runtime/runs/insertion_asset_upgrade_20261124_r6/`。

- `old_video_version_record.json`：旧成片→捕获→transfer→WG-r10的真实身份与哈希，旧视频保留；此前用户认可的是排版，不表示r10是最新版。
- `fixture_transfer/`：选定的新场景packet，**`wva01-closed-reference-fixture-v1`**，模块为TCP固定子体，`free_bodies=[]`。未启用实验自由夹持或额外接触力模型。
- `fixture_physics/`：实际新跑PhysX CPU／PGS／5子步／原厂IK，一次reset；586控制状态全部保留，从第117步起连续470状态进入影片。
- `fixture_capture/`：同状态RTX三机位／腕部六面图，RGB和深度；原纹理参与实际几何渲染，没有在图片上粘贴标志。
- `fixture_templates/`：模块42,441点、插座212,308点，普通0.8mm、重点0.2mm；绿色活动附件不属于刚性目标点云。
- `film/film_manifest.json`：542帧逐帧来源与资产身份；`quality_check.json`、`fixture_validation.json`和源码快照保存核对。

起始横向偏差18.623mm、角度2.504°，在孔口外对准后再进入；最终深度51.281185mm，原入口资格和稳定落座条件通过，worker退出0。全部470状态按原顺序进入3×回放，无跨回合拼接或位姿插值。FK TCP相对源测量最大差约0.480微米，重算深度最大差0.000306mm，均为仿真回放一致性，不是实物精度。

FFprobe尺寸／帧数／时长一致，FFmpeg全片解码通过；9个实际编码帧与同状态合成的RGB平均绝对差约1.53～1.61／255，已查看新版指尖和标志、阶段、同步与点云配色。轻量92项29通过、63可选依赖跳过、0失败；新合同／接触目标数学检查8项在几何环境全部通过。渲染工具会话在`FILM_COMPLETE`之后报告143，成片及manifest完整并独立解码／哈希验证；不把该shell回执记为正常退出0。

点云仍是仿真几何位姿参考，画面遵循用户要求写“几何位姿估计”。未运行网络估计、训练新感知模型或更新BC／RL。

## 自由接触夹持候选：未通过完整移动验证

`transfer_r1`～`transfer_r10`、`grasp_smoke_*`及`physics_updated_*`／`run*`保留了独立GC-r01 PhysX移植尝试，**它们不是成片选用的场景**。原插入代理缺少夹爪接触的模块后段，因此候选从旧分解碰撞几何截取后段，视觉源mesh不改；尝试过TGS、细步长及受法向接触力限制、具有成对反作用的软指摩擦近似，无连续写模块位姿或模块固定关节。

静止保持／释放单测通过过：例如`grasp_smoke_18_soft_finger`最大相对滑移约0.00931mm、转角约0.00924°，松开后重力下落约50.24mm；但移动阶段超出原0.1mm相对滑移门槛，完整自由夹持插入未通过。失败不改判，没有放宽原插入任务阈值，也没有用局部通过替代完整回合成功。

引擎接触参数不能直接按名称等同。扭转patch等参数有求解器／接触锚点条件，见[NVIDIA PhysX形状接口说明](https://nvidia-omniverse.github.io/PhysX/physx/5.5.0/_api_build/classPxShape.html)。候选的接触近似与原MuJoCo局部GC-r01验证另存，不宣称同精度移植或真实夹持认证。最终交付明确选择固定夹持合同，画面也标注“固定夹持插入演示”，不会伪装成自由接触夹持已验收。

## 恢复与保留

[资源清单](../../../../manifests/wva01_isaac_insertion_20261125.json)记录全部资产核对、输入／代码／成片SHA256；`manifests/resources.json`只做资源索引，不是自动下载器。恢复成片直接保留MP4；恢复实验至少包括选定transfer、原始轨迹、捕获、模板和环境，并恢复r15两张PNG在packet引用的路径（或验哈希后显式重绑）。原r15／r08／GC-r01源文件与旧transfer、旧视频均保留。

在仓库根复现，使用全新输出目录：

```bash
# 选定已保存的新版固定夹持packet；不选择实验自由夹持packet。
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  /data/omi_runtime/envs/foundation_stereo/bin/python scripts/simulation/record_alignment_insertion.py \
  --transfer /data/shapeforge/runtime/runs/insertion_asset_upgrade_20261124_r6/fixture_transfer \
  --asset-contract wva01-closed-reference-fixture-v1 --physics-substeps 5 --output <NEW>/physics

/data/isaac-sim-5.1.0/python.sh scripts/simulation/capture_insertion_multiview.py \
  --transfer /data/shapeforge/runtime/runs/insertion_asset_upgrade_20261124_r6/fixture_transfer \
  --case <NEW>/physics/case --worker <NEW>/physics/worker --output <NEW>/capture

OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  /data/omi_runtime/envs/foundation_stereo/bin/python scripts/perception/render_alignment_film.py \
  --capture <NEW>/capture \
  --templates /data/shapeforge/runtime/runs/insertion_asset_upgrade_20261124_r6/fixture_templates \
  --output <NEW>/film --playback-rate 3
```

旧legacy-r10仍为历史训练worker默认合同，未自动迁移旧检查点或把其成绩计入本场景。新版视觉与参考装配接入已完成；完整自由接触夹持及真实相机／惯性标定仍是独立未完成范围。
