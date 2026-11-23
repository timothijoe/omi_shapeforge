# 2026-11-22：新采集数据接收与初检

原始说明、开发阶段记录与采集操作文档现已同步至[本项目文档目录](../data/nov22/README.md)，可直接在docs内查阅；[同步清单](../../manifests/nov22_docs_sync.json)。

用户提供`/data/zt-think-d1-data/nov_22/`，已阅读备份README、CURRENT_DATA_OVERVIEW、TODAY_DEVELOPMENT、COMPLETE、代表样本元数据和两段工具录制的原QC。采集日期为2026-11-21至22日凌晨，保留原始时间。未覆盖现有源码、模型或原始数据。

## 实际位置与内容

本机备份根目录：`/data/zt-think-d1-data/nov_22/session_backup_20261121_20261122_20261122_014108/`。下列路径均相对该根目录：

| 数据 | 位置 | 数量／用途 |
| --- | --- | --- |
| 头部与腕部按键四图 | `captures/BundleSDF_trial/datasets/units/` | 15单元287组；每组头部RGB、腕部RGB、左右IR，共1148图和287份sample.json |
| 戴蒙手／相机外部建模录制 | `captures/FoundationStereo/DATA/recordings/` | 两段约30秒MCAP，D435 RGB＋左右IR＋原生深度；不是两路机器人动作示范 |
| 点云、QC与采集日志 | `session_results/` | 已有五组离线点云及两段建模录制抽样QC等，未把全部点云重新评审 |
| 文档／源码／模型快照 | `documentation/`、`development/`、`models/` | 采集机器的历史来源；不能覆盖本工作区当前状态 |

同级`capture_tools_handoff_20261122_015025/`包含程序ZIP与操作说明，可用于研究采集格式；原脚本有旧机器路径，未直接启动或覆盖当前代码。

## 本机实际执行的检查

15单元样本数依次为31、17、11、11、12、12、18、21、20、30、12、11、20、36、25，合计287。逐张读取1148张图，与sample.json里的SHA256比对，检查PNG完整性与尺寸，错误数0。RGB为1920×1080，IR为1280×720；图像字节合计1,318,216,548（不含sample.json和单元清单）。

全部287份元数据均为`training_label_valid=false`、`mesh_pose=null`、`wrist_calibration=null`、`exposure_synchronization_verified=false`。腕部时间代表完整JPEG接收时刻，不能直接当曝光同步时刻；静态采集请求也不能替代稳定性实测。

抽看unit_001／005／010／015中间样本的头部和腕部图，能看到模块／孔口相对位置与视角变化；另看两段工具录制已有QC的sample_07，含夹爪侧面及相机外壳。仅为代表帧人工查看，不是全数据姿态、清晰度或覆盖验收。

- [初检报告](/data/omi_runtime/runs/nov22_data_intake_20261122/report.json)
- [代表图总览](/data/omi_runtime/runs/nov22_data_intake_20261122/sample_overview.jpg)
- 检查脚本：`/data/omi_runtime/runs/nov22_data_intake_20261122/inspect_data.py`。

两段MCAP文件大小分别4,704,110,192和4,961,569,511字节，已核对存在。原QC记录全消息解码通过、四路同header时间戳组数688＋651＝1339，且有丢帧／间隔不均匀情况；**本次没有重新读取或哈希整个MCAP，也没有运行整包verify_backup.py**。COMPLETE中的3662文件完整校验属于原备份阶段证据。

## 标定、版本与恢复注意事项

四图样本自带头部标定和双目基线；两段工具录制来自SN 152122075750，并明确要求用各自录制标定，不能复用旧相机。代表四图样本双目基线约50.142 mm，工具录制约49.975 mm，应分别读取各自元数据。

我们已有`/home/linux/Downloads/img/wrist_intrinsics_1920x1080.json`，但新批次元数据未绑定该文件；需核实相机、输出模式和配置一致性后再复用，当前不能把null悄悄补成已标定。外参／夹持变换仍需建立。

备份里的“当前V2”是采集机器历史状态，样本mesh_reference也指向V2；本工作区暂定几何基线V4-r05和展示候选r07保持不变。原JSON中的`/home/zhoutong/...`与`/media/zhoutong/...`路径保留，只在加载时映射到本机备份根，不重写原数据。旧/mnt/sfs迁出归档不属于本次已核验内容。

## 与当前工作衔接

1. 287组可用于真机双视角外观对比、相机投影检查、前景／遮挡分割和任务状态覆盖审阅。先按单元查看模块、孔口、夹爪及开度变化，再决定训练／验证划分。
2. 两段MCAP用于夹爪与安装相机的多视角几何补充。先筛选清晰和完整四路帧，使用本录制标定做深度／前景和配准检查，再另建资产；黑色表面、模糊、隐藏面仍可能限制重建。
3. 此批正式样本尚无可靠6D监督，也不是已标注动作／奖励的连续BC episode。若要训练控制策略，仍需动作、状态、时序及接管记录；不能直接把287张采样组算作287条完整示范。
4. 额外marker按用户既有要求不作为模块视觉策略依据。扫描包的marker程序可用于独立研究，不表示自动启用贴纸监督。

当前仅完成数据接收初检与来源登记，未训练、重建工具mesh或修改实时仿真。[此前完整仿真进展](2026-11-22-simulation-mesh-visual-progress.md)中的成绩和限制保持原范围。
