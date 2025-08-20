import aiohttp
from aiohttp_requests import requests


KAPPA_URL = 'https://kappa.lol/api/upload'


async def upload_image(image_url: str) -> str:
    """Upload image to kappa.lol."""
    res = await requests.session.get(image_url)
    image_data = await res.content.read()

    data = aiohttp.FormData()
    data.add_field('file', image_data, content_type=res.content_type)

    res = await requests.session.post(KAPPA_URL, data=data)
    res.raise_for_status()
    data = await res.json()
    return data['link']
