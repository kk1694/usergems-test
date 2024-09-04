# In your_package/module.py

import argparse
import asyncio

from jobsfinder.gpts import follow_links, has_sales_roles


def _create_email(x):
    return f"""
Hey [firstName],

{x} Businesss must be going good!

Given your trajectory, I assume your doing everything to increase conversion. That's also the reason we've built UserGems. You can automatically capture buying signals from your prospect & put your pipeline on auto-pilot.

Let me know if that's of interest.

Best,
[Your Name]
    """.strip()


async def async_process(url):
    print("\n\n*********** PROCESSING ***********")

    result = await follow_links(url, url, [])

    status = result["status"]

    print("\n\n*********** RESULT ***********")

    if status == "Error":
        print(f"Some kind of error occured for {url}")
        return

    #     No jobs              1471
    # Loop detected         226
    # Job open apply         56
    # Job list               43
    # Max depth reached       6

    if status == "No jobs":
        print("Looks like they're not hiring. Probably not the best time to reach out.")
        return

    if status == "Loop detected":
        print("Looks like we're running in a loop. Our bad - this is a buggy well fix.")
        import pdb

        pdb.set_trace()
        return

    if status == "Job open apply":
        print(
            "Looks like they have general applications, but we need specific juicy to qualify them"
        )
        return

    if status == "Max depth reached":
        print(
            "We only check 3 URLs by default, and we've reached that. Increase this limit, and we can do some more!"
        )
        return

    titles = result["titles"]
    num = len(titles)
    print(
        f"Who! looks like they're hiring for {num} positions. Let's check if they qualify...\n\n"
    )

    qualified = await has_sales_roles(titles)

    if not qualified.qualified:
        print(
            "Looks like they're not hiring for sales & marketing. Maybe check back later, since they seem to be growing!"
        )
        return

    print("Looks like they're hiring for sales & marketing. You should reach out!\n\n")

    email = _create_email(qualified.email_line)
    print(f"Use the following email: \n\n{email}")


def main():
    parser = argparse.ArgumentParser(description="Description of your script")
    parser.add_argument("url", help="Company url")

    args = parser.parse_args()

    print(f"Let's see if you should reach out to {args.url}")

    asyncio.run(async_process(args.url))


if __name__ == "__main__":
    main()
