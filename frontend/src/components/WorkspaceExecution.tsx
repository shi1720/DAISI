import { ArrowUpRight, ChevronDown, ShieldCheck } from 'lucide-react';
import type { WorkspacePublication } from '../types';
import { day, money, number, percent, titleCase } from '../format';
import { Metric, Tag } from './UI';

export type RecordedScenario = {id?:string;scenario_id?:string;parameters:{date:string;budget:number};optimisation_summary?:{spent:number;total_meals:number;improvement_pct:number};summary?:{spent:number;total_meals:number;improvement_pct:number}};
export function ScenarioTable({scenarios,caption}:{scenarios:RecordedScenario[];caption:string}) {
  return <div className="table-scroll"><table><caption className="sr-only">{caption}</caption><thead><tr><th>Date</th><th>Budget</th><th>Planned meals</th><th>Spend</th><th>Objective uplift</th></tr></thead><tbody>{scenarios.map((scenario,index)=>{const summary=scenario.optimisation_summary??scenario.summary;return <tr key={scenario.id??scenario.scenario_id??index}><th scope="row">{day(scenario.parameters.date)}</th><td>{money(scenario.parameters.budget)}</td><td>{summary?number(summary.total_meals):'See record'}</td><td>{summary?money(summary.spent):'See record'}</td><td>{summary?percent(summary.improvement_pct):'See record'}</td></tr>;})}</tbody></table></div>;
}

export default function WorkspaceExecution({publication,evaluation}:{publication:WorkspacePublication;evaluation?:Record<string,unknown>|null}) {
  if(publication.pipeline_result!=='SUCCESS'||publication.mlflow_status!=='FINISHED')return null;
  const sources=publication.source_comparison??[];
  const reused=sources.filter(source=>source.reused_at);
  const geometryKeys=['planning_areas','subzones'];
  const checkedArchives=reused.filter(source=>geometryKeys.includes(source.source)&&source.matches_local_source===true);
  const liveTabular=publication.input_mode==='live' ? sources.filter(source=>!source.reused_at&&!geometryKeys.includes(source.source)).length : 0;
  const quality=publication.quality_checks??[];
  const passed=quality.filter(check=>check.passed===true||check.passed==='true').length;
  const scenarios=(evaluation?.results??[]) as RecordedScenario[];
  let runUrl:string|undefined;
  try {const url=new URL(publication.pipeline_run_url??'');if(url.protocol==='https:')runUrl=url.href;}catch{/* Missing proof URLs are displayed as IDs only. */}
  return <section className="panel publication-panel"><div className="panel-heading"><div><div className="eyebrow">EXECUTION EVIDENCE</div><h2>Verified Databricks publication</h2></div><Tag tone="green"><ShieldCheck size={13}/> Completed run</Tag></div><div className="section-padding publication-content">
    <p className="publication-intro">Databricks produced the data snapshot used by this app and recorded a completed MLflow evaluation. This record matches the active publication, source fingerprint and model code.</p>
    <div className="metrics-grid planner-metrics"><Metric label="Cloud evaluation scenarios" value={number(publication.scenarios_evaluated)} note="Recorded in Databricks and MLflow"/><Metric label="Published quality checks" value={`${number(passed)} / ${number(quality.length)}`} note="Passed in the recorded pipeline"/><Metric label="Source inputs" value={number(sources.length)} note={publication.input_mode==='live' ? `${number(sources.length-reused.length)} fetched live · ${number(reused.length)} archived` : 'Archived inputs with preserved provenance'}/></div>
    <p className="publication-source-note">{publication.input_mode==='live' ? `${number(liveTabular)} tabular sources were fetched during this run. ` : 'This publication used archived source files. '}{number(checkedArchives.length)} archived URA geometry files were reused with matching checksums. Archive reuse retains each file’s original fetch date.</p>
    <div className="publication-links">{runUrl&&<a href={runUrl} target="_blank" rel="noreferrer">Open Databricks pipeline run <ArrowUpRight size={15}/></a>}<span>Workspace access required for the run link</span></div>
    {scenarios.length>0&&<details className="method-details"><summary>View {scenarios.length} cloud evaluation scenarios <ChevronDown size={16}/></summary><p className="publication-protocol">Cloud budgets: {[...new Set(scenarios.map(s=>s.parameters.budget))].sort((a,b)=>a-b).map(money).join(', ')}. Objective uplift compares policy-weighted allocation against largest-demand-first. These scenarios measure computational behaviour; field outcomes still require a pilot.</p><ScenarioTable scenarios={scenarios} caption="Databricks cloud evaluation scenarios"/></details>}
    <details className="method-details"><summary>Publication identity & quality checks <ChevronDown size={16}/></summary><dl className="technical-record"><div><dt>Verified</dt><dd>{day(publication.verified_at,{day:'numeric',month:'long',year:'numeric'})}</dd></div><div><dt>Publication</dt><dd><code>{publication.publication_id}</code></dd></div><div><dt>Parent MLflow run</dt><dd><code>{publication.mlflow_run_id}</code></dd></div><div><dt>Source fingerprint</dt><dd><code>{publication.source_fingerprint}</code></dd></div><div><dt>Engine checksum</dt><dd><code>{publication.engine_code_sha256}</code></dd></div></dl><div className="table-scroll"><table><caption className="sr-only">Published data quality checks</caption><thead><tr><th>Check</th><th>Observed value</th><th>Result</th></tr></thead><tbody>{quality.map(check=><tr key={check.check_name}><th scope="row">{titleCase(check.check_name.replaceAll('_',' '))}</th><td>{check.observed_value}</td><td>{check.passed===true||check.passed==='true'?'Passed':'Review'}</td></tr>)}</tbody></table></div></details>
  </div></section>;
}
