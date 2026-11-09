# NTFS USB Recovery

Windows 外接盘 NTFS 恢复经验与工具，源自 2026-11-05 至 11-08 的 E/F 盘修复。本仓收录权限修复工具、Win32 设备访问封装与作业经验；当次按设备布局编写的 MFT 重建脚本不作为通用工具发布。

## 工具

- `scripts/acl_sweep.py`：顶层目录 takeown + 用户继承授权；`--verify-only` 只检查当前用户的实际访问。
- `scripts/rawdev.py`：Win32 设备访问库，默认只读；支持 512/4096 字节扇区，写入拒绝自动补零。它不自动锁定或卸载卷，写入调用者须自行保证卷已离线、备份可用并读回核对。
- `references/`：NTFS 布局、故障辨别、恢复顺序、计划任务提权经验与案例验证范围。

## 权限检查与修复

普通窗口验证：`python scripts/acl_sweep.py --volume X: --user "DOMAIN\user" --verify-only`。
确认目标是需要恢复的个人数据卷后，在管理员窗口运行同一命令并去掉 `--verify-only`。它会变更目录所有者和授予用户完全控制；继承被保护、显式拒绝或链接目标不在本卷时须单独诊断。系统目录默认排除。最后回到普通窗口复验。

## 作业与验证

自动提权作业的本次实证见 [elevated-jobs.md](references/elevated-jobs.md)，可复用流程见全局 skill `windows-silent-elevate`，案例结果见 [case-study.md](references/case-study.md)。目录可读、Healthy 和 NOT Dirty 不构成所有文件内容完整或硬件无故障的证明。

安装 `python -m pip install pytest ruff` 后运行 `pwsh -NoProfile -File examples/quality-gate.ps1`。测试使用临时文件和替身，不写真实磁盘。MIT 许可。
