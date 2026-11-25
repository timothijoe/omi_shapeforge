# Isaac PhysX 后台运行

> 本机迁移提示（2026-11-24）：运行资源实体已迁至 `/data/shapeforge/runtime`；本文中的 `/data/omi_runtime` 是保留的兼容入口，指向同一份内容。目录映射与恢复要求见[当前资源契约](../docs/agent/interfaces/local-resources.md)。

前提：本机已安装 Isaac Sim 5.1.0，所有所需本地扩展完整；场景 USD 由本项目生成。使用供应商 `python.sh`，不用主 venv 或 MuJoCo venv 启动。

先从主环境查看参数，help 不启动 Isaac：

```bash
.venv/bin/python scripts/simulation/run_isaac.py --help
```

实际执行使用新目录，并设置启动时间上限：

```bash
RUNTIME_ROOT=/data/omi_runtime
ISAAC_ROOT=/data/isaac-sim-5.1.0
SCENE_DIR="$RUNTIME_ROOT/assets/optical_scene_v2_20261120"
RUN_DIR="$RUNTIME_ROOT/runs/isaac_$(date +%Y%m%d_%H%M%S)"
timeout --signal=TERM --kill-after=15s 90s \
  env -u CONDA_PREFIX -u CONDA_DEFAULT_ENV -u PYTHONHOME -u PYTHONPATH -u LD_LIBRARY_PATH \
  "$ISAAC_ROOT/python.sh" scripts/simulation/run_isaac.py \
  --isaac-root "$ISAAC_ROOT" --scene "$SCENE_DIR/scene.usda" \
  --output "$RUN_DIR" --steps 240 > "$RUN_DIR.log" 2>&1
```

预期状态为 `passed_isaac_physx_load_step_and_settle`，并有 `states.json`、`settled.usda` 和 `report.json`。脚本实际 attach stage、步进并验证下落、稳定和台面支撑。单模块和 2×2 都有已有验收记录。

这是 PhysX CPU 物理测试，`renderer_executed` 为 false，不输出 RTX 相机图像。不要把它当作 GUI 或渲染器验收。当前不能用“已安装 6.0.1”推导该版本已测试。

按 Ctrl+C 停止，或由 timeout 终止超时进程；中断后保留日志并换新 RUN_DIR。只凭退出状态、目录存在或已有中间文件不能认定通过。扩展解析失败可能发生在报告写入前，首先查看 `$RUN_DIR.log`。
