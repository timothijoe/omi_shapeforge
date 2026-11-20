# 双目与组件样例

前提：已通过[环境检查](environment_setup.md)，使用本机验证过的后端适配。以下为已安装 CLI；显式配置时把 `--config` 放在子命令之前。

## 官方双目样例

```bash
.venv/bin/omi-shapeforge smoke stereo
```

默认输入来自 FoundationStereo 的 `assets/left.png`、`right.png` 和 `K.txt`，权重由主配置指定。当前包装器不暴露换图、迭代次数或分辨率参数；这些不是主 CLI 支持的选项。

预期：960×540 图像的视差／米制深度／点云及两层运行报告。查看 `vis.png`；点云可用支持 PLY 的查看器打开。主包装器不会自动生成 Plotly HTML。

## BundleSDF 组件

```bash
.venv/bin/omi-shapeforge smoke bundlesdf
```

预期生成 `loftr_matches.jpg`、对应点数组和 `report.json`，后端状态为 `passed_cuda_kernels_cpp_bindings_and_real_loftr_matching`。这一步检查编译模块、GPU 运算和真实图像匹配，不运行完整视频重建。

可用 `--output` 指定新路径。已有目录拒绝，失败时先读 `run.log` 与清单；Ctrl+C 后换新目录重跑。算法范围和本机证据见[能力说明](../docs/agent/perception/evolution/stereo-and-backends.md)。
