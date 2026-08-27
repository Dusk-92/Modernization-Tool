import hashlib
import json
import os
import shutil
import stat
import tempfile
import urllib.error
import urllib.request
import uuid
import zipfile

USER_AGENT = "Modernization-Tool/1.0 (+https://github.com/Dusk-92/Modernization-Tool)"
GITHUB_API = "https://api.github.com"
NETWORK_TIMEOUT = 30


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


def _get_json(url):
    try:
        with urllib.request.urlopen(_request(url, "application/vnd.github+json"), timeout=NETWORK_TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        raise RemotePackageError(f"GitHub request failed: {exc}") from exc


def _latest_release(repo):
    data = _get_json(f"{GITHUB_API}/repos/{repo}/releases/latest")
    if data.get("draft") or data.get("prerelease"):
        raise RemotePackageError(f"{repo}: latest release is not a stable release.")
    return data


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


def prepare_vanilla_tweaks(progress=None):
    """Download and extract the latest stable tubtubs vanilla-tweaks Windows build."""
    _emit_progress(progress, "Checking vanilla-tweaks release...", None, None)
    release = _latest_release("tubtubs/vanilla-tweaks")
    asset = _find_asset(
        release,
        predicate=lambda name: (
            name.lower().endswith(".zip")
            and "windows" in name.lower()
            and not name.lower().endswith(".sha256sum")
        ),
    )
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

    return exe_path, extract_root, release.get("name") or release.get("tag_name", "latest")


def install_interact(target_dir, progress=None):
    _emit_progress(progress, "Checking Interact release...", None, None)
    release = _latest_release("lookino/Interact")
    asset = _find_asset(release, exact_name="Interact.zip")
    zip_path = _download_asset(asset, progress=progress, label="Downloading Interact package")
    extract_root = tempfile.mkdtemp(prefix="modernization_interact_")
    try:
        _emit_progress(progress, "Extracting Interact...", None, None)
        _safe_extract(zip_path, extract_root)
        dll_path = _find_file(extract_root, "Interact.dll")

        _emit_progress(progress, "Installing Interact.dll...", None, None)
        _atomic_replace_file(dll_path, os.path.join(target_dir, "Interact.dll"))

        addon_dir = _find_directory_with_file(extract_root, "Interact.toc")
        if addon_dir is not None:
            _emit_progress(progress, "Installing Interact addon...", None, None)
            _replace_directory(
                addon_dir,
                os.path.join(target_dir, "Interface", "AddOns", "Interact"),
            )
    finally:
        try:
            os.remove(zip_path)
        except OSError:
            pass
        shutil.rmtree(extract_root, ignore_errors=True)

    return release.get("tag_name", "latest")


def install_vanilla_multimonitor_fix(target_dir, progress=None):
    _emit_progress(progress, "Checking VanillaMultiMonitorFix release...", None, None)
    release = _latest_release("Mates1500/VanillaMultiMonitorFix")
    asset = _find_asset(release, exact_name="release.zip")
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
    finally:
        try:
            os.remove(zip_path)
        except OSError:
            pass
        shutil.rmtree(extract_root, ignore_errors=True)

    return release.get("tag_name", "latest")



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


def _load_managed_manifest(target_dir, mod_id):
    _, manifest_path, _ = _managed_locations(target_dir, mod_id)
    if not os.path.isfile(manifest_path):
        return []
    try:
        with open(manifest_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        files = data.get("files", [])
        if not isinstance(files, list):
            return []
        return [_safe_relative_path(item) for item in files if isinstance(item, str)]
    except (OSError, json.JSONDecodeError, ValueError):
        return []


def _write_managed_manifest(target_dir, mod_id, relative_files):
    _, manifest_path, _ = _managed_locations(target_dir, mod_id)
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
    temp_path = manifest_path + ".new"
    payload = {
        "mod_id": mod_id,
        "files": [str(path).replace(os.sep, "/") for path in relative_files],
    }
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



def managed_mod_is_installed(target_dir, mod_id):
    """True only when a tool-managed manifest exists and all owned files remain present."""
    files = _load_managed_manifest(target_dir, mod_id)
    if not files:
        return False
    return all(os.path.isfile(os.path.join(target_dir, rel)) for rel in files)


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


def _install_managed_files(target_dir, mod_id, file_mappings):
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

    _write_managed_manifest(target_dir, mod_id, new_files)


def _verify_mpq(path):
    try:
        with open(path, "rb") as handle:
            magic = handle.read(3)
    except OSError as exc:
        raise RemotePackageError(f"Could not inspect downloaded MPQ: {exc}") from exc
    if magic != b"MPQ":
        raise RemotePackageError("Downloaded file is not a valid MPQ archive.")


def _install_remote_mpq(target_dir, mod_id, url, destination, progress=None, label="Downloading visual mod", timeout=300):
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
    )
    return "RetroCro mirror"


def install_pink_herbs(target_dir, progress=None):
    _install_remote_mpq(
        target_dir,
        "visual_pink_herbs",
        "https://raw.githubusercontent.com/seacrabsam/patch-herb/main/patch-H.mpq",
        os.path.join("Data", "patch-H.mpq"),
        progress=progress,
        label="Downloading Pink Herbs",
    )
    return "seacrabsam/patch-herb main"


def _download_github_branch_archive(repo, branch, progress=None, label="Downloading sound mod"):
    url = f"https://codeload.github.com/{repo}/zip/refs/heads/{branch}"
    return _download(
        url,
        suffix=".zip",
        progress=progress,
        label=label,
        timeout=120,
    )



def install_bundled_tree(target_dir, mod_id, source_dir, destination_prefix):
    """Install an already bundled directory tree through the managed-file layer."""
    if not os.path.isdir(source_dir):
        raise RemotePackageError(f"Bundled backup folder is missing: {source_dir}")
    mappings = _collect_tree_files(source_dir, destination_prefix)
    _install_managed_files(target_dir, mod_id, mappings)


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
    zip_path = _download_github_branch_archive(
        repo,
        branch,
        progress=progress,
        label=label,
    )
    extract_root = tempfile.mkdtemp(prefix=f"modernization_{mod_id}_")
    try:
        _emit_progress(progress, f"Extracting {label.replace('Downloading ', '')}...", None, None)
        _safe_extract(zip_path, extract_root)
        source_dir = _find_directory(extract_root, source_folder)
        mappings = _collect_tree_files(source_dir, destination_prefix)
        _emit_progress(progress, f"Installing {label.replace('Downloading ', '')}...", None, None)
        _install_managed_files(target_dir, mod_id, mappings)
    finally:
        try:
            os.remove(zip_path)
        except OSError:
            pass
        shutil.rmtree(extract_root, ignore_errors=True)


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
    zip_path = _download_asset(asset, progress=progress, label="Downloading Nampower package")
    extract_root = tempfile.mkdtemp(prefix="modernization_nampower_")
    try:
        _emit_progress(progress, "Extracting Nampower...", None, None)
        _safe_extract(zip_path, extract_root)
        dll_path = _find_file(extract_root, "nampower.dll")
        addon_dir = _find_directory(extract_root, "NampowerSettings")

        _emit_progress(progress, "Installing nampower.dll...", None, None)
        _atomic_replace_file(dll_path, os.path.join(target_dir, "nampower.dll"))
        _emit_progress(progress, "Installing NampowerSettings addon...", None, None)
        _replace_directory(
            addon_dir,
            os.path.join(target_dir, "Interface", "AddOns", "nampowersettings"),
        )
    finally:
        try:
            os.remove(zip_path)
        except OSError:
            pass
        shutil.rmtree(extract_root, ignore_errors=True)
    return release.get("tag_name", "latest")


def install_vanillahelpers(target_dir, progress=None):
    _emit_progress(progress, "Checking VanillaHelpers release...", None, None)
    release = _latest_release("isfir/VanillaHelpers")
    asset = _find_asset(release, exact_name="VanillaHelpers.dll")
    temp_path = _download_asset(
        asset,
        progress=progress,
        label="Downloading VanillaHelpers.dll",
    )
    try:
        _emit_progress(progress, "Installing VanillaHelpers.dll...", None, None)
        _atomic_replace_file(temp_path, os.path.join(target_dir, "VanillaHelpers.dll"))
    finally:
        os.remove(temp_path)
    return release.get("tag_name", "latest")


def install_no1600x1200(target_dir, progress=None):
    _emit_progress(progress, "Checking no1600x1200 source...", None, None)
    url = (
        "https://raw.githubusercontent.com/RetroCro/TurtleWoW-Mods/"
        "refs/heads/main/Archive/DLL%20BACKUP/no1600x1200.dll"
    )
    temp_path = _download(
        url,
        suffix=".dll",
        progress=progress,
        label="Downloading no1600x1200.dll",
    )
    try:
        _emit_progress(progress, "Installing no1600x1200.dll...", None, None)
        _atomic_replace_file(temp_path, os.path.join(target_dir, "no1600x1200.dll"))
    finally:
        os.remove(temp_path)
    return "RetroCro/TurtleWoW-Mods main"


def install_classicapi(target_dir, progress=None):
    _emit_progress(progress, "Checking ClassicAPI release...", None, None)
    release = _latest_release("brues-code/ClassicAPI")
    asset = _find_asset(release, exact_name="ClassicAPI.dll")
    temp_path = _download_asset(asset, progress=progress, label="Downloading ClassicAPI.dll")
    try:
        _emit_progress(progress, "Installing ClassicAPI.dll...", None, None)
        _atomic_replace_file(temp_path, os.path.join(target_dir, "ClassicAPI.dll"))
    finally:
        os.remove(temp_path)
    return release.get("tag_name", "latest")


def install_auction_query_throttle(target_dir, progress=None):
    _emit_progress(progress, "Checking AuctionQueryThrottle release...", None, None)
    release = _latest_release("brues-code/AuctionQueryThrottle")
    asset = _find_asset(release, exact_name="AuctionQueryThrottle.dll")
    temp_path = _download_asset(
        asset,
        progress=progress,
        label="Downloading AuctionQueryThrottle.dll",
    )
    try:
        _emit_progress(progress, "Installing AuctionQueryThrottle.dll...", None, None)
        _atomic_replace_file(temp_path, os.path.join(target_dir, "AuctionQueryThrottle.dll"))
    finally:
        os.remove(temp_path)
    return release.get("tag_name", "latest")


def install_unitxp(target_dir, progress=None):
    _emit_progress(progress, "Checking UnitXP_SP3 release...", None, None)
    release = _latest_release("brues-code/UnitXP_SP3")
    asset = _find_asset(
        release,
        predicate=lambda name: name.lower().startswith("unitxp_sp3") and name.lower().endswith(".zip"),
    )
    zip_path = _download_asset(asset, progress=progress, label="Downloading UnitXP_SP3 package")
    extract_root = tempfile.mkdtemp(prefix="modernization_unitxp_")
    try:
        _emit_progress(progress, "Extracting UnitXP_SP3...", None, None)
        _safe_extract(zip_path, extract_root)
        dll_path = _find_file(extract_root, "UnitXP_SP3.dll")
        addon_dir = _find_directory(extract_root, "UnitXP_SP3_Addon")

        _emit_progress(progress, "Installing UnitXP_SP3.dll...", None, None)
        _atomic_replace_file(dll_path, os.path.join(target_dir, "UnitXP_SP3.dll"))
        _emit_progress(progress, "Installing UnitXP_SP3_Addon...", None, None)
        _replace_directory(
            addon_dir,
            os.path.join(target_dir, "Interface", "AddOns", "UnitXP_SP3_Addon"),
        )
    finally:
        try:
            os.remove(zip_path)
        except OSError:
            pass
        shutil.rmtree(extract_root, ignore_errors=True)
    return release.get("tag_name", "latest")


def install_superwow(target_dir, progress=None):
    _emit_progress(progress, "Checking SuperWoW release...", None, None)
    release = _latest_release("balakethelock/SuperWoW")
    asset = _find_asset(
        release,
        predicate=lambda name: name.lower().startswith("superwow") and name.lower().endswith(".zip"),
    )
    zip_path = _download_asset(asset, progress=progress, label="Downloading SuperWoW package")
    extract_root = tempfile.mkdtemp(prefix="modernization_superwow_")
    try:
        _emit_progress(progress, "Extracting SuperWoW...", None, None)
        _safe_extract(zip_path, extract_root)
        dll_path = _find_file(extract_root, "SuperWoWhook.dll")
        _emit_progress(progress, "Installing SuperWoWhook.dll...", None, None)
        _atomic_replace_file(dll_path, os.path.join(target_dir, "SuperWoWhook.dll"))
    finally:
        try:
            os.remove(zip_path)
        except OSError:
            pass
        shutil.rmtree(extract_root, ignore_errors=True)

    # SuperAPI has no GitHub Releases. Install the current master branch exactly
    # as its author documents, stripping GitHub's "-master" archive suffix.
    _emit_progress(progress, "Preparing SuperAPI update...", None, None)
    superapi_zip = _download(
        "https://codeload.github.com/balakethelock/SuperAPI/zip/refs/heads/master",
        suffix=".zip",
        progress=progress,
        label="Downloading SuperAPI addon",
    )
    superapi_root = tempfile.mkdtemp(prefix="modernization_superapi_")
    try:
        _emit_progress(progress, "Extracting SuperAPI...", None, None)
        _safe_extract(superapi_zip, superapi_root)
        addon_root = None
        for current_root, _, files in os.walk(superapi_root):
            if "SuperAPI.toc" in files:
                addon_root = current_root
                break
        if addon_root is None:
            raise RemotePackageError("SuperAPI.toc was not found in the SuperAPI archive.")

        _emit_progress(progress, "Installing SuperAPI addon...", None, None)
        _replace_directory(
            addon_root,
            os.path.join(target_dir, "Interface", "AddOns", "SuperAPI"),
        )
    finally:
        try:
            os.remove(superapi_zip)
        except OSError:
            pass
        shutil.rmtree(superapi_root, ignore_errors=True)

    return release.get("name") or release.get("tag_name", "latest")
