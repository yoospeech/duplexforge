#!/usr/bin/env python3
from duplexforge.cli import main

raise SystemExit(main(["generate", *__import__("sys").argv[1:]]))
