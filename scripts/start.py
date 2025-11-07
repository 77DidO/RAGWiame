"""Script de démarrage orchestrant bootstrap et déploiement."""
from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "scripts" / "bootstrap.sh"
DEPLOY = ROOT / "scripts" / "deploy.py"


class StartupError(RuntimeError):
    """Erreur contrôlée émise pendant le démarrage."""


def ensure_file(path: Path) -> None:
    if not path.exists():
        raise StartupError(f"Fichier introuvable: {path}")


def ensure_command(name: str) -> None:
    if shutil.which(name) is None:
        raise StartupError(f"Commande requise non disponible: {name}")


def run_bootstrap(system: str) -> None:
    ensure_file(BOOTSTRAP)
    if system == "Windows":
        ensure_command("wsl")
        wsl_root = subprocess.run(
            ["wsl", "wslpath", "-a", str(ROOT)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        # Assure que le script est exécutable et l'exécute dans WSL.
        subprocess.run(
            [
                "wsl",
                "bash",
                "-lc",
                f"cd {wsl_root} && chmod +x scripts/bootstrap.sh && ./scripts/bootstrap.sh",
            ],
            check=True,
        )
    else:
        BOOTSTRAP.chmod(BOOTSTRAP.stat().st_mode | 0o111)
        subprocess.run([str(BOOTSTRAP)], check=True)


def run_deploy(python_executable: str) -> None:
    ensure_file(DEPLOY)
    ensure_command("docker")
    subprocess.run([python_executable, str(DEPLOY)], check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Initialise l'environnement et lance le docker-compose associé.",
    )
    parser.add_argument(
        "--skip-bootstrap",
        action="store_true",
        help="Ignore l'étape bootstrap (préparez manuellement l'environnement).",
    )
    parser.add_argument(
        "--skip-deploy",
        action="store_true",
        help="Ignore le lancement docker-compose (utile pour un simple bootstrap).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    system = platform.system()

    try:
        if not args.skip_bootstrap:
            run_bootstrap(system)
        if not args.skip_deploy:
            run_deploy(sys.executable)
    except subprocess.CalledProcessError as exc:
        print(f"Commande échouée ({exc.cmd}): {exc}", file=sys.stderr)
        return exc.returncode or 1
    except StartupError as exc:
        print(exc, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
