#!/usr/bin/env bash
set -euo pipefail

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r ingestion/requirements.txt -r indexation/requirements.txt -r llm_pipeline/requirements.txt
