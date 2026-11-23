"""Archive an original and retouched image in an immutable version directory."""

import argparse
import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def publish_without_replacement(staging, destination):
    if os.name == "nt":
        staging.rename(destination)
        return

    # POSIX rename can replace an existing empty directory. Linux renameat2
    # checks that the destination is absent as part of the atomic rename.
    if not sys.platform.startswith("linux"):
        raise OSError("Atomic directory publication requires Linux or Windows")
    libc = ctypes.CDLL(None, use_errno=True)
    try:
        rename = libc.renameat2
    except AttributeError as exc:
        raise OSError("renameat2 is unavailable on this system") from exc
    rename.argtypes = [
        ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint
    ]
    rename.restype = ctypes.c_int
    at_fdcwd = -100
    rename_noreplace = 1
    if rename(
        at_fdcwd, os.fsencode(staging),
        at_fdcwd, os.fsencode(destination),
        rename_noreplace,
    ) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), destination)


def matches_existing(destination, expected):
    if destination.is_symlink() or not destination.is_dir():
        return False
    manifest = destination / "pair.json"
    roles = ("original", "retouched")
    names = {"pair.json", *(expected[role]["path"] for role in roles)}
    if {path.name for path in destination.iterdir()} != names:
        return False
    if manifest.is_symlink() or not manifest.is_file():
        return False
    try:
        if json.loads(manifest.read_text(encoding="utf-8")) != expected:
            return False
    except (ValueError, UnicodeError):
        return False
    for role in roles:
        record = expected[role]
        path = destination / record["path"]
        if path.is_symlink() or not path.is_file() or sha256(path) != record["sha256"]:
            return False
    return True


def archive_pair(destination, original, retouched, source):
    if not source.strip():
        raise ValueError("Specify a nonempty source")
    if not original.is_file() or not retouched.is_file():
        raise ValueError("Original and retouched inputs must be regular files")
    if original.samefile(retouched):
        raise ValueError("Original and retouched inputs must be different files")

    with tempfile.TemporaryDirectory(prefix=".retouch-pair-", dir=destination.parent) as temp:
        staging = Path(temp) / "pair"
        staging.mkdir()
        manifest = {"source": source}
        for role, image in (("original", original), ("retouched", retouched)):
            archived = staging / f"{role}{image.suffix}"
            shutil.copyfile(image, archived)
            manifest[role] = {"path": archived.name, "sha256": sha256(archived)}
        (staging / "pair.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        try:
            publish_without_replacement(staging, destination)
        except OSError as exc:
            if not isinstance(exc, FileExistsError) and exc.errno != errno.ENOTEMPTY:
                raise
            if not matches_existing(destination, manifest):
                raise FileExistsError(
                    f"Archive already exists with different contents: {destination}"
                ) from exc

    return destination / "pair.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pair_dir", type=Path, help="New version directory under an existing parent")
    parser.add_argument("original", type=Path)
    parser.add_argument("retouched", type=Path)
    parser.add_argument("--source", required=True)
    args = parser.parse_args()
    try:
        manifest = archive_pair(args.pair_dir, args.original, args.retouched, args.source)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"{parser.prog}: {exc}\n")
    print(manifest)


if __name__ == "__main__":
    main()
