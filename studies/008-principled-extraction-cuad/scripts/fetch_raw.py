import hashlib
import sys
import urllib.request
import zipfile
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
BASE = "https://raw.githubusercontent.com/TheAtticusProject/cuad/main"

DOWNLOADS = {
    "category_descriptions.csv": "7499950ee04d2ed2841c0f8ec2ef96b91be039bc2ea3c4edcc36334a465b1f36",
    "evaluate.py": "5c56ac9fc82fe56ef77616a1dffba0707e4366ba916f7ab5d3e4434013d0a624",
    "data.zip": "f8161d18bea4e9c05e78fa6dda61c19c846fb8087ea969c172753bc2f45b999a",
}

EXTRACTED = ["CUADv1.json", "test.json", "train_separate_questions.json"]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for name, expected in DOWNLOADS.items():
        dest = RAW / name
        if not dest.exists() or sha256(dest) != expected:
            urllib.request.urlretrieve(f"{BASE}/{name}", dest)
        actual = sha256(dest)
        if actual != expected:
            sys.exit(f"checksum mismatch for {name}: expected {expected}, got {actual}")

    with zipfile.ZipFile(RAW / "data.zip") as zf:
        members = {Path(n).name: n for n in zf.namelist()}
        for name in EXTRACTED:
            if name not in members:
                sys.exit(f"{name} not found in data.zip")
            with zf.open(members[name]) as src, open(RAW / name, "wb") as dst:
                dst.write(src.read())

    for name in EXTRACTED:
        print(f"{name} {(RAW / name).stat().st_size} {sha256(RAW / name)}")


if __name__ == "__main__":
    main()
