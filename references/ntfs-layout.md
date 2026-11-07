# NTFS layout: read-only reference

All offsets are hexadecimal; multibyte integers are little endian. Derive sizes from the current volume. This is not a repair recipe.

- NTFS BPB: bytes/sector at 0x0B (2 bytes), sectors/cluster at 0x0D (1), total sectors at 0x28 (8), MFT LCN at 0x30 (8), mirror LCN at 0x38 (8). Signed record-size encoding is at 0x40: positive values count clusters; negative values mean 2 raised to the absolute value in bytes.
- A FILE record has a USA offset at 0x04 and USA count at 0x06. Validate the update sequence against sector trailers before parsing attributes. First attribute offset is at 0x14. Do not infer a shifted record grid from an earlier snapshot.
- Attribute header: type at 0x00 (4), length at 0x04 (4), nonresident flag at 0x08 (1), name length at 0x09 (1), name offset at 0x0A (2). Resident value length/offset are at 0x10/0x14. Nonresident runlist offset is at 0x20; allocated/real/initialized byte sizes are at 0x28/0x30/0x38.
- Extended STANDARD_INFORMATION values hold the security ID at 0x34. IDs are per-volume references, not universal ACL templates. A value other than 256 is not evidence of corruption.
- FILE_NAME: parent file reference at 0x00 (8), name length at 0x40 (1), namespace at 0x41 (1), UTF-16LE name at 0x42. Namespaces: 0 POSIX, 1 Win32, 2 DOS, 3 Win32 and DOS.
- An INDX block contains an INDEX_HEADER at 0x18. Its first field gives the entry offset relative to that header; do not hardcode the first entry at 0x18. Index-entry flags include 0x01 for a child node and 0x02 for the terminal entry.
- Runlist header low nibble gives cluster-count width; high nibble gives signed relative-LCN width. Zero LCN width denotes a sparse run. Bounds-check both fields and every resulting extent.
- Secure metadata: SDS stores descriptors, SII indexes security IDs, SDH indexes descriptor hashes. Preserve these structures; blanket security-ID replacement can destroy intended permissions.
- VOLUME_INFORMATION: major/minor version at 0x08/0x09, two-byte flags at 0x0A; dirty is 0x0001. Use fsutil dirty query for observation. There is no supported fsutil dirty clear command; repair and verify the underlying filesystem.

The raw wrapper in this repository does not parse or rebuild these structures. Geometry-specific recovery tools from the original case are deliberately not shipped.
