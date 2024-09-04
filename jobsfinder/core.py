import asyncio
import re
from pathlib import Path

import tqdm.asyncio
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from markdownify import markdownify
from openai import AsyncClient
from playwright.async_api import async_playwright

PROJECT_DIR = Path(__file__).parent.parent
DATA_DIR = PROJECT_DIR / "data"
TEMP_DIR = PROJECT_DIR / ".temp"


load_dotenv(PROJECT_DIR / ".env")


async def limit_parallel(tasks, n=5):
    """
    Run up to n async tasks in parallel.

    :param n: Maximum number of concurrent tasks.
    :param tasks: List of coroutine functions to execute.
    :return: List of results from the tasks.
    """
    semaphore = asyncio.Semaphore(n)

    async def sem_task(task):
        async with semaphore:
            return await task

    # Wrap tasks with semaphore logic
    wrapped_tasks = [sem_task(task) for task in tasks]

    # Run all tasks concurrently
    return await tqdm.asyncio.tqdm.gather(*wrapped_tasks)


async def scrape_url(url):
    """
    This can be more advanced, but for now, it will do
    """

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            await page.goto(url)

            await page.wait_for_load_state(timeout=20000)
            await page.keyboard.press("PageDown")
            await page.wait_for_load_state(timeout=20000)

            await page.evaluate("() => document.location.href")
            await page.wait_for_load_state(timeout=20000)

            content = await page.content()
            await browser.close()
            return content
    except Exception as e:
        print(e)
        return None


def _init_openai() -> AsyncClient:
    return AsyncClient()


async def simple_gpt(system_msg, user_msg, schema, temperature=0):
    client = _init_openai()
    for i in range(5):
        try:
            completion = await client.beta.chat.completions.parse(
                model="gpt-4o-mini-2024-07-18",
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
                response_format=schema,
                temperature=temperature,
            )
            return completion.choices[0].message.parsed
        except Exception as err:
            print(err)
            await asyncio.sleep(20)
    raise ValueError("5 iterations did not succeed!")


def replace_empty_newlines(text):
    return re.sub(r"(\n{4,})", "\n\n\n", text)


def html2md(html: str | None):
    if html is None:
        return None

    soup = BeautifulSoup(html, "html.parser")

    try:
        # Noticed this issue in some of the first datapoints.
        # We can also do more cleaning if necessary, but not need to over-optimize this
        # before doing a proper markdown-converter comparison
        for noscript in soup.find_all("noscript"):
            noscript.decompose()

        # Remove all attributes except for alt tags for images (so we don't have bs64 encoded long strings)
        for tag in soup.find_all(["img", "video", "svg"]):
            attributes = {
                key: value for key, value in tag.attrs.items() if key == "alt"
            }
            tag.attrs = attributes

        cleaned_html = str(soup)
        md = markdownify(cleaned_html)
        return replace_empty_newlines(md)
    except Exception as e:
        print(e)
        return None
