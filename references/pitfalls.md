# Pitfalls observed during recovery

- Read APIs on a raw device need sector-aligned transfers. The wrapper rounds a read outwards and trims to the requested range; specify the actual logical sector size. Raw writes reject partial sectors instead of zero-padding adjacent bytes.
- Declare ctypes argument and result types, particularly pointer-sized HANDLE values. Default C integer conversion can truncate handles on 64-bit Python.
- Do not assign a Boolean to `self.write` on an object with a `write()` method. Keep the capability flag separate from the method.
- A CRT open or write error is not proof of hardware read-only state. Record the Win32 error and requested access/share flags before blaming the bridge.
- Use one synchronized handle per device for sequential seek/read work. Multiple independent handles are not inherently wrong, but unsynchronized seek/read on a shared handle can corrupt results. This wrapper is not thread-safe.
- `E:` is drive-relative on Windows; `E:\` is its root. Normalize a drive argument before listing or repairing it.
- Do not suppress list errors: an empty directory and an inaccessible directory are different findings. Get-ChildItem with ErrorAction Stop made this visible in the case.
- Inheritance can take minutes on large trees. Protected children and explicit deny entries may remain inaccessible. Successful root grant is not proof of full descendant access.
- NOT Dirty and zero KB bad sectors are filesystem observations. They do not invalidate SMART error evidence or prove every exported file is complete.
- Keep raw recovery scripts tied to verified device geometry. Record-0 offsets, runlists, allocated ranges and record size must come from the current volume, not an earlier snapshot.
- See [elevated-jobs.md](elevated-jobs.md) for PS 5.1 encoding, independent logs, completion markers, and interruption recovery.
