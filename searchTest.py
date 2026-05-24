import requests
from bs4 import BeautifulSoup
import urllib.parse


def search_duckduckgo(query, max_results=5):
    url = "https://html.duckduckgo.com/html/"
    params = {"q": query}
    headers = {
        "User-Agent": "OperonAgent/0.1"
    }

    resp = requests.post(
        url,
        data=params,
        headers=headers,
        timeout=10,
    )

    if resp.status_code != 200:
        return {
            "ok": False,
            "error": f"HTTP {resp.status_code}"
        }

    soup = BeautifulSoup(resp.text, "html.parser")

    results = []

    for a in soup.select("a.result__a")[:max_results]:
        title = a.get_text(strip=True)
        link = a.get("href", "")

        # unwrap duckduckgo redirect
        if "uddg=" in link:
            link = urllib.parse.unquote(
                link.split("uddg=")[1]
            )

        result_div = a.find_parent("div", class_="result")

        snippet = ""

        if result_div:
            snippet_tag = result_div.select_one(
                ".result__snippet"
            )

            if snippet_tag:
                snippet = snippet_tag.get_text(
                    " ",
                    strip=True
                )

        results.append({
            "title": title,
            "snippet": snippet,
            "url": link,
        })

    return {
        "ok": True,
        "results": results,
    }


def search_engine_tool(data):
    return {
        "type": "Result",
        "data": search_duckduckgo(
            query=data["query"],
            max_results=data.get("max_results", 5),
        )
    }


if __name__ == "__main__":
    result = search_engine_tool({
        "query": "python requests tutorial",
        "max_results": 3,
    })

    from pprint import pprint
    pprint(result)