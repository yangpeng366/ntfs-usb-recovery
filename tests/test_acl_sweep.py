"""Tests for scripts/acl_sweep.py - the DACL repair / verification tool.

The failure this tool exists for is subtle: after $Secure damage the
descriptors name only SYSTEM and BUILTIN\\Administrators, so an elevated
shell reads everything while the interactive user is told "Access is denied"
on every sub-folder.  The repair therefore has to

  * grant the USER (not the Administrators group), because an unelevated
    UAC token carries the group SID deny-only;
  * use the (OI)(CI) inheritance flags, so NTFS pushes the ACE down the
    whole subtree in the kernel instead of walking it file by file;
  * be verified from an UNELEVATED token, because an elevated check proves
    nothing about the user's session.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import acl_sweep  # noqa: E402

SKIP = {"$RECYCLE.BIN", "System Volume Information"}


def test_grant_uses_user_sid_with_inheritance_flags(monkeypatch):
    calls = []

    def fake_run(cmd, timeout=None):
        calls.append(list(cmd))
        return 0, ""

    monkeypatch.setattr(acl_sweep, "run", fake_run)
    monkeypatch.setattr(acl_sweep, "list_top", lambda vol, skip: ([r"E:\top"], None))

    assert acl_sweep.sweep("E:", r"DOMAIN\alice", None, SKIP) is True

    icacls = [c for c in calls if c[0] == "icacls.exe"]
    assert icacls, "icacls was never invoked"
    assert icacls[0][1] == r"E:\top"
    assert icacls[0][2] == "/grant"
    assert icacls[0][3] == r"DOMAIN\alice:(OI)(CI)(F)"


def test_sweep_never_passes_recursive_switch(monkeypatch):
    calls = []
    monkeypatch.setattr(
        acl_sweep, "run", lambda cmd, timeout=None: (calls.append(list(cmd)) or (0, ""))
    )
    monkeypatch.setattr(acl_sweep, "list_top", lambda vol, skip: ([r"E:\top"], None))

    acl_sweep.sweep("E:", r"DOMAIN\alice", None, SKIP)

    for cmd in calls:
        assert "/T" not in cmd, "recursive walk defeats the inheritance shortcut"
        assert "/R" not in cmd


def test_sweep_reports_failure_when_grant_fails(monkeypatch):
    monkeypatch.setattr(
        acl_sweep, "run", lambda cmd, timeout=None: (0, "") if cmd[0] == "takeown.exe" else (5, "denied")
    )
    monkeypatch.setattr(acl_sweep, "list_top", lambda vol, skip: ([r"E:\top"], None))
    assert acl_sweep.sweep("E:", r"DOMAIN\alice", None, SKIP) is False


def test_verify_flags_a_denied_subfolder(monkeypatch):
    monkeypatch.setattr(acl_sweep, 'list_top', lambda vol, skip: ([r'E:\ok', r'E:\bad'], None))
    def fake_listdir(path):
        if path.endswith("ok"):
            return ["a", "b"]
        raise PermissionError(5, "Access is denied")

    monkeypatch.setattr(acl_sweep.os, "listdir", fake_listdir)
    assert acl_sweep.verify("E:", None, SKIP) is False


def test_verify_passes_when_every_subfolder_is_readable(monkeypatch):
    monkeypatch.setattr(acl_sweep, 'list_top', lambda vol, skip: ([r'E:\top'], None))
    monkeypatch.setattr(acl_sweep.os, "listdir", lambda path: ["a"])
    assert acl_sweep.verify("E:", None, SKIP) is True


def test_list_top_skips_system_folders(monkeypatch, tmp_path):
    (tmp_path / "visible").mkdir()
    (tmp_path / "$RECYCLE.BIN").mkdir()
    (tmp_path / "System Volume Information").mkdir()
    (tmp_path / "a-file.txt").write_text("x", encoding="utf-8")

    dirs, err = acl_sweep.list_top(str(tmp_path), SKIP)
    assert err is None
    names = sorted(os.path.basename(d) for d in dirs)
    assert names == ["visible"]


def test_run_reports_missing_command():
    code, out = acl_sweep.run(["definitely-not-a-real-command-xyz"])
    assert code == -1
    assert "command not found" in out


def test_drive_letter_is_normalized_to_root(monkeypatch):
    seen = []
    monkeypatch.setattr(acl_sweep.os, 'listdir', lambda path: seen.append(path) or [])
    assert acl_sweep.list_top('E:', SKIP) == ([], None)
    assert seen == ['E:\\']


@pytest.mark.parametrize("volume", ["E:", "F:"])
def test_is_admin_is_callable(volume):
    assert isinstance(acl_sweep.is_admin(), bool)
