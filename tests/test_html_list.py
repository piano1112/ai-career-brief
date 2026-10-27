from app.agents.background.collectors.html_list import extract_links, path_prefix_counts

PAGE = """
<nav><a href="/news/product">Product</a><a href="/about">About us page link</a></nav>
<a href="/news/first-post"><img src="x.png"></a>
<a href="/news/first-post?ref=home"><h3>First post about something</h3><p>Long summary...</p></a>
<a href="https://other.com/news/external-post">External post with a long title</a>
<a href="/news/second-post">A long summary paragraph that is not the real title of the post</a>
<a href="/news/second-post"><h3>Second post with a long enough title</h3></a>
<a href="/news/a/b">Nested path that should not match the pattern</a>
"""


def test_extract_links_filters_and_dedupes() -> None:
    links = extract_links(PAGE, "https://example.com/news", r"^/news/[^/]+$")
    assert [(link.url, link.title) for link in links] == [
        ("https://example.com/news/first-post", "First post about something"),
        ("https://example.com/news/second-post", "Second post with a long enough title"),
    ]


def test_path_prefix_counts() -> None:
    counts = dict(path_prefix_counts(PAGE, "https://example.com/news"))
    assert counts["/news/first-post"] == 2
    assert "/about" in counts
