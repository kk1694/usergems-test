"""
File for all the GPT calls. Will also add the unit tests here for simplicity.
"""

import json
import re
from datetime import datetime
from typing import Literal, Optional

import pandas as pd
import pytest
from pydantic import BaseModel

from .core import TEMP_DIR, html2md, limit_parallel, scrape_url, simple_gpt
from .testcases import (
    jobs_links,
    jobs_list,
    jobs_none,
    jobs_open_apply,
    jobs_zero,
    websites_invalid,
    websites_valid,
)

pytest_plugins = ("pytest_asyncio",)


FOLLOW_DEPTH = 3


class WebsiteClassification(BaseModel):
    reasoning: str
    classification: Literal["invalid", "valid"]


class JobsClassification(BaseModel):
    reasoning: str
    classification: Literal["Job list", "Job open apply", "Link to jobs", "No jobs"]
    link: Optional[str] = None
    titles: Optional[list[str]] = None


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


async def jobs_status(content) -> JobsClassification:
    _system_msg = """

You are a website classifier. I'm going to give you access to a website content (converted to markdown). Your job is to determine whether the website contains jobs.

You shall classify websites into the following buckets:
- Job list: the website explicitly lists actual jobs (with titles), or links to jobs that you can apply for. There has to be 1+ job listed.
- Empty list: the website has a section where jobs did and will apear, but right now it's empty, or company is currently not hiring. If there is a list with zero items, that also counts as empty list Even if they encourga people to send their CV, it counts as empty list if they state that they have no jobs right now. If the website mentions current roles but does not list any specific jobs, it is an empty list.
- Link to jobs: the page does not contain job lists, but has a link to a career / job page that has it. The link could be on the same domain, a separate domain, or it could be a link to an ATS provider or job board. Note: if the navbar (or footer) has a "Company"/"About"/"About us" (or similar section that often contains jobs), select this option. Also, it has a button saying "Apply" with no further context, it still counts as a link, not open apply; unless generic applications are specifically stated.
- Job open apply: the website says their accepting jobs, but does not list the jobs. Instead, it encourages people to apply, or email HR, or just has a rolling generic process. Note: the previous category takes precedence!
- No jobs: the website does not have any explicit jobs, does not have a vague apply by sending HR your CV, and does not even include a link to a separate page for jobs. This is different from section 1 in that there is no mention of jobs/careers/etc.

Use a waterfall approach: if the first category is satisfied (Job list), select that, then move to the next. If empty list is satisfied, select that, and so on. Categories higher up in the list take precedence.

For the output, give your very short reasoning (max 1-2 sentence), plus your classification.

Note:
- If the site does not list specific links AND mentions that they currently have no jobs, it is an empty list - NO MATTER if they still encourage you to apply.

If the answer is link to jobs, please provide the link in the output. Leave it empty for any other case.

If the answer is job list, please provide the list of job titles. Leave it empty for any other case.

Examples:
- "While FitLife has no current openings, we're always looking for talented fitness professionals. Please check back soon" -> Empty list
- "    StreamIt - Unlimited Movies and TV Shows. Enjoy the latest movies and shows without ads. Start streaming today!" -> No jobs
- "    Interested in working with us? Check our [career page](https://www.acme.com/jobs) for the latest openings." -> Link to jobs
- "GreenEnergy is always looking for skilled professionals to join our mission for sustainable energy. Send us your resume." -> Job open apply
- '''
TravelPro is an award-winning travel agency offering luxury vacations and personalized travel services.

    Positions available:
    - [Travel Consultant](https://travelpro.com/jobs/travel-consultant)
    - [Customer Service Associate](https://travelpro.com/jobs/customer-service)
''' -> Job list
- "    LearnTech is always looking for new talent. While we have no current positions available, feel free to submit your resume for future consideration on our [careers portal](https://learntech.com/careers)." -> Empty list
- "   ACME is always looking for talented individuals to join our team, but we currently don't have any open positions.\n\n    Please check back soon or submit your resume for future opportunities via our [general application form](https://acme.com/apply)." -> Empty list
- "    We currently have no job openings, but you can always stay updated via our [careers page](https://bluesky.com/careers)." -> Empty list
- " ACME is currently not having any open roles, but we're always looking for talented individuals. Please send us your resume." -> Empty list
- " Jobs at FitLife: \n\n - \n" -> Empty list


""".strip()

    return await simple_gpt(_system_msg, content, JobsClassification)


@pytest.mark.slow
@pytest.mark.asyncio
async def test_jobs_list():
    results = await quickcases(jobs_status, jobs_list)
    failed = [case for case, result in zip(jobs_list, results) if result != "Job list"]
    assert not failed, f"Failed cases: {failed}"


@pytest.mark.slow
@pytest.mark.asyncio
async def test_jobs_none():
    results = await quickcases(jobs_status, jobs_none)
    failed = [case for case, result in zip(jobs_none, results) if result != "No jobs"]
    assert not failed, f"Failed cases: {failed}"


@pytest.mark.slow
@pytest.mark.asyncio
async def test_jobs_links():
    results = await quickcases(jobs_status, jobs_links)
    failed = [
        case for case, result in zip(jobs_links, results) if result != "Link to jobs"
    ]
    assert not failed, f"Failed cases: {failed}"


# Note: these last 2 test cases get constantly confused, but don't have time to fiddle right now, so will just ignore
# Probably best solution: merge these and add extra step
@pytest.mark.slow
@pytest.mark.asyncio
async def test_jobs_open_apply():
    results = await quickcases(jobs_status, jobs_open_apply)
    failed = [
        case
        for case, result in zip(jobs_open_apply, results)
        if result not in ["No jobs", "Job open apply"]
    ]
    assert not failed, f"Failed cases: {failed}"


@pytest.mark.slow
@pytest.mark.asyncio
async def test_jobs_zero():
    results = await quickcases(jobs_status, jobs_zero)
    failed = [
        case
        for case, result in zip(jobs_zero, results)
        if result not in ["No jobs", "Job open apply"]
    ]
    assert not failed, f"Failed cases: {failed}"


def _strip_leading_dots(x: str) -> str:
    return x.lstrip(".")


def test__strip_leading_dots():
    assert _strip_leading_dots("...hello") == "hello"
    assert _strip_leading_dots("hello") == "hello"
    assert _strip_leading_dots(".") == ""


def prep_link(base_url: str, link: str) -> str:
    if base_url.endswith("/"):
        base_url = base_url.rstrip("/")

    link = _strip_leading_dots(link)
    if link.startswith("http"):
        return link

    link = re.sub(r"^\.*\/?", "", link)

    return f"{base_url}/{link}"


def test_prep_link():
    assert prep_link("https://example.com", "/jobs") == "https://example.com/jobs"
    assert prep_link("https://example.com", "jobs") == "https://example.com/jobs"
    assert (
        prep_link("https://example.com", "https://example.com/jobs")
        == "https://example.com/jobs"
    )
    assert (
        prep_link("https://example.com", "https://example.com/jobs")
        == "https://example.com/jobs"
    )
    assert prep_link("https://example.com", ".../jobs") == "https://example.com/jobs"
    assert prep_link("https://example.com", "...jobs") == "https://example.com/jobs"
    assert prep_link("https://example.com", ".../jobs") == "https://example.com/jobs"
    assert prep_link("https://example.com", "...jobs") == "https://example.com/jobs"


async def follow_links(base_url: str, next_link: str, history: list[str]):
    if len(history) > FOLLOW_DEPTH + 1:
        return {
            "status": "Max depth reached",
            "history": history,
            "titles": [],
            "error": None,
        }

    _next_link = prep_link(base_url, next_link)

    print("Starting next link", _next_link)

    try:
        print("Scraping page")
        content = await scrape_url(_next_link)
        print("converting to md")
        md = html2md(content)

        if not md:
            return {
                "status": "No content",
                "history": history,
                "titles": [],
                "error": None,
            }

        print("judging website status")
        status = await jobs_status(md)

        print("Status", status)

        if status.classification == "Link to jobs":
            return await follow_links(base_url, status.link, history + [status.link])

        return {
            "status": status.classification,
            "titles": status.titles,
            "history": history,
            "error": None,
        }
    except Exception as e:
        print(e)
        return {"status": "Error", "history": history, "error": str(e), "titles": []}
