import contextlib
from functools import lru_cache
import io
import itertools
import json
from pathlib import Path
import tempfile
import unittest
from editdist import align, main, suggest

@lru_cache(None)
def oracle(a, b):
    if not a: return len(b)
    if not b: return len(a)
    return min(oracle(a[1:], b) + 1, oracle(a, b[1:]) + 1,
               oracle(a[1:], b[1:]) + (a[0] != b[0]))

class Tests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(align('', '').distance, 0)
        self.assertEqual(align('', '').similarity, 1)
    def test_insert(self): self.assertEqual(align('', 'abc').distance, 3)
    def test_delete(self): self.assertEqual(align('abc', '').distance, 3)
    def test_example(self): self.assertEqual(align('kitten', 'sitting').distance, 3)
    def test_transpose(self):
        self.assertEqual(align('form', 'from').distance, 2)
        self.assertEqual(align('form', 'from', transpose=True).distance, 1)
    def test_restricted_not_unrestricted(self):
        self.assertEqual(align('CA', 'ABC', transpose=True).distance, 3)
    def test_unicode(self):
        self.assertEqual(align('café', 'cafe').distance, 1)
        self.assertEqual(align('猫', '狗').distance, 1)
    def test_no_implicit_normalization(self):
        self.assertEqual(align('A', 'a').distance, 1)
        self.assertNotEqual(align('é', 'e\u0301').distance, 0)
    def test_exhaustive_oracle_and_reconstruction(self):
        words=[''.join(p) for size in range(5) for p in itertools.product('ab',repeat=size)]
        for a,b in itertools.product(words, repeat=2):
            with self.subTest(a=a,b=b):
                self.assertEqual(align(a,b).distance, oracle(a,b))
                for transpose in [False,True]:
                    r=align(a,b,transpose=transpose)
                    self.assertEqual(''.join(s.source for s in r.steps),a)
                    self.assertEqual(''.join(s.target for s in r.steps),b)
                    self.assertEqual(sum(s.operation!='match' for s in r.steps),r.distance)
                    self.assertEqual(r.distance,align(b,a,transpose=transpose).distance)
                    self.assertTrue(0<=r.similarity<=1)
    def test_suggestions(self):
        self.assertEqual(suggest('cat',['cut','bat','cat','cat']),[(0,'cat'),(1,'bat'),(1,'cut')])
    def test_filters(self):
        self.assertEqual(suggest('cat',['cat','dog'],max_distance=0),[(0,'cat')])
        self.assertEqual(suggest('cat',['cat'],limit=0),[])
    def test_validation(self):
        for kw in [{'limit':-1},{'max_distance':-1}]:
            with self.assertRaises(ValueError):suggest('x',[],**kw)
    def test_compare_cli(self):
        out=io.StringIO()
        with contextlib.redirect_stdout(out):self.assertEqual(main(['compare','form','from','--transpose','--json']),0)
        self.assertEqual(json.loads(out.getvalue())['distance'],1)
    def test_suggest_cli(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'words.txt';p.write_text('cat\ncut\ncat\n',encoding='utf-8');out=io.StringIO()
            with contextlib.redirect_stdout(out):main(['suggest','cat',str(p),'--json'])
            self.assertEqual(len(json.loads(out.getvalue())),2)
    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as temp,contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as e:main(['suggest','cat',str(Path(temp)/'missing')])
            self.assertEqual(e.exception.code,2)

if __name__=='__main__':unittest.main()
