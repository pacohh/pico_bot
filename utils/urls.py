from urllib.parse import urlparse


def get_domain(url: str) -> str:
    domain = urlparse(url).netloc
    return domain
