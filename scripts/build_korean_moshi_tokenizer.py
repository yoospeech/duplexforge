#!/usr/bin/env python3
"""Append Korean SentencePiece units while preserving every Moshiko token ID."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import sentencepiece as spm
from sentencepiece import sentencepiece_model_pb2 as sp_pb2


HANGUL = re.compile(r"[가-힣]")


def _assistant_texts(manifest: Path) -> list[str]:
    root = manifest.parent
    texts: list[str] = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        metadata = json.loads((root / row["metadata_path"]).read_text(encoding="utf-8"))
        texts.extend(
            event["text"] for event in metadata["events"] if event["speaker"] == "assistant"
        )
    return texts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--base-tokenizer", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--vocab-size", type=int, default=2048)
    args = parser.parse_args()

    texts = _assistant_texts(args.manifest)
    if not texts:
        raise ValueError("no assistant transcript text found")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    corpus = args.output_dir / "assistant_ko_corpus.txt"
    corpus.write_text("\n".join(texts) + "\n", encoding="utf-8")

    seed_prefix = args.output_dir / "korean_seed"
    spm.SentencePieceTrainer.train(
        input=str(corpus),
        model_prefix=str(seed_prefix),
        model_type="unigram",
        vocab_size=args.vocab_size,
        character_coverage=0.9995,
        hard_vocab_limit=False,
        bos_id=1,
        eos_id=2,
        pad_id=-1,
    )

    base = sp_pb2.ModelProto()
    base.ParseFromString(args.base_tokenizer.read_bytes())
    original_size = len(base.pieces)
    known = {piece.piece for piece in base.pieces}

    seed = sp_pb2.ModelProto()
    seed.ParseFromString((args.output_dir / "korean_seed.model").read_bytes())
    added: list[str] = []
    for piece in seed.pieces:
        if (
            piece.type == sp_pb2.ModelProto.SentencePiece.NORMAL
            and HANGUL.search(piece.piece)
            and piece.piece not in known
        ):
            base.pieces.append(piece)
            known.add(piece.piece)
            added.append(piece.piece)

    if not added:
        raise RuntimeError("no Korean pieces were appended")
    base.trainer_spec.vocab_size = len(base.pieces)
    output = args.output_dir / "tokenizer_spm_ko_extended.model"
    output.write_bytes(base.SerializeToString())

    # moshi-finetune accepts this through moshi_paths.config_path.  The tokenizer
    # is passed separately, while text_card makes the three text vocab tensors
    # instantiate at the expanded size before checkpoint weights are loaded.
    from moshi.models.loaders import _lm_kwargs

    lm_config = dict(_lm_kwargs)
    lm_config["text_card"] = len(base.pieces)
    config_path = args.output_dir / "lm_config.json"
    config_path.write_text(
        json.dumps(lm_config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    old = spm.SentencePieceProcessor(str(args.base_tokenizer))
    new = spm.SentencePieceProcessor(str(output))
    old_count = sum(len(old.encode(text)) for text in texts)
    new_count = sum(len(new.encode(text)) for text in texts)
    print(f"base_vocab={original_size}")
    print(f"added_korean_pieces={len(added)}")
    print(f"extended_vocab={new.get_piece_size()}")
    print(f"assistant_tokens_before={old_count}")
    print(f"assistant_tokens_after={new_count}")
    print(f"token_reduction={(1 - new_count / old_count) * 100:.2f}%")
    print(f"tokenizer={output}")
    print(f"lm_config={config_path}")


if __name__ == "__main__":
    main()
