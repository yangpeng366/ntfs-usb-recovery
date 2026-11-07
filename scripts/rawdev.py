#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rawdev.py - open a raw disk/device for reading AND writing on Windows.

WHY THIS EXISTS
---------------
`open(r'\\\\.\\PhysicalDriveN', 'rb+')` goes through the CRT (`_wopen`).  The
USB mass-storage driver rejects the share mode the CRT chooses, so the very
first `write()` fails with `[Errno 9] Bad file descriptor` while reads keep
working.  That is indistinguishable from a read-only device, and it is how
the original case was initially misdiagnosed as device-level read-only.

`CreateFileW` with `FILE_SHARE_READ | FILE_SHARE_WRITE` is what the device
actually wants.  This module is a thin, seekable wrapper over it so the
rest of the tooling can keep using `read()` / `write()` / `seek()`.

The sector-size rule still applies: a raw ReadFile/WriteFile must be a
multiple of the sector size in BOTH length and offset, or it fails with
EINVAL. `read_exact()` rounds reads outward and trims the result;
`write_exact()` rejects unaligned writes rather than padding adjacent bytes.
"""
import ctypes
from ctypes import wintypes

k32 = ctypes.WinDLL('kernel32', use_last_error=True)

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x1
FILE_SHARE_WRITE = 0x2
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x80
INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value

SECTOR = 512
k32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                           wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
k32.CreateFileW.restype = wintypes.HANDLE
k32.CloseHandle.argtypes = [wintypes.HANDLE]
k32.CloseHandle.restype = wintypes.BOOL
k32.SetFilePointerEx.argtypes = [wintypes.HANDLE, ctypes.c_int64,
                               ctypes.POINTER(ctypes.c_int64), wintypes.DWORD]
k32.SetFilePointerEx.restype = wintypes.BOOL
for _name in ('ReadFile', 'WriteFile'):
    _api = getattr(k32, _name)
    _api.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
                     ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
    _api.restype = wintypes.BOOL


class WinError(OSError):
    def __init__(self, winerr, msg=None):
        self.winerr = winerr
        OSError.__init__(self, winerr, msg or ctypes.FormatError(winerr))


def open_device(path, write=False):
    r"""Open \\.\PhysicalDriveN (or \\.\X:) with explicit sharing."""
    access = GENERIC_READ | (GENERIC_WRITE if write else 0)
    h = k32.CreateFileW(path, access, FILE_SHARE_READ | FILE_SHARE_WRITE,
                        None, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, None)
    if h == INVALID_HANDLE_VALUE:
        raise WinError(k32.GetLastError(), 'CreateFileW(%s)' % path)
    return h


class RawDevice(object):
    """Seekable raw device.  Bytes are addressed from the start of the device."""

    def __init__(self, path, write=False, sector_size=512):
        if sector_size not in (512, 4096):
            raise ValueError('sector_size must be 512 or 4096')
        self.path = path
        self.writable = write
        self.sector_size = sector_size
        self.h = open_device(path, write)
        self.pos = 0

    def close(self):
        if self.h:
            k32.CloseHandle(self.h)
            self.h = None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    def seek(self, offset, whence=0):
        if whence == 0:
            self.pos = offset
        elif whence == 1:
            self.pos += offset
        else:
            raise ValueError('only absolute and relative seeks are supported')
        return self.pos

    def tell(self):
        return self.pos

    def _read_at(self, offset, length):
        if offset < 0 or offset % self.sector_size or length < 0 or length % self.sector_size:
            raise ValueError('raw reads require aligned nonnegative offset and length')
        if not k32.SetFilePointerEx(self.h, ctypes.c_int64(offset), None, 0):
            raise WinError(ctypes.get_last_error(), 'SetFilePointerEx')
        buf = ctypes.create_string_buffer(length)
        got = wintypes.DWORD(0)
        if not k32.ReadFile(self.h, buf, length, ctypes.byref(got), None):
            raise WinError(k32.GetLastError(), 'ReadFile')
        self.pos = offset + got.value
        return buf.raw[:got.value]

    def read(self, length):
        return self._read_at(self.pos, length)

    def _write_at(self, offset, data):
        if not self.writable:
            raise PermissionError('device was opened read-only')
        if offset < 0 or offset % self.sector_size or len(data) % self.sector_size:
            raise ValueError('raw writes require an aligned offset and complete sectors')
        if not k32.SetFilePointerEx(self.h, ctypes.c_int64(offset), None, 0):
            raise WinError(ctypes.get_last_error(), 'SetFilePointerEx')
        buf = ctypes.create_string_buffer(data, len(data))
        put = wintypes.DWORD(0)
        if not k32.WriteFile(self.h, buf, len(data), ctypes.byref(put), None):
            raise WinError(k32.GetLastError(), 'WriteFile')
        if put.value != len(data):
            raise OSError('short write: %d/%d' % (put.value, len(data)))
        self.pos = offset + put.value
        return put.value

    def write(self, data):
        return self._write_at(self.pos, data)

    # ---- sector-safe helpers -------------------------------------------
    def read_exact(self, offset, want):
        """Read `want` logical bytes at `offset`; the raw transfer is rounded
        UP to a sector multiple and trimmed back."""
        if offset < 0 or want < 0:
            raise ValueError('offset and length must be nonnegative')
        sector = self.sector_size
        start = offset // sector * sector
        delta = offset - start
        req = (delta + want + sector - 1) // sector * sector
        b = self._read_at(start, req)[delta:]
        if len(b) < want:
            raise WinError(0, 'short read %d/%d at %d' % (len(b), want, offset))
        return b[:want]

    def write_exact(self, offset, data):
        """Write complete sectors only; never pad over adjacent bytes."""
        return self._write_at(offset, data)
