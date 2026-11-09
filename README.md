# webBrowser

A Python-based browser automation agent built on Browser Use. It uses a language model to carry out browser tasks such as opening pages, navigating websites, and extracting information.

## Requirements

- Python 3.11 or later (Python 3.12 recommended)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) for dependency management
- An API key for your chosen language model
- Chrome/Chromium for local browser execution, or a Browser Use Cloud API key for cloud execution

## Installation

Clone the repository and enter its root directory:

```bash
git clone https://github.com/yingzhuchen/webBrowser.git
cd webBrowser
```

Install the project's dependencies from `pyproject.toml`:

```bash
uv sync --python 3.12
```

This installs the local source package and creates a managed virtual environment. Do not run `uv add browser-use` here: the repository already defines the `browser-use` package itself.

## Configuration

Create a local environment file from the provided template:

```bash
cp .env.example .env
```

Edit `.env` and configure the API key for the model you want to use. For example, with OpenAI:

```dotenv
OPENAI_API_KEY=your_openai_api_key
```

Or, to use the Browser Use model and/or cloud browser:

```dotenv
BROWSER_USE_API_KEY=your_browser_use_api_key
```

The template also contains optional logging, browser, proxy, and telemetry settings. Keep `.env` private and do not commit API keys to Git.

## Run an Agent

Create an `agent.py` file in the repository root:

```python
import asyncio

from browser_use import Agent, ChatOpenAI
from dotenv import load_dotenv

load_dotenv()


async def main():
    agent = Agent(
        task='Open https://example.com and report the page title.',
        llm=ChatOpenAI(model='gpt-4.1-mini'),
    )
    history = await agent.run()
    print(history.final_result())


if __name__ == '__main__':
    asyncio.run(main())
```

Start the agent from the repository root:

```bash
uv run python agent.py
```

The agent launches a browser, performs the requested actions, and prints the final result. Change the `task` string to run another browser automation task.

### Alternative: Browser Use model

To use the Browser Use model instead of OpenAI, configure `BROWSER_USE_API_KEY` and replace the model setup:

```python
from browser_use import Agent, ChatBrowserUse

agent = Agent(
    task='Open https://example.com and report the page title.',
    llm=ChatBrowserUse(model='bu-2-0'),
)
```

### Alternative: Cloud browser

To run in a managed cloud browser, configure `BROWSER_USE_API_KEY` and pass a `Browser` instance to the agent:

```python
from browser_use import Agent, Browser, ChatOpenAI

agent = Agent(
    task='Open https://example.com and report the page title.',
    llm=ChatOpenAI(model='gpt-4.1-mini'),
    browser=Browser(use_cloud=True),
)
```

## Command-line entry point

The repository also defines a `browser-use` command and the aliases `browseruse`, `bu`, and `browser`. To inspect the available commands:

```bash
uv run browser-use --help
```

## Project Layout

```text
webBrowser/
├── browser_use/       # Agent, browser automation, CLI, and model integrations
├── examples/          # Example scripts
├── tests/             # Test suite
├── scripts/           # Development and utility scripts
├── pyproject.toml     # Python package and dependency configuration
├── .python-version    # Preferred Python version (3.12)
├── .env.example       # Environment configuration template
└── README.md
```

## Troubleshooting

**Missing API key:** Check that `.env` exists, contains the key required by the selected model, and is loaded with `load_dotenv()`.

**Browser fails to start:** Ensure a compatible local Chrome/Chromium installation is available, or switch to a cloud browser with `Browser(use_cloud=True)` and a valid `BROWSER_USE_API_KEY`.

**Dependency or Python-version errors:** From the project root, rerun `uv sync --python 3.12` and execute scripts using `uv run` so that the repository's environment is used.

## License

MIT License. See [LICENSE](LICENSE).
