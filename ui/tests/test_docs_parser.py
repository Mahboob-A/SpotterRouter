from ui.docs_parser import parse_markdown


def test_parse_markdown_headings() -> None:
    raw = """
# System Architecture
## Layer Isolation
### Domain Entities
"""
    parsed = parse_markdown(raw)
    assert '<h1 id="system-architecture"' in parsed.html_content
    assert '<h2 id="layer-isolation"' in parsed.html_content
    assert '<h3 id="domain-entities"' in parsed.html_content
    assert len(parsed.table_of_contents) == 3
    assert parsed.table_of_contents[0].title == "System Architecture"
    assert parsed.table_of_contents[0].level == 1


def test_parse_markdown_inline_formatting() -> None:
    raw = (
        "This has **bold text**, *italic text*, and `code element` plus "
        "[Link Label](https://example.com)."
    )
    parsed = parse_markdown(raw)
    assert "<strong>bold text</strong>" in parsed.html_content
    assert "<em>italic text</em>" in parsed.html_content
    assert "<code>code element</code>" in parsed.html_content
    assert '<a href="https://example.com"' in parsed.html_content


def test_parse_markdown_xss_protection() -> None:
    raw = "<script>alert('xss')</script> and [Bad](javascript:alert(1))"
    parsed = parse_markdown(raw)
    assert "<script>" not in parsed.html_content
    assert "&lt;script&gt;" in parsed.html_content
    assert "javascript:" not in parsed.html_content


def test_parse_markdown_code_block() -> None:
    raw = """```python
def calculate_fuel():
    return 10
```"""
    parsed = parse_markdown(raw)
    assert '<div class="doc-code-block" data-lang="python">' in parsed.html_content
    expected_code = (
        '<code class="language-python">def calculate_fuel():\n'
        '    return 10</code>'
    )
    assert expected_code in parsed.html_content


def test_parse_markdown_callout() -> None:
    raw = "> Important: Never block the main HTTP request for LLM calls."
    parsed = parse_markdown(raw)
    assert 'class="doc-callout doc-callout-important"' in parsed.html_content
    assert '<span class="doc-callout-badge">Important</span>' in parsed.html_content
    assert "Never block the main HTTP request" in parsed.html_content


def test_parse_markdown_table() -> None:
    raw = """
| Metric | Baseline | Optimized |
|---|---|---|
| Query Time | 850ms | 14ms |
| Memory | 64MB | 8MB |
"""
    parsed = parse_markdown(raw)
    assert '<table class="doc-table">' in parsed.html_content
    assert "<th>Metric</th>" in parsed.html_content
    assert "<td>850ms</td>" in parsed.html_content
    assert "<td>14ms</td>" in parsed.html_content


def test_parse_markdown_lists() -> None:
    raw = """
- Item Alpha
- Item Beta

1. Step One
2. Step Two
"""
    parsed = parse_markdown(raw)
    assert '<ul class="doc-list">' in parsed.html_content
    assert "<li>Item Alpha</li>" in parsed.html_content
    assert '<ol class="doc-list">' in parsed.html_content
    assert "<li>Step One</li>" in parsed.html_content
