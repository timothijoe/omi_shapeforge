# 数据格式、坐标与单位

当前 smoke 和 MuJoCo CLI 已使用[运行与产物合同 v1](run-contract.md)。下文同时说明旧文件语义，旧报告保持原样。

## 主项目实验

新 `run_manifest.json` 保存 schema_version=1、workflow、execution、inputs、artifacts、sources、environment、validation、acceptance 等字段。执行、产物与验收结果独立，原始后端报告与数组位于 `backend/`；记录实际版本、输入／输出哈希和起止时间。字节哈希不能替代源码备份，也不单独证明产物语义。

历史无版本运行清单中的顶层 status／returncode／config／output 保留原义，不用于直接解析新运行。两个后端原 report.status 字符串保持不变；新运行层同时检查文件边界、哈希并在后端环境实际解码内容，结果写入 backend/inspection.json。结构示例校验器仍是独立开发工具，不是控制层的 JSON Schema 运行依赖。

双目 `disparity.npy` 是像素视差，`depth_meter.npy` 是米制深度，`cloud.ply` 是输入相机坐标下的点云；`vis.png` 是图像／视差拼图。预览工具可使用 `(x,z,-y)` 方便展示，不修改 PLY 的原坐标。

## 便携配准

固定样例：`pointcloud.npz` 的 xyz 为 float32 `(100000,3)`，gray 为 `(100000,)`；ROI 包含原选区索引、过滤后 472 点、对应 fit 布尔掩码；刚性 mesh 包含 1500 个顶点和 2964 个三角形。上述数量是当前样例，不是通用格式上限。

`selected_candidate.json` 的 `T_camera_from_model` 是 4×4 刚体矩阵，按列向量有 `p_camera = R p_model + t`，平移单位为米。交付的 `matched_model_confirmed_region.ply` 已变换到点云坐标，不能再次套用同一矩阵。`heldout_*_mm` 等是毫米表面残差，不是实物位姿误差。

## 仿真资产

Blender 导出器把求值对象的 matrix_world 一次应用到顶点，OBJ 的三角形索引从 1 开始。`asset.json` 保存源模型哈希、外观部件、颜色、视觉 bounds、碰撞盒中心／半尺寸及假设质量。

`scene_manifest.json` 记录摆放、物理假设和场景文件哈希。MJCF／USD 都按米制、重力沿 -Z，台面 Z=0。当前合成排布不应用配准的相机矩阵，不是现场坐标对齐。

MuJoCo 输出 qpos／qvel、接触、PNG 和轨迹；Isaac 输出位置／速度、末态 USD 和报告。仿真脚本的报告结构不同于主 CLI 清单，不能凭文件名相同就混用判定。最终方阵报告记录运行脚本和场景哈希，旧单模块报告部分字段较少，应保留原记录。

## OMI 示范包

新到达包的元数据声明 9 个正常原始回合、41 个连续片段、1499 条样本，原回合级训练／验证为 1174／325 条。动作是 6 维末端增量，合同 no_gripper=true，不能直接作为七维仿真关节或夹爪动作标签。历史 BC6148 曾拟合全部1499条，原划分不是该历史 Actor 的独立测试集。本机已做文件哈希核对，尚未执行包内全量数据解码／Actor 推理验证或重新训练。
