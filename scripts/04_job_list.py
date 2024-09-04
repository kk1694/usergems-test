import asyncio
import json

import pandas as pd

from jobsfinder.core import DATA_DIR, limit_parallel
from jobsfinder.gpts import follow_scrape

INPUTFILE = DATA_DIR / "03_valid_website.csv"
SAVEFILE = DATA_DIR / "04_jobs.csv"


def get_data():
    if SAVEFILE.exists():
        print("There is already a save file, loading that")
        return pd.read_csv(SAVEFILE)
    df = pd.read_csv(INPUTFILE)
    assert len(df) == 2000
    assert all(df.md_status == "Success")
    df["history"] = None
    df["status"] = None
    df["error"] = None
    df["jobs"] = None
    return df


async def enrich_md():
    df = get_data()

    print("Data loaded")

    async def _get_jobs(i, url, md, _valid):
        if _valid == "invalid":
            return

        if df.loc[i, "status"] is not None:
            return

        res = await follow_scrape(url, md)

        df.loc[i, "history"] = json.dumps(res["history"])
        df.loc[i, "status"] = res["status"]
        df.loc[i, "error"] = res["error"]
        df.loc[i, "jobs"] = json.dumps(res["titles"])

        if i % 5 == 0:
            df.to_csv(SAVEFILE, index=False)

    await limit_parallel(
        [
            _get_jobs(i, row["Website"], row["md"], row["valid_website"])
            for i, row in df.iterrows()
        ],
        n=25,
    )

    print("Job finished.")

    df.to_csv(SAVEFILE, index=False)

    print("Data saved.")


if __name__ == "__main__":
    asyncio.run(enrich_md())
