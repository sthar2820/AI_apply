# Demo: an end-to-end run

This is an illustrative walkthrough of a single session, from a blank checkout to a
reviewed application, using the demo candidate **Jane Doe**
(`jane.doe@example.com`, San Francisco, CA). Every value here is dummy data.

The format below is an annotated transcript. Lines prefixed `You:` are what you
type, and lines prefixed `Agent:` are a realistic, shortened version of what Claude
replies. Between each prompt and reply is a short note on what actually happens:
which subagent runs and which files it reads or writes.

One thing to keep in mind throughout: **you stay in control.** The agent drafts,
scouts, tailors, and fills forms, but it pauses for you to review and confirm before
anything is submitted on your behalf.

---

## Stage 1: First run and onboarding

You start Claude Code in the repo and ask it to get you going.

```
You: Set me up
```

On the first turn, `CLAUDE.md` tells the agent to check
`profile/about_candidate.yml`. It still holds the placeholder persona
(`Jane Doe` / `jane.doe@example.com` / employer `Example Corp`), so the agent does
not generate anything yet. It launches the **profile-setup** subagent, which
interviews you and writes your real facts back into `profile/about_candidate.yml`.

```
Agent: Your profile is still the starter template, so let me learn about you
first before I generate anything. I have a few questions.

1. What is your full name, email, phone, and city?
2. Where have you worked, and what did you build or ship in each role?
3. What are your strongest projects?
4. Which languages, frameworks, and tools do you use most?
5. What is your education?
6. Are you authorized to work in the US, and do you need visa sponsorship?

We can do this in one pass or a few. Answer what you can and I will follow up.
```

You answer the questions in plain language. The profile-setup agent turns your
answers into structured YAML and confirms the result.

```
You: Jane Doe, jane.doe@example.com, +1-555-0100, San Francisco. Software
Engineer at Example Corp since Jan 2024 building FastAPI services on Postgres
and AWS. SWE intern at Sample Labs summer 2023, did Docker and Kubernetes
migration work. Strong with Python, TypeScript, React, FastAPI, PostgreSQL.
BS in Computer Science from Example University. Authorized to work in the US,
no sponsorship needed.
```

```
Agent: Saved. I wrote your details to profile/about_candidate.yml. Here is the
summary I will treat as your source of truth:

- Name: Jane Doe, San Francisco, CA
- Now: Software Engineer at Example Corp (Jan 2024 to present)
- Before: SWE Intern at Sample Labs (Summer 2023)
- Core skills: Python, TypeScript, React, FastAPI, PostgreSQL, AWS, Docker
- Education: BS Computer Science, Example University
- Work authorization: authorized in the US, no sponsorship required

From now on I will never claim anything that is not in this file. Want me to
generate a quick resume to confirm the pipeline works?
```

---

## Stage 2: Generate a first resume to confirm the pipeline

Before scouting or applying, the agent runs the local document pipeline once to make
sure LaTeX renders cleanly on this machine.

```
You: Yes, run a test resume.
```

The agent runs `main.py` with a throwaway company and role, which reads
`resume/resume.yml` and renders a PDF into `applications/Example Corp/`. It does not
open a browser for this; the document pipeline is fully local. It then reads the
generated PDF back to confirm it is a single page.

```bash
python main.py --company "Example Corp" --role "Software Engineer" --type resume
```

```
Agent: Pipeline works. I ran:

  python main.py --company "Example Corp" --role "Software Engineer" --type resume

Output: applications/Example Corp/Jane_Doe_Resume.pdf
I read the PDF back and it is exactly one page, so the LaTeX toolchain is set up
correctly. Next, if you want me to fill application forms, we need the Playwright
browser tools installed. Want the steps?
```

---

## Stage 3: Install the Playwright MCP

Scouting gated boards and filling ATS forms needs a real browser. The agent points
you at the setup doc and gives you the one-line install command.

```
You: Yes, set up the browser tools.
```

The agent references `docs/PLAYWRIGHT_MCP.md` and gives you the command to register
the official Playwright MCP server. The document pipeline from Stage 2 did not need
this; the browser is only for the scout and submit phases.

```
Agent: Full details are in docs/PLAYWRIGHT_MCP.md. From the repo directory, run:

  claude mcp add playwright -- npx @playwright/mcp@latest

Then verify it loaded with:

  claude mcp list

You should see "playwright" in the list. On first use it may download a browser
once. After that I will have browser tools (browser_navigate, browser_snapshot,
browser_click, browser_type, browser_file_upload, and similar). Tell me when it
shows up and I will scout some roles.
```

---

## Stage 4: Scout jobs

With the profile filled and the browser ready, you ask for fresh roles.

```
You: Find me 5 backend roles posted this week.
```

The agent launches the **job-scout** subagent. It reads `profile/about_candidate.yml`
to understand fit (Python, FastAPI, PostgreSQL, AWS, new-grad to early-career), and
searches across boards. It returns a short ranked table rather than dumping raw
listings, and it does not apply to anything on its own.

```
Agent: Here are 5 backend roles posted in the last 7 days, ranked by fit to your
profile.

| # | Company           | Role                    | Location           | Posted | Fit  |
| - | ----------------- | ----------------------- | ------------------ | ------ | ---- |
| 1 | Northwind Systems | Backend Engineer        | San Francisco (Hybrid) | 2d | High |
| 2 | Globex            | Backend Engineer, Data  | Austin, TX (Remote)| 3d     | High |
| 3 | Initech           | Platform Engineer       | Seattle, WA        | 4d     | Med  |
| 4 | Hooli             | Software Engineer, API  | Remote (US)        | 5d     | Med  |
| 5 | Stark Cloud       | Backend Engineer, Infra | San Francisco, CA  | 6d     | Med  |

Northwind is the closest match: Python, FastAPI, PostgreSQL, REST and GraphQL,
microservices on AWS, and it is entry to early career. Want me to tailor your
resume to one of these?
```

---

## Stage 5: Tailor a resume

You pick the top match.

```
You: Tailor my resume for the Northwind Systems Backend Engineer role.
```

The agent launches the **resume-builder** subagent. It reads the job description and
`profile/about_candidate.yml`, then edits `resume/resume.yml` into a one-page subset
that mirrors the JD's keywords, pulling only facts that exist in the profile. It runs
the local pipeline to render the PDF and reads it back to confirm a single page. The
output is the same shape as the worked sample in `examples/northwind-backend/`
(its `job_description.md`, `resume.yml`, and `coverletter.yml`).

```bash
python main.py --company "Northwind Systems" --role "Backend Engineer" --type both
```

```
Agent: Tailored and rendered. I edited resume/resume.yml against the Northwind JD
and generated:

  applications/Northwind Systems/Jane_Doe_Resume.pdf  (one page, verified)
  applications/Northwind Systems/Jane_Doe_CoverLetter.pdf

Keywords I mirrored from the posting, each backed by a real fact in your profile:
FastAPI, PostgreSQL, REST and GraphQL API design, microservices, query
optimization, AWS, and CI/CD. The summary leads with backend services and APIs in
Python and FastAPI on PostgreSQL.

This matches the layout you can see in examples/northwind-backend/. Want me to fill
out the application form?
```

---

## Stage 6: Submit

You ask the agent to start the application.

```
You: Fill out the Northwind application.
```

The agent launches the **application-submitter** subagent. Using the Playwright MCP,
it opens the application URL, snapshots the form to see the fields, and fills name,
email, phone, location, links, and education from `profile/about_candidate.yml`. It
answers the work-authorization and sponsorship questions honestly from your profile
fields, and attaches the tailored PDF from Stage 5. Then it stops. It does **not**
press submit. It shows you the filled form and waits for your explicit confirmation.

```
Agent: I opened the Northwind Systems application (Greenhouse) and filled it from
your profile. Please review before I submit anything:

- Name: Jane Doe
- Email: jane.doe@example.com
- Phone: +1-555-0100
- Location: San Francisco, CA
- LinkedIn / GitHub: attached from profile
- Resume: Jane_Doe_Resume.pdf (the Northwind-tailored one)
- Authorized to work in the US: Yes
- Requires sponsorship: No

Everything looks consistent with your profile. I have NOT clicked submit. Reply
"submit" to send it, or tell me what to change. If a CAPTCHA or one-time code
appears, I will pause and hand it to you.
```

```
You: Looks good, submit.
```

```
Agent: Submitted. Northwind Systems confirmed receipt of the application.
```

---

## Stage 7: Track

After a confirmed submit, the agent records the application so you have a running
history.

The agent appends a row to `applications-log.md` (created from the
`applications-log.example.md` template the first time it is needed), using the same
columns and status legend.

```
Agent: Logged it to applications-log.md:

| Date       | Company           | Role             | ATS        | Location               | Status    |
| ---------- | ----------------- | ---------------- | ---------- | ---------------------- | --------- |
| 2025-01-08 | Northwind Systems | Backend Engineer | Greenhouse | San Francisco (Hybrid) | submitted |

That is the full loop: onboarded, scouted, tailored, reviewed, submitted, and
tracked. Want me to tailor and queue the next role from the scout list?
```

---

## Try it yourself

- Start with the project overview and first-run flow in `README.md`.
- Walk through installation and configuration in `docs/SETUP.md`.
- See more worked, tailored applications for Jane Doe in `examples/README.md` and the
  per-role folders under `examples/` (for instance `examples/northwind-backend/`).

The agent does the heavy lifting, but you review the resume, the form, and every
submit. Nothing goes out without your confirmation.
