import subprocess
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_script_module():
    script_path = Path(__file__).parents[1] / "scripts" / "create_example_files.py"
    spec = spec_from_file_location("create_example_files", script_path)
    assert spec and spec.loader
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_create_example_files_is_idempotent(tmp_path):
    module = _load_script_module()

    first = module.create_example_files(tmp_path)
    second = module.create_example_files(tmp_path)

    assert len(first) == 5
    assert second == []
    assert (tmp_path / "projects.json").exists()
    assert (tmp_path / "artifacts/model_output.txt").exists()


def test_cli_writes_files(tmp_path):
    script_path = Path(__file__).parents[1] / "scripts" / "create_example_files.py"

    result = subprocess.run(
        [sys.executable, str(script_path), "--output-dir", str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
    )


    assert "Wrote 5 files" in result.stdout
    assert (tmp_path / "runs.jsonl").exists()
