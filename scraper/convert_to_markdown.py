from markdownify import markdownify as md

def html_to_markdown(html_content):
    markdown_text = md(html_content, heading_style="ATX")
    return markdown_text

if __name__ == "__main__":
    sample_html = "<h2>Hello</h2><p>This is <strong>bold</strong> text with a <a href='https://example.com'>link</a>.</p>"
    result = html_to_markdown(sample_html)
    print(result)