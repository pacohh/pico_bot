from __future__ import annotations

from aiohttp_requests import requests
from imdb.parser.http.movieParser import DOMHTMLMovieParser


async def get_movie_details(movie_id: str) -> dict:
    res = await requests.session.get(f'https://www.imdb.com/title/{movie_id}/reference')
    res.raise_for_status()
    html = await res.text()
    parser = DOMHTMLMovieParser()
    data = parser.parse(html)
    return data['data']
