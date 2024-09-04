"""
File for all the GPT calls. Will also add the unit tests here for simplicity.
"""

import json
from datetime import datetime
from typing import Literal

import pandas as pd
import pytest
from pydantic import BaseModel

from .core import TEMP_DIR, limit_parallel, simple_gpt
from .testcases import websites_invalid, websites_valid

pytest_plugins = ("pytest_asyncio",)


class WebsiteClassification(BaseModel):
    reasoning: str
    classification: Literal["invalid", "valid"]


async def valid_website(content) -> WebsiteClassification:
    _system_msg = """

You are a website classifier. I'm going to give you access to a website content (converted to markdown). Your job is to classify it into valid and invalid.

An invalid website is:
- an error message that says the website couldn't load
- just a cookie banner with nothing else
- a cloudfare verify you're human page
- any other page without meaningful content

A valid website is everything else: could be a landing page, an e-commerce shop, a webapp, etc.

Valid websites will be used for downstream processing. We want to filter out invalid ones, where no such thing makes sense. Use your best judgment to determine which is most suitable.

For the output, give your very short reasoning (max 1-2 sentence), plus your classification.

""".strip()

    return await simple_gpt(_system_msg, content, WebsiteClassification)


async def quickcases(process_func, cases):
    """
    Quick wrapper to run our test cases quickly, save an intermediary csv if we need debugging.
    """
    tasks = [process_func(case) for case in cases]
    results = await limit_parallel(tasks, 10)
    reasons, classification = zip(
        *[(result.reasoning, result.classification) for result in results]
    )

    df = pd.DataFrame(
        {
            "classification": classification,
            "case": [json.dumps(c) for c in cases],
            "reasoning": reasons,
        }
    )
    df.to_csv(TEMP_DIR / f".quickcases_{datetime.now().isoformat()}.csv", index=False)
    return classification


@pytest.mark.slow
@pytest.mark.asyncio
async def test_invalid():
    results = await quickcases(valid_website, websites_invalid)
    failed = [
        case for case, result in zip(websites_invalid, results) if result != "invalid"
    ]
    assert not failed, f"Failed cases: {failed}"


@pytest.mark.slow
@pytest.mark.asyncio
async def test_valid():
    results = await quickcases(valid_website, websites_valid)
    failed = [
        case for case, result in zip(websites_valid, results) if result != "valid"
    ]
    assert not failed, f"Failed cases: {failed}"
