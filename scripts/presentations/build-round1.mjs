import fs from 'node:fs/promises';
import crypto from 'node:crypto';
import {execFileSync} from 'node:child_process';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const runtime=process.env.CODEX_PRESENTATION_RUNTIME || '/Users/shivamgupta/.cache/codex-runtimes/codex-primary-runtime/dependencies';
const skill=process.env.PRESENTATIONS_SKILL_DIR || '/Users/shivamgupta/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations';
process.env.RUNTIME_NODE_MODULES=path.join(runtime,'node/node_modules');
const python=process.env.RUNTIME_PYTHON || path.join(runtime,'python/bin/python3');
const {FileBlob,PresentationFile}=await import(pathToFileURL(path.join(runtime,'node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs')).href);
const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
await fs.mkdir(root+'/tmp/presentation',{recursive:true});
await fs.mkdir(root+'/output/presentations',{recursive:true});
await fs.mkdir(root+'/output/qa',{recursive:true});
const revision=Date.now();
const source=root+'/research/official/round1-template.pptx';
const p=await PresentationFile.importPptx(await FileBlob.load(source));
const bodies=[
`Team name: HawkerBridge     Project owner: Shivam Gupta
Problem statement: C3 - KopilamAI: hawker culture and food access

The problem: A closure notice does not tell a community coordinator which
neighbourhoods need temporary meal support, or how to use a limited budget.

Who is affected: Residents who rely on nearby hawker food, especially seniors.
On 28 September, 17 listed centres with 1,025 food stalls have scheduled closures.
These are infrastructure counts, not measured hungry residents.

Why now: Cleaning and renovation closures are known ahead of time. Town councils
can compare cleaning dates and prepare support before a neighbourhood loses access.`,
`The solution: A closure continuity desk that compares dates and proposes a budgeted,
reviewable meal-support plan for neighbourhoods flagged by an access model.

The user: A town council planner or community meal coordinator chooses a date,
planning area and budget, checks alternatives, then exports a plan for human review.

Data from data.gov.sg: NEA closure dates, centre locations and stall counts (2026).
SingStat Census 2020 population by subzone and age, joined to URA 2019 boundaries.
NEA annual food-waste data supplies national context only, never local demand labels.

What differs: Counterfactual cleaning-date comparisons and constrained allocation,
with explicit costs, capacity, source provenance and uncertainty. Every allocation has an explicit objective and a comparison baseline.`,
`Working platform: Public APIs / Lakeflow Job / Bronze raw Delta / Silver validated
closures and population / Gold access model and allocation / Databricks Apps.
Unity Catalog governs tables. MLflow records the optimiser's baseline comparisons.

Demo: hawkerbridge-sg.web.app offers private plans and PDF export. A live Databricks
job passed 12 quality gates and recorded 9 MLflow scenarios, with a SQL dashboard.

Impact to test: Fewer coordinator hours per closure and fewer residents reporting
lost meal access. Pilot targets: reduce planning time by 30% and verify every proposed site.
A funded pilot and organisation subscription are commercial hypotheses, not sales.

Next sprint: Validate locations with a coordinator, measure planning time and
repeat use, then test a paid pilot. Current prices and impact targets are hypotheses.`
];
const anchors=['sh/65g3298r','sh/a10jqpsj','sh/3ah8rqlg'];
const notes=[
'Sources: NEA Dates of Hawker Centre Closures, https://data.gov.sg/datasets/d_bda4baa634dd1cc7a6c7cad5f19e2d68/view . Counts recomputed from the 22 Sep 2026 snapshot for 28 Sep 2026. No claim of food insecurity is inferred. Town council scheduling role: https://www.nea.gov.sg/our-services/hawker-management/announcements . Team institution/course/year/email are required separately before submission.',
'Sources: NEA closure dataset d_bda4baa634dd1cc7a6c7cad5f19e2d68; Census 2020 age and subzone population d_d95ae740c0f8961a0b10435836660ce0; URA planning areas d_4765db0e87b9c86336792efe8a1f7a66 and subzones d_8594ae9ff96d0c708bc2af633048edfb; NEA waste d_daf568968ab40dc81e7b08887a83c8fa. All data.gov.sg. Spatial model uses geographic representative points, not population centroids or walking routes. Closure discovery already exists in myENV and public products; the differentiation is coordinator planning.',
'A real Databricks live run published governed tables after 12 quality checks and 9 MLflow scenarios. Three tabular sources were fetched live; two checksum-verified URA archives retained their original timestamps. See submission/deployment-status.json and data/processed/databricks-publication.json. The separate local robustness benchmark has 15 scenarios. Free Edition is for non-commercial learning/prototyping: https://daisi.online/guide and https://docs.databricks.com/aws/en/getting-started/free-edition-limitations . Pilot targets and pricing are unvalidated. AI-assisted development is disclosed in the repository; project owner and presenter is Shivam Gupta.'
];
for(let i=0;i<3;i++){
 const sh=p.resolve(anchors[i]); const groups=bodies[i].split('\n\n'); if(i===0){const first=groups.shift().split('\n'); groups.unshift(...first);} sh.text=groups.map(group=>{const str=group.replaceAll('\n',' ');const idx=str.indexOf(':');return {runs:[{run:str.slice(0,idx+1),textStyle:{fontSize:'16pt',typeface:'Arial',color:'#132731',bold:true}},{run:str.slice(idx+1),textStyle:{fontSize:'16pt',typeface:'Arial',color:'#526773'}}],spaceAfter:1400,spaceBefore:0};});
 sh.text.style={typeface:'Arial',fontSize:21.3333,color:'#526773',autoFit:'none',lineSpacing:1.16};
 sh.position={left:76.8,top:201.6,width:1132.8,height:425.6};
 p.slides.getItem(i).speakerNotes.textFrame.setText(notes[i]);
}
const candidate=root+'/tmp/presentation/round1-candidate.pptx';
await(await PresentationFile.exportPptx(p)).save(candidate);
execFileSync(root+'/.venv/bin/python',[root+'/scripts/preserve_presentation_template.py',source,candidate]);
const sha=crypto.createHash('sha256').update(await fs.readFile(source)).digest('hex');
await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath:root+`/output/presentations/hawkerbridge-round1-${revision}.pptx`,
 explicitTotalSlideCount:3,sourceTemplatePath:source,requiredTemplateReferenceSlides:[1,2,3],minimumTemplateCoverageRatio:1,requireExactTemplateDimensions:true,
 pythonExecutable:python,
 integrityValidatorPath:skill+'/container_tools/inspect_presentation_package_integrity.py',
 layoutValidatorPath:skill+'/container_tools/inspect_presentation_layout_geometry.py',
 layoutArgs:['--expected-slide-size-emu','12191695,6858000','--validate-heading-fit'],
 fontPolicy:{basis:'reference',families:['Arial'],referencePath:source,referenceSha256:sha},
 verifyArtifactToolImport:true,receiptPath:root+`/tmp/presentation/round1-${revision}.validation.json`});
for(let i=0;i<3;i++){
 const blob=await p.slides.getItem(i).export({format:'png',scale:1.25});
 await fs.writeFile(root+`/output/qa/round1-slide-${i+1}.png`,new Uint8Array(await blob.arrayBuffer()));
}
console.log('Round 1 deck exported and validated.');
