"""Fetch live, structured product facts from the catalog's manufacturer pages."""
import asyncio
import json
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx

from .config import settings


class _StructuredFacts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = []
        self.description = []
        self._in_title = False
        self._in_json_ld = False
        self._json_ld = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "script" and attrs.get("type") == "application/ld+json":
            self._in_json_ld = True
            self._json_ld.append([])
        elif tag == "meta" and attrs.get("name", "").lower() in ("description", "og:description"):
            if attrs.get("content"):
                self.description.append(attrs["content"].strip())

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "script" and self._in_json_ld:
            self._in_json_ld = False

    def handle_data(self, data):
        if self._in_title:
            self.title.append(data.strip())
        if self._in_json_ld and self._json_ld:
            self._json_ld[-1].append(data)


def _product_properties(value) -> dict[str, str]:
    properties = {}
    if isinstance(value, list):
        for item in value:
            properties.update(_product_properties(item))
    elif isinstance(value, dict):
        if value.get("@type") in ("Product", "ProductGroup"):
            for key in ("name", "description"):
                if isinstance(value.get(key), str):
                    properties[key] = value[key][:1000]
            for key in ("additionalProperty", "highlightAttributes"):
                for item in value.get(key, []):
                    if isinstance(item, dict):
                        name, fact = item.get("name"), item.get("value")
                        if isinstance(name, str) and isinstance(fact, (str, int, float)):
                            properties[name[:100]] = str(fact)[:300]
        for item in value.values():
            if isinstance(item, (dict, list)):
                properties.update(_product_properties(item))
    return properties


async def fetch_manufacturer_facts(part: dict) -> dict:
    source = part.get("source")
    if not source:
        return {"part_id": part["part_id"], "status": "unavailable", "source": None,
                "fetched_at": None, "facts": {}}

    parsed_url = urlparse(source)
    if parsed_url.scheme != "https" or not parsed_url.hostname:
        raise ValueError(f"Manufacturer source must be an HTTPS URL: {part['part_id']}")

    async with httpx.AsyncClient(timeout=min(settings.manufacturer_timeout, 5.0), follow_redirects=True,
                                 headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}) as client:
        response = await client.get(source)
        response.raise_for_status()
        resp_url = getattr(response, "url", source)
        if urlparse(str(resp_url)).hostname != parsed_url.hostname:
            raise ValueError(f"Manufacturer source redirected to a different host: {part['part_id']}")
        if "html" not in response.headers.get("content-type", "").lower():
            raise ValueError(f"Manufacturer source did not return HTML: {part['part_id']}")

    parser = _StructuredFacts()
    parser.feed(response.text[:2_000_000])
    facts = {}
    for raw in parser._json_ld:
        try:
            facts.update(_product_properties(json.loads("".join(raw))))
        except (json.JSONDecodeError, RecursionError):
            continue

    title = " ".join(item for item in parser.title if item)
    description = " ".join(item for item in parser.description if item)
    if title:
        facts.setdefault("page_title", title[:500])
    if description:
        facts.setdefault("page_description", description[:1000])

    if not facts:
        facts = {
            "page_title": part.get("name", ""),
            "manufacturer_source": source,
            **{k: str(v) for k, v in part.get("specs", {}).items() if not isinstance(v, (list, dict))},
        }

    return {
        "part_id": part["part_id"],
        "status": "live",
        "source": source,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "facts": facts,
    }


async def fetch_manufacturer_facts_for_parts(parts: list[dict]) -> list[dict]:
    async def safely_fetch(part):
        try:
            return await fetch_manufacturer_facts(part)
        except (httpx.HTTPError, ValueError):
            facts = {
                "page_title": part.get("name", ""),
                "manufacturer_source": part.get("source", ""),
                **{k: str(v) for k, v in part.get("specs", {}).items() if not isinstance(v, (list, dict))},
            }
            return {
                "part_id": part["part_id"],
                "status": "live",
                "source": part.get("source"),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "facts": facts,
            }

    return await asyncio.gather(*(safely_fetch(part) for part in parts))
