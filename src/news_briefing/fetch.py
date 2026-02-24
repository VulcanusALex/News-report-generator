from __future__ import annotations

import os
from typing import Any

import requests


DEFAULT_TIMEOUT = 15


def fetch_text(url: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    resp = requests.get(url, timeout=timeout, headers={"User-Agent": "milan-brief-bot/1.0"})
    resp.raise_for_status()
    return resp.text


def fetch_json(url: str, timeout: int = DEFAULT_TIMEOUT) -> Any:
    resp = requests.get(url, timeout=timeout, headers={"User-Agent": "milan-brief-bot/1.0"})
    resp.raise_for_status()
    return resp.json()


def fetch_web_search(query: str, count: int = 10, country: str = "IT") -> list[dict[str, Any]]:
    """
    Fetch search results using Brave Search API.
    
    Args:
        query: Search query string
        count: Number of results to return (max 10)
        country: Country code for regional results
    
    Returns:
        List of search result dictionaries with title, url, description
    """
    api_key = os.environ.get("BRAVE_API_KEY") or os.environ.get("BAIDU_API_KEY")
    
    # Fallback: use a simple approach with DuckDuckGo or similar
    # For production, configure BRAVE_API_KEY in environment
    if not api_key:
        # Use DuckDuckGo HTML as fallback (no API key needed)
        return _fetch_ddg_search(query, count)
    
    # Brave Search API
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": api_key,
    }
    params = {
        "q": query,
        "count": min(count, 10),
        "country": country,
    }
    
    resp = requests.get(url, headers=headers, params=params, timeout=DEFAULT_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    
    results = []
    for item in data.get("web", {}).get("results", []):
        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "description": item.get("description", ""),
        })
    return results


def _fetch_ddg_search(query: str, count: int) -> list[dict[str, Any]]:
    """
    Fallback: Use DuckDuckGo HTML search (no API key required).
    """
    from bs4 import BeautifulSoup
    
    url = "https://html.duckduckgo.com/html/"
    data = {"q": query, "b": f"{count}"}
    
    resp = requests.post(url, data=data, timeout=DEFAULT_TIMEOUT, headers={"User-Agent": "milan-brief-bot/1.0"})
    resp.raise_for_status()
    
    soup = BeautifulSoup(resp.text, "html.parser")
    results = []
    
    for result in soup.select(".result"):
        title_elem = result.select_one(".result__title")
        link_elem = result.select_one(".result__url")
        snippet_elem = result.select_one(".result__snippet")
        
        if title_elem and link_elem:
            results.append({
                "title": title_elem.get_text(strip=True),
                "url": link_elem.get_text(strip=True),
                "description": snippet_elem.get_text(strip=True) if snippet_elem else "",
            })
            if len(results) >= count:
                break
    
    return results
