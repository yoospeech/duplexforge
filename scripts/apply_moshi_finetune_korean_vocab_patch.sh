#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
trainer_dir="$project_dir/third_party/moshi-finetune"
moshi_dir="$project_dir/third_party/moshi"

if [[ ! -f "$trainer_dir/finetune/args.py" || ! -f "$moshi_dir/moshi/moshi/models/loaders.py" ]]; then
  echo "Moshi submodules are missing. Run: git submodule update --init --recursive" >&2
  exit 2
fi

apply_if_needed() {
  local checkout="$1"
  local patch_file="$2"
  if git -C "$checkout" apply --reverse --check "$patch_file" 2>/dev/null; then
    echo "Already applied: ${patch_file##*/}"
  elif git -C "$checkout" apply --check "$patch_file"; then
    git -C "$checkout" apply "$patch_file"
    echo "Applied: ${patch_file##*/}"
  else
    echo "Patch does not match checkout: $patch_file" >&2
    exit 1
  fi
}

apply_if_needed "$moshi_dir" "$project_dir/patches/moshi-gb10-environment.patch"
apply_if_needed "$trainer_dir" "$project_dir/patches/moshi-finetune-gb10-environment.patch"
apply_if_needed "$moshi_dir" "$project_dir/patches/moshi-korean-vocab-loader.patch"
apply_if_needed "$trainer_dir" "$project_dir/patches/moshi-finetune-korean-vocab.patch"
