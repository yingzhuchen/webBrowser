# webBrowser

webBrowser is a Python browser automation agent. Give it a task in natural language, and it can open pages, follow links, and extract information from a real browser. This repository provides a Python API and a command-line interface. It does not include a standalone web UI for submitting tasks or viewing conversation history.

## Requirements

- [uv](https://docs.astral.sh/uv/getting-started/installation/) and Python 3.11 or newer. The commands below use Python 3.12.
- A local Chrome or Chromium installation and an OpenAI API key.

## Install from source

```bash
git clone https://github.com/yingzhuchen/webBrowser.git
cd webBrowser
uv sync --python 3.12
```

This installs the `browser_use` package from this checkout into the project's virtual environment.

## Run with a local browser

Create a `.env` file in the repository root and add your OpenAI API key. Keep this file out of version control.

```dotenv
OPENAI_API_KEY=your_openai_api_key
```

Create `run_agent.py` in the repository root.

```python
from browser_use import Agent, Browser, ChatOpenAI

agent = Agent(
    task="Open https://example.com and report the page title.",
    llm=ChatOpenAI("gpt-4.1-mini"),
    browser=Browser("chromium"),
)

result = agent.run_sync()
print(result.final_result())
```

```bash
uv run python run_agent.py
```

The script starts a local browser with a temporary profile. On a machine with a graphical desktop, pass `headless=False` to watch the agent operate Chrome. The task result prints in the terminal.

## Continue a conversation

Reuse the same `Agent` instance and call `add_new_task()` before running it again. Set `keep_alive=True` to keep the browser open between runs so the follow-up can use the current page.

```python
import asyncio

from browser_use import Agent, Browser, ChatOpenAI


async def main():
    browser = Browser("chromium", keep_alive=True)
    agent = Agent(
        task="Open https://example.com and report the page title.",
        llm=ChatOpenAI("gpt-4.1-mini"),
        browser=browser,
    )

    try:
        first = await agent.run()
        print(first.final_result())
        agent.add_new_task("List the links on the current page.")
        second = await agent.run()
        print(second.final_result())
    finally:
        await agent.close()
        await browser.stop()


if __name__ == "__main__":
    asyncio.run(main())
```

## Command line

```bash
uv run webBrowser --help
```

