import asyncio
import json

import pandas as pd

from jobsfinder.core import DATA_DIR, limit_parallel, scrape_url

SAVEFILE = DATA_DIR / "01_subset_enriched.csv"
LIMITED_SAVEFILE = DATA_DIR / "01_subset_enriched_limited.csv"


def _parse_single_quote_json(json_str):
    json_str_fixed = json_str.replace("'", '"').replace("None", "null")
    try:
        return json.loads(json_str_fixed)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return None


def _get_country(_str):
    x = _parse_single_quote_json(_str)
    if x is None:
        return None
    if "country" not in x.keys():
        return None
    return x["country"]


def subset_data():
    """
    We'll look at computer software industry, US companies
    """

    df = pd.read_csv(DATA_DIR / "00_websites.csv")
    assert len(df) == 66342  # we know these asserts from initial notebook exploration
    df = df[df["Industry"] == "Computer Software"]
    assert len(df) == 6548

    df["country"] = df.Address.apply(lambda x: _get_country(x))

    df = df[df["country"] == "united states"]
    assert len(df) == 4734

    return df[["CompanyName", "Website"]].reset_index(drop=True)


def get_data():
    if SAVEFILE.exists():
        print("There is already a save file, loading that")
        return pd.read_csv(SAVEFILE)
    return subset_data()


async def enrich_homepage_scrapes():
    """
    Scrape homepages of companies
    """
    df = get_data()

    print("Data loaded")

    df["scrape_status"] = "Not Started"
    df["homepage_content"] = None

    async def scrape_homepage(i, url):
        if df.loc[i, "scrape_status"] in ["Failed", "Success"]:
            return

        content = await scrape_url(url)

        if content is None:
            df.loc[i, "scrape_status"] = "Failed"
            return

        df.loc[i, "scrape_status"] = "Success"
        df.loc[i, "homepage_content"] = content

        if i % 25 == 0:
            df.to_csv(SAVEFILE, index=False)

    await limit_parallel(
        [scrape_homepage(i, row["Website"]) for i, row in df.iterrows()], n=10
    )

    print("Job finished.")

    df.to_csv(SAVEFILE, index=False)

    print("Data saved.")

    # Save git friendly version
    df["homepage_content"] = df["homepage_content"].apply(
        lambda x: x[:100] if x is not None else None
    )
    df.to_csv(LIMITED_SAVEFILE, index=False)

    print("Git friendly data saved.")


if __name__ == "__main__":
    asyncio.run(enrich_homepage_scrapes())
