# 参与 ntfs-usb-recovery

感谢考虑贡献！

## 基本约定

- MIT 许可。提交补丁即表示同意以 MIT 发布。
- 讨论走 GitHub Issues。较大改动请先开 issue 对齐方向。
- **默认只读**。任何写盘行为必须显式开关，并写清为什么需要写。

## 提交之前

先跑门禁（与 CI 跑的是同一套）：

```powershell
pwsh -NoProfile -File examples\quality-gate.ps1
```

- `examples\bom-sweep.py` 必须报 no BOM。**UTF-8 无 BOM** 是硬规矩：
  BOM 在编辑器里是隐形的，会让 Java 编译器和 Linux 构建直接失败。
- `pytest` 必须全绿。跳过的测试**不等于**通过 —— 在 PR 里写明跳过了什么、为什么。
- 涉及 Win32 读写的改动，先用临时普通文件验证 API 契约；设备行为另在可弃置测试盘或等效环境验证，注明范围。不要拿用户数据盘做写入探针。

## 硬性技术约定

1. **裸盘读写必须走 `scripts\rawdev.py`**（`CreateFileW` + `FILE_SHARE_READ|FILE_SHARE_WRITE`）。
   CRT 错误不构成设备只读的证据；记录访问模式、共享标志及 Win32 错误再诊断。
2. **裸盘读写长度与偏移都必须是扇区倍数**，用 `read_exact()` / `write_exact()`。
3. **权限修复用顶层 `takeown` + `icacls (OI)(CI)`**，不要用 `/T` 递归。
4. **权限验收必须用非提权 shell**。提权 token 带 Administrators SID，提权环境里的"能读"是假绿。

## 提权脚本的编码

Windows PowerShell 5.1 会把**无 BOM 的 .ps1 按 ANSI(GBK) 读**，
脚本里的中文字面量会被打乱成解析错误。
所以：提权执行的 `.ps1` 一律**纯 ASCII**，中文注释都不写。
