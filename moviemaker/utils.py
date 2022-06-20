import hashlib
import logging
import re
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)


def hashed(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def video_id_from_url(url: str) -> str:
    if '/shorts/' in url:
        match = re.search(r"/shorts/([\w\d_-]+)", url)
        if not match:
            raise ValueError(f"Invalid Youtube URL: {url}")
        return match.group(1)
    try:
        parsed_url = urlparse(url)
        parsed_query_string = parse_qs(parsed_url.query)
        # noinspection PyTypeChecker
        return parsed_query_string['v'][0]
    except (KeyError, IndexError, ValueError) as exc:
        raise ValueError(f"Invalid Youtube URL: {url}") from exc
