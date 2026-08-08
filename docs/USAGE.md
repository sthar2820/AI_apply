# Day to Day Usage

This guide shows the everyday loop for using the job application agent. The examples use a sample profile so you can see the shape of each request. Replace the persona details with your own in `profile/about_candidate.yml`.

> Sample persona used throughout: Jane Doe, jane.doe@example.com, +1-555-0100, San Francisco, CA. Example University, BS Computer Science, GPA 3.9/4.0, May 2024. Target roles: entry-level / new-grad Software Engineer, ML Engineer, Full-Stack.

## The basic loop

A typical session walks through six steps:

1. **Scout** open roles that match your profile.
2. **Pick and tailor** a resume for one job.
3. **Generate** the resume and cover letter PDFs.
4. **Verify** the output looks right.
5. **Apply** by opening the application and filling the form.
6. **Log** the application so you do not apply twice.

You drive each step by asking Claude in natural language.

## Example prompts

### 1. Scout jobs

> Find 5 entry-level full-stack roles posted in the last 7 days that match my profile.

You can narrow it however you like, for example by location, stack, or company stage:

> Find new-grad Software Engineer roles in San Francisco or remote, Python or TypeScript, posted this week.

### 2. Tailor the resume

> Tailor my resume for this job description: <paste the JD text or the job URL>.

Claude reads the job description, maps it against your profile, and rewrites the summary, skills, and bullets to fit.

### 3. Generate the PDFs

> Generate the resume and cover letter PDFs for Example Corp, Software Engineer.

Under the hood this runs the local pipeline (`python main.py`). No browser is involved in this step.

### 4. Verify the output

> Check the generated PDF is one page and the summary is 2 lines.

Always open and read the PDF yourself too. The agent can check page count and layout, but you are the final reviewer of the wording.

### 5. Apply

> Open this Greenhouse application and fill it from my profile, then pause before submitting.

Claude opens the page in the browser (via the Playwright MCP), reads the form, and fills each field. Tell it to pause before the submit button so you can review.

### 6. Log it

> Log this application to applications-log.md as submitted.

Keeping the log current is what prevents duplicate applications to the same role.

## How subagents work

The repo ships four specialized subagents:

- **profile-setup** interviews you on first run and writes `profile/about_candidate.yml`. Say `Set me up` to trigger it.
- **job-scout** finds roles that match your profile.
- **resume-builder** tailors and generates your resume and cover letter.
- **application-submitter** opens the ATS page and fills the form using the Playwright MCP.

You do not have to invoke these by hand. When you ask Claude to "find roles" or "fill this application," it delegates to the right subagent automatically. If you want to be explicit, you can name one directly, for example:

> Use the job-scout agent to find 5 ML Engineer roles posted in the last 3 days.

> Have the application-submitter open this Lever form and fill it from my profile.

## Safety and review habits

Make these part of every session:

- **Always read the resume PDF** before you send it. Check the wording, dates, and that nothing was overstated.
- **Always review form fields** before submit. Ask the agent to show you the filled form.
- **Solve CAPTCHAs yourself.** When a CAPTCHA appears, the agent will pause and hand it to you.
- **Provide OTP codes yourself.** If a site sends a one time passcode, you enter it.
- **Confirm before submit.** Nothing gets submitted without your explicit go ahead.

The browser acts as you, so treat every submit the way you would treat clicking the button yourself.

## Customizing targets and filters

Two files control what the agent looks for and how it works:

- **`profile/about_candidate.yml`** holds your persona: contact details, education, skills, projects, and the target roles you want. Edit this to change who the agent applies as and what kinds of jobs it should match.
- **`WORKFLOW.md`** describes your scout sources, search filters (freshness window, seniority caps, location, stack keywords), and your review and apply rules. Edit this to tune where roles come from and which ones get filtered out before they reach you.

Update both as your search evolves, for example to add a new target role, drop a source, or tighten the posted-within window.
