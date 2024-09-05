import random
from asyncio import sleep
from dataclasses import dataclass
from pathlib import Path

from fasthtml.common import *

from jobsfinder.core import html2md, scrape_url
from jobsfinder.gpts import has_sales_roles, jobs_status, prep_link


@dataclass
class Profile:
    email: str
    phone: str
    age: int


css = Script(src="https://cdn.tailwindcss.com")
hdrs = (Script(src="https://unpkg.com/htmx-ext-sse@2.2.1/sse.js"), css)


app = FastHTML(hdrs=hdrs, static_path="public")

count = 0


url_form = Form(method="post", hx_post="/url", hx_target="#url_w_quickstart")(
    Label("Enter your prospect's company URL", cls="text-xl font-bold text-slate-800"),
    Fieldset(
        Input(
            name="url",
            cls="border min-w-[300px] rounded py-1 px-2",
            placeholder="https://notion.so",
        ),
        Button("Submit", type="submit", cls="bg-blue-500 text-white rounded py-2 px-6"),
        cls="flex flex-wrap gap-2 justify-center items-center w-full",
    ),
    cls="flex flex-col gap-2 items-center",
)

url_w_quickstart = Div(
    P("Qualify target companies by jobs. Are they hiring for sales & marketing roles?"),
    url_form,
    Div(
        P("Quickstart"),
        Div(
            Button(
                "Notion",
                type="button",
                cls="bg-blue-100 text-blue-800 py-0.5 px-2 rounded",
                hx_vals='{"url": "https://notion.so"}',
                hx_post="/url",
                hx_target="#url_w_quickstart",
            ),
            Button(
                "Zuplo",
                type="button",
                cls="bg-blue-100 text-blue-800 py-0.5 px-2 rounded",
                hx_vals='{"url": "https://zuplo.com"}',
                hx_post="/url",
                hx_target="#url_w_quickstart",
            ),
            Button(
                "Slack",
                type="button",
                cls="bg-blue-100 text-blue-800 py-0.5 px-2 rounded",
                hx_vals='{"url": "https://slack.com"}',
                hx_post="/url",
                hx_target="#url_w_quickstart",
            ),
            cls="flex flex-wrap gap-x-6 gap-y-2 items-center",
        ),
        cls="flex flex-col gap-2 items-center",
    ),
    cls="flex flex-col gap-10 items-center w-full",
    id="url_w_quickstart",
)


def _create_email(x):
    return f"""
Hey [firstName],

{x} Businesss must be going good!

Given your trajectory, I assume your doing everything to increase conversion. That's also the reason we've built UserGems. You can automatically capture buying signals from your prospect & put your pipeline on auto-pilot.

Let me know if that's of interest.

Best,
[Your Name]
    """.strip()


async def message_gen(url: str):
    shutdown_event = signal_shutdown()

    async def follow_links_for_app(url: str):
        global count
        count = count + 1

        if count > 200:
            yield sse_message(
                Article("Restricted trials to max 200 not to user-use the openai API.")
            )
            shutdown_event.set()
            return

        history = []

        next_link = url
        result = None

        while len(history) < 3:
            _next_link = prep_link(url, next_link)

            yield sse_message(
                Div(
                    P(
                        f"Processing link ",
                        A(_next_link, href=_next_link, cls="text-blue-600"),
                        "...",
                    ),
                    cls="text-slate-800 text-lg",
                )
            )

            try:
                content = await scrape_url(_next_link)
                md = html2md(content)

                if not md:
                    yield sse_message(Article("Could not scrape the page :("))
                    shutdown_event.set()
                    return

                result = await jobs_status(md)
                print(result)

                if result.classification == "Link to jobs":
                    next_link = result.link
                    history.append(result.link)
                    yield sse_message(
                        Div(
                            P(
                                f"Let's try the next link",
                            ),
                            cls="text-slate-600 text-sm",
                        )
                    )
                    continue

                break

            except Exception as e:
                print(e)
                yield sse_message(Article("Hmmm... something went wrong"))
                shutdown_event.set()
                return

        if not result:
            yield sse_message(Article("Gave up after trying 3 links :("))
            shutdown_event.set()
            return

        status = result.classification

        if status == "No jobs":
            yield sse_message(
                Article(
                    "Looks like they're not hiring. Probably not the best time to reach out."
                )
            )
            shutdown_event.set()
            return

        if status == "Job open apply":
            yield sse_message(
                Article(
                    "Looks like they have general applications, but not the specific juice we need."
                )
            )
            shutdown_event.set()
            return

        titles = result.titles
        num = len(titles)

        yield sse_message(
            Div(
                P(
                    f"Whoa!",
                    cls="text-slate-800 text-lg font-semibold",
                ),
                P(
                    f"Looks like they're hiring for {num} positions. Let's check if they qualify...",
                ),
                cls="text-slate-600 text-sm flex flex-col gap-2",
            )
        )
        qualified = await has_sales_roles(titles)

        if not qualified.qualified:
            yield sse_message(
                Div(
                    P(
                        f":(",
                        cls="text-slate-800 text-2xl font-semibold",
                    ),
                    cls="bg-red-200",
                )
            )

            await sleep(0.5)

            yield sse_message(
                Div(
                    P(
                        "Looks like they're not hiring for sales & marketing. Maybe check back later, since they seem to be growing!",
                        cls="text-slate-600",
                    ),
                    cls="bg-red-200",
                )
            )

            shutdown_event.set()
            return

        yield sse_message(
            Div(
                P(
                    f"Yesss!",
                    cls="text-slate-800 text-3xl font-semibold",
                ),
                cls="bg-green-200",
            )
        )

        await sleep(0.5)

        yield sse_message(
            Div(
                P(
                    "They are hiring sales & marketing roles: ",
                    cls="text-slate-600",
                ),
                *[P(f"- {t}") for t in qualified.best_roles],
                cls="flex flex-col gap-1",
            )
        )

        await sleep(1)

        email = _create_email(qualified.email_line)

        yield sse_message(
            Div(
                P(
                    "Use this email template: ",
                    cls="text-slate-800 font-semibold",
                ),
                P(
                    email,
                    cls="text-slate-800 whitespace-pre-wrap bg-gray-100 p-2 rounded-lg",
                ),
                cls="flex flex-col gap-y-1",
            )
        )

        await sleep(0.5)

        yield sse_message(
            Div(
                Img(
                    src=f"https://preview.redd.it/fnnuohi0u7h71.png?width=1080&crop=smart&auto=webp&s=46bb56d78a671e891c78795df7fc7d59472ca942"
                ),
                id=f"pointing-img",
                cls="w-full",
            ),
        )

        shutdown_event.set()
        return

    async for msg in follow_links_for_app(url):
        if shutdown_event.is_set():
            break
        yield msg

    # hack
    # yield sse_message(Article("done!"))
    await sleep(3600 * 24 * 365)
    yield sse_message(Article("Restarting..."))


# async def message_gen(url: str):
#     data = Article(url)

#     yield sse_message(data)
#     await sleep(1)

#     yield sse_message(data)
#     await sleep(1)


@app.get("/response_stream")
async def add_message(url: str):
    return EventStream(message_gen(url))


@app.post("/url")
def index(url: str):
    return Div(
        P("Let's look at those results!", cls="text-xl font-bold text-slate-800"),
        Div(
            hx_ext="sse",
            sse_connect=f"/response_stream?url={url}",
            hx_swap="beforeend show:bottom",
            sse_swap="message",
            cls="border p-4 rounded-lg flex grow flex-col gap-4 min-h-48 bg-gray-50 pb-10",
        ),
        cls="w-full h-full",
    )


@app.get("/profile")
def profile():
    return profile_form


@app.get("/")
def home():
    return Title("Usergems Qualifier"), Main(
        Div(
            H1("UserGems Qualifier", cls="text-4xl  text-slate-800"),
            url_w_quickstart,
            cls="max-w-xl flex flex-col gap-y-8 w-full h-full items-center justify-center text-slate-600",
        ),
        cls="h-screen w-screen flex items-center justify-center overflow-y-auto",
    )


serve()
