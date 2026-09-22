# HawkerBridge: start here

**Project owner and presenter: Shivam Gupta**  
**DAISI Singapore 2026, C3: KopilamAI**

HawkerBridge helps a community coordinator prepare for a scheduled hawker-centre closure. Its distinguishing decision is concrete: compare cleaning dates and allocate a reviewable meal-support proposal under budget and capacity limits. On the demonstration date, doubling the budget from S$3,000 to S$6,000 adds no meals because three localities at 150 meals each already reach capacity.

The local handoff includes a [submission-materials ZIP](output/HawkerBridge-submission-pack.zip), which also contains the separate [source-code ZIP](output/HawkerBridge-source.zip). Both contain SHA256 manifests. The source archive includes the data snapshot, tests and deployment code; it installs and runs independently of the private GitHub repository. ZIPs are generated locally rather than checked into GitHub. To regenerate both archives from the current checkout and committed source, run `uv run python scripts/build_submission_pack.py`.

## Try the product

[Open the running local app](http://127.0.0.1:8000) and choose **Explore as a guest**. If the app is stopped, follow the three commands in [README.md](README.md). Set **28 September 2026**, **All Singapore**, **800 m access**. In the planner compare budgets **1,500**, **3,000** and **6,000**. Expected proposals: **225 / 450 / 450 planned meals**. Save a proposal, review the assumptions and export it.

[Product screenshots](docs/screenshots/README.md) come from the executed browser journey, with recorded checksums and the GitHub Actions run. They are not interface mockups.

## Round 1 entry

Use the **[official three-slide concept PDF](output/pdf/hawkerbridge-round1.pdf)**. An [editable PowerPoint](output/presentations/hawkerbridge-round1.pptx) and [supplementary one-page concept note](output/pdf/hawkerbridge-concept-note.pdf) are also supplied.

The official guide gives the deadline as **6 October 2026, 11:59 PM Singapore time**. The entry still needs your institution, course, year, submission email and confirmation of current Singapore IHL enrolment. Fill [team.json](submission/team.json), then run:

```sh
uv run python scripts/check_submission.py --round 1
```

No eligibility or personal academic details have been invented, and no entry has been submitted on your behalf yet.

## Round 2 materials

- [Nine-slide pitch PDF](output/pdf/hawkerbridge-final-pitch.pdf) and [editable PowerPoint](output/presentations/hawkerbridge-final-pitch.pptx).
- [Actual silent product walkthrough](output/video/hawkerbridge-demo-silent.mp4), with [recording provenance](output/video/provenance.json) and [scene timings](output/video/recording-timeline.json). Add your voiceover using the recording guide below.
- [Word-for-word narration and storyboard](submission/video-script.md), [printable narration](output/pdf/hawkerbridge-video-narration.pdf), [editable captions](submission/hawkerbridge-captions.srt) and [video finishing instructions](submission/recording-guide.md).
- [Devpost description](submission/devpost-description.md), [judge questions](submission/judge-qa.md) and [what comes next](submission/whats-next.md).
- [Example exported plan](output/pdf/example-continuity-plan.pdf), with [CSV](output/example-continuity-plan.csv) and [JSON including preserved provenance](output/example-continuity-plan.json).
- [Commercial case](docs/business-case.md), including an operator pilot, pricing hypotheses and cost sensitivity. No customers, measured impact or revenue are claimed.

## Deployment and submission gates

The local application is working and tested. The Databricks source includes the actual serverless pipeline, governed tables, MLflow evaluations, durable application store and native AI/BI dashboard definition. **A cloud deployment is complete only after the workspace run and hosted app are verified.** Current evidence lives in [deployment-status.json](submission/deployment-status.json); code and local tests do not substitute for a cloud run.

The [completed verification run](https://github.com/shi1720/DAISI/actions/runs/35691832262) passed backend and frontend checks plus all four functional browser journeys, including expanded-state accessibility checks. The separately captured walkthrough has its own recording provenance. A clean installation from the source ZIP also created and exported the expected 225-meal proposal with all five source records preserved.

The [Databricks deployment runbook](docs/databricks-deployment.md) covers authentication and verification. The official CLI requires workspace authorization before it can deploy. Never paste a token into a chat, notebook, source file or commit.

The supplied video narration accurately describes the recorded execution mode. Finish the actual voiceover and public/unlisted upload, record the real video URL, then run the Round 2 checker. It deliberately rejects missing cloud evidence, video links or participant details.

These are planning calculations based on public area data and explicit assumptions. They do not count people fed, identify vulnerable individuals or confirm operational venues. Field validation and a paid production environment remain prerequisites for a commercial service.
