# Worked Examples: One Profile, Eight Tailored Applications

These are complete demo outputs produced by the agent. Each folder is a full job application that the agent generated from a single source profile, [`../profile/about_candidate.yml`](../profile/about_candidate.yml), for the fictional candidate **Jane Doe**. The goal is to show the tailoring in action: how one set of facts becomes eight role specific resumes and cover letters.

Across every example, the underlying person never changes. Jane Doe has the same projects, the same employers, the same education, and the same true skills in all eight applications. What changes is emphasis, ordering, the summary line, and which keywords get mirrored back to the target job description. Nothing is invented. Each tailored document is a different lens on the same honest set of facts.

## The eight examples

| Folder | Company | Role | Tailoring leads with |
| --- | --- | --- | --- |
| `northwind-backend` | Northwind Systems | Backend Engineer | Python, FastAPI, PostgreSQL, REST and GraphQL APIs |
| `umbrella-frontend` | Umbrella Web | Frontend Engineer | React, Next.js, TypeScript, Tailwind CSS |
| `initech-fullstack` | Initech | Full Stack Engineer | React, FastAPI, Node.js, PostgreSQL |
| `vortex-ml` | Vortex AI | Machine Learning Engineer | Python, PyTorch, data pipelines, model training and evaluation |
| `globex-data` | Globex Data | Data Engineer | Python ETL, SQL, PostgreSQL data modeling, AWS |
| `hooli-platform` | Hooli | Platform Engineer | Docker, Kubernetes, Terraform, CI/CD on AWS |
| `stark-cloud` | Stark Industries | Cloud Engineer | AWS, Terraform, infrastructure as code, CI/CD |
| `wonka-newgrad` | Wonka Labs | Software Engineer (New Grad) | Full stack fundamentals across backend and frontend |

Read any two side by side and you can see the same person framed for a different audience. The backend example puts API design and PostgreSQL first, while the frontend example leads with React and component work, yet both draw from the identical Jane Doe history.

## What is in each folder

Each example folder contains the inputs and the rendered outputs for one application:

- **`job_description.md`** is the target job description the application was tailored against.
- **`resume.yml`** is the tailored resume source, ready to drop into `resume/resume.yml` and render.
- **`coverletter.yml`** is the tailored cover letter source, ready to drop into `coverletter/coverletter.yml` and render.
- **`resume.pdf`** is the rendered one page resume.
- **`coverletter.pdf`** is the rendered cover letter.

The two YAML files are the interesting part. They show exactly what the agent changed for each role. The PDFs are what those YAMLs produce when rendered through `main.py`.

## Reproduce these yourself

Every example is reproducible from the YAML sources. Copy an example's resume and cover letter into place, then render both. For instance, to rebuild the Northwind Systems backend application:

```bash
cp examples/northwind-backend/resume.yml resume/resume.yml
cp examples/northwind-backend/coverletter.yml coverletter/coverletter.yml
python main.py --company "Northwind Systems" --role "Backend Engineer" --type both
```

The rendered output lands in `applications/Northwind_Systems/`. Swap the folder name, company, and role to rebuild any of the other seven. For example, the Wonka Labs new grad application:

```bash
cp examples/wonka-newgrad/resume.yml resume/resume.yml
cp examples/wonka-newgrad/coverletter.yml coverletter/coverletter.yml
python main.py --company "Wonka Labs" --role "Software Engineer" --type both
```

That output lands in `applications/Wonka_Labs/`.

## Next steps

To point the agent at real postings and generate your own tailored applications, see [`../docs/USAGE.md`](../docs/USAGE.md) and [`../WORKFLOW.md`](../WORKFLOW.md).
