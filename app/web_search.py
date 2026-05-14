from urllib.parse import quote_plus
from urllib.parse import parse_qs, unquote, urlparse
import html
import re

import httpx


async def search_web(query: str, max_results: int = 5, serpapi_api_key: str = "") -> list[dict]:
    if serpapi_api_key.strip():
        try:
            results = await search_serpapi(query, serpapi_api_key, max_results)
            if results:
                return results
        except httpx.HTTPError:
            pass

    url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1&skip_disambig=1"
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url)
        response.raise_for_status()
        payload = response.json()

    results: list[dict] = []
    abstract = payload.get("AbstractText")
    abstract_url = payload.get("AbstractURL")
    if abstract:
        results.append({"title": payload.get("Heading") or "DuckDuckGo result", "url": abstract_url, "snippet": abstract})

    for topic in payload.get("RelatedTopics", []):
        if len(results) >= max_results:
            break
        if "Topics" in topic:
            for nested in topic["Topics"]:
                if len(results) >= max_results:
                    break
                text = nested.get("Text")
                if text:
                    results.append({"title": text.split(" - ", 1)[0], "url": nested.get("FirstURL"), "snippet": text})
            continue

        text = topic.get("Text")
        if text:
            results.append({"title": text.split(" - ", 1)[0], "url": topic.get("FirstURL"), "snippet": text})

    if len(results) >= max_results:
        return results[:max_results]

    html_results = await search_duckduckgo_html(query, max_results - len(results))
    results.extend(html_results)
    return results[:max_results]


async def search_serpapi(query: str, api_key: str, max_results: int) -> list[dict]:
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            "https://serpapi.com/search.json",
            params={
                "engine": "google",
                "q": query,
                "api_key": api_key,
                "num": max_results,
            },
        )
        response.raise_for_status()
        payload = response.json()

    return parse_serpapi_results(payload, max_results)


def parse_serpapi_results(payload: dict, max_results: int) -> list[dict]:
    results: list[dict] = []
    answer_box = payload.get("answer_box") or {}
    answer = answer_box.get("answer") or answer_box.get("snippet") or answer_box.get("description")
    if answer:
        results.append(
            {
                "title": answer_box.get("title") or "Google answer",
                "url": answer_box.get("link"),
                "snippet": answer,
            }
        )

    for item in payload.get("organic_results", []):
        if len(results) >= max_results:
            break

        snippet = item.get("snippet") or item.get("snippet_highlighted_words") or ""
        if isinstance(snippet, list):
            snippet = " ".join(str(value) for value in snippet)

        title = item.get("title")
        if title or snippet:
            results.append({"title": title or "Google result", "url": item.get("link"), "snippet": snippet})

    return results[:max_results]


async def search_duckduckgo_html(query: str, max_results: int) -> list[dict]:
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    async with httpx.AsyncClient(timeout=10, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}) as client:
        response = await client.get(url)
        response.raise_for_status()
        page = response.text

    title_matches = list(
        re.finditer(r'<a rel="nofollow" class="result__a" href="([^"]+)">(.*?)</a>', page, flags=re.DOTALL)
    )
    snippet_matches = list(
        re.finditer(r'<a class="result__snippet"[^>]*>(.*?)</a>', page, flags=re.DOTALL)
    )
    results: list[dict] = []
    for index, title_match in enumerate(title_matches[:max_results]):
        title = clean_html(title_match.group(2))
        snippet = clean_html(snippet_matches[index].group(1)) if index < len(snippet_matches) else ""
        results.append({"title": title, "url": unwrap_duckduckgo_url(title_match.group(1)), "snippet": snippet})

    return results


def clean_html(value: str) -> str:
    return html.unescape(re.sub(r"<.*?>", "", value, flags=re.DOTALL)).strip()


def unwrap_duckduckgo_url(value: str) -> str:
    decoded = html.unescape(value)
    if decoded.startswith("//"):
        decoded = f"https:{decoded}"
    parsed = urlparse(decoded)
    target = parse_qs(parsed.query).get("uddg", [""])[0]
    return unquote(target) if target else decoded
