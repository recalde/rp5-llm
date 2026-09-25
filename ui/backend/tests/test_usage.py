from rp5_llm.usage import extract_usage


def test_json_usage_ignores_message_text():
    body = b'{"model":"demo","choices":[{"message":{"content":"secret reply"}}],"usage":{"prompt_tokens":4,"completion_tokens":9}}'
    assert extract_usage(body) == (4, 9)


def test_sse_usage_reads_the_last_event():
    body = (
        b'data: {"choices":[{"delta":{"content":"secret"}}],"usage":null}\n\n'
        b'data: {"usage":{"prompt_tokens":2,"completion_tokens":6}}\n\n'
        b"data: [DONE]\n"
    )
    assert extract_usage(body) == (2, 6)


def test_missing_usage_is_empty():
    assert extract_usage(b'{"choices":[]}') == (None, None)
