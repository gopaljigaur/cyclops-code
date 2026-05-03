import html.parser
import re
from typing import Optional

import httpx

from cyclops import BaseTool

_MAX_CHARS = 8000
_TIMEOUT = 15.0


class _TextExtractor(html.parser.HTMLParser):
    _SKIP_TAGS = {"script", "style", "noscript", "head"}

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() in self._SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            stripped = data.strip()
            if stripped:
                self._parts.append(stripped)

    def text(self) -> str:
        return "\n".join(self._parts)


def _html_to_text(html_content: str) -> str:
    extractor = _TextExtractor()
    extractor.feed(html_content)
    text = extractor.text()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class WebFetchTool(BaseTool):
    def __init__(self) -> None:
        super().__init__(
            name="WebFetch",
            description="Fetch content from a URL and return as plain text.",
        )

    async def execute(self, url: str) -> str:
        try:
            async with httpx.AsyncClient(
                timeout=_TIMEOUT,
                follow_redirects=True,
                headers={"User-Agent": "cyclops-code/0.1.0"},
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
        except httpx.TimeoutException:
            return f"Error: request to {url} timed out after {int(_TIMEOUT)}s"
        except httpx.HTTPStatusError as e:
            return f"Error: HTTP {e.response.status_code} from {url}"
        except httpx.RequestError as e:
            return f"Error fetching {url}: {e}"

        content_type = response.headers.get("content-type", "")
        raw = response.text

        if "html" in content_type.lower():
            text = _html_to_text(raw)
        else:
            text = raw.strip()

        if len(text) > _MAX_CHARS:
            text = text[:_MAX_CHARS] + f"\n\n[Truncated: showing {_MAX_CHARS} of {len(text)} chars]"

        return f"[{url}]\n\n{text}"
