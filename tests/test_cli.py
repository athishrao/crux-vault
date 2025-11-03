import json
import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cruxvault.cli import app

runner = CliRunner()


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        original_dir = os.getcwd()
        os.chdir(tmpdir)
        yield tmpdir
        os.chdir(original_dir)


class TestCLI:
    def test_init_command(self, temp_dir: str) -> None:
        result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        assert "Initialized cruxvault" in result.stdout
        assert os.path.exists(".cruxvault/config.yaml")
        assert os.path.exists(".cruxvault/store.db")

    def test_init_already_initialized(self, temp_dir: str) -> None:
        runner.invoke(app, ["init"])
        result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        assert "Already initialized" in result.stdout

    def test_set_and_get_secret(self, temp_dir: str) -> None:
        runner.invoke(app, ["init"])

        result = runner.invoke(app, ["set", "test/key", "test-value"])
        assert result.exit_code == 0
        assert "Set test/key" in result.stdout

        result = runner.invoke(app, ["get", "test/key"])
        assert result.exit_code == 0
        assert "test-value" in result.stdout

    def test_get_nonexistent_secret(self, temp_dir: str) -> None:
        runner.invoke(app, ["init"])

        result = runner.invoke(app, ["get", "nonexistent"])
        assert result.exit_code == 1
        assert "not found" in result.stdout

    def test_set_with_tags(self, temp_dir: str) -> None:
        runner.invoke(app, ["init"])

        result = runner.invoke(
            app, ["set", "api/key", "value", "--tag", "production", "--tag", "important"]
        )
        assert result.exit_code == 0

    def test_get_with_json_output(self, temp_dir: str) -> None:
        runner.invoke(app, ["init"])
        runner.invoke(app, ["set", "test/key", "test-value"])

        result = runner.invoke(app, ["get", "test/key", "--json"])
        assert result.exit_code == 0

        data = json.loads(result.stdout)
        assert data["path"] == "test/key"
        assert data["value"] == "test-value"

    def test_get_with_quiet_flag(self, temp_dir: str) -> None:
        runner.invoke(app, ["init"])
        runner.invoke(app, ["set", "test/key", "test-value"])

        result = runner.invoke(app, ["get", "test/key", "--quiet"])
        assert result.exit_code == 0
        assert result.stdout.strip() == "test-value"

    def test_list_secrets(self, temp_dir: str) -> None:
        runner.invoke(app, ["init"])
        runner.invoke(app, ["set", "api/key1", "value1"])
        runner.invoke(app, ["set", "api/key2", "value2"])
        runner.invoke(app, ["set", "db/password", "value3"])

        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "api/key1" in result.stdout
        assert "api/key2" in result.stdout
        assert "db/password" in result.stdout
        assert "Total: 3" in result.stdout

    def test_list_with_prefix(self, temp_dir: str) -> None:
        runner.invoke(app, ["init"])
        runner.invoke(app, ["set", "api/key1", "value1"])
        runner.invoke(app, ["set", "api/key2", "value2"])
        runner.invoke(app, ["set", "db/password", "value3"])

        result = runner.invoke(app, ["list", "api/"])
        assert result.exit_code == 0
        assert "api/key1" in result.stdout
        assert "api/key2" in result.stdout
        assert "db/password" not in result.stdout

    def test_list_with_json_output(self, temp_dir: str) -> None:
        runner.invoke(app, ["init"])
        runner.invoke(app, ["set", "test/key", "test-value"])

        result = runner.invoke(app, ["list", "--json"])
        assert result.exit_code == 0

        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["path"] == "test/key"

    def test_delete_secret(self, temp_dir: str) -> None:
        runner.invoke(app, ["init"])
        runner.invoke(app, ["set", "test/key", "value"])

        result = runner.invoke(app, ["delete", "test/key", "--force"])
        assert result.exit_code == 0
        assert "Deleted test/key" in result.stdout

        result = runner.invoke(app, ["get", "test/key"])
        assert result.exit_code == 1

    def test_delete_nonexistent_secret(self, temp_dir: str) -> None:
        runner.invoke(app, ["init"])

        result = runner.invoke(app, ["delete", "nonexistent", "--force"])
        assert result.exit_code == 1
        assert "not found" in result.stdout

    def test_history_command(self, temp_dir: str) -> None:
        runner.invoke(app, ["init"])
        runner.invoke(app, ["set", "api/key", "value1"])
        runner.invoke(app, ["set", "api/key", "value2"])
        runner.invoke(app, ["set", "api/key", "value3"])

        result = runner.invoke(app, ["history", "api/key"])
        assert result.exit_code == 0
        assert "History for api/key" in result.stdout
        assert "value1" in result.stdout
        assert "value2" in result.stdout
        assert "value3" in result.stdout

    def test_rollback_command(self, temp_dir: str) -> None:
        runner.invoke(app, ["init"])
        runner.invoke(app, ["set", "api/key", "value1"])
        runner.invoke(app, ["set", "api/key", "value2"])

        result = runner.invoke(app, ["rollback", "api/key", "1", "--force"])
        assert result.exit_code == 0
        assert "Rolled back" in result.stdout

        result = runner.invoke(app, ["get", "api/key"])
        assert "value1" in result.stdout

    def test_dev_start_command(self, temp_dir: str) -> None:
        runner.invoke(app, ["init"])

        result = runner.invoke(app, ["dev", "start"])
        assert result.exit_code == 0
        assert "Generated" in result.stdout

        result = runner.invoke(app, ["list"])
        assert "database/pa" in result.stdout

    def test_dev_export_command(self, temp_dir: str) -> None:
        runner.invoke(app, ["init"])
        runner.invoke(app, ["set", "database/password", "secret123"])
        runner.invoke(app, ["set", "api/key", "abc123"])

        result = runner.invoke(app, ["dev", "export"])
        assert result.exit_code == 0
        assert "DATABASE_PASSWORD=" in result.stdout
        assert "API_KEY=" in result.stdout

    def test_dev_export_to_file(self, temp_dir: str) -> None:
        runner.invoke(app, ["init"])
        runner.invoke(app, ["set", "test/key", "value"])

        output_file = "test.env"
        result = runner.invoke(app, ["dev", "export", "--output", output_file])
        assert result.exit_code == 0
        assert os.path.exists(output_file)

        with open(output_file) as f:
            content = f.read()
            assert "TEST_KEY=" in content

    def test_import_env_command(self, temp_dir: str) -> None:
        runner.invoke(app, ["init"])

        env_content = """
DATABASE_HOST=localhost
DATABASE_PORT=5432
API_KEY=abc123
# Comment line
EMPTY_LINE_BELOW=

"""
        env_file = "test.env"
        with open(env_file, "w") as f:
            f.write(env_content)

        result = runner.invoke(app, ["import-env", env_file])
        assert result.exit_code == 0
        assert "Imported 3 secrets" in result.stdout

        result = runner.invoke(app, ["get", "database/host"])
        assert "localhost" in result.stdout

    def test_import_env_with_prefix(self, temp_dir: str) -> None:
        runner.invoke(app, ["init"])

        env_content = "KEY=value\n"
        env_file = "test.env"
        with open(env_file, "w") as f:
            f.write(env_content)

        result = runner.invoke(app, ["import-env", env_file, "--prefix", "prod"])
        assert result.exit_code == 0

        result = runner.invoke(app, ["get", "prod/key"])
        assert "value" in result.stdout

    def test_audit_log_created(self, temp_dir: str) -> None:
        runner.invoke(app, ["init"])
        runner.invoke(app, ["set", "test/key", "value"])

        assert os.path.exists(".cruxvault/audit.log")

        with open(".cruxvault/audit.log") as f:
            log_lines = f.readlines()
            assert len(log_lines) > 0

            for line in log_lines:
                data = json.loads(line)
                assert "timestamp" in data
                assert "user" in data
                assert "action" in data

