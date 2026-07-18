#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

EXAMPLE_FILES = {
    "projects.json": (
        '{\n'
        '  "projects": [\n'
        '    {"id": "proj_demo", "name": "demo-project", "tags": ["demo", "local"]}\n'
        "  ]\n"
        "}\n"
    ),
    "runs.jsonl": (
        '{"id": "run_demo_001", "project_id": "proj_demo", "status": "completed", "tags": ["baseline"]}\n'
        '{"id": "run_demo_002", "project_id": "proj_demo", "status": "running", "tags": ["candidate"]}\n'
    ),
    "metrics.csv": "run_id,key,value,step\\nrun_demo_001,accuracy,0.91,1\\nrun_demo_001,loss,0.12,1\\n",
    "notes.md": (
        "# Demo Notes\\n\\n"
        "- run_demo_001 reached stable metrics.\\n"
        "- run_demo_002 is currently in progress.\\n"
    ),
    "artifacts/model_output.txt": "Sample artifact payload for local testing.\\n",
}


def create_example_files(output_dir: Path, overwrite: bool = False) -> list[Path]:
    created_or_updated: list[Path] = []

    for relative_path, content in EXAMPLE_FILES.items():
        destination = output_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)

        if destination.exists() and not overwrite:
            continue

        destination.write_text(content, encoding="utf-8")
        created_or_updated.append(destination)

    return created_or_updated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create representative Fantomex example files for local testing.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("example_data"),
        help="Directory where example files are written (default: ./example_data)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files instead of skipping them.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    changed_files = create_example_files(output_dir=output_dir, overwrite=args.overwrite)

    if changed_files:
        print(f"Wrote {len(changed_files)} files to {output_dir}")
        for path in changed_files:
            print(f" - {path}")
    else:
        print(f"No files changed. Example files already exist in {output_dir}")


if __name__ == "__main__":
    main()
