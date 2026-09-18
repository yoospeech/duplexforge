#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
trainer_dir="$project_dir/third_party/moshi-finetune"
patch_file="$project_dir/patches/moshi-finetune-korean-vocab.patch"

if [[ ! -d "$trainer_dir/.git" ]]; then
  echo "moshi-finetune checkout not found: $trainer_dir" >&2
  exit 2
fi

if rg -q 'new_token_start' "$trainer_dir/finetune/args.py"; then
  echo "Korean vocabulary patch is already applied."
  exit 0
fi

git -C "$trainer_dir" apply "$patch_file"
echo "Applied Korean vocabulary patch to $trainer_dir"
