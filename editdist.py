"""Edit distance, alignments and typo suggestions using only the standard library."""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class Step:
    operation: str
    source: str
    target: str


@dataclass(frozen=True)
class Alignment:
    distance: int
    similarity: float
    steps: tuple[Step, ...]


def align(source: str, target: str, *, transpose: bool = False) -> Alignment:
    """Return a minimum-cost alignment. Every edit costs one.

    transpose=True enables optimal string alignment (restricted Damerau),
    not unrestricted Damerau-Levenshtein distance. Characters are Unicode
    code points, not grapheme clusters. Inputs are never normalized silently.
    """
    n, m = len(source), len(target)
    table = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        table[i][0] = i
    for j in range(m + 1):
        table[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = source[i - 1] != target[j - 1]
            table[i][j] = min(table[i - 1][j] + 1,
                              table[i][j - 1] + 1,
                              table[i - 1][j - 1] + cost)
            if (transpose and i > 1 and j > 1
                    and source[i - 1] == target[j - 2]
                    and source[i - 2] == target[j - 1]):
                table[i][j] = min(table[i][j], table[i - 2][j - 2] + 1)
    steps: list[Step] = []
    i, j = n, m
    while i or j:
        # Deterministic tie order: match, transpose, replace, delete, insert.
        if i and j and source[i - 1] == target[j - 1] and table[i][j] == table[i - 1][j - 1]:
            steps.append(Step('match', source[i - 1], target[j - 1]))
            i, j = i - 1, j - 1
        elif (transpose and i > 1 and j > 1
              and source[i - 1] == target[j - 2]
              and source[i - 2] == target[j - 1]
              and table[i][j] == table[i - 2][j - 2] + 1):
            steps.append(Step('transpose', source[i - 2:i], target[j - 2:j]))
            i, j = i - 2, j - 2
        elif i and j and table[i][j] == table[i - 1][j - 1] + 1:
            steps.append(Step('replace', source[i - 1], target[j - 1]))
            i, j = i - 1, j - 1
        elif i and table[i][j] == table[i - 1][j] + 1:
            steps.append(Step('delete', source[i - 1], ''))
            i -= 1
        else:
            steps.append(Step('insert', '', target[j - 1]))
            j -= 1
    distance = table[n][m]
    similarity = 1 - distance / max(n, m) if n or m else 1.0
    return Alignment(distance, similarity, tuple(reversed(steps)))


def suggest(word: str, candidates: list[str], *, limit: int = 5,
            max_distance: int | None = None, transpose: bool = False) -> list[tuple[int, str]]:
    """Rank unique candidates by distance, then lexicographically."""
    if limit < 0 or (max_distance is not None and max_distance < 0):
        raise ValueError('limit and max_distance must be non-negative')
    ranked = sorted((align(word, candidate, transpose=transpose).distance, candidate)
                    for candidate in set(candidates))
    if max_distance is not None:
        ranked = [pair for pair in ranked if pair[0] <= max_distance]
    return ranked[:limit]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    compare = sub.add_parser('compare', help='Compare two strings and show their alignment')
    compare.add_argument('source')
    compare.add_argument('target')
    compare.add_argument('--transpose', action='store_true', help='Allow adjacent transpositions (OSA)')
    compare.add_argument('--json', action='store_true')
    hints = sub.add_parser('suggest', help='Rank a UTF-8 word list, one candidate per line')
    hints.add_argument('word')
    hints.add_argument('dictionary', type=Path)
    hints.add_argument('--limit', type=int, default=5)
    hints.add_argument('--max-distance', type=int)
    hints.add_argument('--transpose', action='store_true')
    hints.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.command == 'compare':
            result = align(args.source, args.target, transpose=args.transpose)
            if args.json:
                print(json.dumps(asdict(result), ensure_ascii=False))
            else:
                print(f'distance: {result.distance}; similarity: {result.similarity:.3f}')
                for step in result.steps:
                    print(f'{step.operation:9} {step.source!r} -> {step.target!r}')
        else:
            words = args.dictionary.read_text(encoding='utf-8').splitlines()
            ranked = suggest(args.word, words, limit=args.limit,
                             max_distance=args.max_distance, transpose=args.transpose)
            if args.json:
                print(json.dumps([{'distance': d, 'word': w} for d, w in ranked], ensure_ascii=False))
            else:
                for distance, word in ranked:
                    print(f'{distance}\t{word}')
    except (OSError, UnicodeError, ValueError) as error:
        parser.exit(2, f'editdist: {error}\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
