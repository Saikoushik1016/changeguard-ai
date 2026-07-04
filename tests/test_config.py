import importlib
from pathlib import Path


def test_settings_load_env_from_repo_root(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    import changeguard_ai.core.config as config

    reloaded = importlib.reload(config)
    env_path = Path(__file__).resolve().parents[1] / ".env"

    expected_token = None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("GITHUB_TOKEN="):
            expected_token = line.split("=", 1)[1]
            break

    assert expected_token
    assert reloaded.settings.github_token == expected_token
