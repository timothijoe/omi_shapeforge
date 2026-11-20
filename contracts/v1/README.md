# v1 运行合同与离线示例

规范见[运行与产物合同](../../docs/agent/interfaces/run-contract.md)。这里的 JSON 是接口定义和合成样例，不是实际实验报告；示例路径、哈希、观察值均为占位示范，不能用于能力验收。

- [run.schema.json](run.schema.json)：严格字段与类型，使用 JSON Schema 2020-12；所有引用均在文件内部，检查无需访问网络。
- [profiles.json](profiles.json)：首批三个流程的必需输入、产物、单位、范围与内容规则。
- [examples/](examples/)：成功、运行中、进程失败、启动失败、中断、缺报告、待验收、验收失败与旧报告未知状态，共 11 份。
- [invalid-cases.json](invalid-cases.json)：修改正例得到的 27 个反例，以及应出现的错误信息片段。
- [check_contracts.py](../../scripts/validation/check_contracts.py)：Schema 加字段关系校验；不执行后端、不验证引用文件真实内容，也不转换旧报告。

本机可使用已有 `jsonschema==4.23.0` 的 `python3`：

```bash
python3 scripts/validation/check_contracts.py
python3 scripts/validation/check_contracts.py /absolute/path/to/candidate-run.json
```

缺少开发依赖时，在独立的开发检查环境按 [requirements/contracts.txt](../../requirements/contracts.txt) 安装，再用该环境的解释器运行上述脚本；不向标准库控制环境或 GPU 环境强行加入依赖。脚本返回 0 表示全部示例／反例及附加记录的格式与关系检查通过，1 表示发现不符合约定的记录；非法 JSON 会报告解析错误并以非零退出。

后续真正的运行验收还要解码文件、核对哈希、校验坐标／单位及流程指标。通过这个脚本不足以认定运行成功或结果达标。
