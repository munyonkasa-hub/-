"""Materialize the current per-page inputs from an approved script, CSV and page decisions."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def reference(path, root):
    return {"path": os.path.relpath(path, root), "sha256": digest(path.read_bytes())}


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        tmp = Path(stream.name)
        try:
            stream.write(data)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise
    try:
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def text_input(root, kind, text):
    data = text.encode("utf-8")
    path = root / "execution-inputs" / kind / (digest(data) + ".txt")
    if not path.exists():
        atomic_write(path, data)
    result = reference(path, root)
    if result["sha256"] != digest(data):
        raise ValueError(f"corrupted input: {path}")
    return result


def check_pair(root, name):
    path = root / name
    manifest = json.loads(path.read_text())
    result = {"manifest": reference(path, root)}
    for key in ("original", "retouched"):
        item = manifest[key]
        if item is None:
            result[key] = None
            continue
        candidate = reference(path.parent / item["path"], root)
        if candidate["sha256"] != item["sha256"]:
            raise ValueError(f"{path}: {key} hash mismatch")
        result[key] = candidate
    result["independent_comparison_ready"] = all(result[key] for key in ("original", "retouched"))
    return result


def build(root, script, listing):
    script = root / script
    listing = root / listing
    approval = script.with_name("approval.json")
    approved = reference(script, root)
    if json.loads(approval.read_text())["sha256"] != approved["sha256"]:
        raise ValueError("script differs from approved version")
    decisions = root / "execution-pages.json"
    pages = json.loads(decisions.read_text())
    with listing.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    ids = [row.get("page_id") or row["页码"] for row in rows]
    if not rows or len(set(ids)) != len(rows) or set(ids) != set(pages):
        raise ValueError("execution pages must match the approved list exactly")
    manifest = {"approved_script": approved, "approval": reference(approval, root),
                "approved_list": reference(listing, root), "decisions": reference(decisions, root),
                "pages": []}
    for page_id, row in zip(ids, rows):
        page = dict(pages[page_id])
        for key in ("basis", "owner", "assets", "adoption"):
            if not page.get(key):
                raise ValueError(f"{page_id}: missing {key}")
        page["page_id"] = page_id
        page["assets"] = [reference(root / name, root) for name in page["assets"]]
        page["sku"] = row["SKU"]
        page["method"] = row["方式"]
        page["outputs"] = [reference(root / name, root) for name in page.get("outputs", [])]
        photo = page.pop("photo_prompt")
        if "layout_copy" in page:
            copy = page.pop("layout_copy")
        else:
            copy = row["日文全文"]
        if photo and any(line.strip() in photo for line in copy.splitlines() if line.strip()):
            raise ValueError(f"{page_id}: layout copy leaked into photo prompt")
        page["photo_input"] = text_input(root, "photo", photo) if photo else None
        page["layout_input"] = text_input(root, "layout", copy)
        if page.get("pair_manifest"):
            page["pair"] = check_pair(root, page["pair_manifest"])
        manifest["pages"].append(page)
    output = root / "当前执行清单.json"
    payload = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    atomic_write(output, payload)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", type=Path)
    parser.add_argument("approved_script", type=Path, help="path relative to task")
    parser.add_argument("approved_csv", type=Path, help="path relative to task")
    args = parser.parse_args()
    print(build(args.task.resolve(), args.approved_script, args.approved_csv))
