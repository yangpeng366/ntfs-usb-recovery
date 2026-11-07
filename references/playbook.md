# Recovery order

1. Identify the device and partition by model, serial, capacity and offset. Drive letters and physical disk numbers can change after reconnecting. Record the unelevated user's identity and actual failing path.
2. Preserve metadata and important data on another disk before structural repairs. If hardware read errors are observed, minimize repeated scans and prioritize imaging or valuable files.
3. Diagnose the failure: damaged boot/MFT/index, invalid security descriptor, ordinary DACL denial, or device-level I/O error. A security ID other than 256 is normal on many healthy volumes; its value alone proves nothing.
4. For a confirmed personal-data DACL recovery, use `scripts/acl_sweep.py` in an authorized administrator session. It changes ownership and adds inheritable full control; it does not clear deny entries, override protected inheritance or repair damaged metadata.
5. Structural repair is specific to the current volume layout. The original case required custom recovery scripts and backups, followed by CHKDSK; these scripts are not shipped as a generic command. Never copy a donor MFT blindly.
6. Verify from an unelevated session using `--verify-only`. Record all results including access errors and empty directories. Compare valuable files to backups where possible. Record CHKDSK result, dirty state and hardware error evidence separately.

For long privileged operations, follow [elevated-jobs.md](elevated-jobs.md). Never treat a wait timeout or a process launch as successful completion. Preserve the last completed item to resume only what remains.
