"""Unit tests for selab.diar.metrics (python -m selab.diar.tests_metrics)."""
import numpy as np
from .metrics import der, pyannote_der, cpwer, edit_distance


def close(a, b, tol=1e-3):
    assert abs(a - b) < tol, (a, b)


def merge(segs):
    """merge same-speaker overlaps (an RTTM never has a speaker overlapping itself)."""
    from .core import mask_to_segs
    from .metrics import _mat
    M, keys = _mat(segs, 7000)
    return [(a, b, k) for i, k in enumerate(keys) for a, b in mask_to_segs(M[:, i])]


def main():
    ref = [(0, 10, "A"), (10, 20, "B")]
    # perfect with renamed labels
    close(der(ref, [(0, 10, "x"), (10, 20, "y")])["der"], 0)
    # everything to one speaker -> 10 s confusion of 20
    close(der(ref, [(0, 20, "x")])["der"], 0.5)
    # missing half of B -> 5/20 miss
    d = der(ref, [(0, 10, "x"), (10, 15, "y")]); close(d["miss"], 0.25); close(d["der"], 0.25)
    # false alarm 5 s in silence
    d = der(ref, [(0, 10, "x"), (10, 20, "y"), (25, 30, "y")]); close(d["fa"], 0.25)
    # overlap: ref has 2 speakers 5-10, hyp only one -> miss 5 of 25 total ref
    ref2 = [(0, 10, "A"), (5, 20, "B")]
    d = der(ref2, [(0, 10, "x"), (10, 20, "y")]); close(d["der"], 5 / 25)
    # collar: boundary shifted by 0.2 s -> 0 with collar 0.25, >0 without
    hyp = [(0, 10.2, "x"), (10.2, 20, "y")]
    assert der(ref, hyp)["der"] > 0
    close(der(ref, hyp, collar=0.25)["der"], 0)
    # agreement with pyannote.metrics on random cases
    rng = np.random.default_rng(0)
    for _ in range(20):
        mk = lambda n, ks: [(a, a + rng.uniform(0.3, 4), rng.choice(ks)) for a in np.sort(rng.uniform(0, 60, n))]
        r = merge(mk(30, ["A", "B", "C"])); h = merge(mk(25, ["1", "2", "3", "4"]))
        for c in (0.0, 0.25):
            ours = der(r, h, collar=c)["der"]; pa = pyannote_der(r, h, collar=c)
            assert abs(ours - pa) < 0.02, (c, ours, pa)
    # edit distance
    assert edit_distance("a b c".split(), "a x c".split()) == 1
    assert edit_distance("a b c".split(), "a c".split()) == 1
    assert edit_distance("a b".split(), "a b c d".split()) == 2
    assert edit_distance([], ["a"]) == 1
    import jiwer
    for _ in range(50):
        r = list(rng.choice(list("abcde"), rng.integers(1, 15))); h = list(rng.choice(list("abcdef"), rng.integers(1, 15)))
        o = jiwer.process_words(" ".join(r), " ".join(h))
        assert edit_distance(r, h) == o.substitutions + o.deletions + o.insertions
    # cpWER: swapped labels -> 0; merged speakers -> errors
    R = {"A": "hello there".split(), "B": "good morning sir".split()}
    close(cpwer(R, {"1": "good morning sir".split(), "2": "hello there".split()})["cpwer"], 0)
    c = cpwer(R, {"1": "hello there good morning sir".split()})
    assert c["errors"] == 4, c   # B->1: 2 insertions; A unmatched: 2 deletions
    print("all metric tests passed")


if __name__ == "__main__":
    main()
