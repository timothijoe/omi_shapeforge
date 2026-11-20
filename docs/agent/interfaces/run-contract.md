# 运行与产物合同 v1

ENG-002 于 2026-11-20 定版，ENG-003 已将两个 smoke 与 MuJoCo CLI 接入此合同，三项实际运行验证见[证据清单](../../../manifests/workflow_validation_20261120.json)。Schema、流程要求和示例见 [contracts/v1](../../../contracts/v1/README.md)。已有历史报告和后端入口保持原样；旧格式转换规则仍为待实现的迁移约定。

## 1. 文件布局与职责

```text
<新建运行目录>/
  run_manifest.json       调度器维护的 v1 运行记录
  run.log                 调度器捕获的 stdout/stderr
  inputs.json             可选：输入依赖集合，文件路径、大小和哈希
  backend/                后端的独占输出目录
    report.json           后端原始报告，不改字段或覆盖为统一报告
    ...                   后端原样产物
```

调度器用独占创建建立运行根目录；目录已存在时直接拒绝，不能在旧目录写失败报告。调度器不预建 `backend/`，将这个尚不存在的路径传给后端，从而兼容仿真脚本的 `exist_ok=False` 与 smoke 的 `exist_ok=True`。以后不允许新流程写到运行根目录之外。

先写初始清单再启动进程，清单更新采用同目录临时文件加原子替换。已创建运行目录后的启动异常、检查失败与可捕获中断均保留日志和终态；目录创建／初次落盘失败只能报 CLI 错误，不能声称已经保存完整运行。断电或 SIGKILL 可能留下 `running`，后续只标记状态待核实，不自动宣称失败或重跑。

`run_manifest.json` 是记录入口，不把自身哈希写入自身。控制器日志也不属于 `backend/` 的产物清单。后端产物、输入清单和原始报告各自记录 SHA256；产物路径以运行根目录为基准，输入路径为已解析的绝对本地路径。跨机恢复通过资源清单显式映射，不能仅根据同名文件替换输入。

## 2. 顶层字段

全部字段必须出现；未知值只在 Schema 允许处用 `null`，不能写空字符串或虚构默认值。严格 JSON 禁止重复键、NaN 和 Infinity。

| 字段 | 约定 |
| --- | --- |
| schema_version | 整数 `1`；未知版本拒绝读取，不自动按旧格式解释 |
| record_kind | `native` 新执行、`imported` 旧证据转换、`example` 合成格式示例；示例不能进入能力验收证据 |
| run_id | 唯一标识；新执行使用 UTC 时间加随机后缀，不能复用旧任务标识充当运行标识 |
| workflow | 首批为 `smoke.stereo`、`smoke.bundlesdf`、`simulation.mujoco`；必须存在对应流程规则 |
| started_utc／finished_utc | 带 UTC 时区的时间；开始是任务尝试开始，包含启动准备；结束不得早于开始；旧报告未记录时为 null |
| execution | `state`、整数或 null 的 `returncode`、参数数组 `command`、`cwd`、相对 `log`、异常原因 `error`；不用 shell 命令字符串 |
| sources | 本次调用涉及的源码库，包括主调度器与后端；记录 repository、head、dirty、entrypoint_sha256、note；无法读取的字段为 null 并写原因 |
| environment | 实际启动器路径 `executable` 和已读取的版本字典 `versions`；保留 venv 启动器路径，不解引用成系统 Python，不抄录整份进程环境变量 |
| parameters | 本次已解析参数，如迭代数、缩放、步数、渲染后端；预期参数与报告实际参数不符属于产物检查失败 |
| inputs | 文件或依赖清单记录；权重旁的配置、相机标定、场景网格等传递依赖不能只记顶层文件 |
| artifacts | 后端实际生成的文件记录；没有生成的文件不伪造条目，已产生的部分输出可保留 |
| validation | 产物检查的 status 和 checks；完整性／格式／单位／内容与运行的对应关系 |
| acceptance | 任务验收的 status、scope 和 checks；严格限定到流程已声明的能力 |
| legacy | 新执行为 null；旧转换保留 format、adapter_version、documents、raw_status、missing_fields |
| limitations | 人工 ROI、假设质量、缺少真值、未验收范围等明确限制 |

源代码脏工作树可以用于探索，但须如实记录；正式共享的复现实验要能恢复实际源码，提交或完整备份要求延续 ENG-001。`dirty=false` 本身不证明环境与二进制由该提交构建。

## 3. 三项状态分别判断

`execution.state` 的新运行转换为 `pending → running → succeeded/failed/cancelled`；准备阶段失败可以 `pending → failed`。`unknown` 只用于没有进程证据的旧转换。`pending` 没有起止时间；`running` 没有结束时间。启动失败的 returncode 为 null，已退出进程记录真实返回值；非零退出或信号中断不能写 succeeded。进程退出 0 后检查产物失败，execution 仍为 succeeded，错误写入 validation，不伪造进程异常。

`validation.status` 与 `acceptance.status` 都为 `passed/failed/not_evaluated`。全部计划检查通过且非空才汇总 passed；任何失败汇总 failed；部分未检查且没有失败或尚未开始时为 not_evaluated。不得用空检查列表得到 passed。

| 场景 | execution | validation | acceptance |
| --- | --- | --- | --- |
| 启动器不存在 | failed，returncode=null | not_evaluated | not_evaluated |
| 后端退出 7 | failed，returncode=7 | not_evaluated | not_evaluated |
| 用户中断 | cancelled，实际返回码或 null | not_evaluated | not_evaluated |
| 退出 0，缺报告／坏 JSON／缺产物 | succeeded，returncode=0 | failed | not_evaluated |
| 文件有效，尚未运行任务指标 | succeeded | passed | not_evaluated |
| 文件有效，任务指标未达标 | succeeded | passed | failed |
| 文件和限定任务检查均通过 | succeeded | passed | passed |
| 旧报告仅包含 passed 字符串 | unknown，returncode=null | not_evaluated | not_evaluated |

验收只有在进程成功且产物检查通过后才能求值。旧资料可以独立重验文件，但在进程事实未知时不能声明整个任务通过。当前 CLI 成功退出要求三项均通过；退出码 0=通过、1=运行／检查未通过、2=参数、配置读取或输出目录调用错误、130=用户中断。若后端在收到中断后自行退出 0，保留其真实 succeeded／0，但 validation 和 acceptance 不求值，CLI 仍返回 130，原因保存在 limitations。

每个 check 记录 `id/status/method/expected/observed/evidence`。expected 是事先定义的要求；observed 是观测值及单位，未执行可为 null；evidence 引用 inputs／artifacts／legacy.documents 中的文件 ID。通过项必须有观测和证据。失败项可以没有文件证据，例如报告缺失，但要说明方法和观察到的缺失。

## 4. 文件与几何语义

每项文件记录为 `id/path/sha256/size_bytes/format/units/frame`。ID 跨输入、输出和旧证据唯一；输出路径不得重复，不得包含绝对路径、反斜线、空路径段、`.`、`..` 或盘符。路径解析后仍须位于运行目录内；后续运行层还须检查符号链接逃逸。离线 Schema 检查只检查路径文本，不替代文件系统检查。

完成产物检查时，必需文件存在且非空、大小与 SHA256 一致；格式可解码，数组维度／有限性符合流程要求。目录依赖由 `inputs.json` 等文件清单描述，每个成员记录相对路径、大小、哈希；传递引用的实际路径必须核实，清单自身也作为输入哈希。已存在的资源集合清单可复用，但每次必须验证成员内容，不能只信清单声明。

- 视差单位 `pixel`，坐标 `left_image`；深度与点云单位 `m`，坐标 `camera`，不得使用预览坐标替代原坐标。
- MuJoCo 广义位姿／速度含长度、四元数、线速度、角速度，文件级单位为 `mixed`、坐标 `mjcf_world`。具体字段单位依据 MJCF 与内容规则，禁止将整个 qpos／qvel 标为米。
- PNG／JSON 报告等无单一几何单位的文件使用 `units=null`、`frame=null`，避免猜测。
- 后续配准、机器人流程必须另定义变换方向和动作语义。`p_camera = R p_model + t`、变换是否已作用于顶点、末端增量还是关节值，不能靠文件名推断。

## 5. 首批流程验收

机器可读的必需输入、产物及固定单位见 [profiles.json](../../../contracts/v1/profiles.json)。产物检查必须包含 `required_artifacts/report_status/hashes/content` 四项；原始 report.status 精确匹配流程要求，不能使用 `startswith('passed')`。

| 流程／scope | 产物内容检查与任务验收 | 不证明的能力 |
| --- | --- | --- |
| smoke.stereo／official_stereo_sample | 左右图同形 RGB，标定有效，配置／权重可追溯；视差与深度为有限 H×W，深度非负；点云有限、非空且点数与报告一致，预览可解码。`official_sample_checks` 只验收这一固定官方样例的处理 | 光模块真实录制、深度真值精度、自动定位 |
| smoke.bundlesdf／bundlesdf_components | LoFTR 匹配为有限 N×5，N≥10 且与报告一致；图像缩放为 640×448；哈希编码及梯度、SO(3)、CUDA KNN 及梯度、Warp 状态通过，Kaolin 输出非空；`component_checks` 引用这些断言的报告与匹配文件 | 完整视频跟踪、融合或 textured mesh |
| simulation.mujoco／mujoco_load_step_render_settle | 输入场景及全部依赖明确，步数和模块数一致，图像解码与状态有限；`fall_contact_settle` 检查每个模块落差>0.01 m、有末态接触、碰撞底部≥−0.001 m、max(abs(qvel))≤0.05，沿用现有原型阈值。`max(abs(qvel))` 混合线速度和角速度，必须注明此限制 | 实测质量／摩擦／惯量、真实夹持插接、校准物理精度 |

当前 MuJoCo 报告未完整输出每个碰撞体的底部高度，旧报告只能说明原脚本的断言通过；ENG-003 的独立检查器会从保存的末态和原场景重新计算各碰撞体底部高度、落差和接触，并写入 backend/inspection.json；不改旧 report。不能从 report.status 伪造原报告没有的测量值。场景附带的 `physical_accuracy_validated=false` 必须保留。

Isaac、Blender、场景生成与配准本轮仅制定兼容规则，不注册已支持的 v1 流程。未来添加流程必须一起提交明确 scope、输入、产物、单位、判据和成功／失败示例。

## 6. 旧格式适配规则

转换是读取旧文件后在新的运行目录写一份新清单。读取器必须显式选择旧格式，不能因文件叫 `report.json` 就判断类型。原始文件不改写；`legacy.documents` 记录原绝对路径、字节大小和实际哈希，`raw_status` 保留原值，`missing_fields` 列出缺项。原文件损坏／不支持的格式应拒绝转换并返回诊断，不能静默生成空成功记录。

| 原格式 | 映射与证据要求 |
| --- | --- |
| 主调度器无版本 run_manifest | workflow `stereo/bundlesdf` 映射到对应 smoke；command/config/source 字段按原意读取；只有记录 returncode=0 才能认定进程成功；旧 status=failed 且 returncode=0 表示后处理失败，应保留进程成功并单独标识验证失败。未知工作流拒绝 |
| 主调度器运行中／中断残留 | 有原始时间或错误就保留；仅有 error 不能判断一定是用户中断。没有返回码或充分终态证据时用 unknown，缺项列入 missing_fields |
| 独立 MuJoCo／Isaac report | status 仅表示旧脚本声明；单独报告不推断命令、退出码、Git HEAD 或起止时间。scene_sha256／runner_sha256 缺失时保持未知，不用当前文件哈希冒充当时值 |
| Blender asset.json | 导出器的状态只打印到 stdout，asset.json 本身没有该状态；检查 parts、单位、源模型和引用网格，不要求不存在的 report.status |
| scene_manifest.json | 检查 scene.xml／scene.usda 与引用网格；原 stdout 的 authored 状态不能作为物理仿真通过证据 |

旧运行根目录内产物不会自动移动到 `backend/`。转换若需要填写 v1 artifacts，必须在新的目录复制对应原文件或建立受控的本地只读内容副本并验证字节哈希；不能用越界链接绕过路径约定。未复制／未复验时 artifacts 可以为空，validation 和 acceptance 保持 not_evaluated。旧报告状态不会自动提升为新验收通过。

字段名、语义或必需字段变化需要新 schema_version；现有 v1 拒绝未声明字段。新增流程可扩展 profiles，但不能修改已有流程的 scope 或阈值来让历史失败变成通过；此类变化需要新合同版本。

## 7. ENG-003 接入范围

1. 保留目前两个 smoke 的 CLI 调用形式，公共运行层输出 v1；后端仍输出原始报告，避免同时改三个仓库。
2. 所有新运行采用新根目录及未预建的 backend 子目录，处理失败、中断、重复输出路径和原子写入。
3. 进程、产物和验收分别计算；文件检查包含符号链接边界、真实内容与来源，不只运行 Schema 校验。
4. 明确解码职责：重型数组／图像检查在对应环境运行，主控制层保持标准库依赖；将检查结果与输入哈希关联。
5. 先迁移两个 smoke，再接 MuJoCo；在各实际环境验证并保存新报告，已有历史报告原样保留。
6. 本轮上述三项新运行、14 项控制层测试及 v1 结构检查通过；CLI、教程与能力事实同步。Isaac、旧报告转换和自动 CI 仍未接入，不能据此扩大验收范围。
