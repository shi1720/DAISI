# HawkerBridge: a commercial hypothesis to test

Research and assumptions dated 22 September 2026. There are no claimed customers, stakeholder interviews, partnerships, pilot outcomes or revenue. This case explains what would have to be true for a useful planning tool to become a sustainable business.

## Buyer and job

The first buyer hypothesis is an estate operator or funded community organisation coordinating multiple sites. The job is to prepare a defensible response to a scheduled hawker-centre closure: establish what changes, prioritise verification, compare a support budget and leave a record a colleague can review. Residents should not pay for essential assistance information, and small hawkers should not have to finance the coordination layer.

[NEA states](https://www.nea.gov.sg/our-services/hawker-management/announcements) that town councils conduct cleaning and repairs for HDB-owned centres while NEA handles MSE-owned centres. That provides a concrete process to investigate, not proof of a software budget. A closure planner and a funded meal operator may be different organisations; the first pilot must identify the accountable owner of each action.

Existing alternatives include NEA/myENV notices, closure-calendar services such as SGMakan, nearby-food searches, and a coordinator's spreadsheet or phone calls. A calendar may be entirely sufficient when disruption is minor. HawkerBridge adds a dated comparison, explicit cost/capacity choices and a saved proposal. It should win only where those extra decisions recur and matter.

## Value and defensibility

The plausible benefit is reduced preparation time and a more complete handover, not an unmeasured reduction in hunger. The September 28 example gives a concrete planning insight: with three localities limited to 150 meals each, both S$3,000 and S$6,000 produce a 450-meal proposal costing S$2,700. Verifying more capacity matters before requesting more money for that arrangement. These inputs remain assumptions until an operator validates them.

Neither public data nor mixed-integer optimisation is a moat. Verified capacities, source corrections, permissioned operational feedback and integrations could support a durable product after repeated use. We should not collect personal beneficiary information merely to create proprietary data. The initial Singapore hawker-closure niche is limited; there is no credible large-market claim without evidence of a broader recurring workflow.

## Pricing and cost assumptions

Proposed experiment: **S$1,000 for one scoped closure-planning pilot**, creditable against a **S$250–500 monthly organisation subscription**. Define included sites, onboarding, support and report scope before any pilot. These are willingness-to-pay questions, not prices validated by a customer. Meal provision and venue costs belong in the operator's separate intervention budget; they are not subscription revenue or software margins.

At S$300 per month and an assumed fully loaded staff cost of S$30/hour, ten hours saved per month covers the subscription alone. Onboarding, verification and staff training increase that threshold. Both the hourly rate and time saving require evidence. A rare closure may support a project fee rather than a recurring contract.

There is **no required paid LLM or other per-request AI API** in the current product. That does not make operating the service free. Production cost includes hosting and databases, monitoring, backups, security maintenance, source changes, support, procurement, and founder time. [Databricks Free Edition](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations) is noncommercial, has usage limits and carries no SLA; it cannot be the hosting assumption for a paid customer service. Use a paid workspace and measure its workload, or explicitly assess another paid deployment architecture. Do not promise enterprise reliability based on a locally fast solve.

The table is arithmetic sensitivity, **not vendor quotations, forecast revenue or an estimated Databricks bill**. Hosting values are hypothetical monthly budget allowances that must be replaced by measured or quoted costs. Support uses an assumed S$30/hour opportunity cost, including founder-delivered work.

| Illustrative case | Organisations | Price / month each | Support hours / organisation | Hosting allowance / month | Revenue / month | Support opportunity cost | Contribution after only these two costs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Slow start, high support | 5 | S$250 | 5 | S$600 | S$1,250 | S$750 | **−S$100** |
| Repeatable workflow | 10 | S$350 | 2 | S$300 | S$3,500 | S$600 | **S$2,600** |
| Higher cost at the same scale | 10 | S$350 | 5 | S$1,500 | S$3,500 | S$1,500 | **S$500** |

Calculation: organisations × price − organisations × support hours × S$30 − hosting. This contribution is before product development, sales, acquisition, administration, taxes, insurance and any other cost; it is not profit. An actual infrastructure bill above the assumed allowance lowers it dollar for dollar. At the middle price and scale, each additional support hour per organisation costs another S$300/month. The downside case already fails before these omitted costs.

For the proposed S$1,000 pilot, twenty hours of founder/coordinator work at S$30/hour consume S$600 before travel, hosting and other work. Forty hours consume S$1,200 and make the pilot uneconomic before those additional costs. Record time from the first engagement rather than describing uncompensated founder labour as free. A one-time pilot can be a learning investment; repeated loss-making delivery is not a sustainable subscription.

The default S$4 meal input is also unverified for temporary collection. [AIC lists Meals on Wheels from S$4 before subsidies](https://www.aic.sg/Care-Services/Meals-on-Wheels); its eligibility and operating model differ. Obtain an operator quote including setup, staff, dietary needs, delivery and safe handling before making a real intervention budget.

## Pilot and decision gates

Begin with three non-leading coordinator interviews and one consented observation of an existing closure-planning task. Establish its frequency, accountable buyer, staff time and existing alternatives before offering software. The [interview guide](../submission/buyer-interview-guide.md) is prepared; no outreach has been performed.

Then propose a four-to-six-week engagement with one willing operator and one actual scheduled closure. Agree on a common task checklist and a baseline process. Record preparation minutes, factual omissions, corrections, venue verification, support minutes, actual uptake if an authorised service operates, and who would approve repeat spending. Avoid collecting beneficiary identities or recording sensitive case notes in plans. A before/after comparison with one operator is a small operational study, not causal proof of welfare benefit.

Proposed go/no-go targets: at least 30% less preparation time with no increase in critical omissions; every operational venue and cost checked before use; and a repeat paid-use commitment that covers measured paid hosting and support. All are targets, none are achieved results. Field rejection of an apparently attractive recommendation is useful evidence, not something to remove from the report.

Narrow, reprice or stop if closures create too little recurring work, existing tools are adequate, proxy outputs cannot survive verification, or willingness to pay falls below the fully loaded cost. Expand to other neighbourhood disruptions only after repeat use demonstrates that the same decision process transfers. A careful, small service business would be a legitimate outcome; the hackathon does not establish a venture-scale market.
