#!/usr/bin/env bash
set -euo pipefail

addon_id="plugin.video.dizibox"
version=""
bump_patch=0
repository_id="repository.manitux"

usage() {
    cat <<'EOF'
Usage:
  scripts/package-addon.sh [--addon-id ID] [--version VERSION | --bump-patch] [--repository-id ID]

Examples:
  scripts/package-addon.sh --addon-id plugin.video.dizibox
  scripts/package-addon.sh --addon-id plugin.video.dizibox --bump-patch
  scripts/package-addon.sh --addon-id plugin.video.dizibox --version 1.0.2
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --addon-id)
            addon_id="${2:?--addon-id requires a value}"
            shift 2
            ;;
        --version)
            version="${2:?--version requires a value}"
            shift 2
            ;;
        --bump-patch)
            bump_patch=1
            shift
            ;;
        --repository-id)
            repository_id="${2:?--repository-id requires a value}"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [[ -n "$version" && "$bump_patch" -eq 1 ]]; then
    echo "--version and --bump-patch cannot be used together." >&2
    exit 2
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/.." && pwd)"

python3 - "$repo_root" "$addon_id" "$version" "$bump_patch" "$repository_id" <<'PY'
import hashlib
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


repo_root = Path(sys.argv[1])
addon_id = sys.argv[2]
requested_version = sys.argv[3]
bump_patch = sys.argv[4] == "1"
repository_id = sys.argv[5]

addon_dir = repo_root / addon_id
addon_xml = addon_dir / "addon.xml"
repo_xml = repo_root / repository_id / "addons.xml"
repo_md5 = repo_xml.with_name(repo_xml.name + ".md5")

if not addon_xml.exists():
    raise SystemExit(f"Addon not found: {addon_xml}")
if not repo_xml.exists():
    raise SystemExit(f"Repository addons.xml not found: {repo_xml}")


def read_text(path):
    return path.read_text(encoding="utf-8")


def write_text(path, text):
    path.write_text(text, encoding="utf-8", newline="")


def addon_version(path):
    return ET.fromstring(read_text(path)).attrib["version"]


def set_addon_version(path, new_version):
    text = read_text(path)
    updated = re.sub(
        r'(<addon\b[^>]*?\bversion=")[^"]+(")',
        rf'\g<1>{new_version}\2',
        text,
        count=1,
        flags=re.S,
    )
    write_text(path, updated)


def next_patch(version):
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
    if not match:
        raise SystemExit(f"Patch bump requires semver version: {version}")
    major, minor, patch = match.groups()
    return f"{major}.{minor}.{int(patch) + 1}"


def addon_block_without_xml(path):
    text = read_text(path).strip()
    text = re.sub(r"^\s*<\?xml[^>]*>\s*", "", text)
    return text.strip()


def update_repository_block():
    repo_text = read_text(repo_xml)
    addon_text = addon_block_without_xml(addon_xml)
    pattern = re.compile(
        rf'<addon\b(?=[^>]*\bid="{re.escape(addon_id)}")[\s\S]*?</addon>',
        re.S,
    )

    if pattern.search(repo_text):
        repo_text = pattern.sub(addon_text, repo_text, count=1)
    else:
        repo_text = re.sub(r"</addons>\s*$", addon_text + "\n</addons>\n", repo_text, count=1, flags=re.S)

    ET.fromstring(repo_text)
    write_text(repo_xml, repo_text)


def make_zip(version):
    target_dir = repo_root / repository_id / addon_id
    target_dir.mkdir(parents=True, exist_ok=True)
    zip_path = target_dir / f"{addon_id}-{version}.zip"
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(addon_dir.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(repo_root).as_posix())
    return zip_path


current_version = addon_version(addon_xml)
target_version = current_version

if bump_patch:
    target_version = next_patch(current_version)
elif requested_version:
    target_version = requested_version

if target_version != current_version:
    set_addon_version(addon_xml, target_version)

update_repository_block()
zip_path = make_zip(target_version)
md5 = hashlib.md5(repo_xml.read_bytes()).hexdigest()
repo_md5.write_text(md5, encoding="utf-8", newline="")

print(f"Addon: {addon_id}")
print(f"Version: {target_version}")
print(f"Zip: {zip_path}")
print(f"MD5: {md5}")
PY
