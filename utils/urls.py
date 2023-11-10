from __future__ import annotations
import re
from urllib.parse import urlparse


URL_RE = re.compile(r'https?://[^\s]+')


def get_domain(url: str) -> str:
    domain = urlparse(url).netloc
    return domain


def extract_urls(text: str) -> list[str]:
    matches = URL_RE.findall(text)
    return matches


def expand_tenor_url(url: str) -> str:
    if is_tenor_url(url):
        return f'{url}.gif'
    else:
        return url


def is_tenor_url(url: str) -> bool:
    return url.startswith('https://tenor.com/view/')
