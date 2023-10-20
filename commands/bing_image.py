from __future__ import annotations

import asyncio
import io
import logging
import random
import re

import discord
import httpx
import regex
import requests.utils as requests_utils
from aiohttp_requests import requests

from commands.base import BaseCommand
from utils import env

BING_AUTH_COOKIE = env.require('BING_AUTH_COOKIE')

logger = logging.getLogger(__name__)


class GenerateImageCommand(BaseCommand):
    re_command = re.compile(r'^!(img|image|imagine)\b')
    allow_pm = False

    async def handle(self, message, response_channel):
        parts = message.content.split()
        if len(parts) <= 1:
            return await response_channel.send(content='Missing prompt')
        if len(parts) <= 3:
            return await response_channel.send(content='Add more detail to your prompt')
        prompt = ' '.join(parts[1:])

        logger.info('Image generation for %s with prompt: %s', message.author, prompt)

        is_dm = isinstance(response_channel, discord.DMChannel)
        loading = None
        if is_dm:
            await response_channel.typing()
        else:
            loading = await response_channel.send('<a:loading:1085904578798694410>')

        try:
            gen = ImageGenAsync(BING_AUTH_COOKIE)
            polling_endpoint, wait_time, token_left = await self.submit_image_request(gen, prompt)
        except Exception as exc:
            if loading:
                await response_channel.delete_messages([loading])
            response = await response_channel.send(f'Error: {exc.args[0]}', reference=message)
            return response

        if wait_time and loading:
            await loading.edit(content=f'<a:loading:1085904578798694410> ({wait_time})')

        images = await self.poll_images(gen, polling_endpoint)

        if loading:
            await response_channel.delete_messages([loading])
        response = await response_channel.send(
            content=f'🎟️ {token_left} tokens left',
            files=[discord.File(image, filename='image.png') for image in images],
            reference=message,
        )
        for image in images:
            image.close()
        return response

    @staticmethod
    async def submit_image_request(gen: ImageGenAsync, prompt: str) -> tuple[str, str, str]:
        return await gen.submit_image_request(prompt)

    @staticmethod
    async def poll_images(gen: ImageGenAsync, polling_endpoint: str) -> list[io.BytesIO]:
        urls = await gen.poll_images(polling_endpoint)
        images = []
        for url in urls:
            res = await requests.session.get(url)
            data = await res.content.read()
            image = io.BytesIO(data)
            images.append(image)
        return images


class ImageGenAsync:
    """
    Image generation by Microsoft Bing
    Parameters:
        auth_cookie: str
    Optional Parameters:
        debug_file: str
        quiet: bool
        all_cookies: list[dict]
    """

    BING_URL = "https://www.bing.com"
    # Generate random IP between range 13.104.0.0/14
    FORWARDED_IP = (
        f"13.{random.randint(104, 107)}.{random.randint(0, 255)}.{random.randint(0, 255)}"
    )
    HEADERS = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "en-US,en;q=0.9",
        "cache-control": "max-age=0",
        "content-type": "application/x-www-form-urlencoded",
        "referrer": "https://www.bing.com/images/create/",
        "origin": "https://www.bing.com",
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36 Edg/110.0.1587.63",
        "x-forwarded-for": FORWARDED_IP,
    }
    WAIT_RE = re.compile(r'gi_rmtime">([^<]+)<')
    TOKEN_RE = re.compile(r'id="token_bal".+?>(\d+)<')

    def __init__(
        self,
        auth_cookie: str = None,
        all_cookies: list[dict] = None,
    ) -> None:
        if auth_cookie is None and not all_cookies:
            raise Exception("No auth cookie provided")
        self.session = httpx.AsyncClient(
            headers=self.HEADERS,
            trust_env=True,
        )
        if auth_cookie:
            self.session.cookies.update({"_U": auth_cookie})
        if all_cookies:
            for cookie in all_cookies:
                self.session.cookies.update(
                    {cookie["name"]: cookie["value"]},
                )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *excinfo) -> None:
        await self.session.aclose()

    async def submit_image_request(self, prompt: str) -> tuple[str, str, str]:
        """
        Fetches image links from Bing
        Parameters:
            prompt: str
        """
        url_encoded_prompt = requests_utils.quote(prompt)
        # https://www.bing.com/images/create?q=<PROMPT>&rt=3&FORM=GENCRE
        url = f"{self.BING_URL}/images/create?q={url_encoded_prompt}&rt=4&FORM=GENCRE"
        payload = f"q={url_encoded_prompt}&qs=ds"
        response = await self.session.post(
            url,
            follow_redirects=False,
            data=payload,
        )
        content = response.text
        if "this prompt has been blocked" in content.lower():
            raise Exception(
                "Your prompt has been blocked by Bing. Try to change any bad words and try again.",
            )
        if response.status_code != 302:
            # if rt4 fails, try rt3
            url = f"{self.BING_URL}/images/create?q={url_encoded_prompt}&rt=3&FORM=GENCRE"
            response = await self.session.post(
                url,
                follow_redirects=False,
                timeout=200,
            )
            if response.status_code != 302:
                print(f"ERROR: {response.text}")
                raise Exception("Redirect failed")

        # Get redirect URL
        redirect_url = response.headers["Location"].replace("&nfy=1", "")
        request_id = redirect_url.split("id=")[-1]
        response = await self.session.get(f"{self.BING_URL}{redirect_url}")
        content = response.content.decode()
        # Get metadata
        wait_time = self.WAIT_RE.search(content)
        token_left = self.TOKEN_RE.search(content)
        wait_time = wait_time.group(1) if wait_time else ''
        token_left = token_left.group(1) if token_left else ''
        polling_endpoint = f"images/create/async/results/{request_id}?q={url_encoded_prompt}"
        return polling_endpoint, wait_time, token_left

    async def poll_images(self, polling_endpoint: str) -> list:
        # https://www.bing.com/images/create/async/results/{ID}?q={PROMPT}
        polling_url = f"{self.BING_URL}/{polling_endpoint}"
        # Poll for results
        while True:
            # By default, timeout is 300s, change as needed
            response = await self.session.get(polling_url)
            if response.status_code != 200:
                raise Exception("Could not get results")
            content = response.text
            if content and content.find("errorMessage") == -1:
                break

            await asyncio.sleep(1)
            continue
        # Use regex to search for src=""
        image_links = regex.findall(r'src="([^"]+)"', content)
        # Remove size limit
        normal_image_links = [link.split("?w=")[0] for link in image_links]
        # Remove duplicates
        normal_image_links = list(set(normal_image_links))

        # Bad images
        bad_images = [
            "https://r.bing.com/rp/in-2zU3AJUdkgFe7ZKv19yPBHVs.png",
            "https://r.bing.com/rp/TX9QuO3WzcCJz1uaaSwQAz39Kb0.jpg",
        ]
        for im in normal_image_links:
            if im in bad_images:
                raise Exception("Bad images")
        # No images
        if not normal_image_links:
            raise Exception("No images")
        return normal_image_links
