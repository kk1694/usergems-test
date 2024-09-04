import asyncio
from pathlib import Path

import tqdm.asyncio
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
            await page.wait_for_load_state()
            await page.goto(url)
            content = await page.content()
            await browser.close()
            return content
    except Exception as e:
        print(e)
        return None
