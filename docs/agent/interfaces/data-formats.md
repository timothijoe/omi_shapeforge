# 数据格式、坐标与单位

## 主项目实验

`run_manifest.json` 保存 workflow、status、命令列表、解析后的配置、输出路径、Git 来源及起止时间。正常进程返回有 returncode；启动异常或中断可能只有 error。来源中的 tracked diff 哈希与入口脚本哈希不包含完整未跟踪文件内容，不能替代提交或备份。

后端 `report.json` 状态分别为 `passed_real_gpu_stereo_inference`、`passed_cuda_kernels_cpp_bindings_and_real_loftr_matching`。控制器只强制检查状态字段，没有完整 JSON Schema 验证。

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
