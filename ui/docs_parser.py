import html
import re
from typing import NamedTuple


class TocItem(NamedTuple):
    level: int
    title: str
    slug: str


class ParsedDocument(NamedTuple):
    html_content: str
    table_of_contents: list[TocItem]


def _slugify(text: str) -> str:
    """Generate clean URL slug for heading anchors."""
    cleaned = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    return re.sub(r"[-\s]+", "-", cleaned) or "section"


def _format_inline(text: str) -> str:
    """Format inline markdown elements: bold, italic, code, and links.
    Text must already be HTML-escaped.
    """
    # Inline code: `code`
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)

    # Bold: **bold**
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)

    # Italic: *italic* or _italic_
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"(?<!_)_([^_]+)_(?!_)", r"<em>\1</em>", text)

    # Links: [text](url)
    def _link_replacer(match: re.Match[str]) -> str:
        label = match.group(1)
        url = match.group(2)
        if url.strip().lower().startswith("javascript:"):
            return label
        return (
            f'<a href="{url}" class="doc-link" target="_blank" '
            f'rel="noopener noreferrer">{label}</a>'
        )

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _link_replacer, text)
    return text


def parse_markdown(raw_markdown: str) -> ParsedDocument:
    """Parse Markdown text into safe, semantic HTML with table of contents.
    Requires no third-party dependencies.
    """
    lines = raw_markdown.splitlines()
    output_html: list[str] = []
    toc: list[TocItem] = []

    i = 0
    num_lines = len(lines)

    in_code_block = False
    code_block_lang = ""
    code_block_lines: list[str] = []

    in_list: str | None = None  # "ul" or "ol"
    list_items: list[str] = []

    def flush_list() -> None:
        nonlocal in_list, list_items
        if in_list and list_items:
            output_html.append(f'<{in_list} class="doc-list">')
            for item in list_items:
                output_html.append(f"  <li>{_format_inline(item)}</li>")
            output_html.append(f"</{in_list}>")
        in_list = None
        list_items = []

    while i < num_lines:
        line = lines[i]
        stripped = line.strip()

        # Handle fenced code blocks
        if stripped.startswith("```"):
            if in_code_block:
                flush_list()
                code_content = html.escape("\n".join(code_block_lines))
                lang_display = code_block_lang or "text"
                safe_lang = html.escape(lang_display)
                output_html.append(
                    f'<div class="doc-code-block" data-lang="{safe_lang}">'
                    f'  <div class="doc-code-header">'
                    f'    <span class="doc-code-lang">{safe_lang}</span>'
                    f'    <button type="button" class="doc-copy-btn" '
                    f'onclick="copyDocCode(this)">Copy</button>'
                    f"  </div>"
                    f'  <pre><code class="language-{safe_lang}">'
                    f"{code_content}</code></pre>"
                    f"</div>"
                )
                in_code_block = False
                code_block_lang = ""
                code_block_lines = []
                i += 1
                continue
            else:
                flush_list()
                in_code_block = True
                code_block_lang = stripped[3:].strip().lower()
                code_block_lines = []
                i += 1
                continue

        if in_code_block:
            code_block_lines.append(line)
            i += 1
            continue

        # Blank line breaks lists and paragraphs
        if not stripped:
            flush_list()
            i += 1
            continue

        # Horizontal rule: --- or *** or ___
        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", stripped):
            flush_list()
            output_html.append('<hr class="doc-divider">')
            i += 1
            continue

        # Headings: #, ##, ###, ####
        heading_match = re.match(r"^(#{1,4})\s+(.+)$", stripped)
        if heading_match:
            flush_list()
            level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()
            heading_slug = _slugify(heading_text)
            toc.append(TocItem(level=level, title=heading_text, slug=heading_slug))
            safe_text = _format_inline(html.escape(heading_text))
            output_html.append(
                f'<h{level} id="{heading_slug}" class="doc-heading '
                f'doc-heading-{level}">'
                f'  <a href="#{heading_slug}" class="doc-heading-anchor" '
                f'aria-hidden="true">#</a>'
                f"  <span>{safe_text}</span>"
                f"</h{level}>"
            )
            i += 1
            continue

        # Callout blockquotes: > Note: ..., > Tip: ..., > Warning: ..., > Important: ...
        if stripped.startswith(">"):
            flush_list()
            quote_lines: list[str] = []
            while i < num_lines and lines[i].strip().startswith(">"):
                quote_lines.append(lines[i].strip()[1:].strip())
                i += 1

            combined_quote = " ".join(quote_lines)
            callout_type = "note"
            callout_title = "Note"
            body_text = combined_quote

            callout_pattern = (
                r"^(Note|Tip|Warning|Important|Caution):\s*(.*)$"
            )
            callout_match = re.match(
                callout_pattern, combined_quote, re.IGNORECASE
            )
            if callout_match:
                callout_type = callout_match.group(1).lower()
                callout_title = callout_match.group(1).capitalize()
                body_text = callout_match.group(2)

            safe_body = _format_inline(html.escape(body_text))
            output_html.append(
                f'<div class="doc-callout doc-callout-{callout_type}">'
                f'  <div class="doc-callout-header">'
                f'    <span class="doc-callout-badge">'
                f"{html.escape(callout_title)}</span>"
                f"  </div>"
                f'  <div class="doc-callout-body">{safe_body}</div>'
                f"</div>"
            )
            continue

        # Tables: begins with | and ends with |
        if stripped.startswith("|") and stripped.endswith("|"):
            flush_list()
            table_lines: list[str] = []
            while i < num_lines:
                curr_s = lines[i].strip()
                if curr_s.startswith("|") and curr_s.endswith("|"):
                    table_lines.append(curr_s)
                    i += 1
                else:
                    break

            if len(table_lines) >= 2:
                header_cols = [
                    c.strip() for c in table_lines[0].strip("|").split("|")
                ]
                has_separator = re.match(
                    r"^\|?\s*[-:]+[-| :]*\s*\|?$", table_lines[1]
                )
                row_start = 2 if has_separator else 1

                rows: list[list[str]] = []
                for r_line in table_lines[row_start:]:
                    rows.append(
                        [c.strip() for c in r_line.strip("|").split("|")]
                    )

                table_html = [
                    '<div class="doc-table-wrapper">'
                    '<table class="doc-table"><thead><tr>'
                ]
                for hc in header_cols:
                    table_html.append(
                        f"<th>{_format_inline(html.escape(hc))}</th>"
                    )
                table_html.append("</tr></thead><tbody>")
                for row in rows:
                    table_html.append("<tr>")
                    for cell in row:
                        table_html.append(
                            f"<td>{_format_inline(html.escape(cell))}</td>"
                        )
                    table_html.append("</tr>")
                table_html.append("</tbody></table></div>")
                output_html.append("".join(table_html))
            continue

        # Unordered list: - item or * item
        ul_match = re.match(r"^[-*]\s+(.+)$", stripped)
        if ul_match:
            if in_list != "ul":
                flush_list()
                in_list = "ul"
            list_items.append(ul_match.group(1))
            i += 1
            continue

        # Ordered list: 1. item
        ol_match = re.match(r"^\d+\.\s+(.+)$", stripped)
        if ol_match:
            if in_list != "ol":
                flush_list()
                in_list = "ol"
            list_items.append(ol_match.group(1))
            i += 1
            continue

        # Paragraph text: gather lines until blank line or special block
        flush_list()
        para_lines: list[str] = []
        while i < num_lines:
            cur_line = lines[i]
            cur_strip = cur_line.strip()
            if not cur_strip:
                break
            if (
                cur_strip.startswith("```")
                or cur_strip.startswith("#")
                or cur_strip.startswith(">")
                or (cur_strip.startswith("|") and cur_strip.endswith("|"))
                or re.match(r"^[-*]\s+", cur_strip)
                or re.match(r"^\d+\.\s+", cur_strip)
                or re.match(r"^(-{3,}|\*{3,}|_{3,})$", cur_strip)
            ):
                break
            para_lines.append(cur_strip)
            i += 1

        if para_lines:
            combined_para = " ".join(para_lines)
            safe_para = _format_inline(html.escape(combined_para))
            output_html.append(f'<p class="doc-paragraph">{safe_para}</p>')

    flush_list()
    return ParsedDocument(
        html_content="\n".join(output_html),
        table_of_contents=toc,
    )
