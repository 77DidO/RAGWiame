"""Script de déploiement docker-compose."""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCKER_COMPOSE_FILE = ROOT / "infra" / "docker-compose.yml"


def run_compose() -> None:
    subprocess.run(["docker", "compose", "-f", str(DOCKER_COMPOSE_FILE), "up", "-d"], check=True)


if __name__ == "__main__":
    run_compose()
