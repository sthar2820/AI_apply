# Architecture

This repo is a Claude Code "job application agent": a set of subagents, prompts, and a YAML to PDF resume pipeline that together find roles, tailor a resume, and submit applications. This document explains how the pieces fit together and where you customize them.

## Component overview

| Component | Path | Role |
| --- | --- | --- |
| Candidate profile | `profile/about_candidate.yml` | Single source of truth. Every fact in a resume (employers, projects, skills, education) must trace back here. |
| Resume generator | `resume/generator.py`, `main.py` | Renders a resume YAML into LaTeX and then a PDF. |
| Cover letter generator | `coverletter/generator.py` | Renders a cover letter YAML into a matching PDF. |
| Resume variants | `resume/resume.yml`, `resume/resume_ml.yml`, `resume/resume_sw.yml` | The working resume plus role slanted starting templates. |
| profile-setup subagent | `.claude/agents/profile-setup.md` | Interviews the user on first run and writes `profile/about_candidate.yml`. |
| job-scout subagent | `.claude/agents/job-scout.md` | Searches job boards and company career pages for fresh, matching roles. |
| resume-builder subagent | `.claude/agents/resume-builder.md` | Copies a variant, tailors it to a job description, edits `resume/resume.yml`. |
| application-submitter subagent | `.claude/agents/application-submitter.md` | Drives the ATS form via the Playwright MCP to submit the application. |
| Playwright MCP | MCP server config | Gives the submitter a real browser to navigate ATS forms, fill fields, and attach the PDF. |
| Tracking log | `applications-log.md` | Append only record of every application: company, role, req ID, ATS, status. |
| Project instructions | `CLAUDE.md` | Behavior rules Claude Code loads automatically for this project. |
| Workflow notes | `WORKFLOW.md` | The end to end playbook a human or the orchestrator follows per application. |

## Data flow

```
  profile/about_candidate.yml        (source of truth)
              |
              v
       job-scout subagent  ----> finds a role + job description (JD)
              |
              v
     resume-builder subagent
       copies resume_ml.yml or resume_sw.yml
       tailors content to the JD
              |
              v
        resume/resume.yml
              |
              v
   python main.py  (resume/generator.py)
       YAML  ->  LaTeX (.tex)  ->  pdflatex x2  ->  PDF
              |
              v
   applications/{Company}/resume.pdf
              |
              v
   application-submitter subagent  (Playwright MCP)
       navigates ATS, fills form, attaches PDF, submits
              |
              v
        ATS  (Greenhouse / Lever / Workday / ...)
              |
              v
       applications-log.md  (status recorded)
```

## Generation pipeline

`python main.py` turns a resume YAML into a one-page PDF in two stages.

1. **YAML to LaTeX.** `resume/generator.py` reads the YAML schema (see below) and emits a `.tex` file. Tech terms are bolded with `\textbf{}` and ampersands in category names are escaped as `\&`. Date ranges use the word "to" (for example "Aug 2020 to May 2024").
2. **LaTeX to PDF.** The generator invokes `pdflatex` twice (two passes so cross references and layout settle), producing the final PDF under `applications/{Company}/`.

The cover letter follows the same shape through `coverletter/generator.py`.

### Resume YAML schema

Top level keys consumed by the generator:

- `personal`: `name`, `location`, `phone`, `email`, `website`, `linkedin`
- `summary`: a block scalar, with `\textbf{}` around key technologies
- `experience`: list of `{title, company, location, date, achievements: [...]}`
- `projects`: list of `{name, description, link}`
- `skills`: list of `{name, items}` (use `\&` in `name`)
- `education`: list of `{name, location, degree, GPA, date, courses}`
- `leadership`: list of `{name, description, date}`
- `awards`: list of `{title, issuer, date}`

## How Claude Code discovers the agents

- **Subagents** live in `.claude/agents/`. Each `*.md` file defines one subagent (its name, when to use it, and its tools). Claude Code loads them at startup, so the orchestrator can delegate to `profile-setup`, `job-scout`, `resume-builder`, or `application-submitter` without any extra wiring.
- **Project instructions** live in `CLAUDE.md` at the repo root. Claude Code reads it automatically and treats it as standing behavior rules for this project. `WORKFLOW.md` holds the longer per application playbook the agents reference.
- **MCP servers** (such as Playwright) are declared in the project MCP config and surface their tools to whichever subagent is allowed to use them, here the `application-submitter`.

## Where you customize things

- **Your facts:** edit `profile/about_candidate.yml`. This is the only place real history should live; the resume variants and tailored resumes derive from it.
- **Resume look and content:** start from `resume/resume_ml.yml` or `resume/resume_sw.yml`, or adjust `resume/generator.py` for layout, margins, and fonts.
- **Agent behavior:** edit the files in `.claude/agents/` to change how scouting, tailoring, or submitting works.
- **Global rules:** edit `CLAUDE.md` (always on rules) and `WORKFLOW.md` (the playbook).
- **Tracking:** the agents append to `applications-log.md`; you read it to see status at a glance.
