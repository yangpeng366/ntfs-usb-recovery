# E/F 盘恢复案例（2026-11-05 至 11-08）

两块外接盘先报需要格式化，恢复挂载后又出现一级目录拒绝访问。处理顺序为保留元数据与重要数据、按当时设备布局修复、CHKDSK、用户 SID 授权、普通窗口验收。设备专用重建脚本未收入本仓。

## 最终验证

2026-11-08 07:33（Asia/Shanghai），普通用户令牌 admin=False：E 盘 17/17、F 盘 18/18 个非系统一级目录可列举。目录数量会随新增目录变化，不能沿用历史分母。两盘 Get-Volume 为 Healthy/OK，fsutil dirty query 均为 NOT Dirty。

F 盘 found.000 最后补修成功，可列举 5 项；此处只验证目录入口，未验证其全部后代或找回碎片内容。系统回收目录及 System Volume Information 保持原权限。

## 最后一项权限修复

takeown 成功后，两次 icacls 授权长时间未结束，均主动停止并确认任务退出。备份原 DACL 后，使用旧式 Win32 GetFileSecurityW/SetFileSecurityW，仅对 found.000 自身添加当前用户的非继承允许 ACE，保留原 ACE。该 API 不自动向后代传播权限；写入约 0.52 秒完成，普通窗口随后验证可读。此为特定故障的范围收敛，不替代正常继承修复。

## 证据边界

F 盘第二轮 CHKDSK 报告已更正文件系统，51.59 分钟、坏扇区 0 KB；历史 SMART ReadErrorsTotal=27，曾有导出读取失败。没有逐文件哈希全盘比对，不能声称零丢失、全部完整或硬件无故障。

本机证据留在 D:\_diskrec\diag：verify_top_20261108.log、fix_found_direct.log、found_root_dacl_before.bin、chkdsk_F2.log。磁盘元数据、导出数据及个人路径日志不发布。
