"""
The layering rule and the file-size ceiling, enforced instead of remembered.

Both are broken silently and one at a time, which is exactly the kind of drift a test is
for: found the day it happens, not at the review six weeks later.
"""

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[3] / "src"
MAX_FILE_LINES = 500

FORBIDDEN_IMPORTS = {
    # routers call one service method; reaching for a repository or an ORM model means the
    # rule that belongs in a service has leaked into the transport layer.
    "routers": ("repos", "models.course", "models.user", "sqlalchemy"),
    # SQL is not written above the repository. Enum imports are fine, queries are not.
    "services": ("sqlalchemy",),
}


def python_files(layer: str) -> list[Path]:
    """Every module of one layer."""
    return sorted((SRC / layer).rglob("*.py"))


def imported_modules(path: Path) -> set[str]:
    """Names this module imports, as written."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_layers_only_import_downwards() -> None:
    """Routers reach services only, and no layer above repos writes SQL."""
    violations: list[str] = []

    for layer, forbidden in FORBIDDEN_IMPORTS.items():
        for path in python_files(layer):
            for module in imported_modules(path):
                if any(module == item or module.startswith(f"{item}.") for item in forbidden):
                    violations.append(f"{path.relative_to(SRC)} imports {module}")

    assert violations == []


def test_no_source_file_exceeds_the_ceiling() -> None:
    """500 lines is a hard limit: past it a file is doing more than one thing."""
    oversized = [
        f"{path.relative_to(SRC)}: {len(path.read_text(encoding='utf-8').splitlines())} lines"
        for path in SRC.rglob("*.py")
        if len(path.read_text(encoding="utf-8").splitlines()) > MAX_FILE_LINES
    ]

    assert oversized == []
