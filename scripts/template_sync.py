"""Shared tracked-file rules for Nova UI source and starter synchronization."""
from pathlib import Path

TRACKED_DIRS = ("lib", "test")
TRACKED_FILES = (
    ".gitignore",
    "pubspec.yaml",
    "pubspec.lock",
    "analysis_options.yaml",
    "README.md",
    "CHANGELOG.md",
    "docs/DESIGN_SYSTEM.md",
    "docs/PROJECT_STATUS.md",
)


def collect_files(root: Path) -> dict[str, Path]:
    result = {}

    for directory in TRACKED_DIRS:
        folder = root / directory
        if folder.is_dir():
            for path in folder.rglob("*"):
                if path.is_file():
                    result[path.relative_to(root).as_posix()] = path

    for filename in TRACKED_FILES:
        path = root / filename
        if path.is_file():
            result[filename] = path

    return result


def compare_files(source: Path, target: Path) -> dict:
    source_files = collect_files(source)
    target_files = collect_files(target)
    return {
        "source_files": source_files,
        "target_files": target_files,
        "missing": sorted(set(source_files) - set(target_files)),
        "extra": sorted(set(target_files) - set(source_files)),
        "different": sorted(
            name for name in set(source_files) & set(target_files)
            if source_files[name].read_bytes() != target_files[name].read_bytes()
        ),
    }
