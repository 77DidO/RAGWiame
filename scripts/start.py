"""Script de demarrage orchestrant bootstrap et deploiement."""
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
    """Erreur controlee emise pendant le demarrage."""


def ensure_file(path: Path) -> None:
    if not path.exists():
        raise StartupError(f"Fichier introuvable: {path}")


def ensure_command(name: str) -> None:
    if shutil.which(name) is None:
        raise StartupError(f"Commande requise non disponible: {name}")


def run_bootstrap(system: str) -> None:
    ensure_file(BOOTSTRAP)
    if system == "Windows":
        if shutil.which("wsl"):
            try:
                wsl_root = subprocess.run(
                    ["wsl", "wslpath", "-a", str(ROOT)],
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip()
                subprocess.run(
                    [
                        "wsl",
                        "bash",
                        "-lc",
                        "cd {root} && chmod +x scripts/bootstrap.sh && ./scripts/bootstrap.sh".format(
                            root=wsl_root
                        ),
                    ],
                    check=True,
                )
                return
            except subprocess.CalledProcessError as exc:
                print(
                    (
                        "Execution WSL du bootstrap impossible, "
                        "bascule vers l'installation native (cause: {exc})"
                    ).format(exc=exc),
                    file=sys.stderr,
                )

        run_native_bootstrap(system)
        return

    BOOTSTRAP.chmod(BOOTSTRAP.stat().st_mode | 0o111)
    subprocess.run([str(BOOTSTRAP)], check=True)


def run_native_bootstrap(system: str) -> None:
    """Execute le bootstrap directement avec Python (fallback Windows)."""
    venv_dir = ROOT / ".venv"
    python_exe = Path(
        venv_dir
        / ("Scripts" if system == "Windows" else "bin")
        / ("python.exe" if system == "Windows" else "python")
    )

    if not python_exe.exists():
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)

    if not python_exe.exists():
        raise StartupError("Python du virtualenv introuvable, creation venv echouee ?")

    pip_cmd = [str(python_exe), "-m", "pip"]

    pip_ok = subprocess.run(
        pip_cmd + ["--version"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0
    if not pip_ok:
        subprocess.run([str(python_exe), "-m", "ensurepip", "--upgrade"], check=True)

    subprocess.run(pip_cmd + ["install", "--upgrade", "pip"], check=True)

    requirements = [
        ROOT / "ingestion" / "requirements.txt",
        ROOT / "indexation" / "requirements.txt",
        ROOT / "llm_pipeline" / "requirements.txt",
    ]
    for req_file in requirements:
        ensure_file(req_file)
        subprocess.run(pip_cmd + ["install", "-r", str(req_file)], check=True)


def run_deploy(python_executable: str) -> None:
    ensure_file(DEPLOY)
    ensure_command("docker")
    subprocess.run([python_executable, str(DEPLOY)], check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Initialise l'environnement et lance le docker-compose associe.",
    )
    parser.add_argument(
        "--skip-bootstrap",
        action="store_true",
        help="Ignore l'etape bootstrap (preparez manuellement l'environnement).",
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
        print(f"Commande echouee ({exc.cmd}): {exc}", file=sys.stderr)
        return exc.returncode or 1
    except StartupError as exc:
        print(exc, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
