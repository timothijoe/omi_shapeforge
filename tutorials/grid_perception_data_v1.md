# 使用感知细网格数据 v1

[范围、标注、筛选与验证记录](../docs/agent/perception/evolution/grid-perception-data-v1.md)。查看器：`http://127.0.0.1:8895`。

运行目录：`/data/omi_runtime/runs/grid_perception_20261123_v1/`。

- 推荐主数据：`data_strict/records.jsonl`，14549张，训练12463／验证987／测试1099。
- 物理有效父集：`data/records.jsonl`，16251张。辅助样本不默认混入主集。
- 覆盖与缺口：`coverage.csv`、`coverage_by_grasp.json`；分层采样索引：`sampling_pools.json`。
- 每张主集记录包含RGB路径、可见掩码路径、实际位姿、请求／实际参数、几何参考点和检查信息。
- 共享点云模板：`network_templates/`链接原模板，模块37895点、插座204820点，按实际相机变换展开。
- `annotation_example_5964/`是已导出的完整单样本，包括RGB、mask、内参、实际标签、NPZ与PLY。

服务恢复：

```bash
python3 -m http.server 8895 --bind 127.0.0.1 --directory /data/omi_runtime/runs/grid_perception_20261123_v1
```

查看器顶部切换模块网格、插座平移、插座转角、孔口附近细网格。绿色状态为严格主集，黄色为物理有效辅助样本，红色为未收录组合；红色组合没有有效图像，不用其他帧替代。所有点云均为仿真标注，不是网络预测。

复制到其他机器时须一起恢复`shards/`、`data/`、`data_strict/`及共享模板和源资产；记录中的路径与符号链接需要按新根目录重建。不要只复制JSONL而漏掉图片／状态文件。

复现应使用新输出目录。从仓库根，用`omi_mesh_audit`环境依次执行：`build_grid_perception_plan.py`，8份`generate_grid_perception.py`，`audit_grid_perception.py`，`filter_grid_three_variable.py`，`verify_grid_render_replay.py`，`render_grid_perception.py`。脚本均在`scripts/perception/`，具体参数见能力记录与运行目录的源码快照。

本版未启动训练，sample_id不代表时间序列；密集插座层在零位模块训练组中，后续需按覆盖层／夹持格点平衡监督，并另设专门的插座组合与真机泛化验证。
