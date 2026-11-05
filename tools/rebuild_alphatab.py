#!/usr/bin/env python3
"""Rebuild the pinned alphaTab assets. Default: verify against the vendored files.

Supply --archive for offline use or --fetch for the fixed registry URL. No npm
installation or package scripts are used. --output writes only verified assets.
"""
import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "tools/alphatab.lock.json"
VENDOR = ROOT / "UsableTab/AlphaTabAssets"
MAX_ARCHIVE_BYTES = 16 * 1024 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verify_archive(data, lock):
    if len(data) > MAX_ARCHIVE_BYTES:
        raise ValueError("Archive exceeds 16 MiB limit")
    integrity = "sha512-" + base64.b64encode(hashlib.sha512(data).digest()).decode("ascii")
    if integrity != lock["integrity"] or digest(data) != lock["archiveSHA256"]:
        raise ValueError("Archive integrity mismatch; archive was not parsed")


def extract_members(data, lock):
    """Read exact regular members in memory; never extract a tar onto disk."""
    result = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        for member in archive:
            if member.name not in lock["members"]:
                continue
            expected = lock["members"][member.name]
            if member.name in result or not member.isfile() or member.size != expected["size"]:
                raise ValueError("Unexpected, duplicate or non-regular member: " + member.name)
            content = archive.extractfile(member).read(expected["size"] + 1)
            if len(content) != expected["size"] or digest(content) != expected["sha256"]:
                raise ValueError("Upstream member hash mismatch: " + member.name)
            result[member.name] = content
    if result.keys() != lock["members"].keys():
        raise ValueError("Required upstream members are missing")
    package = json.loads(result["package/package.json"])
    if package["name"] != lock["package"] or package["version"] != lock["version"]:
        raise ValueError("Upstream package identity mismatch")
    return result


def apply_empty_stem_guard(source, guard):
    before, after = guard["before"], guard["after"]
    if source.count(before) != 1 or after in source:
        raise ValueError("Empty-stem anchor is missing, ambiguous or already patched")
    return source.replace(before, after, 1)


PATCH_SCRIPTS = {"patch_alphatab_notation.py", "patch_alphatab_tab_ties.py", "patch_alphatab_multirest.py",
                 "patch_alphatab_effect_rows.py"}


def verify_patch_scripts(lock):
    if set(lock["patches"]) != PATCH_SCRIPTS:
        raise ValueError("Missing or unexpected patch scripts")
    for name, expected in lock["patches"].items():
        if name not in PATCH_SCRIPTS:
            raise ValueError("Unknown patch script")
        if digest((ROOT / "tools" / name).read_bytes()) != expected:
            raise ValueError("Patch script changed; review and update the lock: " + name)


def verify_outputs(outputs, lock):
    expected = {entry["output"]: entry["finalSHA256"] for entry in lock["members"].values() if "output" in entry}
    if set(expected) != {"alphaTab.min.js", "font/Bravura.woff2", "alphaTab-LICENSE.txt"} or outputs.keys() != expected.keys():
        raise ValueError("Unexpected output assets")
    for name, content in outputs.items():
        if digest(content) != expected[name]:
            raise ValueError("Final asset hash mismatch: " + name)


def rebuild(data, lock):
    if lock["schema"] != 1 or lock["package"] != "@coderline/alphatab" or lock["version"] != "1.8.4":
        raise ValueError("Unsupported lock; review the pipeline before upgrading")
    verify_archive(data, lock)
    members = extract_members(data, lock)
    verify_patch_scripts(lock)
    # The existing notation entry point includes the TAB ties patch itself.
    # Empty stem slots are an earlier, separately required patch.
    # Multi-bar rest bounds and effects are an independent layer on top, then the effect row packing switch.
    from patch_alphatab_notation import patch
    from patch_alphatab_multirest import patch as patch_multirest
    from patch_alphatab_effect_rows import patch as patch_effect_rows
    source = apply_empty_stem_guard(members["package/dist/alphaTab.min.js"].decode("utf-8"), lock["emptyStemGuard"])
    outputs = {entry["output"]: members[name] for name, entry in lock["members"].items() if "output" in entry}
    outputs["alphaTab.min.js"] = patch_effect_rows(patch_multirest(patch(source))).encode("utf-8")
    verify_outputs(outputs, lock)
    return outputs


def fetch_archive(lock):
    # The lock pins a registry archive, not a moving tag or metadata lookup.
    expected = "https://registry.npmjs.org/@coderline/alphatab/-/alphatab-1.8.4.tgz"
    if lock["url"] != expected:
        raise ValueError("Unexpected download URL")
    with urllib.request.urlopen(expected, timeout=60) as response:
        if response.url != expected:
            raise ValueError("Unexpected archive redirect")
        return response.read(MAX_ARCHIVE_BYTES + 1)


def write_outputs(outputs, directory):
    # Call only after all upstream, patch and final hashes have passed.
    # Atomic per file. For upgrades, stage in a temporary directory for review.
    if directory.is_symlink() or (directory.exists() and (not directory.is_dir() or any(directory.iterdir()))):
        raise ValueError("Output directory must be new or empty, and must not be a symlink")
    for name, content in outputs.items():
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=".alphatab-", dir=path.parent)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                os.fchmod(stream.fileno(), 0o644)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--archive", type=Path, help="Previously downloaded, pinned npm .tgz")
    source.add_argument("--fetch", action="store_true", help="Download the fixed archive with no package execution")
    parser.add_argument("--output", type=Path, help="Write verified assets here; default compares current App assets")
    args = parser.parse_args()
    try:
        lock = json.loads(LOCK.read_text())
        if args.archive:
            with args.archive.open("rb") as stream:
                data = stream.read(MAX_ARCHIVE_BYTES + 1)
        else:
            data = fetch_archive(lock)
        outputs = rebuild(data, lock)
        if args.output:
            write_outputs(outputs, args.output)
        else:
            for name, content in outputs.items():
                if (VENDOR / name).read_bytes() != content:
                    raise ValueError("Vendored asset differs from the verified rebuild: " + name)
        print(json.dumps({"package": lock["package"], "version": lock["version"],
                          "mode": "write" if args.output else "verify", "sha256": {name: digest(data) for name, data in outputs.items()}}, indent=2))
        return 0
    except (OSError, ValueError, KeyError, tarfile.TarError) as error:
        parser.exit(1, "alphaTab rebuild failed: " + str(error) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
