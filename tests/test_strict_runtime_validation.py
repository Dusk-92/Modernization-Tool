import os
import struct
import tempfile
import unittest

import remote_packages
import setup_tool_dynamic as dynamic


def _classic_mpq_bytes(
    *,
    archive_size=96,
    hash_table_offset=32,
    block_table_offset=48,
    inner_magic=b"MPQ\x1A",
    sector_size_shift=3,
):
    header = inner_magic + struct.pack(
        "<IIHHIIII",
        32,
        archive_size,
        0,
        sector_size_shift,
        hash_table_offset,
        block_table_offset,
        1,
        1,
    )
    data = bytearray(archive_size)
    data[:32] = header
    return data


def _write_wrapped_mpq(
    path,
    *,
    header_offset=32,
    user_header_size=16,
    user_data_size=None,
    inner_magic=b"MPQ\x1A",
    hash_table_offset=32,
    block_table_offset=48,
    sector_size_shift=3,
):
    inner = _classic_mpq_bytes(
        inner_magic=inner_magic,
        hash_table_offset=hash_table_offset,
        block_table_offset=block_table_offset,
        sector_size_shift=sector_size_shift,
    )
    total_size = max(16, header_offset + len(inner))
    data = bytearray(total_size)
    if user_data_size is None:
        user_data_size = max(0, header_offset - user_header_size)
    data[:16] = b"MPQ\x1B" + struct.pack(
        "<III",
        user_data_size,
        header_offset,
        user_header_size,
    )
    if 0 <= header_offset <= total_size - len(inner):
        data[header_offset:header_offset + len(inner)] = inner
    with open(path, "wb") as handle:
        handle.write(data)


class StrictStagedExecutableValidationTests(unittest.TestCase):
    def test_non_mz_buffer_does_not_bypass_numeric_validation(self):
        tool = object.__new__(dynamic.ModernWowSetupTool)
        desired = {
            "fov": 1.9199,
            "farclip": 1500.0,
            "frill": 300.0,
            "nameplate": 41.0,
            "maxcam": 100.0,
            "sound": 64,
            "sound_bytes": b"64\x00\x00",
        }
        source_states = {
            "fov": struct.pack("<f", 1.5708),
            "farclip": struct.pack("<f", 777.0),
            "frill": struct.pack("<f", 70.0),
            "nameplate": struct.pack("<f", 20.0),
            "maxcam": struct.pack("<f", 50.0),
            "sound": b"12\x00\x00",
        }
        data = bytearray(0x46795C + 16)
        for key, offset, _label, _minimum, _maximum in dynamic._NUMERIC_SITES:
            data[offset:offset + 4] = source_states[key]
        sound_key, sound_offset, _label, _minimum, _maximum = dynamic._SOUND_SITE
        data[sound_offset:sound_offset + 4] = source_states[sound_key]

        struct.pack_into("<f", data, 0x40FED8, 2345.0)
        with self.assertRaisesRegex(RuntimeError, "produced by vanilla-tweaks"):
            tool._validate_staged_numeric_states(data, source_states, desired)

    def test_client_identity_has_no_non_mz_fixture_bypass(self):
        data = bytearray(0x46795C + 16)
        with self.assertRaisesRegex(RuntimeError, "build 5875"):
            dynamic.ModernWowSetupTool._validate_client_identity(data)


class WrappedMpqValidationTests(unittest.TestCase):
    def test_accepts_valid_user_data_wrapped_mpq(self):
        with tempfile.TemporaryDirectory() as temp:
            path = os.path.join(temp, "wrapped.mpq")
            _write_wrapped_mpq(path)
            dynamic._strict_verify_mpq(path)

    def test_rejects_user_data_wrapper_with_invalid_archive_offset(self):
        with tempfile.TemporaryDirectory() as temp:
            path = os.path.join(temp, "wrapped.mpq")
            data = bytearray(128)
            data[:16] = b"MPQ\x1B" + struct.pack("<III", 0, 8, 16)
            with open(path, "wb") as handle:
                handle.write(data)
            with self.assertRaisesRegex(
                remote_packages.RemotePackageError,
                "invalid nested archive offset",
            ):
                dynamic._strict_verify_mpq(path)

    def test_rejects_user_data_wrapper_with_out_of_bounds_archive_offset(self):
        with tempfile.TemporaryDirectory() as temp:
            path = os.path.join(temp, "wrapped.mpq")
            data = bytearray(128)
            data[:16] = b"MPQ\x1B" + struct.pack("<III", 0, 120, 16)
            with open(path, "wb") as handle:
                handle.write(data)
            with self.assertRaisesRegex(
                remote_packages.RemotePackageError,
                "invalid nested archive offset",
            ):
                dynamic._strict_verify_mpq(path)

    def test_rejects_user_data_wrapper_with_invalid_header_size(self):
        with tempfile.TemporaryDirectory() as temp:
            path = os.path.join(temp, "wrapped.mpq")
            data = bytearray(128)
            data[:16] = b"MPQ\x1B" + struct.pack("<III", 24, 32, 8)
            with open(path, "wb") as handle:
                handle.write(data)
            with self.assertRaisesRegex(
                remote_packages.RemotePackageError,
                "invalid nested archive offset",
            ):
                dynamic._strict_verify_mpq(path)

    def test_rejects_user_data_size_smaller_than_user_header(self):
        with tempfile.TemporaryDirectory() as temp:
            path = os.path.join(temp, "wrapped.mpq")
            _write_wrapped_mpq(path, user_data_size=8)
            with self.assertRaisesRegex(
                remote_packages.RemotePackageError,
                "invalid user-data size",
            ):
                dynamic._strict_verify_mpq(path)

    def test_rejects_user_data_size_beyond_nested_archive_offset(self):
        with tempfile.TemporaryDirectory() as temp:
            path = os.path.join(temp, "wrapped.mpq")
            _write_wrapped_mpq(path, user_data_size=40)
            with self.assertRaisesRegex(
                remote_packages.RemotePackageError,
                "invalid user-data size",
            ):
                dynamic._strict_verify_mpq(path)

    def test_rejects_wrapper_with_corrupt_nested_mpq(self):
        with tempfile.TemporaryDirectory() as temp:
            path = os.path.join(temp, "wrapped.mpq")
            _write_wrapped_mpq(path, inner_magic=b"NOPE")
            with self.assertRaisesRegex(
                remote_packages.RemotePackageError,
                "not a valid MPQ archive",
            ):
                dynamic._strict_verify_mpq(path)

    def test_rejects_wrapped_mpq_with_out_of_bounds_tables(self):
        with tempfile.TemporaryDirectory() as temp:
            path = os.path.join(temp, "wrapped.mpq")
            _write_wrapped_mpq(path, block_table_offset=88)
            with self.assertRaisesRegex(
                remote_packages.RemotePackageError,
                "out-of-bounds block table",
            ):
                dynamic._strict_verify_mpq(path)

    def test_rejects_zero_sector_size_shift(self):
        with tempfile.TemporaryDirectory() as temp:
            path = os.path.join(temp, "wrapped.mpq")
            _write_wrapped_mpq(path, sector_size_shift=0)
            with self.assertRaisesRegex(
                remote_packages.RemotePackageError,
                "invalid sector-size shift",
            ):
                dynamic._strict_verify_mpq(path)


if __name__ == "__main__":
    unittest.main()
