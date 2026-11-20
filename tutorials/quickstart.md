# 最短可运行案例

前提：主环境已安装，两个后端源码／环境／权重已按配置准备。缺少它们时先读[环境教程](environment_setup.md)。

```bash
.venv/bin/omi-shapeforge doctor
.venv/bin/omi-shapeforge smoke stereo
```

第一条只做路径体检；第二条实际启动 GPU 推理。默认配置把结果写入 `/data/omi_runtime/runs/omi_shapeforge/` 的新 UTC 时间目录，终端 JSON 中可找到 `output`。

预期有 `run_manifest.json`、`run.log`、`report.json`、`vis.png`、`disparity.npy`、`depth_meter.npy`、`cloud.ply`。主清单 status 为 passed，后端 report status 为 `passed_real_gpu_stereo_inference`。

运行中按 Ctrl+C 可停止，保留已有日志，下一次使用新目录。不要把单样例输出解释为光模块原始数据或真实深度精度验收。

无 GPU 时可按[便携 CPU 配准](portable_registration.md)使用现成点云；查看已有结果也无需重新推理。
