# Three-minute demo: HawkerBridge

The script below is ready to read word for word. It uses the current verified **local** build. Its cloud-status sentence is intentional: no successful workspace execution is presently recorded in `submission/deployment-status.json`. Use the optional replacement only after the real cloud evidence exists.

Record at about 125–135 words per minute, with brief pauses for the three result changes. Aim for 2:45–2:55 overall; never exceed 3:00. The speaking text is separated from screen directions. Do not read the headings, timing or instructions aloud. Record real interactions; a cut between screens is fine, but never present a loading state or fabricated result as a completed operation.

## Prepare the screen

Start the app using the repository instructions. Sign in or select **Explore as a guest**. Set scope to **All Singapore**, **Analysis date** to **2026-09-28**, and **800 m access**. Use a desktop browser at 1440 × 1000 or wider and 100% zoom. Close unrelated tabs and hide personal identifiers.

In **Continuity planner**, use **Assumed meal uptake** 5%, **Maximum collection localities** 3 and **Cost per meal** S$4. Expand **Cost, capacity & priority settings** and set **Setup cost per locality** S$300, **Meal capacity per locality** 150, **Senior priority weight** 2×. Retain all published closures; do not remove any in the cleaning counterfactual. Return to **Overview** for the opening frame. These exact settings reproduce the figures below.

## Narration and storyboard

**0:00–0:22 · Overview.** Keep the product name and map visible; move the pointer to the analysis date. No stock footage or invented resident testimonial is needed.

> A familiar hawker centre closes for repairs. The notice gives a date. A community coordinator still has to decide where support is needed, and what the available budget can actually achieve.
>
> I’m Shivam Gupta. This is HawkerBridge: a closure continuity desk for Singapore.

**0:22–0:52 · Overview metrics.** Show the selected date, 17 scheduled closures, 91,180 newly exposed residents and 17,120 aged 65+. Briefly point to the proximity and Census caveat on screen.

> Let’s examine September twenty-eighth. Seventeen centres have scheduled closures. At an eight-hundred-metre threshold, six subzones lose nearby hawker coverage at their representative points.
>
> Those areas contain about ninety-one thousand Census twenty-twenty residents. That is an exposure screen, not a count of people going hungry. Coffee shops, walking barriers and individual needs still require verification.

**0:52–1:22 · Continuity planner.** Show the assumption fields. Set **Daily support budget** to **1500**, then click **Generate support proposal**. Show the result's 225 planned meals and two localities.

> Now we turn the map into a proposal. I’ll assume five-percent participation, four dollars per meal, three hundred dollars to set up a collection locality, and a hundred and fifty meals of capacity at each locality.
>
> With fifteen hundred dollars, the planner allocates two hundred and twenty-five meals across two proposed localities. These locations and capacities are assumptions to check with an operator.

**1:22–1:54 · Compare capacity.** Manually enter **3000**, click **Generate support proposal**, then enter **6000** and regenerate. Pause on the 450-meal result and S$2,700 cost. Do not rely on a result left stale after editing an input.

> At three thousand dollars, we reach four hundred and fifty meals. Double the budget to six thousand, and the number stays the same. Three localities times a hundred and fifty meals is the ceiling. The proposal spends twenty-seven hundred dollars.
>
> That is the decision: verify more capacity before requesting more funding for this arrangement.

**1:54–2:09 · Save and export.** Click **Save proposal**, title it **28 September — capacity review**, add **Draft; verify operators, venues, uptake and costs.**, then **Save draft**. Open it in **Saved plans** and use **Export PDF**. Show the exported document, with its assumptions and draft status visible. Cut between the saved plan and its actual downloaded PDF if necessary.

> Save the proposal, inspect its assumptions, and export the brief for review. Nothing here books a venue or dispatches food.

**2:09–2:55 · Evidence & methods.** Show source years, unresolved-date quality findings and benchmark evidence. End on the product with a small readable “Local execution verified · Databricks workspace execution pending” recording caption.

> Behind the interface, the pipeline archives official source data, quarantines ambiguous dates and preserves the last good snapshot. The optimiser checks budget, reach and capacity against a simple baseline.
>
> The inventory includes a hundred and twenty-three centres. Three markets have no listed food stalls, so they remain visible in the inventory but do not count toward nearby meal access.
>
> This demonstration runs locally. Databricks deployment code is included; workspace execution is still awaiting verification.
>
> Our next test is a paid operator pilot: measure planning time, verify the proposed localities, and learn whether the support is useful. HawkerBridge makes that decision visible, testable and reviewable.

## Optional replacement after verified cloud execution

Replace only “This demonstration runs locally. Databricks deployment code is included; workspace execution is still awaiting verification.” with the following **if and only if the recording is of the running Databricks App and the relevant successful run and MLflow links have been captured**:

> This demonstration runs in Databricks. Here are the successful pipeline run, governed tables and MLflow evaluation behind the application.

Show those actual workspace pages for approximately ten seconds. If the successful run used the checksummed archived input mode, add **“This run uses our dated, archived public-data snapshot.”** Do not say “live ingestion” in that case. Shorten the opening pause if needed to keep the video below three minutes. If cloud execution is still pending, the main script is the complete, honest fallback; retain its status caption and mention the limitation in the submission.

## Recording checks

- Keep the same date, geographic scope and assumptions for all three budget runs. Expected results: 225 / 450 / 450 planned meals, costing S$1,500 / S$2,700 / S$2,700.
- Re-run against the final committed snapshot before recording. If the published source changes, update the script and screenshots together; never freeze a claim to preserve a nicer result.
- Speak “planned meals,” not “people fed.” Say “Census twenty-twenty,” not “today's population.” The smaller optimisation improvement on this date is acceptable: the useful story is capacity.
- A recording does not need to show personal email, workspace identifiers, tokens or passwords. The public/unlisted upload and human voiceover remain recording steps, not completed artifacts.
