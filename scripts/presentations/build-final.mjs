// Rebuild with the bundled Codex Node runtime. Set PPTX_REVISION for a new
// validated output filename, then promote the inspected result to the final path.
// Real CI screenshots belong in the assets directory. No mock screenshots.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { execFileSync } from 'node:child_process';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const runtime = process.env.CODEX_PRESENTATION_RUNTIME || '/Users/shivamgupta/.cache/codex-runtimes/codex-primary-runtime/dependencies';
const skill = process.env.CODEX_PRESENTATION_SKILL || '/Users/shivamgupta/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations';
process.env.RUNTIME_NODE_MODULES = path.join(runtime, 'node/node_modules');
const { Presentation, PresentationFile } = await import(pathToFileURL(path.join(runtime, 'node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs')).href);
const { finalizePresentation, applyPresentationChartFont } = await import(pathToFileURL(path.join(skill, 'container_tools/artifact_tool_utils.mjs')).href);
const assets = path.join(root, 'scripts/presentations/assets');
const build = path.join(root, 'tmp/final-pitch');
const revision = process.env.PPTX_REVISION || 'final';
const previewOnly = process.argv.includes('--preview-layout-only');
const final = path.join(root, `output/presentations/hawkerbridge-final-pitch${revision==='final'?'':'-'+revision}.pptx`);
await fs.mkdir(build, { recursive: true });
await fs.mkdir(path.dirname(final), { recursive: true });
const snapshot = JSON.parse(await fs.readFile(path.join(root, 'data/processed/snapshot.json')));
const evaluation = JSON.parse(await fs.readFile(path.join(root, 'data/processed/evaluation.json')));
const status = JSON.parse(await fs.readFile(path.join(root, 'submission/deployment-status.json')));
const sourceNotes = snapshot.manifest.sources.map(s => `${s.title}: ${s.url}`).join('\n');
const facts = evaluation.scenarios.find(s => s.id === '2026-09-28-sgd1500-r800').analysis_summary;
const cloud = status.databricks_workspace_execution_verified === true;
const readiness = cloud ? 'Workspace execution verified' : 'Workspace execution pending';
const primary = evaluation.protocol.primary_scenarios.map(id => evaluation.scenarios.find(s => s.id === id));
if (primary.length !== 9 || !primary.every(s => s.constraint_audit.feasible)) throw Error('Expected nine feasible primary benchmark scenarios');
const engineSha=crypto.createHash('sha256').update(await fs.readFile(path.join(root,'backend/hawkerbridge/engine.py'))).digest('hex');
if(evaluation.source_content_sha256!==snapshot.manifest.content_sha256 || engineSha!==evaluation.engine_code_sha256) throw Error('Evidence is stale. Re-run the model benchmark and review slide claims before building.');
if(facts.closed_centres!==17 || facts.food_stalls_closed!==1025 || facts.newly_exposed_residents!==91180) throw Error('September 28 evidence changed. Review screenshots, copy and narration before rebuilding.');
const p = Presentation.create({ slideSize: { width: 1280, height: 720 } });
const C = { cream:'#F7F6F0', ink:'#173D35', forest:'#123B36', muted:'#65756D', orange:'#C94C30', sage:'#AFC1A4', pale:'#E9EEE5', line:'#DADED2', white:'#FFFEFA' };
const font = 'Helvetica Neue';

function text(s, str, x, y, w, h, size=26, color=C.ink, bold=false) {
  const sh=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
  sh.text=str;
  sh.text.style={typeface:font,fontSize:size,color,bold,autoFit:'none',wrap:true,insets:{left:0,right:0,top:0,bottom:0}};
  return sh;
}
function slide(title, n, bg=C.cream) {
  const s=p.slides.add();s.background.fill=bg;
  if(title) text(s,title,60,48,1160,74,44,bg===C.forest?C.cream:C.ink,true);
  if(n>1) text(s,`${String(n).padStart(2,'0')}`,1172,664,45,22,15,bg===C.forest?C.sage:C.muted);
  return s;
}
function note(s, str){s.speakerNotes.textFrame.setText(str);}
function foot(s,str,dark=false){text(s,str,60,654,1076,42,15,dark?C.sage:C.muted);}
async function image(s,name,x,y,w,h,fit='contain',alt=''){
  let bytes;
  try { bytes=await fs.readFile(path.join(assets,name)); }
  catch(error) { if(previewOnly && error.code==='ENOENT') return; throw error; }
  s.images.add({blob:new Uint8Array(bytes),contentType:name.endsWith('.jpg')?'image/jpeg':'image/png',position:{left:x,top:y,width:w,height:h},fit,alt});
}
function table(s,values,x,y,w,h,widths,fsz=23){
 const tb=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:w,height:h,values,columnWidths:widths});
 tb.styleOptions={headerRow:false,bandedRows:false};
 tb.borders.assign({style:'solid',fill:C.line,width:.7});
 tb.cells.block({row:0,column:0,rowCount:values.length,columnCount:values[0].length}).assign({fill:C.cream,textStyle:{typeface:font,fontSize:fsz,color:C.ink},margins:{left:15,right:15,top:10,bottom:10},anchor:'center'});
 for(let c=0;c<values[0].length;c++){const cell=tb.getCell(0,c);cell.fill=C.forest;cell.text.style={typeface:font,fontSize:fsz,bold:true,color:C.cream};}
 return tb;
}

// 1. Real image as context only. It does not depict a closure or a pilot.
{
 const s=slide('',1,C.forest);
 text(s,'HawkerBridge',60,145,670,100,74,C.cream,true);
 text(s,'A closure continuity desk\nfor Singapore',63,268,580,122,38,C.cream);
 text(s,'Shivam Gupta\nDAISI Singapore 2026\nC3  KopilamAI',64,510,500,99,22,C.sage);
 await image(s,'tampines-hawker-centre.jpg',780,0,500,720,'cover','Tampines Round Market and Food Centre in February 2020. Context photograph, not a pilot site.');
 text(s,'Photo: Kagenlim, Tampines Round Market (2020), cropped\ncreativecommons.org/licenses/by-sa/4.0',64,656,670,43,14,C.sage);
 note(s,'Project owner: Shivam Gupta. No institution or student enrollment is implied. Context photograph only. Photo: Kagenlim, 12 February 2020, Tampines Round Market and Food Centre. Cropped for layout. https://commons.wikimedia.org/wiki/File:Hawker_Center,_Singapore.jpg . License: https://creativecommons.org/licenses/by-sa/4.0/ . Photo crop retains CC BY-SA 4.0. No endorsement by the photographer or depicted people. Product scope: https://daisi.online/guide .');
}
// 2. Infrastructure counts, then the demographic proxy with its limitation.
{
 const s=slide('A closure notice leaves a planning gap',2);
 text(s,'28 September 2026',60,141,1160,38,24,C.muted);
 text(s,String(facts.closed_centres),60,215,340,118,98,C.orange,true);
 text(s,'scheduled centre closures',65,337,360,65,26);
 text(s,facts.food_stalls_closed.toLocaleString('en-SG'),580,215,620,118,98,C.ink,true);
 text(s,'listed food stalls inside those centres',585,337,590,65,26);
 text(s,'A coordinator still needs to decide\nwhere temporary support is feasible.',65,445,1040,99,36,C.ink);
 foot(s,'Source: NEA schedule archived 22 Sep 2026. Stall counts describe infrastructure, not measured meal capacity.');
 note(s,`Verified snapshot counts for 2026-09-28: ${JSON.stringify(facts)}. Full data provenance: data/processed/snapshot.json. NEA source: ${snapshot.manifest.sources[0].url}. Published closures may change. Do not claim all stalls are normally open or that every customer needs assistance. NEA closure responsibilities: https://www.nea.gov.sg/our-services/hawker-management/announcements .`);
}
// 3. The screenshot is actual browser execution, never a reconstructed UI.
{
 const s=slide('The coordinator’s working view',3);
 await image(s,'overview.png',60,137,840,500,'contain','Actual HawkerBridge overview from an executed browser test.');
 text(s,'Test cleaning changes',946,160,270,74,28,C.ink,true);
 text(s,'Compare nearby\nhawker coverage\nbefore funding support.',946,255,275,110,26);
 text(s,'Inspect the assumptions',946,390,274,74,28,C.ink,true);
 text(s,'Census 2020\n800 m straight line\nSubzone points',946,487,275,110,25,C.muted);
 foot(s,'Actual local application. Cleaning-date changes are hypothetical. Area exposure is a screening proxy.');
 note(s,'Screenshot provenance is recorded in scripts/presentations/assets/README.md. Product code: frontend/src/App.tsx and backend/hawkerbridge/engine.py. This is the working application, not a design mockup. The cleaning counterfactual removes a chosen adjustable event from the selected day for comparison. It does not modify a published government closure schedule or choose an operationally valid replacement date. For the dated 28 Sep 2026 model at 800 m, six populated subzones contain 91,180 census residents and 17,120 seniors whose representative points lose listed hawker coverage. These are not observed hungry residents. The screen omits coffee shops, food courts, individual needs and accessible walking routes. '+sourceNotes);
}
// 4. Editable source inventory rather than an ornamental data pipeline graphic.
{
 const s=slide('Five public sources, visible uncertainty',4);
 table(s,[['Official source','Coverage','Role in the model'],['NEA closure calendar','2026, 123 centres','Dates, coordinates, stall counts'],['SingStat census','2020, 332 subzones','Resident and senior counts'],['URA planning areas','2019, 55 areas','Area scope and grouping'],['URA subzones','2019, 332 boundaries','Geographic joins and points'],['SingStat / NEA waste','2000–2025 national series','Context only']],60,150,1160,332,[330,315,515],23);
 text(s,String(snapshot.manifest.quality.resolved_closure_intervals),60,529,175,73,58,C.ink,true);
 text(s,'resolved closure intervals',230,549,375,42,24);
 text(s,String(snapshot.manifest.quality.quarantined_closure_intervals),710,529,140,73,58,C.orange,true);
 text(s,'quarantined date records',827,549,390,42,24);
 foot(s,'Archived raw responses and SHA-256 provenance. Failed refreshes retain the last good publication.');
 note(s,sourceNotes+'\nQuality: '+JSON.stringify(snapshot.manifest.quality)+'. Unknown dates and block-specific ambiguity are quarantined. Older repair dates remain in the archive but do not falsely imply current closure. 123 centres include three zero-food-stall markets excluded from meal-access distances. National food-waste statistics are not centre waste estimates. Singapore Open Data Licence: https://data.gov.sg/open-data-licence .');
}
// 5. Every architecture stage is editable text within a native table.
{
 const s=slide('Databricks architecture',5);
 table(s,[['Layer','Databricks component','What the run records'],['Ingestion','Serverless Lakeflow Job','Official responses and checksums'],['Bronze / Silver','Delta tables in Unity Catalog','Raw archive, typed rows, quarantine'],['Gold','Published snapshot and SQL views','Access model, allocations, audit'],['Evaluation','MLflow experiment','Parameters and baseline comparisons'],['Delivery','Databricks App + Firebase site','Same publication; private proposals']],60,150,1160,340,[220,400,540],23);
 text(s,readiness,60,527,1130,49,32,cloud?C.ink:C.orange,true);
 text(s,cloud?'12 quality gates. 9 cloud scenarios. Published data powers the public app.':'Local execution verified. Cloud run evidence remains the next gate.',60,586,1150,40,24,C.muted);
 foot(s,'A publication record exposes completed outputs. A failed run cannot silently replace the current snapshot.');
 note(s,'Implemented code: databricks/notebooks/01_pipeline.py, databricks.yml, resources/, backend/hawkerbridge/databricks_store.py and docs/databricks-deployment.md. Execution status at deck build: '+JSON.stringify(status)+'. Unity Catalog governance and explicit lineage records are implemented. Do not claim unverified automatic column lineage. Publication uses staging plus a final pointer record, not cross-table ACID. Archived replay is explicitly labeled if used. Cloud mode fails closed rather than silently displaying local data. Free Edition limitations: https://docs.databricks.com/aws/en/getting-started/free-edition-limitations .');
}
// 6. Nine complete benchmark rows expressed as a native editable grouped chart.
{
 const s=slide('Capacity limits the September 28 proposal',6);
 text(s,'Objective improvement over largest-demand-first',60,135,790,40,24,C.muted);
 const chart=s.charts.add('bar',{
  position:{left:44,top:184,width:760,height:375},categories:['22 Sep','28 Sep','14 Dec'],
  series:[1500,3000,6000].map((b,i)=>({name:`S$${b.toLocaleString('en-SG')}`,values:['2026-09-22','2026-09-28','2026-12-14'].map(d=>Number((primary.find(s=>s.parameters.date===d&&s.parameters.budget===b).summary.improvement_pct/100).toFixed(4))),fill:[C.sage,C.forest,C.orange][i],valuesFormatCode:'0.0%'})),
  barOptions:{direction:'column',grouping:'clustered',gapWidth:100},hasLegend:true,
  legend:{position:'bottom',overlay:false,textStyle:{typeface:font,fontSize:19,fill:C.ink}},
  xAxis:{textStyle:{typeface:font,fontSize:20,fill:C.ink},line:{fill:C.line,width:1},majorGridlines:null},
  yAxis:{min:0,max:.1,majorUnit:.05,numberFormatCode:'0%',textStyle:{typeface:font,fontSize:18,fill:C.muted},majorGridlines:{fill:C.line,width:1},line:{fill:'none',width:0}},
  dataLabels:{showValue:true,position:'outEnd',textStyle:{typeface:font,fontSize:17,fill:C.ink}},chartFill:C.cream,plotAreaFill:C.cream,chartLine:{fill:'none',width:0},plotAreaLine:{fill:'none',width:0}});
 applyPresentationChartFont(chart,{fontFamily:font});
 text(s,'450',878,171,337,109,84,C.orange,true);
 text(s,'planned meals at both\nS$3,000 and S$6,000',882,284,326,91,28,C.ink,true);
 text(s,'3 localities × 150 meals\nS$2,700 allocated\nMore capacity changes the ceiling.',882,409,323,126,25,C.muted);
 text(s,'15 / 15 unique scenarios passed an independent constraint audit',60,578,1160,44,27,C.ink,true);
 foot(s,'800 m, 5% uptake, S$4/meal, S$300 setup, 3 localities, 150 meals each, senior weight 2. Mixed-integer optimisation. Welfare outcomes remain unmeasured.');
 note(s,'Complete 9-row primary grid plus radius sensitivity totals 15 unique solves. Source: data/processed/evaluation.json and docs/evaluation.md. Benchmark input source SHA-256: '+evaluation.source_content_sha256+'. Primary data: '+JSON.stringify(primary.map(s=>({id:s.id,summary:s.summary})))+'. Optimisation and baseline use the same constraints and explicit senior policy. Optimality is within 0.1% configured MIP gap, not an absolute proof for every possible input. Scenario uplift is not the number of meals delivered or the number of additional people helped. Nine tiny test cases also compare MILP with exhaustive enumeration. The September 28 S$1,500 scenario plans 225 meals for S$1,500. S$3,000 and S$6,000 scenarios each plan 450 for S$2,700. No operator has verified these capacities.');
}
// 7. One actual saved proposal screenshot, with human operational controls.
{
 const s=slide('A proposal carries its assumptions into review',7);
 await image(s,'saved-plan.png',530,149,690,467,'contain','Actual saved plan detail in HawkerBridge showing the allocation and review workflow.');
 text(s,'Before any service runs',60,167,418,79,31,C.ink,true);
 text(s,'Confirm resident need\nand accessible routes.',60,272,410,89,28);
 text(s,'Verify the venue, operator,\nmeal cost and capacity.',60,386,410,89,28);
 text(s,'Save the decision record.\nExport PDF, CSV or JSON.',60,500,415,89,28);
 foot(s,'Browser-test proposal. A review flag does not book a venue, approve an agency service or dispatch meals.');
 note(s,'Screenshot provenance: scripts/presentations/assets/README.md and screenshots.json. Real executed browser-test workflow, 28 Sep 2026, S$1,500 budget, 225 planned meals. The automated test exercises the review checklist and PDF download. No real venue verification, operator review or delivery occurred. The application preserves source fingerprints and parameters in saved plans and exports. Owner filtering is application-enforced in the Databricks store. It is not a claim of database row-level tenant isolation against workspace administrators. Human review is an operational gate, not an automated authorisation. No personal beneficiary records are required by the product.');
}
// 8. Commercial hypotheses remain explicitly unvalidated.
{
 const s=slide('One operator pilot tests the business',8);
 text(s,'Buyer hypothesis',60,146,540,39,24,C.muted);
 text(s,'Estate operators and funded\ncommunity organisations',60,199,680,94,37,C.ink,true);
 text(s,'The paid job: prepare a reliable closure plan\nand reduce coordination time.',60,327,708,88,28);
 text(s,'S$1,000',852,157,360,73,58,C.orange,true);
 text(s,'scoped pilot',856,239,332,42,27);
 text(s,'S$250–500',852,330,365,62,47,C.ink,true);
 text(s,'monthly organisation\nsubscription hypothesis',856,409,334,79,26);
 text(s,'The data is public. Defensibility would come from verified capacity\nand a workflow operators choose to reuse.',60,510,1128,87,28,C.ink);
 foot(s,'No customers or willingness-to-pay validation yet. Commercial use needs paid hosting. The current product requires no LLM API.');
 note(s,'Price hypotheses and full sensitivity: docs/business-case.md. Proposed S$1,000 pilot creditable to S$250–500 subscription. These are not validated prices or revenue. Example downside: 5 organisations × S$250, 5 support hours each × assumed S$30/hour, S$600 assumed hosting = −S$100 before development and other costs. Hosting numbers are planning allowances, not Databricks quotes. Public sources are not proprietary advantage. Existing alternatives include NEA myENV, SGMakan closure dates and coordinator spreadsheets. NEA operating context: https://www.nea.gov.sg/our-services/hawker-management/announcements . Databricks Free Edition is noncommercial and has no SLA: https://docs.databricks.com/aws/en/getting-started/free-edition-limitations .');
}
// 9. A specific test rather than an unearned impact claim.
{
 const s=slide('The next test is an operator’s decision',9,C.forest);
 text(s,'1 operator\n1 scheduled closure\n4–6 weeks',60,180,566,246,53,C.cream,true);
 text(s,'Prospective pilot target',739,173,464,45,25,C.sage);
 text(s,'30%',738,236,472,111,87,C.cream,true);
 text(s,'less preparation time,\nwith no increase in critical omissions',742,368,440,109,29,C.cream);
 text(s,'Every venue verified before use.\nSupport time and repeat payment measured.',60,516,1152,93,29,C.cream);
 foot(s,'Targets remain unachieved. Shivam Gupta owns the project. github.com/shi1720/DAISI',true);
 note(s,'Prospective validation protocol: submission/whats-next.md, submission/buyer-interview-guide.md and docs/business-case.md. No stakeholder interview, actual pilot, commercial commitment or measured welfare outcome is claimed. At least three non-leading interviews and observation of an existing workflow should precede a funded engagement. Compare equal preparation tasks, record corrections, venue rejection, support hours and willingness to repeat a paid engagement. The small pilot cannot establish national causal impact. Platform prerequisite status: '+JSON.stringify(status)+'. Newer compatible demographics and real operator capacity are prioritised inputs. Project owner: Shivam Gupta. Confirm eligibility and full team details separately; the deck does not imply IHL enrollment.');
}

const candidate=path.join(build,`candidate-${revision}.pptx`);
await (await PresentationFile.exportPptx(p)).save(candidate);
for(let i=0;i<9;i++){
 const slide=p.slides.getItem(i);
 const png=await p.export({slide,format:'png',scale:1});
 await fs.writeFile(path.join(build,`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
 const layout=await slide.export({format:'layout'});
 await fs.writeFile(path.join(build,`slide-${String(i+1).padStart(2,'0')}.layout.json`),await layout.text());
}
if(previewOnly){console.log('Private layout preview only. No final deliverable produced.');process.exit(0);}
await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath:final,pythonExecutable:path.join(runtime,'python/bin/python3'),integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit','--require-native-table-slide','4','--require-native-table-slide','5'],explicitTotalSlideCount:9,requiredNativeTableOwnerSlides:[4,5],requiredNativeChartOwnerSlides:[6],materializeLiteralChartWorkbooks:true,fontPolicy:{basis:'design',families:[font]},verifyArtifactToolImport:true,receiptPath:path.join(build,`validation-${revision}.json`)});
const pdfDir=path.join(root,'output/pdf');await fs.mkdir(pdfDir,{recursive:true});
// Use the bundled LibreOffice only. Never substitute a user's desktop install.
// Its Fontconfig build needs explicit macOS font directories to preserve the
// chosen sans font. This private configuration does not change the runtime.
const fontConfig=path.join(build,'fonts.conf');
await fs.writeFile(fontConfig,`<?xml version="1.0"?><fontconfig><dir>/System/Library/Fonts</dir><dir>/System/Library/Fonts/Supplemental</dir><dir>${runtime}/native/libreoffice-headless/libreoffice/LibreOfficeDev.app/Contents/Resources/fonts/truetype</dir><cachedir>${build}/font-cache</cachedir></fontconfig>`);
execFileSync(path.join(runtime,'bin/override/soffice'),['-env:UserInstallation=file://'+path.join(build,'lo-profile-'+revision),'--headless','--convert-to','pdf','--outdir',pdfDir,final],{stdio:'inherit',env:{...process.env,FONTCONFIG_FILE:fontConfig}});
await fs.writeFile(path.join(build,`provenance-${revision}.json`),JSON.stringify({built_at:new Date().toISOString(),source_fingerprint:evaluation.source_fingerprint,source_content_sha256:evaluation.source_content_sha256,cloud_status:status,screenshots:['overview.png','saved-plan.png'],authoring_sha256:crypto.createHash('sha256').update(await fs.readFile(fileURLToPath(import.meta.url))).digest('hex')},null,2));
console.log(final);
