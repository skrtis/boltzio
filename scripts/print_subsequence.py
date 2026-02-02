#!/usr/bin/env python3
"""Simple helper to print a subsequence from a FASTA file.

Usage examples:
  python scripts/print_subsequence.py inputs/cdPDE3A.fasta 678 1141
  python scripts/print_subsequence.py inputs/cdPDE3A.fasta 100 -w 80

The residue coordinates are 1-based and inclusive.
"""
import argparse
import sys


def read_fasta(path):
    seq_lines = []
    try:
        with open(path, "r") as fh:
            for line in fh:
                if line.startswith(">"):
                    continue
                seq_lines.append(line.strip())
    except FileNotFoundError:
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(2)
    return "".join(seq_lines)


def main():
    p = argparse.ArgumentParser(description="Print subsequence from FASTA (1-based inclusive).")
    p.add_argument("fasta", help="Path to FASTA file")
    p.add_argument("start", type=int, help="Start residue (1-based)")
    p.add_argument("end", type=int, nargs="?", help="End residue (1-based, inclusive). If omitted, prints only the start residue")
    p.add_argument("-w", "--width", type=int, default=0, help="Wrap output to this column width (0 = no wrap)")
    args = p.parse_args()

    seq = read_fasta(args.fasta)
    n = len(seq)

    if args.end is None:
        end = args.start
    else:
        end = args.end
    start = args.start

    if start < 1 or end < start or end > n:
        print(f"Error: invalid range {start}-{end} for sequence length {n}", file=sys.stderr)
        sys.exit(2)

    sub = seq[start - 1 : end]

    if args.width and args.width > 0:
        for i in range(0, len(sub), args.width):
            print(sub[i : i + args.width])
    else:
        print(sub)


if __name__ == "__main__":
    main()
