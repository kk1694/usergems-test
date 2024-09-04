import asyncio

import pandas as pd

from jobsfinder.core import DATA_DIR, limit_parallel
from jobsfinder.gpts import valid_website

INPUTFILE = DATA_DIR / "02_adding_markdown.csv"
SAVEFILE = DATA_DIR / "03_valid_website.csv"


def get_data():
    if SAVEFILE.exists():
        print("There is already a save file, loading that")
        return pd.read_csv(SAVEFILE)
    df = pd.read_csv(INPUTFILE)
    assert len(df) > 3000
    assert all(df.md_status == "Success")
    df["valid_website"] = None
    return df


async def enrich_md():
    df = get_data()

    print("Data loaded")

    async def _is_valid(i, md):
        if df.loc[i, "valid_website"] is not None:
            return

        result = await valid_website(md)

        df.loc[i, "valid_website"] = result.classification

        if i % 25 == 0:
            df.to_csv(SAVEFILE, index=False)

    await limit_parallel(
        [_is_valid(i, row["Website"]) for i, row in df.iterrows()], n=10
    )

    print("Job finished.")

    df.to_csv(SAVEFILE, index=False)

    print("Data saved.")


if __name__ == "__main__":
    asyncio.run(enrich_md())
