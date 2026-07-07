from __future__ import annotations

from urllib.parse import quote

import httpx

from tools.registry import aos_toolset

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
WIKIPEDIA_REST = "https://en.wikipedia.org/api/rest_v1/page/summary"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"

MATH_PROPERTY_IDS = ("P2534", "P1096", "P2812")

# Wikimedia rejects generic/anonymous User-Agents with 403s (see
# https://meta.wikimedia.org/wiki/User-Agent_policy) — a descriptive UA with
# contact info is required for API access.
USER_AGENT = "AOS-LectureBot/1.0 (educational Manim lecture generator; https://github.com/AOS)"
REQUEST_HEADERS = {"User-Agent": USER_AGENT}


async def fetch_wikipedia(query: str) -> str:
    """Fetch a Wikipedia summary for *query*; returns formatted text."""
    query = query.strip()
    if not query:
        return "Error: empty Wikipedia query."

    async with httpx.AsyncClient(timeout=15.0, headers=REQUEST_HEADERS) as client:
        search_resp = await client.get(
            WIKIPEDIA_API,
            params={
                "action": "opensearch",
                "search": query,
                "limit": 1,
                "namespace": 0,
                "format": "json",
            },
        )
        search_resp.raise_for_status()
        titles = search_resp.json()[1]
        if not titles:
            return f"Error: no Wikipedia page found for {query!r}."

        title = titles[0]
        summary_resp = await client.get(f"{WIKIPEDIA_REST}/{quote(title, safe='')}")
        if summary_resp.status_code == 404:
            return f"Error: Wikipedia page {title!r} not found."

        summary_resp.raise_for_status()
        data = summary_resp.json()

    extract = data.get("extract", "")
    description = data.get("description", "")
    parts = [f"Title: {data.get('title', title)}"]
    if description:
        parts.append(f"Description: {description}")
    if extract:
        parts.append(f"Extract: {extract}")
    return "\n".join(parts)


async def fetch_wikidata(query: str) -> str:
    """Fetch Wikidata entity info for *query*; returns formatted text."""
    query = query.strip()
    if not query:
        return "Error: empty Wikidata query."

    async with httpx.AsyncClient(timeout=15.0, headers=REQUEST_HEADERS) as client:
        search_resp = await client.get(
            WIKIDATA_API,
            params={
                "action": "wbsearchentities",
                "search": query,
                "language": "en",
                "limit": 1,
                "format": "json",
            },
        )
        search_resp.raise_for_status()
        hits = search_resp.json().get("search", [])
        if not hits:
            return f"Error: no Wikidata entity found for {query!r}."

        entity_id = hits[0]["id"]
        entity_resp = await client.get(
            WIKIDATA_API,
            params={
                "action": "wbgetentities",
                "ids": entity_id,
                "props": "labels|descriptions|claims",
                "languages": "en",
                "format": "json",
            },
        )
        entity_resp.raise_for_status()
        entity = entity_resp.json()["entities"][entity_id]

    label = entity.get("labels", {}).get("en", {}).get("value", entity_id)
    description = entity.get("descriptions", {}).get("en", {}).get("value", "")
    parts = [f"Entity: {label} ({entity_id})"]
    if description:
        parts.append(f"Description: {description}")

    claims = entity.get("claims", {})
    for prop_id in MATH_PROPERTY_IDS:
        for claim in claims.get(prop_id, []):
            try:
                value = claim["mainsnak"]["datavalue"]["value"]
                if isinstance(value, str):
                    parts.append(f"Formula ({prop_id}): {value}")
                elif isinstance(value, dict) and "text" in value:
                    parts.append(f"Formula ({prop_id}): {value['text']}")
            except (KeyError, TypeError):
                continue

    return "\n".join(parts) if parts else f"Entity: {label} ({entity_id})"


@aos_toolset.tool_plain
async def search_wikipedia(query: str) -> str:
    """Search Wikipedia and return title, description, and extract for a query."""
    return await fetch_wikipedia(query)


@aos_toolset.tool_plain
async def search_wikidata(query: str) -> str:
    """Search Wikidata and return label, description, and any formula properties."""
    return await fetch_wikidata(query)
