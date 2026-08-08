---
name: job-application-workflow
description: End-to-end, reusable job-application workflow for the Claude Code job agent. Covers finding roles, tailoring a resume and cover letter to LaTeX PDFs, verifying output, submitting through ATS forms, tracking, follow-up, and weekly review.
type: reference
---

# Job Application Workflow

A generalized, repeatable pipeline that turns Claude Code into a job-application
assistant. It finds roles, tailors a resume and cover letter, renders one-page
LaTeX PDFs through `main.py`, fills ATS forms through the Playwright MCP, and
keeps a running log.

All examples use the canonical demo persona. Replace it with your own profile in
`profile/about_candidate.yml` before running.

| Field | Value |
| --- | --- |
| Name | Jane Doe |
| Email | jane.doe@example.com |
| Phone | +1-555-0100 |
| Location | San Francisco, CA |
| Website | https://www.example.com |
| LinkedIn | https://linkedin.com/in/janedoe |
| GitHub | https://github.com/janedoe |
| Education | Example University, BS Computer Science, GPA 3.9/4.0, May 2024 |
| Target roles | Entry-level / new-grad Software Engineer, ML Engineer, Full-Stack Engineer |

The phases run in order, but you can re-enter any phase on its own (for example
re-render after editing YAML, or re-verify after a fix).

---

## Phase 1: Finding Jobs

### Sources

Pull from a broad set of channels so you are not dependent on any one board.

- **Hacker News "Who is Hiring"** monthly thread (one comment per company).
- **Company career pages** for any company already on your shortlist.
- **Y Combinator Work at a Startup** (workatastartup.com).
- **Wellfound** (formerly AngelList Talent).
- **LinkedIn Jobs** with role and location filters saved as alerts.
- **ATS boards directly**: Lever (`jobs.lever.co/{company}`), Greenhouse
  (`boards.greenhouse.io/{company}`), Ashby (`jobs.ashbyhq.com/{company}`).
  These expose clean JSON endpoints and are easy to scan in bulk.
- **New-grad GitHub trackers** (community-maintained lists of new-grad and
  internship postings).
- **Aggregators** such as Jobright and similar feeds. Treat aggregator metadata
  as a lead, not as truth: re-verify posted date, seniority, and sponsorship
  language at the source ATS before investing time.

### Filtering rules

Apply these gates in order and drop anything that fails:

1. **Role family.** Keep only roles that map to your configured target families
   (for the demo persona: Software Engineer, ML Engineer, Full-Stack Engineer).
2. **Seniority window.** Keep entry-level, junior, and new-grad roles. Enforce a
   configurable years-of-experience cap (default: 0 to 3 years). Skip Senior,
   Staff, Principal, and Lead titles regardless of the stated YoE floor. The YoE
   floor often lives in the JD body, not the title, so read the body before you
   keep or drop a role.
3. **Freshness.** Default to roles posted within the last 7 days. Widen to 14
   days only when the fresh pool is exhausted.
4. **Location preference.** Keep roles matching your configured location and
   remote preferences. Remote and relocation-friendly roles count.
5. **Dedupe.** Grep `applications-log.md` by company name and by req-id. Skip
   anything you have already applied to within your cooldown window. Different
   req-id at the same company is a fresh apply; the same req-id waits out the
   cooldown.

### Verify before investing

Open each candidate role URL and confirm it returns HTTP 200 and shows a live
posting. Dead links, expired reqs, and redirect-to-careers-home pages are common
in aggregator feeds. Verifying first saves you from tailoring against a role that
no longer exists.

---

## Phase 2: Tailoring the Resume

### Source of truth

`profile/about_candidate.yml` is the master record of everything true about the
candidate: every job, project, skill, and metric. It is never trimmed to fit a
single application.

`resume/resume.yml` is the **tailored subset** for one role. You build it by
selecting and reordering content from the profile, never by inventing new
content.

### Rules

- **Keyword-mirror the JD.** Pull the role's top skills and responsibilities and
  make sure the matching true items from the profile appear, using the JD's
  wording where it is honest to do so.
- **Summary is at most 2 lines** when rendered. Lead with role fit and the two
  or three strongest signals.
- **Every bullet has a metric.** Scope, scale, latency, throughput, user count,
  percentage, or count. If a true metric is not available, rewrite the bullet
  around one that is.
- **Never fabricate.** Every technology in the summary, skills, and bullets must
  trace back to `profile/about_candidate.yml`. No invented projects, employers,
  metrics, or product context.
- **Technology substitution is category-bound.** You may swap one tool for a
  near-equivalent only within the same category (for example one cloud provider
  for another, one frontend framework for another) and only if the candidate
  actually has that skill in the profile. Never substitute across categories and
  never add a skill the candidate does not have.
- **Company field is a bare name.** The `company:` YAML field holds the plain
  company name only, no parenthetical product descriptor; ATS parsers reject the
  extra text.

---

## Phase 3: Tailoring the Cover Letter

### Write one or skip

Write a cover letter when:

- The application form has a cover letter field (optional or required).
- The role is a high-priority target.
- The JD asks for one or asks a specific motivation question.

Skip it when the form has no field and the role is a routine apply; spend the
time on more applications instead.

### Structure (3 paragraphs)

1. **Hook.** Why this company and this role, with one concrete, specific reason
   tied to the team or product. No generic "I am excited to apply" opener.
2. **Evidence.** Two or three sentences mapping the candidate's real experience
   and metrics from the profile to the role's top requirements.
3. **Close.** A short, confident sign-off and a clear statement of interest in
   next steps.

### `coverletter/coverletter.yml` rules

- No em-dashes anywhere. Use periods, commas, or restructure the sentence.
- Standard business-letter format (date, greeting, body, closing, name).
- Use the company-name placeholder; the generator auto-replaces it with the
  company you pass at render time, so one template serves every application.
- Same source-of-truth discipline as the resume: every claim traces to
  `profile/about_candidate.yml`.

---

## Phase 4: Generating PDFs

Run the generator from the repo root:

```
python main.py --company "Company Name" --role "Role Title" --type both
```

The piped input answers the prompts in order: company name, role title, a blank
line, then the document selector.

| Selector | Output |
| --- | --- |
| `1` | Resume only |
| `2` | Cover letter only |
| `3` | Both |

### Output

PDFs are written to `applications/{Company}/`, named per document. One folder per
company keeps each application self-contained.

### Pipeline

For each document the generator runs: **YAML to LaTeX to pdflatex to PDF**.
`pdflatex` runs **two passes** so cross-references and layout settle. The PDF in
`applications/{Company}/` is the final artifact you verify and upload.

---

## Phase 5: Verification

Before any document leaves the repo, read the rendered PDF and confirm:

1. **Exactly one page.** Check the actual rendered page count, not the YAML
   length. Two pages is an automatic fail for entry-level resumes.
2. **Summary is 2 lines.** Check the rendered text, not the source; wrapping can
   push a 2-line summary to 3.
3. **No whitespace gap at the bottom.** Content should fill the page cleanly. A
   large trailing gap means too little content or bad sizing.
4. **Content matches the profile.** Spot-check that every employer, project,
   skill, and metric on the page exists in `profile/about_candidate.yml`.
5. **Top JD keywords present.** The role's most important skills appear somewhere
   on the page.

If any check fails, edit `resume/resume.yml` or `coverletter/coverletter.yml`,
re-run Phase 4, and re-verify. Do not submit an unverified PDF.

---

## Phase 6: Submitting

Always upload the **tailored PDF** from `applications/{Company}/`, not a generic
base resume.

Form-fill defaults (name, email, phone, location, links, work authorization)
come from the profile, so answers stay consistent across applications.

### ATS-specific tips (generic, may drift)

- **Ashby.** Clean, single-page forms. Resume upload often auto-parses fields;
  review the parsed values before submit.
- **Lever.** Straightforward. Resume upload plus a few short fields. Watch for an
  optional cover-letter and additional-information box.
- **Greenhouse.** If a third-party autofill blocks you, use the "Enter manually"
  / "Apply without" path and fill fields by hand.
- **Workday.** Multi-step and account-based. Expect a create-account step, a
  resume-parse step you must audit, and several pages. Verify the parsed work
  history matches your resume before advancing.

### Pause for the user

Always pause and hand control to the user for:

- **CAPTCHA** of any kind.
- **OTP / magic-link / email verification** steps.
- **The final submit button**, so the user reviews the complete application
  before it is sent.

### Work authorization and sponsorship

If you require work-authorization sponsorship, configure it in your profile and
the agent will answer the form questions honestly. Leave it unset and the agent
answers as needing no sponsorship. This is profile-driven and never hardcoded.

---

## Phase 7: Tracking

Append one row to `applications-log.md` for every application, immediately after
submit. Suggested fields:

```
| Date | Company | Role | Req-ID | ATS | Location | Status |
```

### Status categories

| Status | Meaning |
| --- | --- |
| `submitted` | Application sent and confirmed. |
| `pending` | Started but one user action away from done (CAPTCHA, OTP, final click). |
| `blocked` | Cannot complete (broken form, anti-bot wall, required info unavailable). |
| `interview` | Advanced to a screen or interview. |
| `rejected` | Declined by the company. |
| `closed` | Posting was taken down or filled before submit. |
| `skipped` | Intentionally not applied (failed a filter gate, dupe, no fit). |

The log is the dedupe source for Phase 1, so keep it current and grep it before
every new apply.

---

## Phase 8: Follow-up

Optional, light-touch, and only when it adds signal.

Within roughly 48 hours of applying, you may send one short, polite LinkedIn note
to a recruiter or hiring manager on the team. Keep it under about 300 characters,
specific, and free of pressure. Send at most one; do not chase.

Template (demo persona):

> Hi [Name], I just applied for the [Role] role at [Company] and wanted to flag
> my interest directly. I am a recent CS grad who builds full-stack and ML
> projects, and the team's work on [specific thing] stood out. Happy to share
> more if useful. Thanks, Jane Doe

Personalize the `[specific thing]` from the JD or the company's product. Do not
spray a templated message; if you cannot make it specific, skip it.

---

## Phase 9: Weekly Review

Once a week, step back from individual applies and look at the system.

- **Conversion.** Count interviews against submitted applications. A low ratio
  usually means a targeting or tailoring problem, not a volume problem.
- **Clean up pending.** Resolve every `pending` row: finish the CAPTCHA/OTP/submit
  or move it to `blocked` or `closed`. Pending rows that linger distort dedupe.
- **Refresh resume variants.** Update the role-family resume bases as you learn
  which bullets and keywords land. Roll any new true wins from the week into
  `profile/about_candidate.yml` first, then into the tailored subsets.
- **Note recurring blockers.** Track ATS platforms, sponsorship gates, or
  seniority drift that repeatedly cost time, and adjust Phase 1 filters so those
  roles get dropped earlier next week.
