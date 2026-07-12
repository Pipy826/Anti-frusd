from __future__ import annotations

import argparse
import shutil
import time
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INCLUDE = [
    "backend/app",
    "backend/requirements.txt",
    "backend/Dockerfile",
    "backend/.dockerignore",
    "frontend/src",
    "frontend/public",
    "frontend/index.html",
    "frontend/package.json",
    "frontend/package-lock.json",
    "frontend/vite.config.js",
    "frontend/Dockerfile",
    "frontend/nginx.conf",
    "frontend/.dockerignore",
    "scripts",
    "文档",
    "README.md",
    "docker-compose.yml",
]
EXCLUDE_PARTS = {"node_modules", ".venv", "dist", "__pycache__", "data", "logs", ".git", ".pnpm-store"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Create V1.0 release/offline deployment package.")
    parser.add_argument("--out", default="", help="Output zip path")
    args = parser.parse_args()

    out_dir = ROOT / "release"
    out_dir.mkdir(exist_ok=True)
    output = Path(args.out) if args.out else out_dir / f"anti-fraud-v1.0-{time.strftime('%Y%m%d-%H%M%S')}.zip"
    if output.exists():
        output.unlink()

    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for item in INCLUDE:
            path = ROOT / item
            if not path.exists():
                continue
            if path.is_file():
                archive.write(path, path.relative_to(ROOT))
                continue
            for file in path.rglob("*"):
                if file.is_file() and not should_exclude(file):
                    archive.write(file, file.relative_to(ROOT))

    print(output)


def should_exclude(path: Path) -> bool:
    return any(part in EXCLUDE_PARTS for part in path.relative_to(ROOT).parts)


if __name__ == "__main__":
    main()
