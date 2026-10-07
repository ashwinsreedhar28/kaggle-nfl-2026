#!/usr/bin/env bash
# Requires: Kaggle API token at ~/.kaggle/kaggle.json and competition rules accepted on kaggle.com.
# Usage: scripts/download_data.sh
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data/raw
kaggle competitions download -c nfl-big-data-bowl-2027 -p data/raw
cd data/raw && unzip -o nfl-big-data-bowl-2027.zip && rm nfl-big-data-bowl-2027.zip
ls -lh
