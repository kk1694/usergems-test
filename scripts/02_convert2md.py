import pandas as pd
from tqdm import tqdm

from jobsfinder.core import DATA_DIR, html2md

INPUTFILE = DATA_DIR / "01_subset_enriched.csv"
SAVEFILE = DATA_DIR / "02_adding_markdown.csv"


def get_data():
    if SAVEFILE.exists():
        print("There is already a save file, loading that")
        return pd.read_csv(SAVEFILE)
    df = pd.read_csv(INPUTFILE)
    df = df[df.scrape_status == "Success"].reset_index(drop=True)
    assert len(df) > 3000
    df["md_status"] = "Not Started"
    df["md"] = None
    return df


def enrich_md():
    df = get_data()

    print("Data loaded")

    for i, row in tqdm(df.iterrows()):
        if row["scrape_status"] != "Success":
            continue

        if row["md_status"] in ["Failed", "Success"]:
            continue

        try:
            md = html2md(row["homepage_content"])

            if not md or len(md) < 100:
                raise Exception("No content")

            df.loc[i, "md"] = md
            df.loc[i, "md_status"] = "Success"
        except Exception as e:
            print(e)
            df.loc[i, "md_status"] = "Failed"

    df["html_length"] = df.homepage_content.apply(
        lambda x: None if x is None else len(x)
    )
    df["md_length"] = df.md.apply(lambda x: None if x is None else len(x))

    del df["homepage_content"]

    df.to_csv(SAVEFILE, index=False)

    print("Data saved.")


if __name__ == "__main__":
    enrich_md()
