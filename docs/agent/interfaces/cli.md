# CLI 与 Python 入口

源码：[cli.py](../../../src/omi_shapeforge/cli.py)、[workspace.py](../../../src/omi_shapeforge/workspace.py)。安装后命令 `omi-shapeforge` 与 `python -m omi_shapeforge` 调用同一 `main()`。

```text
omi-shapeforge [--config CONFIG] doctor
omi-shapeforge [--config CONFIG] smoke {stereo,bundlesdf} [--output OUTPUT]
omi-shapeforge --version
```

`--config` 是顶层参数，放在子命令前。当前没有 `simulation`、`register`、`blender` 或硬件 CLI 子命令。

## doctor

输出 JSON，路径检查全部为真则退出 0，否则 1。检查项为：后端目录、可执行 Python、入口脚本；stereo 另检查 checkpoint 文件，bundlesdf 另检查 nvcc 文件。Git HEAD、状态和哈希记录在 `backends`。

它不导入后端，不检查 CUDA 运算、动态库、模型内容哈希、Blender、仿真或机器人资产。Git 读取错误会进入 `backends.*.error`，不会单独改变 `ready` 的路径判定。

## smoke

只要求所选后端的路径检查通过；为两个后端配置建立独立子进程，避免 shell 字符串拼接。默认使用 UTC 时间新目录，已有输出拒绝。标准输出为主项目运行清单；后端日志进入文件。

`returncode != 0` 为失败；零退出码还要读取 `report.json` 并匹配状态。缺报告、坏 JSON 或状态不符也不能通过。目录和初始清单写入后，后端调用及报告检查阶段会在 finally 中补记结束状态；若创建目录或初次写清单本身失败，可能没有完整记录。CLI 捕获常见配置／文件错误退出 1；用户中断等异常可能仍显示 traceback。

## Python 边界

`load_config(path)` 解析配置，`doctor(config)` 只读诊断，`run_smoke(config, name, output)` 有进程与文件副作用，返回运行清单；`git_snapshot()` 生成来源快照。这些是当前内部控制层函数，尚未定义稳定的第三方 Python API。

直接仿真脚本的真实参数见对应[教程](../../../tutorials/README.md)，它们不读取主 CLI 配置，也不自动生成同一套 `run_manifest.json`。
