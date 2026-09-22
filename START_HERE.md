# HawkerBridge: start here

**Project owner: Shivam Gupta**

**DAISI Singapore 2026, C3: KopilamAI**

HawkerBridge helps a community coordinator prepare for a scheduled hawker-centre closure. Compare cleaning dates, identify areas to investigate, and allocate a reviewable meal-support proposal under budget and capacity limits. In the demonstration, doubling the budget from S$3,000 to S$6,000 adds no meals because three localities at 150 meals each already reach capacity.

[Watch the narrated demo](https://youtu.be/vioVop-MEVA), with timed English captions.

## Try the product

Open **[hawkerbridge-sg.web.app](https://hawkerbridge-sg.web.app)** and choose **Explore as a guest**. Set **28 September 2026**, **All Singapore**, **800 m access**. In the planner compare budgets **1,500**, **3,000** and **6,000**. Expected proposals: **225 / 450 / 450 planned meals**. Save a draft, inspect its review checklist and export PDF, CSV or JSON. [Full testing instructions](submission/testing-instructions.md).

A named email/password account retains access across visits. Firebase Authentication manages identity; Firestore preserves private plans across deployments. Each guest has an isolated workspace, limited to seven days and deleted on guest logout. Account settings allow deletion. Guest plans do not transfer to a named account.

[Product screenshots](docs/screenshots/README.md) come from actual browser journeys, with checksums and capture provenance. They are not interface mockups.

## What ran on Databricks

The real serverless pipeline successfully published governed Bronze, Silver and Gold tables, passed **12 quality checks**, and recorded **nine cloud scenario comparisons in MLflow**. The native Databricks App and AI/BI dashboard use this publication. The public Firebase app serves an explicitly verified export of the same data for judges without workspace access.

Three tabular sources were fetched live; two checksummed URA geometry archives were reused. The separate local robustness benchmark contains **15 scenarios**. Its dates and budget grid differ from the nine cloud scenarios. [Workspace evidence](data/processed/databricks-publication.json), [evaluation protocol](docs/evaluation.md) and [deployment status](submission/deployment-status.json) preserve the distinction.

## Submission materials

- **Round 1:** [official three-slide concept PDF](output/pdf/hawkerbridge-round1.pdf), [editable PowerPoint](output/presentations/hawkerbridge-round1.pptx) and [one-page concept note](output/pdf/hawkerbridge-concept-note.pdf).
- **Round 2:** [nine-slide pitch PDF](output/pdf/hawkerbridge-final-pitch.pdf) and [editable PowerPoint](output/presentations/hawkerbridge-final-pitch.pptx).
- **Demo:** [narrated hosted walkthrough](output/video/hawkerbridge-demo-narrated.mp4), [verbatim script](submission/video-script.md), [printable narration](output/pdf/hawkerbridge-video-narration.pdf), [captions](submission/hawkerbridge-captions.srt) and [recording provenance guide](submission/recording-guide.md). The generic synthetic narrator is disclosed.
- **Submission copy:** [Devpost story](submission/devpost-description.md), [YouTube title and description](submission/youtube-metadata.md), [judge Q&A](submission/judge-qa.md) and [what comes next](submission/whats-next.md).
- **Example output:** [exported plan PDF](output/pdf/example-continuity-plan.pdf), [CSV](output/example-continuity-plan.csv) and [JSON with preserved provenance](output/example-continuity-plan.json).
- **Commercial case:** [operator pilot, pricing hypotheses and cost sensitivity](docs/business-case.md). No customers, measured impact or revenue are claimed.

The [submission ZIP](https://github.com/shi1720/DAISI/releases/download/daisi-2026/HawkerBridge-submission-pack.zip) includes a separate [source ZIP](https://github.com/shi1720/DAISI/releases/download/daisi-2026/HawkerBridge-source.zip). Both have verified SHA256 manifests. The source installs independently of GitHub. ZIPs are generated locally from committed source with `uv run python scripts/build_submission_pack.py`.

## Reproduce and deploy

Follow [README.md](README.md) for the three-command local installation and test suite. No OpenAI key is needed for the application. The [Databricks runbook](docs/databricks-deployment.md) covers its governed pipeline and workspace app; the [Firebase runbook](docs/firebase-deployment.md) covers public releases, persistence checks, retention and rollback.

The GitHub Actions workflow runs backend, frontend and real Chromium journeys. Its manual `base_url` option tests the public Firebase site; `record_demo=true` captures the actual hosted walkthrough. Current verification links and fingerprints belong in [deployment-status.json](submission/deployment-status.json), rather than being inferred from a successful build.

## Participant and submission gates

Devpost confirmed **[Project submitted](https://devpost.com/software/hawkerbridge)** on 22 September 2026 after Shivam's explicit authorisation. It remains editable before the deadline. Submission does not establish student eligibility.

The official guide gives the Round 1 deadline as **6 October 2026, 11:59 PM Singapore time**. Shivam supplied Computer Science as his course. The organiser contact is saved privately in Devpost. Current Singapore IHL, year of study, enrolment and any additional teammates still require confirmation. Fill [team.json](submission/team.json), then run `uv run python scripts/check_submission.py --round 1`. Round 2 additionally checks the verified cloud execution and real video URL.

These are planning calculations based on public area data and explicit assumptions. They do not count people fed, identify vulnerable individuals or confirm venues. Field validation and a suitable paid production environment remain prerequisites for a commercial service.
