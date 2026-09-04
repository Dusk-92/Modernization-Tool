import hashlib
import json
import os
import shutil
import struct
import time
import urllib.error
import urllib.request
import zipfile


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT_ROOT = os.path.join(ROOT, "Payload", "Fallback", "Remote")
MANIFEST_PATH = os.path.join(ROOT, "Payload", "Fallback", "remote_fallbacks.json")
USER_AGENT = "Modernization-Tool build fallback fetcher"


FALLBACKS = [
    {
        "id": "wowpresence",
        "filename": "WowPresence.zip",
        "revision": "v1.3",
        "url": "https://github.com/Dusk-92/WowPresence/releases/download/v1.3/WowPresence.zip",
        "kind": "wowpresence_zip",
        "size": 141423,
        "sha256": "9b2dca9c69b5ab3b6dae3ef3b3efc9671779a227802ebb6ac98cb22bc6ea448a",
    },
]



def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest().lower()


def _download(url, destination, retries=3):
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last_error = None
    for attempt in range(1, retries + 1):
        temp_path = destination + ".new"
        try:
            with urllib.request.urlopen(request, timeout=300) as response, open(temp_path, "wb") as out:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
            os.replace(temp_path, destination)
            return
        except (OSError, urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            last_error = exc
            try:
                os.remove(temp_path)
            except OSError:
                pass
            if attempt < retries:
                time.sleep(attempt * 2)
    raise RuntimeError(f"Could not download {url}: {last_error}")


def _verify_x86_pe_bytes(data, label):
    if len(data) < 1024 or data[:2] != b"MZ":
        raise RuntimeError(f"{label} is not a valid PE file")
    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    if pe_offset < 64 or pe_offset > len(data) - 26:
        raise RuntimeError(f"{label} has an invalid PE offset")
    if data[pe_offset:pe_offset + 4] != b"PE\0\0":
        raise RuntimeError(f"{label} is missing the PE signature")
    machine = struct.unpack_from("<H", data, pe_offset + 4)[0]
    optional_size = struct.unpack_from("<H", data, pe_offset + 20)[0]
    optional_offset = pe_offset + 24
    if optional_size < 2 or optional_offset + 2 > len(data):
        raise RuntimeError(f"{label} has an invalid optional header")
    optional_magic = struct.unpack_from("<H", data, optional_offset)[0]
    if machine != 0x014C or optional_magic != 0x010B:
        raise RuntimeError(f"{label} is not a 32-bit x86 PE file")


def _verify_wowpresence_zip(path):
    with zipfile.ZipFile(path) as archive:
        entries = {name.rsplit("/", 1)[-1].lower(): name for name in archive.namelist()}
        for filename in ("WowPresence.dll", "WowPresence.exe"):
            member = entries.get(filename.lower())
            if member is None:
                raise RuntimeError(f"{filename} is missing from {path}")
            _verify_x86_pe_bytes(archive.read(member), filename)


def main():
    shutil.rmtree(OUTPUT_ROOT, ignore_errors=True)
    os.makedirs(OUTPUT_ROOT, exist_ok=True)

    manifest = {
        "schema": 1,
        "generated_for": "Modernization Tool release build",
        "fallbacks": {},
    }

    for item in FALLBACKS:
        destination = os.path.join(OUTPUT_ROOT, item["id"], item["filename"])
        print(f"Preparing bundled fallback: {item['id']}", flush=True)
        _download(item["url"], destination)

        if item["kind"] == "wowpresence_zip":
            _verify_wowpresence_zip(destination)
        else:
            raise RuntimeError(f"Unknown fallback kind: {item['kind']}")

        digest = _sha256(destination)
        expected = item.get("sha256")
        if expected and digest != expected.lower():
            raise RuntimeError(
                f"SHA-256 mismatch for {item['id']}: expected {expected}, got {digest}"
            )

        size = os.path.getsize(destination)
        expected_size = item.get("size")
        if expected_size is not None and size != expected_size:
            raise RuntimeError(
                f"Size mismatch for {item['id']}: expected {expected_size}, got {size}"
            )

        manifest["fallbacks"][item["id"]] = {
            "filename": item["filename"],
            "kind": item["kind"],
            "revision": item["revision"],
            "source": item["url"],
            "size": size,
            "sha256": digest,
        }
        print(
            f"FALLBACK {item['id']} size={size} sha256={digest}",
            flush=True,
        )

    staged = MANIFEST_PATH + ".new"
    with open(staged, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(staged, MANIFEST_PATH)
    print(f"Wrote {MANIFEST_PATH}", flush=True)


if __name__ == "__main__":
    main()
