---
name: ntfs-usb-recovery
description: Diagnose Windows NTFS USB recovery and restore access to personal data directories after damaged security descriptors. Includes a case study and elevated-job operating notes.
---

# NTFS USB recovery

Identify the physical device, volume, user and failure before changing anything. Never format a data disk as a recovery step. For metadata damage, preserve an image or MFT and export important data to another disk before filesystem repair.

## Available tools

- `scripts/acl_sweep.py`: `--volume X: --user "DOMAIN\user" --verify-only` checks current-token access. Run without verify-only only in an authorized administrator session to take ownership and grant inheritable full control on personal top-level directories. It does not follow protected inheritance or guarantee access to every descendant. Verify again from an unelevated session.
- `scripts/rawdev.py`: low-level Win32 library, read-only by default. Specify the actual logical sector size. Writes require complete aligned sectors and explicit write mode; callers must arrange offline access, backups, and read-back verification. No raw write probe is run automatically.

## Workflow

Read `references/playbook.md` for recovery order; `references/failure-modes.md` to distinguish DACL, metadata, device and I/O failures; `references/ntfs-layout.md` for record layout. Read `references/elevated-jobs.md` for the case record of scheduled-task channels and interrupt recovery - the reusable recipe lives in the `windows-silent-elevate` skill - and `references/case-study.md` for evidence limits. Record a start marker before each long operation, retain its exit code and end marker, and verify the result from the user's token.

This repository does not contain a generic MFT transplant, boot-sector repair or raw export command. The original case used scripts specific to that disk geometry. Do not invent paths or run those operations from illustrative historical references.
