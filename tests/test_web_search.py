from app.web_search import clean_html, parse_serpapi_results, unwrap_duckduckgo_url


def test_clean_html_strips_tags_and_entities():
    assert clean_html("<b>PostgreSQL</b> &amp; news") == "PostgreSQL & news"


def test_unwrap_duckduckgo_url_returns_target():
    wrapped = "//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.postgresql.org%2Fabout%2Fnews%2F"

    assert unwrap_duckduckgo_url(wrapped) == "https://www.postgresql.org/about/news/"


def test_parse_serpapi_results_uses_answer_box_and_organic_results():
    payload = {
        "answer_box": {"title": "PostgreSQL", "link": "https://postgresql.org", "answer": "PostgreSQL 18 is current."},
        "organic_results": [
            {"title": "Postgres Weekly", "link": "https://postgresweekly.com", "snippet": "Latest Postgres news."}
        ],
    }

    results = parse_serpapi_results(payload, max_results=5)

    assert results == [
        {"title": "PostgreSQL", "url": "https://postgresql.org", "snippet": "PostgreSQL 18 is current."},
        {"title": "Postgres Weekly", "url": "https://postgresweekly.com", "snippet": "Latest Postgres news."},
    ]
