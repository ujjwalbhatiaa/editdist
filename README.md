# editdist

A dependency-free Python tool for understanding string differences and ranking typo suggestions. It returns both an edit distance and the actual alignment, so a number is not a black box.

Requires Python 3.10 or later. No installation, network access or account is needed.

## Compare strings

```sh
python editdist.py compare kitten sitting
python editdist.py compare form from --transpose --json
```

The second example has distance 1 when adjacent transpositions are enabled, rather than the ordinary Levenshtein distance of 2. Alignment operations are `match`, `replace`, `insert`, `delete` and, when enabled, `transpose`.

## Rank suggestions

Create a UTF-8 text file with one candidate per line:

```text
form
from
forum
farm
```

```sh
python editdist.py suggest from words.txt --transpose --limit 3 --max-distance 2
python editdist.py suggest from words.txt --json
```

Candidates are deduplicated. Ties are sorted lexicographically, and blank lines are valid empty-string candidates. A missing or invalid UTF-8 file produces an error and exit status 2.

## Use the API

```python
from editdist import align, suggest

result = align('form', 'from', transpose=True)
assert result.distance == 1
assert ''.join(step.source for step in result.steps) == 'form'
assert ''.join(step.target for step in result.steps) == 'from'

print(suggest('cat', ['cut', 'cat', 'bat']))
# [(0, 'cat'), (1, 'bat'), (1, 'cut')]
```

## Algorithm and limits

The implementation uses a dynamic-programming matrix with deterministic traceback. Time and memory are O(n*m), so use it for words and short strings, not large documents. Each edit costs one. Similarity is `1 - distance / max(lengths)`, with two empty strings defined as 1.

`--transpose` implements **optimal string alignment**, also called restricted Damerau distance. It is not unrestricted Damerau-Levenshtein distance. For example, `CA` to `ABC` has OSA distance 3 but unrestricted distance 2. OSA does not satisfy the triangle inequality, so do not use it as a metric-tree distance.

Strings are compared as Unicode code points. Case folding, normalization and grapheme segmentation are deliberately not implicit: `A` and `a` differ, as do composed and decomposed accented characters.

## Tests

```sh
python -m unittest -v
```

The suite checks examples, Unicode, CLI errors, ranking, duplicate removal, OSA's restricted behavior, and all 961 pairs of binary strings up to length four against an independent recursive Levenshtein oracle. It also reconstructs both inputs from every generated alignment and checks the edit count.
