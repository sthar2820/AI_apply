# Playwright MCP

This project uses the official [Playwright MCP](https://github.com/microsoft/playwright-mcp) server from Microsoft and the Playwright team. It gives Claude a real, controllable web browser with tools to navigate pages, take accessibility snapshots, click, type, select options, and upload files.

## Why this project needs it

The agent has three phases, and only some of them touch a browser:

- **Scout (browse):** Some job boards sit behind sign-in walls or render listings with JavaScript. The Playwright MCP lets Claude open a real browser, sign in, and read those listings directly instead of guessing from a static fetch.
- **Submit:** Application Tracking System (ATS) forms (Greenhouse, Lever, Workable, Ashby, Workday, and similar) are interactive web forms. The Playwright MCP lets Claude open the application page, read the form, fill each field from your profile, and upload your resume PDF.
- **Resume pipeline (no browser needed):** Generating and tailoring resume and cover letter PDFs is fully local. It runs through `python main.py` and never opens a browser. You do not need the Playwright MCP for that part.

In short: install the Playwright MCP if you want Claude to browse gated boards and fill application forms for you. If you only want to generate documents, you can skip it.

## Install it into Claude Code

Run this from the repository directory:

```bash
claude mcp add playwright -- npx @playwright/mcp@latest
```

How to read that command:

- `claude mcp add playwright` registers a new MCP server named `playwright`.
- The `-- ` (two dashes followed by a space) separates Claude's own arguments from the command that launches the MCP server. Everything after `-- ` is run as is to start the server, which here is `npx @playwright/mcp@latest`.

### Scope

By default the server is saved to your user configuration, so it is available in every project. To save it to this project instead, add `--scope project`:

```bash
claude mcp add playwright --scope project -- npx @playwright/mcp@latest
```

Project scope writes the server into a project `.mcp.json` file that you can commit, so anyone who clones the repo gets the same setup. User scope keeps it private to your machine. Pick whichever fits your workflow.

### Equivalent `.mcp.json`

If you prefer to configure the server by hand (or want to commit it for your team), add a `.mcp.json` at the repo root with this content:

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    }
  }
}
```

This is the same as running the `claude mcp add` command above with `--scope project`.

## Verify it loaded

List the registered servers:

```bash
claude mcp list
```

You should see `playwright` in the output.

Then, inside a Claude session, confirm the browser tools are available. When the server is loaded, Claude has access to a set of `browser_*` tools (for example `browser_navigate`, `browser_snapshot`, `browser_click`, `browser_type`, `browser_select_option`, and `browser_file_upload`). You can simply ask Claude "do you have the Playwright browser tools available?" to check.

On the first run, the server may need to download a browser. If it does, it will use Playwright's installer, equivalent to:

```bash
npx playwright install
```

This is a one time download. Later runs reuse the installed browser.

## Using it day to day

You do not call the tools directly. You ask Claude in plain language and it picks the right browser tools. For example:

> Open this job application URL in the browser and start filling the form from my profile.

> Open the careers page for Example Corp, sign in, and list the open Software Engineer roles.

Claude will navigate, snapshot the page so it can see the fields, and fill them in for you.

## Security note

The browser acts as you. It uses whatever sessions and logins you give it, and anything it submits is submitted under your identity.

- Review every field before any submit step. Ask Claude to pause and show you the filled form first.
- Never let the agent submit an application without your explicit confirmation.
- Solve CAPTCHAs yourself and enter any one time passcodes (OTP) yourself when prompted.

When in doubt, tell Claude to stop before the submit button and wait for you.
