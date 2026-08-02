"""Plain assert-based smoke checks — no framework, no API key/DB needed. Run: python -m tests.test_context_store"""

from app.context_store import _cosine


def test_cosine_identical_vectors():
    assert _cosine([1.0, 0.0], [1.0, 0.0]) == 1.0


def test_cosine_orthogonal_vectors():
    assert _cosine([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_cosine_zero_vector():
    assert _cosine([0.0, 0.0], [1.0, 0.0]) == 0.0


if __name__ == "__main__":
    test_cosine_identical_vectors()
    test_cosine_orthogonal_vectors()
    test_cosine_zero_vector()
    print("ok")
