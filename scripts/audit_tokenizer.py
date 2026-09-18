#!/usr/bin/env python3
"""Audit Korean coverage for the exact SentencePiece model used by Moshi."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("tokenizer", type=Path)
    parser.add_argument("text", type=Path, help="UTF-8 file with one sentence per line")
    args = parser.parse_args()
    try:
        import sentencepiece as spm
    except ImportError as exc:
        raise SystemExit("Install sentencepiece to run this audit") from exc
    tokenizer = spm.SentencePieceProcessor(model_file=str(args.tokenizer))
    sentences = [line.strip() for line in args.text.read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = [tokenizer.encode(sentence, out_type=int) for sentence in sentences]
    unk_id = tokenizer.unk_id()
    unknown = sum(token == unk_id for row in ids for token in row)
    tokens = sum(map(len, ids))
    hangul = [chr(code) for code in range(0xAC00, 0xD7A4)]
    covered = sum(tokenizer.piece_to_id(char) != unk_id for char in hangul)
    print(json.dumps({
        "sentences": len(sentences),
        "tokens": tokens,
        "average_tokens_per_sentence": tokens / len(sentences) if sentences else 0,
        "unknown_tokens": unknown,
        "unknown_rate": unknown / tokens if tokens else 0,
        "hangul_syllables_directly_covered": covered,
        "hangul_syllable_coverage": covered / len(hangul),
        "vocabulary_size": tokenizer.vocab_size(),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
