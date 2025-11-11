from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
EXAMPLES_DIR = DATA_DIR / "examples"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="RAGWiame - Upload documents")


def _run_compose_service(
    service: str,
    compose_args: List[str] | None = None,
    service_args: List[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Exécute un service via docker compose."""
    cmd = [
        "docker",
        "compose",
        "-f",
        str(REPO_ROOT / "infra" / "docker-compose.yml"),
        "run",
        "--rm",
    ]
    if compose_args:
        cmd.extend(compose_args)
    cmd.append(service)
    if service_args:
        cmd.extend(service_args)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        check=False,
    )


@app.get("/", response_class=HTMLResponse)
async def upload_form() -> str:
    return (
        "<h2>Uploader des documents</h2>"
        "<form method='post' enctype='multipart/form-data'>"
        "<input type='file' name='files' multiple required><br><br>"
        "<label><input type='checkbox' name='trigger' value='1'>"
        "Lancer ingestion + indexation après l'upload</label><br><br>"
        "<button type='submit'>Envoyer</button>"
        "</form>"
    )


@app.post("/")
async def handle_upload(
    files: List[UploadFile] = File(...),
    trigger: int = Form(0),
) -> RedirectResponse:
    saved = []
    for up in files:
        data = await up.read()
        destination = EXAMPLES_DIR / up.filename
        destination.write_bytes(data)
        saved.append(up.filename)

    msg = f"Upload: {', '.join(saved)}"
    if trigger:
        loop = asyncio.get_event_loop()
        indexation = await loop.run_in_executor(
            None,
            _run_compose_service,
            "indexation",
            ["-e", "INGESTION_CONFIG_PATH=/app/ingestion/config/upload_ui.json"],
        )
        msg = f"{msg}<br>Indexation exit code: {indexation.returncode}"

    return HTMLResponse(
        f"<p>{msg}</p><p><a href='/'>Retour</a></p>",
        status_code=200,
    )
