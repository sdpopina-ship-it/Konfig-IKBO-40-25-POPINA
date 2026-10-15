#!/bin/sh
PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_DIR" || exit 1
python3 -m src.main \
  --vfs-path examples/vfs-deep \
  --log-path logs/vfs-deep.json \
  --script-path scripts/startup_vfs_deep.txt
