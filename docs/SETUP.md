# Setup Guide

This guide walks you through installing the job application agent from a clean machine, generating your first tailored resume, and connecting it to Claude Code so the agent can find roles and fill web forms for you.

Follow the steps in order. Each step includes concrete commands.

## 1. Prerequisites

Install the following tools before cloning the repo.

### Python 3.8+

Check whether Python is already installed:

```bash
python3 --version
```

If you need it, download it from [python.org](https://www.python.org/downloads/) or install it with your package manager:

```bash
# macOS (Homebrew)
brew install python

# Debian / Ubuntu
sudo apt update && sudo apt install python3 python3-pip
```

### A LaTeX distribution (provides pdflatex)

The resume and cover letter PDFs are compiled with `pdflatex`, so you need a LaTeX distribution installed.

```bash
# macOS (Homebrew, no GUI apps)
brew install --cask mactex-no-gui

# Debian / Ubuntu
sudo apt update && sudo apt install texlive-full
```

On Windows, install [MiKTeX](https://miktex.org/download). During first use MiKTeX may prompt to install missing packages on the fly; allow it.

After installing, open a fresh terminal so the new binaries land on your `PATH`, then verify:

```bash
pdflatex --version
```

You should see version output beginning with `pdfTeX`. If the command is not found, see Troubleshooting below.

### Node.js

Node.js is required later for the Playwright MCP, which lets the agent fill web forms. Install the LTS release from [nodejs.org](https://nodejs.org/) or via a package manager:

```bash
# macOS (Homebrew)
brew install node

# Debian / Ubuntu
sudo apt install nodejs npm
```

Verify:

```bash
node --version
npm --version
```

### Claude Code

Claude Code is the agent runtime that reads this project and drives the workflow. Install it globally with npm:

```bash
npm install -g @anthropic-ai/claude-code
```

See the official docs at [claude.ai/code](https://claude.ai/code) for sign-in and the latest install instructions. Verify:

```bash
claude --version
```

## 2. Clone the repository and install Python dependencies

Clone the repo and move into it:

```bash
git clone <repo-url>
cd <repo-directory>
```

Install the Python dependencies (pyyaml, python-frontmatter, PyQt6, and others):

```bash
pip install -r requirements.txt
```

If you prefer an isolated environment, create a virtual environment first:

```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Configure your profile

Your entire candidate identity lives in one file: `profile/about_candidate.yml`. This is the single source of truth. The agent will never claim anything about you that is not written in this file, so accuracy and honesty here directly control what shows up on every resume, cover letter, and application form.

**The easy way: let Claude interview you.** Once you open the project in Claude Code (step 5), just say `Set me up`. The profile-setup agent notices the file is still the placeholder, asks you about your experience, education, skills, and work authorization, and writes the profile for you. You can skip the manual edit below.

**The manual way.** Open it in your editor:

```bash
${EDITOR:-nano} profile/about_candidate.yml
```

The file ships with a dummy persona. Replace every field with your real information. For reference, the placeholder data looks like this:

```yaml
name: Jane Doe
email: jane.doe@example.com
phone: "+1-555-0100"
location: San Francisco, CA

education:
  - school: Example University
    degree: BS Computer Science
    gpa: 3.9/4.0
    graduation: May 2024
```

Replace `Jane Doe`, `jane.doe@example.com`, `+1-555-0100`, `San Francisco, CA`, and the `Example University` education block with your own values, then continue through the experience, projects, and skills sections.

Fill in the `work_authorization` fields honestly. The agent uses these to decide whether to apply and how to answer sponsorship questions on application forms, so an inaccurate value here leads to applications that misrepresent you. State your real status (for example, whether you are a citizen, a permanent resident, or require visa sponsorship) exactly as it is.

## 4. Generate your first resume to test the pipeline

Run the generator to confirm Python and `pdflatex` work together end to end:

```bash
python main.py --company "Example Corp" --role "Software Engineer" --type resume
```

The command takes three options:

1. `--company` the company name (for example `Example Corp`)
2. `--role` the role title (for example `Software Engineer`)
3. `--type` the output: `resume`, `coverletter`, or `both` (defaults to `both`)

Use `--type resume` to generate just the resume for this first test.

When it finishes, the PDF lands under the `applications/` directory, organized by company:

```bash
ls applications/Example\ Corp/
```

Open the generated PDF and confirm it is **one page**. A clean one-page resume means the LaTeX pipeline is healthy and your profile data rendered correctly. If the PDF is missing, the most common cause is `pdflatex` not being on your `PATH` (see Troubleshooting).

## 5. Open the project in Claude Code

From inside the repo directory, start Claude Code:

```bash
claude
```

Claude Code automatically reads `CLAUDE.md` and the agent definitions in `.claude/agents/` when it starts, so it already knows the project conventions, your workflow, and which specialized agents are available. You do not need to load anything manually.

## 6. Install the Playwright MCP

To let Claude fill web application forms in a real browser, install the Playwright MCP. The exact command and configuration are documented separately:

See [docs/PLAYWRIGHT_MCP.md](PLAYWRIGHT_MCP.md) for the install command and verification steps.

After installing, restart Claude Code so it picks up the new MCP server.

## 7. Run the workflow

You are now ready to use the agent. The full workflow, including how the scout, tailor, and apply steps fit together, is documented in:

- [docs/USAGE.md](USAGE.md)
- [WORKFLOW.md](../WORKFLOW.md)

To get started, give Claude a first prompt like:

```
Find me 5 entry-level software engineer roles posted this week, then tailor my resume for the best fit.
```

Claude will use the scout to find roles, pull details from your profile, and generate a tailored resume under `applications/`. From there you can ask it to draft a cover letter or fill an application form with the Playwright MCP.

## Troubleshooting

### `pdflatex` not found

The generator runs but no PDF appears, or you see a "command not found" error.

- Open a brand-new terminal so a freshly installed LaTeX distribution is on your `PATH`.
- Confirm the binary is reachable: `which pdflatex` (macOS/Linux) or `where pdflatex` (Windows).
- On macOS, MacTeX installs to `/Library/TeX/texbin`. Add it to your shell profile if missing:
  ```bash
  echo 'export PATH="/Library/TeX/texbin:$PATH"' >> ~/.zshrc && source ~/.zshrc
  ```
- On Windows with MiKTeX, allow it to install missing packages when prompted the first time you compile.

### PyQt6 install issues

`pip install -r requirements.txt` fails on PyQt6.

- Upgrade pip and packaging tools first, then retry:
  ```bash
  pip install --upgrade pip setuptools wheel
  pip install -r requirements.txt
  ```
- On Debian/Ubuntu you may need system Qt libraries:
  ```bash
  sudo apt install python3-pyqt6
  ```
- Make sure you are on Python 3.8 or newer; older interpreters lack a compatible PyQt6 wheel.

### MCP not detected

Claude Code does not see the Playwright tools.

- Restart Claude Code after installing the MCP so it loads the new server.
- Confirm Node.js is installed and on your `PATH`: `node --version`.
- List configured MCP servers from inside Claude Code with the `/mcp` command and confirm Playwright is listed and connected.
- Review [docs/PLAYWRIGHT_MCP.md](PLAYWRIGHT_MCP.md) and re-run the install command.
