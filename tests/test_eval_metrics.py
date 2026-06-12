import pytest
from evaluation.eval import calculate_mrr, calculate_dcg, calculate_ndcg

class MockDoc:
    def __init__(self, content):
        self.page_content = content

def test_calculate_mrr_found_first():
    docs = [MockDoc("insurellm policy"), MockDoc("unrelated"), MockDoc("other")]
    assert calculate_mrr("insurellm", docs) == 1.0

def test_calculate_mrr_found_second():
    docs = [MockDoc("unrelated"), MockDoc("insurellm policy"), MockDoc("other")]
    assert calculate_mrr("insurellm", docs) == 0.5

def test_calculate_mrr_not_found():
    docs = [MockDoc("unrelated"), MockDoc("other")]
    assert calculate_mrr("insurellm", docs) == 0.0

def test_calculate_mrr_case_insensitive():
    docs = [MockDoc("InsureLLM policy")]
    assert calculate_mrr("insurellm", docs) == 1.0

def test_calculate_dcg():
    relevances = [1, 0, 1]
    # log2(2) = 1.0 -> 1/1 = 1.0
    # log2(3) = 1.585 -> 0/1.585 = 0.0
    # log2(4) = 2.0 -> 1/2 = 0.5
    # dcg = 1.0 + 0.0 + 0.5 = 1.5
    assert calculate_dcg(relevances, 3) == pytest.approx(1.5)

def test_calculate_ndcg_perfect():
    docs = [MockDoc("insurellm policy"), MockDoc("other"), MockDoc("other")]
    # keyword found at position 1. Relevances: [1, 0, 0]. Sorted ideal relevances: [1, 0, 0].
    # DCG = 1.0 / log2(2) = 1.0. IDCG = 1.0. nDCG = 1.0
    assert calculate_ndcg("insurellm", docs, k=3) == pytest.approx(1.0)

def test_calculate_ndcg_not_perfect():
    docs = [MockDoc("other"), MockDoc("insurellm policy"), MockDoc("other")]
    # keyword found at position 2. Relevances: [0, 1, 0]. Sorted ideal relevances: [1, 0, 0].
    # DCG = 1.0 / log2(3) = 0.63092975
    # IDCG = 1.0 / log2(2) = 1.0
    # nDCG = 0.63092975
    assert calculate_ndcg("insurellm", docs, k=3) == pytest.approx(0.63092975)

def test_calculate_ndcg_no_match():
    docs = [MockDoc("other"), MockDoc("other")]
    assert calculate_ndcg("insurellm", docs, k=2) == 0.0
