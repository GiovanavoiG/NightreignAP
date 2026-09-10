"""Zip apworld/<name> into build/<name>.apworld. Usage: python tools/pack_apworld.py"""
import pathlib
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
NAME = "nightreign"
folder = ROOT / "apworld" / NAME
out = ROOT / "build" / f"{NAME}.apworld"
out.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
    for path in sorted(folder.rglob("*")):
        if path.is_dir() or "__pycache__" in path.parts:
            continue
        zf.write(path, f"{NAME}/{path.relative_to(folder).as_posix()}")
print(f"wrote {out} ({out.stat().st_size} bytes)")
