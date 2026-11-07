#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
acl_sweep.py - restore access to a volume whose DACLs lost the user.

Why this exists
---------------
After `$Secure` damage the records' security descriptors end up granting
only `SYSTEM` and `BUILTIN\\Administrators`.  The interactive user is not
named, so Explorer reports "Access is denied" on every sub-folder - while an
elevated shell reads everything fine.  Two separate causes produce that
picture, and both are fixed the same way:

  (a) the descriptor does not name the user at all;
  (b) it names the Administrators group, but an unelevated UAC token carries
      that SID **deny-only**, so an ACE for the group does not grant the
      user's own session anything.

The fix is to grant the **user's SID** (not the group), with the `(OI)(CI)`
inherit flags, on the top-level folder.  NTFS then propagates the
inheritable ACE down the entire subtree in the kernel.  No `/T`, no
per-file walk.

Why not `takeown /R` + `icacls /T`?  Measured on this workstation:
takeown alone ran at ~300 files/s (2.5 h for 2.6 M records, 6 h for 7 M),
while the top-level + inheritance route ran at ~1,200-2,000 files/s.

Usage (needs elevation):
  python acl_sweep.py --volume E: --user "DESKTOP-DKA0K47\\admin"
  python acl_sweep.py --volume F: --user "DOMAIN\\user" --log out.log

`--verify-only` re-tests every top-level folder from the current (possibly
unelevated) token and prints a pass/fail table.
"""
import argparse
import ctypes
import os
import subprocess
import sys
import time

# ctypes only for the SID -> name lookup; the ACL work is done by the
# built-in takeown/icacls, which know how to handle a broken SD.
advapi = ctypes.WinDLL('advapi32', use_last_error=True)

SE_FILE_OBJECT = 1
DACL_SECURITY_INFORMATION = 0x00000004
OWNER_SECURITY_INFORMATION = 0x00000001


def log(msg, fh=None):
    line = '%s %s' % (time.strftime('%Y-%m-%dT%H:%M:%S'), msg)
    print(line)
    if fh:
        fh.write(line + '\n')
        fh.flush()


def is_admin():
    return bool(ctypes.windll.shell32.IsUserAnAdmin())


def run(cmd, timeout=None):
    """run a command, return (exit_code, combined_output)"""
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=timeout)
        out = (p.stdout or b'') + (p.stderr or b'')
        return p.returncode, out.decode('utf-8', 'replace')
    except FileNotFoundError:
        return -1, 'command not found: %s' % cmd[0]
    except subprocess.TimeoutExpired:
        return -1, 'timeout'


def list_top(volume, skip):
    root = volume + '\\' if len(volume) == 2 and volume[1] == ':' else volume
    try:
        names = os.listdir(root)
    except OSError as e:
        return None, str(e)
    out = []
    for n in names:
        if n in skip:
            continue
        p = os.path.join(root, n)
        if os.path.isdir(p):
            out.append(p)
    return out, None


def sweep(volume, user, fh, skip):
    dirs, err = list_top(volume, skip)
    if dirs is None:
        log('cannot list %s: %s' % (volume, err), fh)
        return False
    log('%s: %d top-level folders' % (volume, len(dirs)), fh)

    ok = True
    for p in dirs:
        t0 = time.time()
        te, tout = run(['takeown.exe', '/F', p, '/A'])
        ge, gout = run(['icacls.exe', p, '/grant', '%s:(OI)(CI)(F)' % user])
        secs = round(time.time() - t0, 1)
        flag = ''
        if te != 0:
            flag += ' takeown=%d' % te
            ok = False
        if ge != 0:
            flag += ' GRANT-FAILED=%d' % ge
            ok = False
        log('  %-42s %.1fs%s' % (os.path.basename(p), secs, flag), fh)
        if te != 0:
            log('      takeown: %s' % ' '.join(tout.split())[:200], fh)
        if ge != 0:
            log('      icacls : %s' % ' '.join(gout.split())[:200], fh)
    return ok


def verify(volume, fh, skip):
    """enumerate each top-level folder with the CURRENT token"""
    dirs, err = list_top(volume, skip)
    if dirs is None:
        log('cannot list %s: %s' % (volume, err), fh)
        return False
    ok = True
    for p in dirs:
        try:
            n = len(os.listdir(p))
            log('  %-42s OK (%d entries)' % (os.path.basename(p), n), fh)
        except OSError as e:
            log('  %-42s DENIED: %s' % (os.path.basename(p), e.strerror), fh)
            ok = False
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--volume', required=True, help='e.g. E:')
    ap.add_argument('--user', required=True, help='DOMAIN\\user')
    ap.add_argument('--log')
    ap.add_argument('--verify-only', action='store_true')
    ap.add_argument('--skip', default='$RECYCLE.BIN,System Volume Information')
    args = ap.parse_args()

    skip = set(s for s in args.skip.split(',') if s)
    fh = open(args.log, 'a', encoding='utf-8') if args.log else None

    log('=== acl_sweep volume=%s user=%s admin=%s ==='
        % (args.volume, args.user, is_admin()), fh)
    if not args.verify_only and not is_admin():
        log('NOT elevated - no repair attempted. Re-run as administrator.', fh)
        if fh:
            fh.close()
        return 2

    if args.verify_only:
        rc = 0 if verify(args.volume, fh, skip) else 1
    else:
        rc = 0 if sweep(args.volume, args.user, fh, skip) else 1

    log('=== done rc=%d ===' % rc, fh)
    if fh:
        fh.close()
    return rc


if __name__ == '__main__':
    sys.exit(main())
