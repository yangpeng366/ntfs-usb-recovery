# Failure modes

- Root lists, children deny access: compare security descriptors and the current token. An Administrators allow entry may not help an unelevated token. Add a user-specific grant only after confirming ownership and intended access; ACL protection and explicit deny entries require separate investigation.
- Missing security descriptor or damaged MFT/index: an ACL grant alone may not work. Preserve metadata and recover data before attempting structural repair.
- Raw read succeeds, write returns a CRT error: this does not prove the device is read-only. Compare the requested Win32 access/share flags and real error code. A successful API write also does not prove hardware health.
- Filesystem reports NOT Dirty: this reports the NTFS dirty flag, not an exhaustive data-integrity check. CHKDSK reporting zero KB of bad sectors is distinct from SMART error history.
- Job exit 0xC000013A: process was interrupted; inspect the last completed item and verify remaining paths. It is not a successful completion.
- Job exit 0xC0000142: process initialization failed; memory pressure is one possible cause. Correlate available memory and logs before assigning a cause.
