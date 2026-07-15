"""Command-line interface for :mod:`nepal_ttf2utf`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from . import __version__, convert, supported_fonts


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nepal-ttf2utf",
        description="Convert legacy-font text or validate an already-Unicode font span.",
    )
    parser.add_argument("text", nargs="?", help="text to convert; reads stdin when omitted")
    parser.add_argument("-f", "--font", help="font or encoding key (case-insensitive)")
    parser.add_argument("-i", "--input-file", type=Path, help="read input from this file")
    parser.add_argument("-o", "--output-file", type=Path, help="write output to this file")
    parser.add_argument(
        "--input-encoding",
        default="utf-8",
        help="input byte encoding for files/stdin (default: utf-8; try cp1252 for 8-bit fonts)",
    )
    parser.add_argument(
        "--output-encoding",
        default="utf-8",
        help="output file byte encoding (default: utf-8)",
    )
    parser.add_argument("--strict", action="store_true", help="fail on unresolved input")
    parser.add_argument("--list-fonts", action="store_true", help="list font keys and exit")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def _read_stdin(encoding: str) -> str:
    stream = getattr(sys.stdin, "buffer", None)
    if stream is None:
        return sys.stdin.read()
    return stream.read().decode(encoding)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line converter and return an exit status."""
    parser = _parser()
    args = parser.parse_args(argv)

    if args.list_fonts:
        for key, script in sorted(supported_fonts().items()):
            print(f"{key}\t{script}")
        return 0

    if not args.font:
        parser.error("--font is required unless --list-fonts is used")
    if args.text is not None and args.input_file is not None:
        parser.error("TEXT and --input-file cannot be used together")

    try:
        if args.input_file is not None:
            source = args.input_file.read_text(encoding=args.input_encoding)
        elif args.text is not None:
            source = args.text
        else:
            source = _read_stdin(args.input_encoding)
        output = convert(source, font=args.font, strict=args.strict)
        if args.output_file is not None:
            args.output_file.write_text(output, encoding=args.output_encoding)
        else:
            sys.stdout.write(output)
    except (LookupError, OSError, UnicodeError, ValueError) as error:
        parser.exit(2, f"nepal-ttf2utf: error: {error}\n")
    return 0
