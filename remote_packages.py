import hashlib
import json
import os
import shutil
import tempfile
import urllib.error
import urllib.request
import zipfile

USER_AGENT = "Modernization-Tool/1.0 (+https://github.com/Dusk-92/Modernization-Tool)"
GITHUB_API = "https://api.github.com"
NETWORK_TIMEOUT = 30


class RemotePackageError(RuntimeError):
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
        if exact_name is not None and name == exact_name:
            return asset
        if predicate is not None and predicate(name):
            return asset
    wanted = exact_name or "matching release asset"
    raise RemotePackageError(f"Could not find {wanted} in release {release.get('tag_name', '?')}.")


def _download(url, suffix="", expected_digest=None):
    fd, temp_path = tempfile.mkstemp(prefix="modernization_", suffix=suffix)
    os.close(fd)
    try:
        digest = hashlib.sha256()
        with urllib.request.urlopen(_request(url), timeout=NETWORK_TIMEOUT) as response, open(temp_path, "wb") as out:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
                digest.update(chunk)

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


def _download_asset(asset):
    url = asset.get("browser_download_url")
    if not url:
        raise RemotePackageError(f"Release asset {asset.get('name', '?')} has no download URL.")
    suffix = os.path.splitext(asset.get("name", ""))[1]
    try:
        return _download(url, suffix=suffix, expected_digest=asset.get("digest"))
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


def _replace_directory(source_dir, target_dir):
    os.makedirs(os.path.dirname(os.path.abspath(target_dir)), exist_ok=True)
    staged = target_dir + ".modernization-new"
    backup = target_dir + ".modernization-backup"

    shutil.rmtree(staged, ignore_errors=True)
    shutil.rmtree(backup, ignore_errors=True)
    shutil.copytree(source_dir, staged)

    had_existing = os.path.exists(target_dir)
    try:
        if had_existing:
            os.replace(target_dir, backup)
        os.replace(staged, target_dir)
        shutil.rmtree(backup, ignore_errors=True)
    except Exception:
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir, ignore_errors=True)
        if had_existing and os.path.exists(backup):
            os.replace(backup, target_dir)
        raise
    finally:
        shutil.rmtree(staged, ignore_errors=True)
        shutil.rmtree(backup, ignore_errors=True)


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


def install_classicapi(target_dir):
    release = _latest_release("brues-code/ClassicAPI")
    asset = _find_asset(release, exact_name="ClassicAPI.dll")
    temp_path = _download_asset(asset)
    try:
        _atomic_replace_file(temp_path, os.path.join(target_dir, "ClassicAPI.dll"))
    finally:
        os.remove(temp_path)
    return release.get("tag_name", "latest")


def install_auction_query_throttle(target_dir):
    release = _latest_release("brues-code/AuctionQueryThrottle")
    asset = _find_asset(release, exact_name="AuctionQueryThrottle.dll")
    temp_path = _download_asset(asset)
    try:
        _atomic_replace_file(temp_path, os.path.join(target_dir, "AuctionQueryThrottle.dll"))
    finally:
        os.remove(temp_path)
    return release.get("tag_name", "latest")


def install_unitxp(target_dir):
    release = _latest_release("brues-code/UnitXP_SP3")
    asset = _find_asset(
        release,
        predicate=lambda name: name.lower().startswith("unitxp_sp3-") and name.lower().endswith(".zip"),
    )
    zip_path = _download_asset(asset)
    extract_root = tempfile.mkdtemp(prefix="modernization_unitxp_")
    try:
        _safe_extract(zip_path, extract_root)
        dll_path = _find_file(extract_root, "UnitXP_SP3.dll")
        addon_dir = _find_directory(extract_root, "UnitXP_SP3_Addon")

        _atomic_replace_file(dll_path, os.path.join(target_dir, "UnitXP_SP3.dll"))
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


def install_superwow(target_dir):
    release = _latest_release("balakethelock/SuperWoW")
    asset = _find_asset(
        release,
        predicate=lambda name: name.lower().startswith("superwow") and name.lower().endswith(".zip"),
    )
    zip_path = _download_asset(asset)
    extract_root = tempfile.mkdtemp(prefix="modernization_superwow_")
    try:
        _safe_extract(zip_path, extract_root)
        dll_path = _find_file(extract_root, "SuperWoWhook.dll")
        _atomic_replace_file(dll_path, os.path.join(target_dir, "SuperWoWhook.dll"))
    finally:
        try:
            os.remove(zip_path)
        except OSError:
            pass
        shutil.rmtree(extract_root, ignore_errors=True)

    # SuperAPI has no GitHub Releases. Install the current master branch exactly
    # as its author documents, stripping GitHub's "-master" archive suffix.
    superapi_zip = _download(
        "https://codeload.github.com/balakethelock/SuperAPI/zip/refs/heads/master",
        suffix=".zip",
    )
    superapi_root = tempfile.mkdtemp(prefix="modernization_superapi_")
    try:
        _safe_extract(superapi_zip, superapi_root)
        addon_root = None
        for current_root, _, files in os.walk(superapi_root):
            if "SuperAPI.toc" in files:
                addon_root = current_root
                break
        if addon_root is None:
            raise RemotePackageError("SuperAPI.toc was not found in the SuperAPI archive.")
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
