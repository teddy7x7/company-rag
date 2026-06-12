from utils.answer import merge_chunks, Result

def test_merge_chunks_no_overlap():
    chunks = [
        Result(page_content="chunk A", metadata={"source": "A", "type": "info"}),
        Result(page_content="chunk B", metadata={"source": "B", "type": "info"}),
    ]
    reranked = [
        Result(page_content="chunk C", metadata={"source": "C", "type": "info"}),
    ]
    merged = merge_chunks(chunks, reranked)
    assert len(merged) == 3
    assert [c.page_content for c in merged] == ["chunk A", "chunk B", "chunk C"]

def test_merge_chunks_with_overlap():
    chunks = [
        Result(page_content="chunk A", metadata={"source": "A", "type": "info"}),
        Result(page_content="chunk B", metadata={"source": "B", "type": "info"}),
    ]
    reranked = [
        Result(page_content="chunk B", metadata={"source": "B", "type": "info"}),
        Result(page_content="chunk C", metadata={"source": "C", "type": "info"}),
    ]
    merged = merge_chunks(chunks, reranked)
    assert len(merged) == 3
    assert [c.page_content for c in merged] == ["chunk A", "chunk B", "chunk C"]

def test_merge_chunks_all_overlap():
    chunks = [
        Result(page_content="chunk A", metadata={"source": "A", "type": "info"}),
    ]
    reranked = [
        Result(page_content="chunk A", metadata={"source": "A", "type": "info"}),
    ]
    merged = merge_chunks(chunks, reranked)
    assert len(merged) == 1
    assert merged[0].page_content == "chunk A"
