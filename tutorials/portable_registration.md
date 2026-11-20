# CPU 复跑光模块已确认区域配准

前提：已解压 portable 包；Python 中有 NumPy 1.26.4、SciPy 1.17.1、Open3D 0.19.0。该任务不需要 CUDA、ROS、相机或 Blender。

以下变量按实际资源目录填写，当前本机可用值为：

```bash
RUNTIME_ROOT=/data/omi_runtime
PACKAGE="$RUNTIME_ROOT/inputs/optical_packages_20261120_001316/optical_module_portable_20261119"
MATCH_PYTHON="$RUNTIME_ROOT/envs/foundation_stereo/bin/python"
RUN_DIR="$RUNTIME_ROOT/runs/portable_$(date +%Y%m%d_%H%M%S)"
"$MATCH_PYTHON" "$PACKAGE/scripts/verify_package.py"
CUDA_VISIBLE_DEVICES='' "$MATCH_PYTHON" "$PACKAGE/scripts/run_demo.py" --output "$RUN_DIR"
CUDA_VISIBLE_DEVICES='' "$MATCH_PYTHON" "$PACKAGE/tests/check_replay.py" --run "$RUN_DIR"
```

预期首先校验 62 个清单文件，随后生成新配准和自包含 `overlay.html`。独立检查状态为 `passed_independent_replay_checks`。打开新 HTML，查看 `fit/selected_candidate.json`、`qa/surface_checks.json` 和 `qa/independent_replay_check.json`。

页面设计为左键旋转、Shift+左键平移和滚轮缩放，不要求鼠标中键；当前尚未完成浏览器交互验收。

该样例已由用户圈选目标。检查点残差参考中位数约 0.148 mm、P90 约 0.731 mm；全部原始圈选点的 P90 约 2.771 mm，需一起看。不同平台可改变近似候选排序，不能仅因矩阵或低残差相似就认定方向正确。

这是包内 Python 文件入口，尚无同名主 CLI 子命令。`--open` 会请求浏览器；默认不打开。Ctrl+C 后保留失败目录并换新 RUN_DIR，不复用旧结果。更换物体／场景需要重新定义 ROI 与模型，不能直接沿用此样例先验。
