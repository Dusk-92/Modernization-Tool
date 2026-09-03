import hashlib
import json
import os
import shutil
import stat
import struct
import tempfile
import time
import urllib.error
import urllib.request
import uuid
import zipfile

USER_AGENT = "Modernization-Tool/1.0 (+https://github.com/Dusk-92/Modernization-Tool)"
GITHUB_API = "https://api.github.com"
NETWORK_TIMEOUT = 30
WOWPRESENCE_REPO = "Dusk-92/WowPresence"
WOWPRESENCE_MANAGED_ID = "wowpresence"
WOWPRESENCE_DEFAULT_APPLICATION_ID = "1544072796098011176"
WOWPRESENCE_APPLICATION_ID_PLACEHOLDER = "PASTE_YOUR_DISCORD_APPLICATION_ID_HERE"

WOWPRESENCE_SHARE_NAME = 1
WOWPRESENCE_SHARE_GUILD = 2
WOWPRESENCE_SHARE_FACTION = 4
WOWPRESENCE_SHARE_CLASS = 8
WOWPRESENCE_SHARE_LEVEL = 16
WOWPRESENCE_SHARE_ZONE = 32
WOWPRESENCE_SHARE_RACE = 64
WOWPRESENCE_SHARE_ALL = 127


class RemotePackageError(RuntimeError):
    pass


def _emit_progress(callback, message, current=None, total=None):
    if callback is None:
        return
    try:
        callback(message, current, total)
    except Exception:
        # UI/progress reporting must never break an installation.
        pass


def _request(url, accept=None):
    headers = {"User-Agent": USER_AGENT}
    if accept:
        headers["Accept"] = accept
    return urllib.request.Request(url, headers=headers)


JSON_CACHE_TTL = 300
_JSON_CACHE = {}


def _get_json(url):
    now = time.monotonic()
    cached = _JSON_CACHE.get(url)
    if cached and now - cached[0] < JSON_CACHE_TTL:
        return cached[1]

    try:
        with urllib.request.urlopen(_request(url, "application/vnd.github+json"), timeout=NETWORK_TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        raise RemotePackageError(f"GitHub request failed: {exc}") from exc

    _JSON_CACHE[url] = (now, data)
    return data


def _latest_release(repo):
    data = _get_json(f"{GITHUB_API}/repos/{repo}/releases/latest")
    if data.get("draft") or data.get("prerelease"):
        raise RemotePackageError(f"{repo}: latest release is not a stable release.")
    return data


def _branch_head_sha(repo, branch):
    data = _get_json(f"{GITHUB_API}/repos/{repo}/commits/{branch}")
    sha = data.get("sha") if isinstance(data, dict) else None
    if not isinstance(sha, str) or len(sha) < 7:
        raise RemotePackageError(f"{repo}@{branch}: could not resolve branch revision.")
    return sha


def _release_revision(release):
    tag = release.get("tag_name") if isinstance(release, dict) else None
    if isinstance(tag, str) and tag.strip():
        return tag.strip()
    release_id = release.get("id") if isinstance(release, dict) else None
    if release_id is not None:
        return f"release:{release_id}"
    return "latest"


def _release_asset_revision(release, asset):
    """Track the actual release asset, even when an upstream reuses one tag."""
    base = _release_revision(release)
    digest = _asset_sha256(asset)
    if digest:
        return f"{base}|sha256:{digest}"

    asset_id = asset.get("id") if isinstance(asset, dict) else None
    updated = asset.get("updated_at") if isinstance(asset, dict) else None
    size = asset.get("size") if isinstance(asset, dict) else None
    name = asset.get("name") if isinstance(asset, dict) else None
    return (
        f"{base}|asset:{asset_id or name or '?'}"
        f"|updated:{updated or '?'}|size:{size or '?'}"
    )


def _find_asset(release, exact_name=None, predicate=None):
    for asset in release.get("assets", []):
        name = asset.get("name", "")
        if exact_name is not None and name.lower() == exact_name.lower():
            return asset
        if predicate is not None and predicate(name):
            return asset
    wanted = exact_name or "matching release asset"
    raise RemotePackageError(f"Could not find {wanted} in release {release.get('tag_name', '?')}.")


def _download(url, suffix="", expected_digest=None, progress=None, label="Downloading", timeout=NETWORK_TIMEOUT):
    fd, temp_path = tempfile.mkstemp(prefix="modernization_", suffix=suffix)
    os.close(fd)
    try:
        digest = hashlib.sha256()
        with urllib.request.urlopen(_request(url), timeout=timeout) as response, open(temp_path, "wb") as out:
            total = None
            length = response.headers.get("Content-Length")
            if length:
                try:
                    total = int(length)
                except (TypeError, ValueError):
                    total = None

            downloaded = 0
            _emit_progress(progress, label, downloaded, total)

            while True:
                chunk = response.read(256 * 1024)
                if not chunk:
                    break
                out.write(chunk)
                digest.update(chunk)
                downloaded += len(chunk)
                _emit_progress(progress, label, downloaded, total)

            _emit_progress(progress, label, downloaded, total or downloaded)

        if expected_digest and expected_digest.startswith("sha256:"):
            expected = expected_digest.split(":", 1)[1].lower()
            actual = digest.hexdigest().lower()
            if actual != expected:
                raise RemotePackageError(
                    f"SHA-256 mismatch for downloaded file (expected {expected}, got {actual})."
                )
        return temp_path
    except Exception:
        try:
            os.remove(temp_path)
        except OSError:
            pass
        raise


def _download_asset(asset, progress=None, label=None):
    url = asset.get("browser_download_url")
    if not url:
        raise RemotePackageError(f"Release asset {asset.get('name', '?')} has no download URL.")
    suffix = os.path.splitext(asset.get("name", ""))[1]
    display = label or f"Downloading {asset.get('name', 'release asset')}"
    try:
        return _download(
            url,
            suffix=suffix,
            expected_digest=asset.get("digest"),
            progress=progress,
            label=display,
        )
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        raise RemotePackageError(f"Download failed for {asset.get('name', '?')}: {exc}") from exc


def _verify_x86_pe(path, label="downloaded DLL", min_size=1024):
    """Validate a 32-bit x86 PE binary before it can reach the WoW folder."""
    try:
        size = os.path.getsize(path)
        if size < min_size:
            raise RemotePackageError(
                f"{label} is unexpectedly small ({size} bytes)."
            )

        with open(path, "rb") as handle:
            dos = handle.read(64)
            if len(dos) < 64 or dos[:2] != b"MZ":
                raise RemotePackageError(
                    f"{label} is not a valid Windows PE binary (missing MZ header)."
                )

            pe_offset = struct.unpack_from("<I", dos, 0x3C)[0]
            if pe_offset < 64 or pe_offset > size - 26:
                raise RemotePackageError(
                    f"{label} has an invalid PE header offset."
                )

            handle.seek(pe_offset)
            if handle.read(4) != b"PE\0\0":
                raise RemotePackageError(
                    f"{label} is not a valid Windows PE binary (missing PE signature)."
                )

            coff = handle.read(20)
            if len(coff) != 20:
                raise RemotePackageError(
                    f"{label} has a truncated COFF header."
                )

            machine = struct.unpack_from("<H", coff, 0)[0]
            optional_size = struct.unpack_from("<H", coff, 16)[0]
            if optional_size < 2:
                raise RemotePackageError(
                    f"{label} has an invalid optional-header size."
                )

            optional_magic_raw = handle.read(2)
            if len(optional_magic_raw) != 2:
                raise RemotePackageError(
                    f"{label} has a truncated optional header."
                )
            optional_magic = struct.unpack("<H", optional_magic_raw)[0]

        if machine != 0x014C or optional_magic != 0x010B:
            raise RemotePackageError(
                f"{label} is not a 32-bit x86 PE binary "
                f"(machine=0x{machine:04X}, optional=0x{optional_magic:04X})."
            )

    except RemotePackageError:
        raise
    except (OSError, struct.error) as exc:
        raise RemotePackageError(
            f"Could not validate {label}: {exc}"
        ) from exc


def _atomic_replace_file(source, target):
    os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
    staged = target + ".modernization-new"
    try:
        shutil.copy2(source, staged)
        os.replace(staged, target)
    finally:
        if os.path.exists(staged):
            try:
                os.remove(staged)
            except OSError:
                pass


def _remove_tree(path):
    if not os.path.exists(path):
        return

    def onerror(func, failing_path, _exc_info):
        try:
            os.chmod(failing_path, stat.S_IWRITE)
            func(failing_path)
        except Exception:
            raise

    shutil.rmtree(path, onerror=onerror)


def _replace_directory(source_dir, target_dir):
    """Replace an addon directory without reusing stale fixed backup names."""
    os.makedirs(os.path.dirname(os.path.abspath(target_dir)), exist_ok=True)

    token = uuid.uuid4().hex[:10]
    staged = f"{target_dir}.modernization-new-{token}"
    backup = f"{target_dir}.modernization-backup-{token}"

    shutil.copytree(source_dir, staged)
    had_existing = os.path.exists(target_dir)
    backup_created = False

    try:
        if had_existing:
            try:
                os.replace(target_dir, backup)
                backup_created = True
            except PermissionError:
                # Windows can refuse directory renames in some addon folders.
                # Fall back to a direct remove-and-replace after the new copy has
                # already been fully staged.
                try:
                    _remove_tree(target_dir)
                except Exception as exc:
                    raise RemotePackageError(
                        f"Could not replace {target_dir}. Close WoW and any program "
                        f"using this addon folder, then try again. ({exc})"
                    ) from exc

        os.replace(staged, target_dir)

        if backup_created and os.path.exists(backup):
            _remove_tree(backup)

    except Exception:
        if backup_created and os.path.exists(backup):
            if os.path.exists(target_dir):
                try:
                    _remove_tree(target_dir)
                except Exception:
                    pass
            if not os.path.exists(target_dir):
                try:
                    os.replace(backup, target_dir)
                except Exception:
                    pass
        raise
    finally:
        if os.path.exists(staged):
            try:
                _remove_tree(staged)
            except Exception:
                pass
        if os.path.exists(backup):
            try:
                _remove_tree(backup)
            except Exception:
                pass



def _remove_path(path):
    """Remove a file, symlink or directory without following directory symlinks."""
    if not os.path.lexists(path):
        return
    if os.path.islink(path) or os.path.isfile(path):
        try:
            os.chmod(path, os.stat(path).st_mode | stat.S_IWRITE)
        except OSError:
            pass
        os.remove(path)
        return
    if os.path.isdir(path):
        _remove_tree(path)
        return
    os.remove(path)


def _cleanup_transaction_backups(target):
    """Best-effort cleanup of stale backups once a valid live target exists."""
    target = os.path.abspath(target)
    if not os.path.lexists(target):
        return

    parent = os.path.dirname(target)
    prefix = os.path.basename(target) + ".modernization-backup-"
    try:
        names = os.listdir(parent)
    except OSError:
        return

    for name in names:
        if not name.startswith(prefix):
            continue
        backup = os.path.join(parent, name)
        try:
            _remove_path(backup)
        except OSError:
            # The old file may still be locked by WoW/Windows. Keep it safe
            # and retry automatically the next time this package is verified.
            pass


def _transactional_replace_bundle(items, label="component bundle"):
    """Replace a group of files/directories as one rollback-safe transaction.

    items contains tuples of (kind, source, target), where kind is "file" or
    "dir". Every new item is fully staged first. Existing targets are then
    renamed to unique backups before any staged item becomes live. If any
    commit step fails, all changed targets are removed and every backup is
    restored, preventing mixed DLL/AddOn versions.
    """
    token = uuid.uuid4().hex[:12]
    records = []

    try:
        # Stage the complete new bundle before touching any installed file.
        for kind, source, target in items:
            if kind not in ("file", "dir"):
                raise RemotePackageError(f"Unsupported transactional item type: {kind}")
            if kind == "file" and not os.path.isfile(source):
                raise RemotePackageError(f"Transactional source file is missing: {source}")
            if kind == "dir" and not os.path.isdir(source):
                raise RemotePackageError(f"Transactional source directory is missing: {source}")

            target = os.path.abspath(target)
            parent = os.path.dirname(target)
            os.makedirs(parent, exist_ok=True)

            staged = f"{target}.modernization-new-{token}"
            backup = f"{target}.modernization-backup-{token}"

            if os.path.lexists(staged) or os.path.lexists(backup):
                raise RemotePackageError(
                    f"Unexpected temporary path already exists while installing {label}."
                )

            if kind == "file":
                shutil.copy2(source, staged)
            else:
                shutil.copytree(source, staged)

            records.append(
                {
                    "kind": kind,
                    "target": target,
                    "staged": staged,
                    "backup": backup,
                    "backup_created": False,
                    "installed": False,
                }
            )

        # Move all old components out of the way first.
        for record in records:
            if os.path.lexists(record["target"]):
                try:
                    os.replace(record["target"], record["backup"])
                    record["backup_created"] = True
                except OSError as exc:
                    raise RemotePackageError(
                        f"Could not prepare {record['target']} for replacement. "
                        "Close WoW and any program using its files, then try again."
                    ) from exc

        # Only now expose the complete new bundle.
        for record in records:
            os.replace(record["staged"], record["target"])
            record["installed"] = True

    except Exception as exc:
        rollback_errors = []

        # Remove any new components that were already committed.
        for record in reversed(records):
            if record["installed"] and os.path.lexists(record["target"]):
                try:
                    _remove_path(record["target"])
                except Exception as rollback_exc:
                    rollback_errors.append(
                        f"could not remove new {record['target']}: {rollback_exc}"
                    )

        # Put every previous component back exactly where it was.
        for record in reversed(records):
            if record["backup_created"] and os.path.lexists(record["backup"]):
                try:
                    if os.path.lexists(record["target"]):
                        _remove_path(record["target"])
                    os.replace(record["backup"], record["target"])
                except Exception as rollback_exc:
                    rollback_errors.append(
                        f"could not restore {record['target']}: {rollback_exc}"
                    )

        if rollback_errors:
            remaining = [
                record["backup"]
                for record in records
                if os.path.lexists(record["backup"])
            ]
            details = "; ".join(rollback_errors)
            backup_note = (
                " Remaining backups: " + ", ".join(remaining)
                if remaining
                else ""
            )
            raise RemotePackageError(
                f"{label} update failed and rollback was incomplete. "
                f"{details}.{backup_note}"
            ) from exc

        if isinstance(exc, RemotePackageError):
            raise
        raise RemotePackageError(
            f"{label} update failed; the previous installation was restored. ({exc})"
        ) from exc

    else:
        # Commit succeeded. Old copies are no longer needed. Clean the current
        # transaction backup plus any stale backup left by an earlier run.
        for record in records:
            _cleanup_transaction_backups(record["target"])

    finally:
        # Staged paths are safe to remove. Backups are intentionally not
        # deleted here: if rollback itself fails, they are the recovery copy.
        for record in records:
            if os.path.lexists(record["staged"]):
                try:
                    _remove_path(record["staged"])
                except OSError:
                    pass


def _safe_extract(zip_path, destination):
    root = os.path.realpath(destination)
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            candidate = os.path.realpath(os.path.join(destination, member.filename))
            if candidate != root and not candidate.startswith(root + os.sep):
                raise RemotePackageError(f"Unsafe ZIP path: {member.filename}")
        archive.extractall(destination)


def _find_file(root, filename):
    wanted = filename.lower()
    for current_root, _, files in os.walk(root):
        for item in files:
            if item.lower() == wanted:
                return os.path.join(current_root, item)
    raise RemotePackageError(f"{filename} was not found in downloaded archive.")


def _find_directory(root, dirname):
    wanted = dirname.lower()
    for current_root, dirs, _ in os.walk(root):
        for item in dirs:
            if item.lower() == wanted:
                return os.path.join(current_root, item)
    raise RemotePackageError(f"{dirname} was not found in downloaded archive.")


def _find_directory_with_file(root, filename):
    wanted = filename.lower()
    for current_root, _, files in os.walk(root):
        if any(item.lower() == wanted for item in files):
            return current_root
    return None


def vanilla_tweaks_release_info():
    release = _latest_release("tubtubs/vanilla-tweaks")
    asset = _find_asset(
        release,
        predicate=lambda name: (
            name.lower().endswith(".zip")
            and "windows" in name.lower()
            and not name.lower().endswith(".sha256sum")
        ),
    )
    return {
        "release": release,
        "asset": asset,
        "revision": _release_asset_revision(release, asset),
        "version": release.get("name") or _release_revision(release),
    }


def prepare_vanilla_tweaks(progress=None, release_info=None):
    """Download and extract the latest stable tubtubs vanilla-tweaks Windows build."""
    _emit_progress(progress, "Checking vanilla-tweaks release...", None, None)
    info = release_info or vanilla_tweaks_release_info()
    release = info["release"]
    asset = info["asset"]
    zip_path = _download_asset(
        asset,
        progress=progress,
        label="Downloading vanilla-tweaks",
    )
    extract_root = tempfile.mkdtemp(prefix="modernization_vanillatweaks_")
    try:
        _emit_progress(progress, "Extracting vanilla-tweaks...", None, None)
        _safe_extract(zip_path, extract_root)
        exe_path = _find_file(extract_root, "vanilla-tweaks.exe")
    except Exception:
        shutil.rmtree(extract_root, ignore_errors=True)
        raise
    finally:
        try:
            os.remove(zip_path)
        except OSError:
            pass

    return exe_path, extract_root, info["version"], info["revision"]


def _write_text_if_missing(path, text):
    """Create a small user-editable config file without overwriting it later."""
    if os.path.exists(path):
        return
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    temp_path = path + ".new"
    try:
        with open(temp_path, "w", encoding="ascii", newline="\n") as handle:
            handle.write(text)
        if not os.path.exists(path):
            os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


def ensure_wowpresence_config(target_dir):
    """Prepare the Modernization Tool-specific WowPresence data directory."""
    data_dir = os.path.join(target_dir, ".modernization_tool", "WowPresence")
    os.makedirs(data_dir, exist_ok=True)

    app_id_path = os.path.join(data_dir, "discord_application_id")
    _write_text_if_missing(
        app_id_path,
        WOWPRESENCE_DEFAULT_APPLICATION_ID + "\n",
    )

    # Migrate the placeholder created by early test builds to the OctoWoW
    # Application ID, but never overwrite a user's own configured ID.
    try:
        with open(app_id_path, "r", encoding="ascii", errors="ignore") as handle:
            current_id = handle.read().strip()
    except OSError:
        current_id = ""

    if current_id == WOWPRESENCE_APPLICATION_ID_PLACEHOLDER:
        temp_path = app_id_path + ".new"
        try:
            with open(temp_path, "w", encoding="ascii", newline="\n") as handle:
                handle.write(WOWPRESENCE_DEFAULT_APPLICATION_ID + "\n")
            os.replace(temp_path, app_id_path)
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    _write_text_if_missing(
        os.path.join(data_dir, "discord_broadcast_flags"),
        "127\n",
    )
    return data_dir


def read_wowpresence_broadcast_flags(target_dir):
    """Read the user-visible WowPresence detail mask, or None when invalid."""
    path = os.path.join(
        target_dir,
        ".modernization_tool",
        "WowPresence",
        "discord_broadcast_flags",
    )
    try:
        with open(path, "r", encoding="ascii", errors="ignore") as handle:
            text = handle.read().strip()
        value = int(text, 10)
    except (OSError, ValueError):
        return None

    if value < 0:
        return None
    return value & WOWPRESENCE_SHARE_ALL


def write_wowpresence_broadcast_flags(target_dir, value):
    """Atomically persist the WowPresence detail mask without touching other config."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("WowPresence broadcast flags must be an integer.")
    if value < 0 or value > WOWPRESENCE_SHARE_ALL:
        raise ValueError(
            f"WowPresence broadcast flags must be between 0 and {WOWPRESENCE_SHARE_ALL}."
        )

    data_dir = ensure_wowpresence_config(target_dir)
    path = os.path.join(data_dir, "discord_broadcast_flags")
    temp_path = path + ".new"
    try:
        with open(temp_path, "w", encoding="ascii", newline="\n") as handle:
            handle.write(f"{value}\n")
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
    return path



def install_wowpresence(target_dir, progress=None):
    """Install or update WowPresence from its latest stable GitHub release ZIP."""
    _emit_progress(progress, "Checking WowPresence release...", None, None)
    release = _latest_release(WOWPRESENCE_REPO)
    revision = _release_revision(release)
    package_asset = _find_asset(release, exact_name="WowPresence.zip")
    package_revision = _release_asset_revision(release, package_asset)

    # Preserve whether dlls.txt already belonged to a standalone/manual
    # WowPresence install before this tool first takes ownership.
    existing_manifest = _load_managed_manifest_data(
        target_dir,
        WOWPRESENCE_MANAGED_ID,
    )
    dlls_entry_preexisting = existing_manifest.get("dlls_entry_preexisting")
    if not isinstance(dlls_entry_preexisting, bool):
        if existing_manifest:
            # Legacy test manifests predate explicit dlls.txt ownership.
            # A saved DLL backup is the conservative signal that a manual
            # WowPresence installation existed before the tool took over.
            dlls_entry_preexisting = _managed_backup_exists(
                target_dir,
                WOWPRESENCE_MANAGED_ID,
                "WowPresence.dll",
            )
        else:
            dlls_entry_preexisting = _dlls_contains_entry(
                target_dir,
                "WowPresence.dll",
            )

    # The directory itself is the signal used by WowPresence to select
    # the Modernization Tool managed data location instead of the standalone
    # one. User-editable config is created only when missing.
    ensure_wowpresence_config(target_dir)

    if managed_mod_is_current(target_dir, WOWPRESENCE_MANAGED_ID, revision):
        manifest = _load_managed_manifest_data(target_dir, WOWPRESENCE_MANAGED_ID)
        saved_hashes = manifest.get("file_sha256")
        if not isinstance(saved_hashes, dict):
            saved_hashes = {}

        saved_package_revision = manifest.get("package_revision")
        current_digest = package_asset.get("digest")
        saved_digest = manifest.get("package_digest")
        package_matches = (
            str(saved_package_revision) == str(package_revision)
            or (
                saved_package_revision in (None, "")
                and isinstance(saved_digest, str)
                and isinstance(current_digest, str)
                and saved_digest == current_digest
            )
        )

        def installed_file_ok(filename):
            path = os.path.join(target_dir, filename)
            expected = saved_hashes.get(filename)
            if isinstance(expected, str):
                expected = expected.strip().lower()
                if len(expected) == 64 and all(ch in "0123456789abcdef" for ch in expected):
                    try:
                        return _file_sha256(path) == expected
                    except OSError:
                        return False
            try:
                _verify_x86_pe(path, filename)
                return True
            except RemotePackageError:
                return False

        dll_ok = installed_file_ok("WowPresence.dll")
        exe_ok = installed_file_ok("WowPresence.exe")
        if dll_ok and exe_ok and package_matches:
            _set_managed_manifest_values(
                target_dir,
                WOWPRESENCE_MANAGED_ID,
                dlls_entry_preexisting=bool(dlls_entry_preexisting),
                package_revision=package_revision,
                package_digest=current_digest,
            )
            _emit_progress(
                progress,
                f"WowPresence {revision} is already current.",
                None,
                None,
            )
            return revision
        _emit_progress(
            progress,
            f"WowPresence {revision} needs repair; refreshing package...",
            None,
            None,
        )

    zip_path = None
    extract_root = None
    try:
        zip_path = _download_asset(
            package_asset,
            progress=progress,
            label="Downloading WowPresence.zip",
        )
        extract_root = tempfile.mkdtemp(prefix="modernization_wowpresence_")
        _emit_progress(progress, "Extracting WowPresence...", None, None)
        _safe_extract(zip_path, extract_root)

        dll_path = _find_file(extract_root, "WowPresence.dll")
        exe_path = _find_file(extract_root, "WowPresence.exe")
        _verify_x86_pe(dll_path, "WowPresence.dll")
        _verify_x86_pe(exe_path, "WowPresence.exe")

        _emit_progress(progress, f"Installing WowPresence {revision}...", None, None)
        _install_managed_files_transactional(
            target_dir,
            WOWPRESENCE_MANAGED_ID,
            [
                (dll_path, "WowPresence.dll"),
                (exe_path, "WowPresence.exe"),
            ],
            revision=revision,
        )
        _set_managed_manifest_values(
            target_dir,
            WOWPRESENCE_MANAGED_ID,
            dlls_entry_preexisting=bool(dlls_entry_preexisting),
            file_sha256={
                "WowPresence.dll": _file_sha256(dll_path),
                "WowPresence.exe": _file_sha256(exe_path),
            },
            package_digest=package_asset.get("digest"),
            package_revision=package_revision,
        )
    finally:
        if zip_path and os.path.exists(zip_path):
            try:
                os.remove(zip_path)
            except OSError:
                pass
        if extract_root:
            shutil.rmtree(extract_root, ignore_errors=True)

    # Never overwrite user-editable settings with the copies bundled in the
    # release ZIP. The managed config folder remains owned by the user/tool.
    ensure_wowpresence_config(target_dir)
    return revision


def install_interact(target_dir, progress=None):
    _emit_progress(progress, "Checking Interact release...", None, None)
    release = _latest_release("lookino/Interact")
    asset = _find_asset(release, exact_name="Interact.zip")
    revision = _release_asset_revision(release, asset)
    version = _release_revision(release)
    package_id = "interact"

    if _package_state_is_current(target_dir, package_id, revision):
        _emit_progress(progress, f"Interact {version} is already current.", None, None)
        return version

    zip_path = _download_asset(asset, progress=progress, label="Downloading Interact package")
    extract_root = tempfile.mkdtemp(prefix="modernization_interact_")
    try:
        _emit_progress(progress, "Extracting Interact...", None, None)
        _safe_extract(zip_path, extract_root)
        dll_path = _find_file(extract_root, "Interact.dll")
        _verify_x86_pe(dll_path, "Interact.dll")
        addon_dir = _find_directory_with_file(extract_root, "Interact.toc")
        if addon_dir is None:
            raise RemotePackageError("Interact.toc was not found in the Interact archive.")

        _emit_progress(progress, "Installing Interact atomically...", None, None)
        _transactional_replace_bundle(
            [
                ("file", dll_path, os.path.join(target_dir, "Interact.dll")),
                (
                    "dir",
                    addon_dir,
                    os.path.join(target_dir, "Interface", "AddOns", "Interact"),
                ),
            ],
            label="Interact",
        )
        _record_package_state_safely(
            target_dir,
            package_id,
            revision,
            [
                "Interact.dll",
                os.path.join("Interface", "AddOns", "Interact"),
            ],
        )
    finally:
        try:
            os.remove(zip_path)
        except OSError:
            pass
        shutil.rmtree(extract_root, ignore_errors=True)

    return version



def install_vanilla_multimonitor_fix(target_dir, progress=None):
    _emit_progress(progress, "Checking VanillaMultiMonitorFix release...", None, None)
    release = _latest_release("Mates1500/VanillaMultiMonitorFix")
    asset = _find_asset(release, exact_name="release.zip")
    revision = _release_asset_revision(release, asset)
    version = _release_revision(release)
    package_id = "vanilla_multimonitor_fix"

    if _package_state_is_current(target_dir, package_id, revision):
        _emit_progress(
            progress,
            f"VanillaMultiMonitorFix {version} is already current.",
            None,
            None,
        )
        return version

    zip_path = _download_asset(
        asset,
        progress=progress,
        label="Downloading VanillaMultiMonitorFix package",
    )
    extract_root = tempfile.mkdtemp(prefix="modernization_vmmfix_")
    try:
        _emit_progress(progress, "Extracting VanillaMultiMonitorFix...", None, None)
        _safe_extract(zip_path, extract_root)
        dll_path = _find_file(extract_root, "VanillaMultiMonitorFix.dll")
        _verify_x86_pe(dll_path, "VanillaMultiMonitorFix.dll")
        config_path = _find_file(extract_root, "VMMFix_preferred_monitor.txt")

        _emit_progress(progress, "Installing VanillaMultiMonitorFix.dll...", None, None)
        _atomic_replace_file(
            dll_path,
            os.path.join(target_dir, "VanillaMultiMonitorFix.dll"),
        )

        # Preserve a user's chosen monitor index on subsequent runs.
        target_config = os.path.join(target_dir, "VMMFix_preferred_monitor.txt")
        if not os.path.exists(target_config):
            _emit_progress(progress, "Installing monitor preference file...", None, None)
            _atomic_replace_file(config_path, target_config)

        # The preference file is intentionally excluded from integrity tracking
        # because it is user-editable.
        _record_package_state_safely(
            target_dir,
            package_id,
            revision,
            ["VanillaMultiMonitorFix.dll"],
        )
    finally:
        try:
            os.remove(zip_path)
        except OSError:
            pass
        shutil.rmtree(extract_root, ignore_errors=True)

    return version

MANAGED_ROOT = ".modernization_tool"


def _safe_relative_path(relative_path):
    rel = os.path.normpath(str(relative_path).replace("\\", os.sep).replace("/", os.sep))
    if os.path.isabs(rel) or rel == ".." or rel.startswith(".." + os.sep):
        raise RemotePackageError(f"Unsafe managed path: {relative_path}")
    return rel


def _managed_locations(target_dir, mod_id):
    root = os.path.join(target_dir, MANAGED_ROOT)
    manifest = os.path.join(root, "manifests", f"{mod_id}.json")
    backups = os.path.join(root, "backups", mod_id)
    return root, manifest, backups


def _load_managed_manifest_data(target_dir, mod_id):
    _, manifest_path, _ = _managed_locations(target_dir, mod_id)
    if not os.path.isfile(manifest_path):
        return {}
    try:
        with open(manifest_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError, ValueError):
        return {}


def _load_managed_manifest(target_dir, mod_id):
    data = _load_managed_manifest_data(target_dir, mod_id)
    files = data.get("files", [])
    if not isinstance(files, list):
        return []
    return [_safe_relative_path(item) for item in files if isinstance(item, str)]


def managed_mod_has_manifest(target_dir, mod_id):
    """Return True when a valid managed manifest claims at least one file."""
    return bool(_load_managed_manifest(target_dir, mod_id))


def managed_mod_manifest_value(target_dir, mod_id, key, default=None):
    """Read one non-file metadata value from a managed manifest."""
    data = _load_managed_manifest_data(target_dir, mod_id)
    return data.get(key, default)


def _set_managed_manifest_values(target_dir, mod_id, **values):
    """Atomically add/update metadata without changing managed file ownership."""
    _, manifest_path, _ = _managed_locations(target_dir, mod_id)
    data = _load_managed_manifest_data(target_dir, mod_id)
    if not data or not isinstance(data.get("files"), list):
        return
    data.update(values)
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
    temp_path = manifest_path + ".new"
    try:
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        os.replace(temp_path, manifest_path)
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


def _dlls_contains_entry(target_dir, entry):
    path = os.path.join(target_dir, "dlls.txt")
    wanted = str(entry).strip().casefold()
    if not wanted or not os.path.isfile(path):
        return False
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            for raw in handle:
                line = raw.strip()
                if not line or line.startswith("#") or line.startswith(";"):
                    continue
                if line.casefold() == wanted:
                    return True
    except OSError:
        return False
    return False


def _managed_backup_exists(target_dir, mod_id, relative_path):
    _, _, backup_root = _managed_locations(target_dir, mod_id)
    rel = _safe_relative_path(relative_path)
    return os.path.isfile(os.path.join(backup_root, rel))


def _asset_sha256(asset):
    digest = (asset or {}).get("digest")
    if isinstance(digest, str) and digest.lower().startswith("sha256:"):
        value = digest.split(":", 1)[1].strip().lower()
        if len(value) == 64 and all(ch in "0123456789abcdef" for ch in value):
            return value
    return None


def _file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest().lower()


PACKAGE_STATE_DIR = "package_state"


def _package_state_path(target_dir, package_id):
    safe_id = "".join(
        ch if ch.isalnum() or ch in ("-", "_", ".") else "_"
        for ch in str(package_id)
    )
    return os.path.join(
        target_dir,
        MANAGED_ROOT,
        PACKAGE_STATE_DIR,
        safe_id + ".json",
    )


def _hash_directory(path):
    digest = hashlib.sha256()
    if not os.path.isdir(path):
        raise OSError(f"Directory does not exist: {path}")

    found_file = False
    for current_root, dirs, files in os.walk(path):
        dirs.sort(key=str.casefold)
        files.sort(key=str.casefold)
        for filename in files:
            found_file = True
            full_path = os.path.join(current_root, filename)
            rel = os.path.relpath(full_path, path).replace(os.sep, "/")
            digest.update(b"F\0")
            digest.update(rel.encode("utf-8", "surrogatepass"))
            digest.update(b"\0")
            digest.update(_file_sha256(full_path).encode("ascii"))
            digest.update(b"\0")

    if not found_file:
        digest.update(b"EMPTY\0")
    return digest.hexdigest().lower()


def _snapshot_package_paths(target_dir, relative_paths):
    entries = {}
    for relative in relative_paths:
        rel = _safe_relative_path(relative)
        full_path = os.path.join(target_dir, rel)
        key = rel.replace(os.sep, "/")

        if os.path.isfile(full_path):
            entries[key] = {
                "type": "file",
                "sha256": _file_sha256(full_path),
            }
        elif os.path.isdir(full_path):
            entries[key] = {
                "type": "dir",
                "sha256": _hash_directory(full_path),
            }
        else:
            raise OSError(f"Package path is missing: {full_path}")
    return entries


def _load_package_state(target_dir, package_id):
    path = _package_state_path(target_dir, package_id)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        return {}


def _record_package_state(target_dir, package_id, revision, relative_paths):
    entries = _snapshot_package_paths(target_dir, relative_paths)
    path = _package_state_path(target_dir, package_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temp_path = path + ".new"
    payload = {
        "schema": 1,
        "package_id": str(package_id),
        "revision": str(revision),
        "paths": entries,
    }
    try:
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
    return payload


def _package_state_is_current(target_dir, package_id, revision):
    data = _load_package_state(target_dir, package_id)
    if str(data.get("revision")) != str(revision):
        return False

    paths = data.get("paths")
    if not isinstance(paths, dict) or not paths:
        return False

    try:
        current = _snapshot_package_paths(target_dir, paths.keys())
    except OSError:
        return False

    is_current = current == paths
    if is_current:
        # A verified current package no longer needs rollback artifacts from
        # earlier successful installs. Retry best-effort cleanup here so a
        # Windows file lock does not leave them around indefinitely.
        for relative_path in paths:
            _cleanup_transaction_backups(
                os.path.join(target_dir, relative_path)
            )
    return is_current


def _record_package_state_safely(target_dir, package_id, revision, relative_paths):
    try:
        _record_package_state(target_dir, package_id, revision, relative_paths)
        return True
    except OSError:
        # Update metadata is an optimization only. A successful component
        # install must remain usable even if its cache state cannot be saved.
        return False


def _record_release_asset_state_if_matching(
    target_dir,
    package_id,
    revision,
    relative_path,
    asset,
):
    """Migrate an existing direct release asset without downloading it again."""
    expected_sha = _asset_sha256(asset)
    if not expected_sha:
        return False

    rel = _safe_relative_path(relative_path)
    path = os.path.join(target_dir, rel)
    if not os.path.isfile(path):
        return False

    try:
        if _file_sha256(path) != expected_sha:
            return False
        _record_package_state(target_dir, package_id, revision, [rel])
        return True
    except OSError:
        return False


def _installed_asset_is_current(path, asset, label):
    """Validate an installed release asset without trusting existence alone."""
    if not os.path.isfile(path):
        return False
    expected_size = asset.get("size") if isinstance(asset, dict) else None
    if isinstance(expected_size, int) and expected_size > 0:
        try:
            if os.path.getsize(path) != expected_size:
                return False
        except OSError:
            return False

    expected_sha = _asset_sha256(asset)
    if expected_sha:
        try:
            return _file_sha256(path) == expected_sha
        except OSError:
            return False

    try:
        _verify_x86_pe(path, label)
        return True
    except RemotePackageError:
        return False


def _write_managed_manifest(target_dir, mod_id, relative_files, revision=None):
    _, manifest_path, _ = _managed_locations(target_dir, mod_id)
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
    temp_path = manifest_path + ".new"
    payload = {
        "mod_id": mod_id,
        "files": [str(path).replace(os.sep, "/") for path in relative_files],
    }
    if revision is not None:
        payload["revision"] = str(revision)
    with open(temp_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    os.replace(temp_path, manifest_path)


def _prune_empty_parents(path, stop_dir):
    current = os.path.abspath(path)
    stop = os.path.abspath(stop_dir)
    while current != stop and current.startswith(stop + os.sep):
        try:
            os.rmdir(current)
        except OSError:
            break
        current = os.path.dirname(current)


def _restore_or_remove_managed_file(target_dir, mod_id, relative_path):
    rel = _safe_relative_path(relative_path)
    _, _, backup_root = _managed_locations(target_dir, mod_id)
    target = os.path.join(target_dir, rel)
    backup = os.path.join(backup_root, rel)

    if os.path.isfile(backup):
        os.makedirs(os.path.dirname(target), exist_ok=True)
        _atomic_replace_file(backup, target)
        try:
            os.remove(backup)
        except OSError:
            pass
    elif os.path.isfile(target):
        try:
            os.remove(target)
        except OSError as exc:
            raise RemotePackageError(
                f"Could not remove {target}. Close WoW and try again. ({exc})"
            ) from exc

    _prune_empty_parents(os.path.dirname(target), target_dir)



# Existing manifests created before revision tracking correspond to revision 1
# of these visual sources. This lets current installations migrate without one
# unnecessary large re-download, while a future revision bump can still force
# a refresh automatically.
VISUAL_MOD_REVISIONS = {
    "visual_darker_nights": "1",
    "visual_pretty_night_sky": "1",
    "visual_epoch_water": "1",
    "visual_fog_pushback": "1",
    "visual_pink_herbs": "2",
}


def managed_mod_is_installed(target_dir, mod_id):
    """True only when a tool-managed manifest exists and all owned files remain present."""
    files = _load_managed_manifest(target_dir, mod_id)
    if not files:
        return False
    return all(os.path.isfile(os.path.join(target_dir, rel)) for rel in files)


def managed_mod_is_current(target_dir, mod_id, revision):
    """Check installed files plus the source revision recorded by the tool."""
    if not managed_mod_is_installed(target_dir, mod_id):
        return False

    data = _load_managed_manifest_data(target_dir, mod_id)
    installed_revision = data.get("revision")

    # Migrate pre-revision manifests for the visual sources that existed when
    # revision tracking was introduced.
    if installed_revision is None and mod_id in VISUAL_MOD_REVISIONS:
        installed_revision = "1"

    return str(installed_revision) == str(revision)


def managed_mpq_is_current(target_dir, mod_id, revision):
    """Cheap integrity check for an already installed managed MPQ."""
    if not managed_mod_is_current(target_dir, mod_id, revision):
        return False
    files = _load_managed_manifest(target_dir, mod_id)
    if len(files) != 1:
        return False
    path = os.path.join(target_dir, files[0])
    try:
        with open(path, "rb") as handle:
            return handle.read(3) == b"MPQ"
    except OSError:
        return False


def remove_managed_mod(target_dir, mod_id):
    """Remove only files previously installed by this tool, restoring backups."""
    root, manifest_path, backup_root = _managed_locations(target_dir, mod_id)
    files = _load_managed_manifest(target_dir, mod_id)
    if not files:
        return

    for rel in reversed(files):
        _restore_or_remove_managed_file(target_dir, mod_id, rel)

    try:
        os.remove(manifest_path)
    except OSError:
        pass

    if os.path.isdir(backup_root):
        shutil.rmtree(backup_root, ignore_errors=True)

    manifests_dir = os.path.join(root, "manifests")
    backups_dir = os.path.join(root, "backups")
    for directory in (manifests_dir, backups_dir, root):
        if os.path.isdir(directory):
            try:
                os.rmdir(directory)
            except OSError:
                pass


def _install_managed_files(target_dir, mod_id, file_mappings, revision=None):
    """Install files while preserving any pre-existing user files for restore."""
    root, _, backup_root = _managed_locations(target_dir, mod_id)
    del root
    previous = set(_load_managed_manifest(target_dir, mod_id))
    new_files = []

    normalized = []
    for source_path, relative_target in file_mappings:
        rel = _safe_relative_path(relative_target)
        normalized.append((source_path, rel))
        new_files.append(rel)

    # Restore/remove files that belonged to an older version but disappeared.
    for old_rel in sorted(previous - set(new_files), reverse=True):
        _restore_or_remove_managed_file(target_dir, mod_id, old_rel)

    for source_path, rel in normalized:
        target = os.path.join(target_dir, rel)
        backup = os.path.join(backup_root, rel)

        # Only snapshot a pre-existing file when this tool is taking ownership
        # of that path for the first time. On updates, the current target is
        # already our managed copy.
        if rel not in previous and os.path.isfile(target) and not os.path.exists(backup):
            os.makedirs(os.path.dirname(backup), exist_ok=True)
            shutil.copy2(target, backup)

        _atomic_replace_file(source_path, target)

    _write_managed_manifest(target_dir, mod_id, new_files, revision=revision)



def _install_managed_files_transactional(
    target_dir,
    mod_id,
    file_mappings,
    revision=None,
):
    """Install a multi-file managed pack with complete rollback on failure.

    This is intentionally used for sound packs where dozens of loose files are
    updated together. It snapshots the affected live files, this mod's saved
    user backups and its manifest before changing anything. If any write fails,
    the exact pre-update state is restored.
    """
    _, manifest_path, backup_root = _managed_locations(target_dir, mod_id)
    previous = set(_load_managed_manifest(target_dir, mod_id))

    normalized = []
    new_files = []
    seen = set()
    for source_path, relative_target in file_mappings:
        rel = _safe_relative_path(relative_target)
        key = os.path.normcase(rel)
        if key in seen:
            raise RemotePackageError(
                f"Duplicate managed target in {mod_id}: {relative_target}"
            )
        seen.add(key)

        if not os.path.isfile(source_path):
            raise RemotePackageError(
                f"Managed source file is missing: {source_path}"
            )

        normalized.append((source_path, rel))
        new_files.append(rel)

    if not normalized:
        raise RemotePackageError(f"No files were provided for managed mod {mod_id}.")

    affected = sorted(previous | set(new_files))
    snapshot_root = tempfile.mkdtemp(prefix=f"modernization_{mod_id}_rollback_")
    live_snapshot = os.path.join(snapshot_root, "live")
    backup_snapshot = os.path.join(snapshot_root, "backups")
    manifest_snapshot = os.path.join(snapshot_root, "manifest.json")
    had_backup_root = os.path.isdir(backup_root)
    had_manifest = os.path.isfile(manifest_path)

    try:
        # Snapshot all affected live files before touching the installation.
        for rel in affected:
            target = os.path.join(target_dir, rel)
            if os.path.isfile(target):
                snapshot = os.path.join(live_snapshot, rel)
                os.makedirs(os.path.dirname(snapshot), exist_ok=True)
                shutil.copy2(target, snapshot)
            elif os.path.lexists(target):
                raise RemotePackageError(
                    f"Managed audio target is not a regular file: {target}"
                )

        # Snapshot ownership metadata as well. Persistent backups are part of
        # the user's restore state and must roll back together with the WAVs.
        if had_backup_root:
            shutil.copytree(backup_root, backup_snapshot)
        if had_manifest:
            os.makedirs(os.path.dirname(manifest_snapshot), exist_ok=True)
            shutil.copy2(manifest_path, manifest_snapshot)

        try:
            # Remove files no longer present in a newer pack version, restoring
            # the user's original file when this tool had backed one up.
            for old_rel in sorted(previous - set(new_files), reverse=True):
                _restore_or_remove_managed_file(target_dir, mod_id, old_rel)

            # Install every new file. First ownership of an existing user file
            # still creates the same persistent restore backup as before.
            for source_path, rel in normalized:
                target = os.path.join(target_dir, rel)
                backup = os.path.join(backup_root, rel)

                if (
                    rel not in previous
                    and os.path.isfile(target)
                    and not os.path.exists(backup)
                ):
                    os.makedirs(os.path.dirname(backup), exist_ok=True)
                    shutil.copy2(target, backup)

                _atomic_replace_file(source_path, target)

            _write_managed_manifest(
                target_dir,
                mod_id,
                new_files,
                revision=revision,
            )

        except Exception as install_exc:
            rollback_errors = []

            # Restore every affected live file to its exact pre-update state.
            for rel in affected:
                target = os.path.join(target_dir, rel)
                snapshot = os.path.join(live_snapshot, rel)
                try:
                    if os.path.isfile(snapshot):
                        os.makedirs(os.path.dirname(target), exist_ok=True)
                        _atomic_replace_file(snapshot, target)
                    elif os.path.isfile(target):
                        os.remove(target)
                    elif os.path.lexists(target):
                        _remove_path(target)
                except Exception as rollback_exc:
                    rollback_errors.append(
                        f"could not restore {target}: {rollback_exc}"
                    )

            # Restore the persistent user-backup tree exactly as it was.
            try:
                if os.path.isdir(backup_root):
                    shutil.rmtree(backup_root)
                if had_backup_root:
                    os.makedirs(os.path.dirname(backup_root), exist_ok=True)
                    shutil.copytree(backup_snapshot, backup_root)
            except Exception as rollback_exc:
                rollback_errors.append(
                    f"could not restore managed backups: {rollback_exc}"
                )

            # Restore/remove the manifest to its previous state.
            try:
                if had_manifest:
                    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
                    _atomic_replace_file(manifest_snapshot, manifest_path)
                elif os.path.exists(manifest_path):
                    os.remove(manifest_path)
            except Exception as rollback_exc:
                rollback_errors.append(
                    f"could not restore managed manifest: {rollback_exc}"
                )

            if rollback_errors:
                raise RemotePackageError(
                    f"{mod_id} installation failed and rollback was incomplete. "
                    + "; ".join(rollback_errors)
                ) from install_exc

            raise RemotePackageError(
                f"{mod_id} installation failed; the previous sound-pack state "
                f"was restored. ({install_exc})"
            ) from install_exc

    finally:
        shutil.rmtree(snapshot_root, ignore_errors=True)


def _verify_mpq(path):
    try:
        with open(path, "rb") as handle:
            magic = handle.read(3)
    except OSError as exc:
        raise RemotePackageError(f"Could not inspect downloaded MPQ: {exc}") from exc
    if magic != b"MPQ":
        raise RemotePackageError("Downloaded file is not a valid MPQ archive.")



def _files_match_exactly(path_a, path_b):
    """Compare two files byte-for-byte without loading them fully into memory."""
    try:
        if os.path.getsize(path_a) != os.path.getsize(path_b):
            return False
        with open(path_a, "rb") as first, open(path_b, "rb") as second:
            while True:
                first_chunk = first.read(1024 * 1024)
                second_chunk = second.read(1024 * 1024)
                if first_chunk != second_chunk:
                    return False
                if not first_chunk:
                    return True
    except OSError:
        return False


def _migrate_legacy_pink_herbs_patch(target_dir, downloaded_path, progress=None):
    """Release legacy patch-H ownership only when doing so is demonstrably safe."""
    mod_id = "visual_pink_herbs"
    legacy_rel = _safe_relative_path(os.path.join("Data", "patch-H.mpq"))
    legacy_key = os.path.normcase(legacy_rel)
    files = _load_managed_manifest(target_dir, mod_id)

    if not any(os.path.normcase(rel) == legacy_key for rel in files):
        return

    legacy_target = os.path.join(target_dir, legacy_rel)
    safe_to_release = not os.path.lexists(legacy_target)
    if os.path.isfile(legacy_target):
        safe_to_release = _files_match_exactly(legacy_target, downloaded_path)

    if safe_to_release:
        _restore_or_remove_managed_file(target_dir, mod_id, legacy_rel)
        _emit_progress(
            progress,
            "Released legacy Pink Herbs patch-H.mpq for migration to patch-V.mpq.",
            None,
            None,
        )
    else:
        _emit_progress(
            progress,
            "Keeping existing patch-H.mpq because it no longer matches Pink Herbs.",
            None,
            None,
        )

    data = _load_managed_manifest_data(target_dir, mod_id)
    remaining = [rel for rel in files if os.path.normcase(rel) != legacy_key]
    _write_managed_manifest(
        target_dir,
        mod_id,
        remaining,
        revision=data.get("revision"),
    )

def _install_remote_mpq(
    target_dir,
    mod_id,
    url,
    destination,
    progress=None,
    label="Downloading visual mod",
    timeout=300,
    revision=None,
):
    temp_path = _download(
        url,
        suffix=".mpq",
        progress=progress,
        label=label,
        timeout=timeout,
    )
    try:
        _verify_mpq(temp_path)
        _emit_progress(progress, f"Installing {os.path.basename(destination)}...", None, None)
        _install_managed_files(
            target_dir,
            mod_id,
            [(temp_path, destination)],
            revision=revision,
        )
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


def _google_drive_download_url(file_id):
    return (
        "https://drive.usercontent.google.com/download"
        f"?id={file_id}&export=download&confirm=t"
    )


def install_darker_nights(target_dir, progress=None):
    _install_remote_mpq(
        target_dir,
        "visual_darker_nights",
        "https://pub-0f05631d243e4046993fc02ca7be9542.r2.dev/patches/patch-N.mpq",
        os.path.join("Data", "patch-N.mpq"),
        progress=progress,
        label="Downloading Darker Nights",
        revision=VISUAL_MOD_REVISIONS["visual_darker_nights"],
    )
    return "Project Reforged Patch-N"


def install_pretty_night_sky(target_dir, progress=None):
    # The hosted file is traditionally named patch-9.mpq. Never use that stock
    # numeric name in Data; install it as patch-Z.mpq instead.
    _install_remote_mpq(
        target_dir,
        "visual_pretty_night_sky",
        _google_drive_download_url("1qu99ZS-SQFfTtYodBmZWYiHmxL8QtUY4"),
        os.path.join("Data", "patch-Z.mpq"),
        progress=progress,
        label="Downloading Pretty Night Sky",
        revision=VISUAL_MOD_REVISIONS["visual_pretty_night_sky"],
    )
    return "RetroCro mirror"


def install_epoch_water(target_dir, progress=None):
    _install_remote_mpq(
        target_dir,
        "visual_epoch_water",
        _google_drive_download_url("1xRx9OrznbgbE1uBae3H3OGke9UoXtzmU"),
        os.path.join("Data", "patch-W.mpq"),
        progress=progress,
        label="Downloading Epoch Water",
        revision=VISUAL_MOD_REVISIONS["visual_epoch_water"],
    )
    return "RetroCro mirror"


def install_fog_pushback(target_dir, progress=None):
    _install_remote_mpq(
        target_dir,
        "visual_fog_pushback",
        _google_drive_download_url("14aHvyfr_ACL-UURbNa_fXRPcfQZoIw8n"),
        os.path.join("Data", "patch-Y.mpq"),
        progress=progress,
        label="Downloading Fog Pushback",
        revision=VISUAL_MOD_REVISIONS["visual_fog_pushback"],
    )
    return "RetroCro mirror"



def install_pink_herbs(target_dir, progress=None):
    mod_id = "visual_pink_herbs"
    destination = os.path.join("Data", "patch-V.mpq")
    revision = _branch_head_sha("seacrabsam/patch-herb", "main")

    if _package_state_is_current(target_dir, mod_id, revision):
        _emit_progress(
            progress,
            f"Pink Herbs {revision[:7]} is already current.",
            None,
            None,
        )
        return f"seacrabsam/patch-herb main@{revision[:7]}"

    temp_path = _download(
        f"https://raw.githubusercontent.com/seacrabsam/patch-herb/{revision}/patch-H.mpq",
        suffix=".mpq",
        progress=progress,
        label="Downloading Pink Herbs",
        timeout=300,
    )
    try:
        _verify_mpq(temp_path)
        _migrate_legacy_pink_herbs_patch(target_dir, temp_path, progress=progress)
        _emit_progress(
            progress,
            f"Installing {os.path.basename(destination)}...",
            None,
            None,
        )
        _install_managed_files(
            target_dir,
            mod_id,
            [(temp_path, destination)],
            revision=VISUAL_MOD_REVISIONS[mod_id],
        )
        _record_package_state_safely(
            target_dir,
            mod_id,
            revision,
            [destination],
        )
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass

    return f"seacrabsam/patch-herb main@{revision[:7]}"


def _download_github_branch_archive(
    repo,
    branch,
    progress=None,
    label="Downloading sound mod",
    revision=None,
):
    revision = revision or _branch_head_sha(repo, branch)
    url = f"https://codeload.github.com/{repo}/zip/{revision}"
    return _download(
        url,
        suffix=".zip",
        progress=progress,
        label=label,
        timeout=120,
    )



def install_bundled_tree(target_dir, mod_id, source_dir, destination_prefix):
    """Install a bundled multi-file tree with full rollback protection."""
    if not os.path.isdir(source_dir):
        raise RemotePackageError(f"Bundled backup folder is missing: {source_dir}")
    mappings = _collect_tree_files(source_dir, destination_prefix)
    _install_managed_files_transactional(target_dir, mod_id, mappings)


def _collect_tree_files(source_dir, destination_prefix):
    mappings = []
    for current_root, _, files in os.walk(source_dir):
        for filename in files:
            source_path = os.path.join(current_root, filename)
            relative = os.path.relpath(source_path, source_dir)
            target_rel = os.path.join(destination_prefix, relative)
            mappings.append((source_path, target_rel))
    if not mappings:
        raise RemotePackageError(f"No files found in downloaded sound pack: {source_dir}")
    return mappings



def _install_github_sound_pack(target_dir, mod_id, repo, branch, source_folder, destination_prefix, progress=None, label="Downloading sound mod"):
    revision = _branch_head_sha(repo, branch)
    if _package_state_is_current(target_dir, mod_id, revision):
        _emit_progress(
            progress,
            f"{label.replace('Downloading ', '')} is already current.",
            None,
            None,
        )
        return revision

    zip_path = _download_github_branch_archive(
        repo,
        branch,
        progress=progress,
        label=label,
        revision=revision,
    )
    extract_root = tempfile.mkdtemp(prefix=f"modernization_{mod_id}_")
    try:
        _emit_progress(progress, f"Extracting {label.replace('Downloading ', '')}...", None, None)
        _safe_extract(zip_path, extract_root)
        source_dir = _find_directory(extract_root, source_folder)
        mappings = _collect_tree_files(source_dir, destination_prefix)
        _emit_progress(progress, f"Installing {label.replace('Downloading ', '')}...", None, None)
        _install_managed_files_transactional(target_dir, mod_id, mappings)
        _record_package_state_safely(
            target_dir,
            mod_id,
            revision,
            _load_managed_manifest(target_dir, mod_id),
        )
    finally:
        try:
            os.remove(zip_path)
        except OSError:
            pass
        shutil.rmtree(extract_root, ignore_errors=True)
    return revision


def install_no_error_sounds(target_dir, progress=None):
    _install_github_sound_pack(
        target_dir,
        "audio_no_error_sounds",
        "Macumbafeh/NoErrorSounds",
        "main",
        "Sound",
        "Sound",
        progress=progress,
        label="Downloading NoErrorSounds",
    )
    return "Macumbafeh/NoErrorSounds main"


def install_fish_ping(target_dir, progress=None):
    _install_github_sound_pack(
        target_dir,
        "audio_fish_ping",
        "notsureawake/FishPing",
        "master",
        "Sound",
        "Sound",
        progress=progress,
        label="Downloading FishPing",
    )
    return "notsureawake/FishPing master"


def install_warlock_muted_demons(target_dir, progress=None):
    _install_github_sound_pack(
        target_dir,
        "audio_warlock_muted_demons",
        "spzilyk/Warlock-Muted-Demons",
        "main",
        "Data",
        "Data",
        progress=progress,
        label="Downloading Warlock Muted Demons",
    )
    return "spzilyk/Warlock-Muted-Demons main"



def install_nampower(target_dir, progress=None):
    _emit_progress(progress, "Checking Nampower release...", None, None)
    release = _latest_release("brues-code/nampower")
    asset = _find_asset(
        release,
        predicate=lambda name: name.lower().startswith("nampower-") and name.lower().endswith(".zip"),
    )
    revision = _release_asset_revision(release, asset)
    version = _release_revision(release)
    package_id = "nampower"

    if _package_state_is_current(target_dir, package_id, revision):
        _emit_progress(progress, f"Nampower {version} is already current.", None, None)
        return version

    zip_path = _download_asset(asset, progress=progress, label="Downloading Nampower package")
    extract_root = tempfile.mkdtemp(prefix="modernization_nampower_")
    try:
        _emit_progress(progress, "Extracting Nampower...", None, None)
        _safe_extract(zip_path, extract_root)
        dll_path = _find_file(extract_root, "nampower.dll")
        _verify_x86_pe(dll_path, "nampower.dll")
        addon_dir = _find_directory(extract_root, "NampowerSettings")

        _emit_progress(progress, "Installing Nampower atomically...", None, None)
        _transactional_replace_bundle(
            [
                ("file", dll_path, os.path.join(target_dir, "nampower.dll")),
                (
                    "dir",
                    addon_dir,
                    os.path.join(target_dir, "Interface", "AddOns", "nampowersettings"),
                ),
            ],
            label="Nampower",
        )
        _record_package_state_safely(
            target_dir,
            package_id,
            revision,
            [
                "nampower.dll",
                os.path.join("Interface", "AddOns", "nampowersettings"),
            ],
        )
    finally:
        try:
            os.remove(zip_path)
        except OSError:
            pass
        shutil.rmtree(extract_root, ignore_errors=True)
    return version


def install_vanillahelpers(target_dir, progress=None):
    _emit_progress(progress, "Checking VanillaHelpers release...", None, None)
    release = _latest_release("isfir/VanillaHelpers")
    asset = _find_asset(release, exact_name="VanillaHelpers.dll")
    revision = _release_asset_revision(release, asset)
    version = _release_revision(release)
    package_id = "vanillahelpers"
    relative_path = "VanillaHelpers.dll"

    if (
        _package_state_is_current(target_dir, package_id, revision)
        or _record_release_asset_state_if_matching(
            target_dir,
            package_id,
            revision,
            relative_path,
            asset,
        )
    ):
        _emit_progress(progress, f"VanillaHelpers {version} is already current.", None, None)
        return version

    temp_path = _download_asset(
        asset,
        progress=progress,
        label="Downloading VanillaHelpers.dll",
    )
    try:
        _verify_x86_pe(temp_path, "VanillaHelpers.dll")
        _emit_progress(progress, "Installing VanillaHelpers.dll...", None, None)
        _atomic_replace_file(temp_path, os.path.join(target_dir, relative_path))
        _record_package_state_safely(
            target_dir,
            package_id,
            revision,
            [relative_path],
        )
    finally:
        os.remove(temp_path)
    return version


def install_no1600x1200(target_dir, progress=None):
    _emit_progress(progress, "Checking no1600x1200 source...", None, None)
    revision = _branch_head_sha("RetroCro/TurtleWoW-Mods", "main")
    package_id = "no1600x1200"
    relative_path = "no1600x1200.dll"

    if _package_state_is_current(target_dir, package_id, revision):
        _emit_progress(
            progress,
            f"no1600x1200 {revision[:7]} is already current.",
            None,
            None,
        )
        return f"RetroCro/TurtleWoW-Mods main@{revision[:7]}"

    url = (
        "https://raw.githubusercontent.com/RetroCro/TurtleWoW-Mods/"
        f"{revision}/Archive/DLL%20BACKUP/no1600x1200.dll"
    )
    temp_path = _download(
        url,
        suffix=".dll",
        progress=progress,
        label="Downloading no1600x1200.dll",
    )
    try:
        _verify_x86_pe(temp_path, "no1600x1200.dll")
        _emit_progress(progress, "Installing no1600x1200.dll...", None, None)
        _atomic_replace_file(temp_path, os.path.join(target_dir, relative_path))
        _record_package_state_safely(
            target_dir,
            package_id,
            revision,
            [relative_path],
        )
    finally:
        os.remove(temp_path)
    return f"RetroCro/TurtleWoW-Mods main@{revision[:7]}"



def install_classicapi(target_dir, progress=None):
    _emit_progress(progress, "Checking ClassicAPI release...", None, None)
    release = _latest_release("brues-code/ClassicAPI")
    asset = _find_asset(release, exact_name="ClassicAPI.dll")
    revision = _release_asset_revision(release, asset)
    version = _release_revision(release)
    package_id = "classicapi"
    relative_path = "ClassicAPI.dll"

    if (
        _package_state_is_current(target_dir, package_id, revision)
        or _record_release_asset_state_if_matching(
            target_dir,
            package_id,
            revision,
            relative_path,
            asset,
        )
    ):
        _emit_progress(progress, f"ClassicAPI {version} is already current.", None, None)
        return version

    temp_path = _download_asset(asset, progress=progress, label="Downloading ClassicAPI.dll")
    try:
        _verify_x86_pe(temp_path, "ClassicAPI.dll")
        _emit_progress(progress, "Installing ClassicAPI.dll...", None, None)
        _atomic_replace_file(temp_path, os.path.join(target_dir, relative_path))
        _record_package_state_safely(
            target_dir,
            package_id,
            revision,
            [relative_path],
        )
    finally:
        os.remove(temp_path)
    return version


def install_auction_query_throttle(target_dir, progress=None):
    _emit_progress(progress, "Checking AuctionQueryThrottle release...", None, None)
    release = _latest_release("brues-code/AuctionQueryThrottle")
    asset = _find_asset(release, exact_name="AuctionQueryThrottle.dll")
    revision = _release_asset_revision(release, asset)
    version = _release_revision(release)
    package_id = "auction_query_throttle"
    relative_path = "AuctionQueryThrottle.dll"

    if (
        _package_state_is_current(target_dir, package_id, revision)
        or _record_release_asset_state_if_matching(
            target_dir,
            package_id,
            revision,
            relative_path,
            asset,
        )
    ):
        _emit_progress(
            progress,
            f"AuctionQueryThrottle {version} is already current.",
            None,
            None,
        )
        return version

    temp_path = _download_asset(
        asset,
        progress=progress,
        label="Downloading AuctionQueryThrottle.dll",
    )
    try:
        _verify_x86_pe(temp_path, "AuctionQueryThrottle.dll")
        _emit_progress(progress, "Installing AuctionQueryThrottle.dll...", None, None)
        _atomic_replace_file(temp_path, os.path.join(target_dir, relative_path))
        _record_package_state_safely(
            target_dir,
            package_id,
            revision,
            [relative_path],
        )
    finally:
        os.remove(temp_path)
    return version


def install_unitxp(target_dir, progress=None):
    _emit_progress(progress, "Checking UnitXP_SP3 release...", None, None)
    release = _latest_release("brues-code/UnitXP_SP3")
    asset = _find_asset(
        release,
        predicate=lambda name: name.lower().startswith("unitxp_sp3") and name.lower().endswith(".zip"),
    )
    revision = _release_asset_revision(release, asset)
    version = _release_revision(release)
    package_id = "unitxp_sp3"

    if _package_state_is_current(target_dir, package_id, revision):
        _emit_progress(progress, f"UnitXP_SP3 {version} is already current.", None, None)
        return version

    zip_path = _download_asset(asset, progress=progress, label="Downloading UnitXP_SP3 package")
    extract_root = tempfile.mkdtemp(prefix="modernization_unitxp_")
    try:
        _emit_progress(progress, "Extracting UnitXP_SP3...", None, None)
        _safe_extract(zip_path, extract_root)
        dll_path = _find_file(extract_root, "UnitXP_SP3.dll")
        _verify_x86_pe(dll_path, "UnitXP_SP3.dll")
        addon_dir = _find_directory(extract_root, "UnitXP_SP3_Addon")

        _emit_progress(progress, "Installing UnitXP_SP3 atomically...", None, None)
        _transactional_replace_bundle(
            [
                ("file", dll_path, os.path.join(target_dir, "UnitXP_SP3.dll")),
                (
                    "dir",
                    addon_dir,
                    os.path.join(target_dir, "Interface", "AddOns", "UnitXP_SP3_Addon"),
                ),
            ],
            label="UnitXP_SP3",
        )
        _record_package_state_safely(
            target_dir,
            package_id,
            revision,
            [
                "UnitXP_SP3.dll",
                os.path.join("Interface", "AddOns", "UnitXP_SP3_Addon"),
            ],
        )
    finally:
        try:
            os.remove(zip_path)
        except OSError:
            pass
        shutil.rmtree(extract_root, ignore_errors=True)
    return version


def install_superwow(target_dir, progress=None):
    _emit_progress(progress, "Checking SuperWoW release...", None, None)
    release = _latest_release("balakethelock/SuperWoW")
    release_version = release.get("name") or _release_revision(release)
    asset = _find_asset(
        release,
        predicate=lambda name: name.lower().startswith("superwow") and name.lower().endswith(".zip"),
    )
    release_asset_revision = _release_asset_revision(release, asset)

    _emit_progress(progress, "Checking SuperAPI revision...", None, None)
    superapi_revision = _branch_head_sha("balakethelock/SuperAPI", "master")
    revision = f"{release_asset_revision}|superapi:{superapi_revision}"
    package_id = "superwow"

    if _package_state_is_current(target_dir, package_id, revision):
        _emit_progress(
            progress,
            f"{release_version} + SuperAPI {superapi_revision[:7]} are already current.",
            None,
            None,
        )
        return release_version

    wow_zip = None
    superapi_zip = None
    wow_root = tempfile.mkdtemp(prefix="modernization_superwow_")
    superapi_root = tempfile.mkdtemp(prefix="modernization_superapi_")
    try:
        # Prepare the DLL completely.
        wow_zip = _download_asset(
            asset,
            progress=progress,
            label="Downloading SuperWoW package",
        )
        _emit_progress(progress, "Extracting SuperWoW...", None, None)
        _safe_extract(wow_zip, wow_root)
        dll_path = _find_file(wow_root, "SuperWoWhook.dll")
        _verify_x86_pe(dll_path, "SuperWoWhook.dll")

        # Prepare SuperAPI completely before changing the installed DLL.
        _emit_progress(progress, "Preparing SuperAPI update...", None, None)
        superapi_zip = _download(
            f"https://codeload.github.com/balakethelock/SuperAPI/zip/{superapi_revision}",
            suffix=".zip",
            progress=progress,
            label="Downloading SuperAPI addon",
        )
        _emit_progress(progress, "Extracting SuperAPI...", None, None)
        _safe_extract(superapi_zip, superapi_root)

        addon_root = None
        for current_root, _, files in os.walk(superapi_root):
            if "SuperAPI.toc" in files:
                addon_root = current_root
                break
        if addon_root is None:
            raise RemotePackageError("SuperAPI.toc was not found in the SuperAPI archive.")

        _emit_progress(progress, "Installing SuperWoW + SuperAPI atomically...", None, None)
        _transactional_replace_bundle(
            [
                (
                    "file",
                    dll_path,
                    os.path.join(target_dir, "SuperWoWhook.dll"),
                ),
                (
                    "dir",
                    addon_root,
                    os.path.join(target_dir, "Interface", "AddOns", "SuperAPI"),
                ),
            ],
            label="SuperWoW + SuperAPI",
        )
        _record_package_state_safely(
            target_dir,
            package_id,
            revision,
            [
                "SuperWoWhook.dll",
                os.path.join("Interface", "AddOns", "SuperAPI"),
            ],
        )
    finally:
        for path in (wow_zip, superapi_zip):
            if path:
                try:
                    os.remove(path)
                except OSError:
                    pass
        shutil.rmtree(wow_root, ignore_errors=True)
        shutil.rmtree(superapi_root, ignore_errors=True)

    return release_version


