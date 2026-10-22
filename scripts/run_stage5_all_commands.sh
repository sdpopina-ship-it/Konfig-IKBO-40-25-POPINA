#!/bin/sh
PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_DIR" || exit 1
python3 -m src.main \
  --vfs-path examples/vfs-files \
  --log-path logs/stage5-all-commands.json \
  --script-path scripts/startup_stage5_all_commands.txt
