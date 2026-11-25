# 查看 V3 与插接座的插入关系

> 本机迁移提示（2026-11-24）：运行资源实体已迁至 `/data/shapeforge/runtime`；本文中的 `/data/omi_runtime` 是保留的兼容入口，指向同一份内容。目录映射与恢复要求见[当前资源契约](../docs/agent/interfaces/local-resources.md)。

使用 Open3D，不需要打开 Blender 界面：

```bash
cd /home/linux/omi_folder/omi_shapeforge
/data/omi_runtime/envs/foundation_stereo/bin/python \
  scripts/simulation/view_v3_insertion.py \
  --run /data/omi_runtime/runs/v3_socket_r04_20261120T082303Z
```

默认展示用户要求略放宽后的 **r04（通道宽 19.00 mm）**，V3 位于约 51.28 mm 的头部台阶限位位置，并显示完整下部支架。点击“入口”“弹片接触”“接近终点”“台阶限位”或修改深度。左键旋转，滚轮缩放，Ctrl＋左键平移；可切换整体、孔口、侧面和俯视，或使用“显示下部支架”“显示白色壳体”开关。

当前 19.00 mm 比 r03 的 18.60 mm 每侧多留 0.20 mm，相对 V3 名义单侧间隙约 0.41 mm；白色孔口同步为 20.60 mm。它是用户要求下的检查候选，未做内孔图像／点云定量拟合，模块自身的尺寸误差也未排除。原 20.90 mm 也未经内孔独立实测。以全刚体处理弹片会在约 4.21 mm 出现相交；窗口显示深放置不代表弹性插装已验收。完整[几何解释和证据](../docs/agent/simulation/evolution/v3-insertion.md)。

若需对照 r03，将 `--run` 改为 `/data/omi_runtime/runs/v3_socket_insertion_20261120T073119Z/narrow_candidate`；r01 基准则使用该路径的父目录。各目录的模型、源哈希和碰撞报告分别保留。

实现入口：`export_insertion_inputs.py` 由 Blender 后台导出实际求值分件；`audit_v3_insertion.py` 由 Blender 后台执行表面相交检查；各运行目录的 `verify_geometry.py` 执行包含／采样距离／截面检查，`finalize_contract.py` 保存相对变换。新计算必须使用新输出目录，不能覆盖旧实验。V3 原工作文件未在本轮改形。
