# CLI 与 Python 入口

源码：[cli.py](../../../src/omi_shapeforge/cli.py)、[workspace.py](../../../src/omi_shapeforge/workspace.py)、[runner.py](../../../src/omi_shapeforge/runner.py)、[workflows.py](../../../src/omi_shapeforge/workflows.py)。控制层仅依赖标准库。

```text
omi-shapeforge [--config CONFIG] doctor
omi-shapeforge [--config CONFIG] smoke {stereo,bundlesdf} [--output OUTPUT]
omi-shapeforge [--config CONFIG] simulate mujoco [--scene SCENE] [--steps STEPS] [--output OUTPUT]
omi-shapeforge --version
```

`--config` 是顶层参数，须放在子命令前。当前没有 Isaac、配准、Blender 或硬件控制子命令。默认 MuJoCo 场景来自 `simulations.mujoco.scene`，当前模板指向已有 2×2 场景。

## doctor

只检查配置中的路径与可执行解释器。两个后端检查 repository、python、entrypoint，stereo 另查 checkpoint，bundlesdf 另查 nvcc；已配置的 MuJoCo 检查 python、entrypoint 和 scene。全部存在则 ready=true、退出 0，否则退出 1。Git 来源读取失败单独记录，不改变路径就绪结论。

不检查全部动态库、场景传递依赖、GPU 运算、模型或机器人能力。工作流执行时会进一步读取实际输入和引用文件。

## smoke 与 simulate

ENG-003 已接入[运行合同 v1](run-contract.md)。保留原两个 smoke 调用形式，但新输出布局为 `run_manifest.json`、`run.log`、`inspection.log` 和 `backend/`；后端原始 report／图像／数组写在 backend 中。输入、源码和产物记录路径及哈希，MuJoCo 另写 `inputs.json` 保存场景依赖集合。

输出目录必须尚不存在；指定 `--output` 便于定位。省略时在配置的 run_directory 下创建 UTC 时间与随机后缀目录，终端清单的 `execution.command` 包含实际 backend 输出位置。

新清单不再提供旧的顶层 `status/returncode/output/config`。执行状态在 `execution`，产物检查在 `validation`，任务验收在 `acceptance`；参数在 `parameters`，版本在 `sources/environment`。只有三项均通过才返回 0。

退出码：0=通过，1=工作流执行或检查失败，2=命令参数、配置读取或输出目录等调用错误，130=用户中断。任务准备开始后发现输入缺失，会保留 failed 清单并返回 1。已有输出目录拒绝时不写入该目录。

原始进程返回 0 但缺报告、报告不符、文件越界或内容错误，execution 仍为 succeeded，validation 为 failed，acceptance 不求值。检查器在对应环境解码数组／图片／点云及 MuJoCo 状态；控制器核对必需文件、哈希与边界。结果写入 `backend/inspection.json`。

Ctrl+C 会向所拥有的进程组发送中断；无响应时终止并回收，保存终态。若后端处理中断后实际退出 0，则保留该真实进程结果，但不执行验收，CLI 仍返回 130。SIGKILL／断电可能留下 running 记录，不能据此判断完成。

## Python 与范围

`load_config()`、`doctor()` 和 `run_smoke()` 保留；后者现在返回 v1 字典。`workflows.launch()` 为三个流程准备命令与输入，`runner.run_task()` 管理进程和记录。这些仍是项目内部 API。

MuJoCo 接口只验收当前生成的自由刚体光模块原型，不是通用机器人场景验收器。Blender、Isaac、便携配准仍按独立脚本教程运行。旧报告继续原样保存，批量转换器尚未实现。
