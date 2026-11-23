# 外部系统边界

| 系统 | 本项目当前依赖方式 | 没有包含的能力 |
| --- | --- | --- |
| FoundationStereo 自有仓库 | 配置路径＋独立解释器调用样例 | 完整光模块原始录制验收 |
| BundleSDF 自有仓库 | 配置路径＋组件样例、原生扩展 | 全视频重建与最终 textured mesh 验收 |
| 光模块 portable 包 | 外部只读输入及其独立 CPU 脚本 | 新场景自动 ROI、原始双目恢复 |
| Blender 4.5.16 LTS | 官方本地执行文件、自带 bpy | 本轮完整建模重估和 GUI 人工验收 |
| MuJoCo 3.3.7／OpenUSD | 独立 simulation 环境 | 标定物理或机器人控制 |
| Isaac Sim 5.1.0 | 官方 python.sh、供应商扩展与 Python | GUI与6.0.1场景验收；5.1 RTX双相机已在[同源插接实验](../simulation/evolution/isaac-contact.md)验证 |
| omi_proj | 资产／迁移资料、已恢复模型及离线仿真预检 | ROS、控制器、SDK 或真机调用 |

Isaac 运行前清除 CONDA_PREFIX、CONDA_DEFAULT_ENV、PYTHONHOME、PYTHONPATH、LD_LIBRARY_PATH；由 `python.sh` 选择供应商库。当前脚本关闭扩展注册表，并显式指定本地扩展目录，不从网络资产服务器加载场景。

开源主仓库采用 MIT；外部算法、权重、模型及厂商包仍遵循其自身许可，不能因主项目许可证而改变再分发权限。资源恢复与公开提交是不同操作。
