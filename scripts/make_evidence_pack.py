#!/usr/bin/env python
"""Create a minimal EvidencePack output folder + zip."""

from __future__ import annotations
import argparse
import shutil
from pathlib import Path
import zipfile

from aurora_kernel.tick import run_minimal_scenario

def zip_dir(folder: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in folder.rglob("*"):
            if p.is_file():
                zf.write(p, p.relative_to(folder))

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="dist")
    args = ap.parse_args()

    out_root = Path(args.out)
    pack_dir = out_root / "EvidencePack"
    if pack_dir.exists():
        shutil.rmtree(pack_dir)

    run_minimal_scenario(pack_dir)

    zip_path = out_root / "EvidencePack.zip"
    if zip_path.exists():
        zip_path.unlink()
    zip_dir(pack_dir, zip_path)

    print(f"Wrote: {zip_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
