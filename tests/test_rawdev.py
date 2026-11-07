"""Tests for scripts/rawdev.py - the raw-device wrapper.

These tests never touch a real disk.  They pin down the two properties that
actually broke in the field:

  1. the device must be opened with FILE_SHARE_READ|FILE_SHARE_WRITE, because
     the CRT's share mode is rejected by the USB mass-storage driver and the
     failure looks exactly like a read-only device;
  2. every raw transfer length must be a multiple of the sector size, and
     the answer must be trimmed back to the logical length afterwards.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import rawdev  # noqa: E402


class _FakeK32(object):
    """Records CreateFileW arguments and returns a fake handle."""

    def __init__(self):
        self.calls = []

    def CreateFileW(self, path, access, share, *rest):
        self.calls.append((path, access, share))
        return 4242

    def CloseHandle(self, h):
        return True

    def SetFilePointerEx(self, h, offset, *rest):
        return True

    def ReadFile(self, *a):
        return True

    def WriteFile(self, *a):
        return True

    def GetLastError(self):
        return 0


@pytest.fixture
def fake_k32(monkeypatch):
    fake = _FakeK32()
    monkeypatch.setattr(rawdev, "k32", fake)
    return fake


def test_open_device_requests_share_read_and_share_write(fake_k32):
    handle = rawdev.open_device(r"\\.\PhysicalDrive2", write=True)
    assert handle == 4242
    path, access, share = fake_k32.calls[0]
    assert path == r"\\.\PhysicalDrive2"
    assert access & rawdev.GENERIC_READ
    assert access & rawdev.GENERIC_WRITE
    assert share & rawdev.FILE_SHARE_READ
    assert share & rawdev.FILE_SHARE_WRITE


def test_open_device_read_only_omits_generic_write(fake_k32):
    rawdev.open_device(r"\\.\PhysicalDrive2", write=False)
    _path, access, _share = fake_k32.calls[0]
    assert access & rawdev.GENERIC_READ
    assert not access & rawdev.GENERIC_WRITE


def test_read_exact_rounds_up_to_sector_and_trims(monkeypatch):
    dev = rawdev.RawDevice.__new__(rawdev.RawDevice)
    dev.sector_size = 512
    seen = {}

    def fake_read_at(offset, length):
        seen["offset"] = offset
        seen["length"] = length
        return b"\x00" * length

    monkeypatch.setattr(dev, "_read_at", fake_read_at)
    data = dev.read_exact(1024, 947)  # 947 is not a multiple of 512
    assert len(data) == 947
    assert seen["length"] % rawdev.SECTOR == 0
    assert seen["length"] >= 947


def test_write_exact_rejects_partial_sector(fake_k32):
    dev = rawdev.RawDevice('test', write=True)
    with pytest.raises(ValueError):
        dev.write_exact(0, b'abc')


def test_write_method_is_callable(fake_k32):
    dev = rawdev.RawDevice('test')
    assert callable(dev.write)
    with pytest.raises(PermissionError):
        dev.write_exact(0, bytes(512))


def test_write_exact_preserves_sector_bytes(monkeypatch):
    dev = rawdev.RawDevice.__new__(rawdev.RawDevice)
    seen = {}

    def fake_write_at(offset, data):
        seen["length"] = len(data)
        return len(data)

    monkeypatch.setattr(dev, "_write_at", fake_write_at)
    dev.write_exact(0, bytes(512))
    assert seen['length'] == 512


def test_read_exact_raises_on_short_read(monkeypatch):
    dev = rawdev.RawDevice.__new__(rawdev.RawDevice)
    dev.sector_size = 512
    monkeypatch.setattr(dev, "_read_at", lambda offset, length: bytes(length // 2))
    with pytest.raises(OSError):
        dev.read_exact(0, 4096)


def test_win32_file_read_and_explicit_write(tmp_path):
    path = tmp_path / 'device-fixture.bin'
    original = bytes(range(256)) * 16
    path.write_bytes(original)
    with rawdev.RawDevice(str(path)) as dev:
        assert dev.read_exact(511, 947) == original[511:1458]
        with pytest.raises(PermissionError):
            dev.write(bytes(512))
    with rawdev.RawDevice(str(path), write=True) as dev:
        dev.seek(512)
        assert dev.write(b'x' * 512) == 512
        assert dev.read_exact(512, 512) == b'x' * 512
    assert path.read_bytes() == original[:512] + b'x' * 512 + original[1024:]
