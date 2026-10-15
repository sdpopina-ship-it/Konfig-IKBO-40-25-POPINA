#!/bin/sh
PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_DIR" || exit 1
python3 -m src.main \
  --vfs-path examples/vfs-files \
  --log-path logs/vfs-files.json \
  --script-path scripts/startup_vfs_files.txt
