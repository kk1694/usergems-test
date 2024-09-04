import asyncio
from pathlib import Path

import tqdm.asyncio
from openai import AsyncClient
from playwright.async_api import async_playwright

DATA_DIR = Path(__file__).parent.parent / "data"


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
    return AsyncClient


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
            print(completion.usage.total_tokens)
            return completion.choices[0].message.parsed
        except Exception as err:
            print(err)
            await asyncio.sleep(20)
    raise ValueError("5 iterations did not succeed!")
