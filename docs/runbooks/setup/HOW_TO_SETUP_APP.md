# How to set up the app

Install the tools and packages you need before you start the participant UI. The participant UI is the set of web screens a study participant sees.

## Tools to install

You need Node.js 20.x and npm to run the UI. You need Python 3.12 and uv only if you will run lint or tests at the repo root. uv is the installer for Python packages in this repo.

- Node.js 20.x
- npm (included with Node.js)
- Python 3.12 (lint and tests)
- uv (lint and tests)

## Install UI packages

Run `npm install` in `ui/` so packages from `ui/package-lock.json` are in `ui/node_modules`.

```bash
cd ui
npm install
```

## Install Python packages

Run `uv sync --group dev` at the repo root so packages from `uv.lock` are in `.venv`. Skip this step if you only want to start the UI.

```bash
uv sync --group dev
```

## After setup

Start the app with [How to run the app](../HOW_TO_RUN_APP.md).
