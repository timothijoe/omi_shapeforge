# 最短可运行案例

> 本机迁移提示（2026-11-24）：运行资源实体已迁至 `/data/shapeforge/runtime`；本文中的 `/data/omi_runtime` 是保留的兼容入口，指向同一份内容。目录映射与恢复要求见[当前资源契约](../docs/agent/interfaces/local-resources.md)。

前提：按[环境教程](environment_setup.md)准备所选后端的源码、解释器与资源。

```bash
.venv/bin/omi-shapeforge doctor
RUN_DIR="/data/omi_runtime/runs/stereo_$(date +%Y%m%d_%H%M%S)"
.venv/bin/omi-shapeforge smoke stereo --output "$RUN_DIR"
```

第一条只做路径体检；第二条实际启动 GPU 推理与独立产物检查。RUN_DIR 必须不存在。主清单、运行日志和检查日志位于 RUN_DIR；后端报告、视差、深度、点云和预览位于 `backend/`。

验收看 `run_manifest.json` 的 `execution.state=succeeded`、`validation.status=passed`、`acceptance.status=passed`。原后端报告为 `backend/report.json`，检查结果为 `backend/inspection.json`，预览为 `backend/vis.png`。旧格式的顶层 status／output 不再出现在新清单中。

使用现有 2×2 光模块场景：

```bash
.venv/bin/omi-shapeforge simulate mujoco --steps 240
```

这条命令使用独立 simulation 环境，默认场景来自配置。实际物理假设与范围见[MuJoCo 教程](mujoco_scene.md)。

Ctrl+C 会停止所拥有的子进程并保留已有记录；下一次使用新目录。查看[已有图册](../docs/visual-results.md)无需重新运行；无 GPU 时可使用[便携 CPU 配准](portable_registration.md)。
