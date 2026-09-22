import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, within } from '@testing-library/react';
import Evidence from './Evidence';
import type { WorkspacePublication } from '../types';

const publication:WorkspacePublication={input_mode:'live',pipeline_result:'SUCCESS',mlflow_status:'FINISHED',pipeline_run_url:'https://example.databricks.com/run/verified',publication_id:'publication-test',verified_at:'2026-09-22T06:00:00Z',source_fingerprint:'source-test',engine_code_sha256:'engine-test',mlflow_run_id:'parent-run-test',scenarios_evaluated:9,source_comparison:[...['closures','population','waste'].map(source=>({source,reused_at:null,matches_local_source:true})),...['planning_areas','subzones'].map(source=>({source,reused_at:'2026-09-22',matches_local_source:true}))],quality_checks:Array.from({length:12},(_,i)=>({check_name:`check_${i}`,passed:'true',observed_value:'1'}))};
const scenarios=Array.from({length:9},(_,i)=>({scenario_id:`scenario-${i}`,parameters:{date:'2026-09-22',budget:[600,1500,3000][i%3]},summary:{spent:600,total_meals:75,improvement_pct:7.5}}));
function respond(extra:Record<string,unknown>){vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({manifest:{population_year:2020,sources:[]},methodology:{version:'test'},evaluation_status:'current',...extra}),{status:200})));}
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
describe('execution provenance boundaries',()=>{
  it('distinguishes verified cloud execution from the separate local regression benchmark',async()=>{
    respond({workspace_execution:publication,cloud_evaluation:{results:scenarios},evaluation_execution:'local',evaluation:{summary:{unique_runs:15,all_feasible:true,primary_improvement_pct_min:.3,primary_improvement_pct_max:9.2},scenarios}});
    render(<Evidence/>);
    await screen.findByRole('heading',{name:'Verified Databricks publication'});
    expect(screen.getByText('Local regression runs')).toBeInTheDocument();
    expect(screen.getByText('15',{selector:'.metric-value'})).toBeInTheDocument();
    expect(screen.getByText('9',{selector:'.metric-value'})).toBeInTheDocument();
    expect(screen.getByText(/3 tabular sources were fetched/)).toHaveTextContent('2 archived URA geometry files');
    expect(screen.getByRole('link',{name:'Open Databricks pipeline run'})).toHaveAttribute('href',publication.pipeline_run_url);
    expect(screen.getByText('parent-run-test')).toBeInTheDocument();
    const table=screen.getByRole('table',{name:'Databricks cloud evaluation scenarios',hidden:true});
    expect(within(table).getAllByRole('row',{hidden:true})).toHaveLength(10);
  });
  it('renders results-shaped workspace evaluations instead of an empty scenario record',async()=>{
    respond({workspace_execution:null,evaluation_execution:'databricks',evaluation:{results:scenarios}});
    render(<Evidence/>);await screen.findByText(/This evaluation ran in Databricks/);
    expect(screen.queryByRole('heading',{name:'Verified Databricks publication'})).not.toBeInTheDocument();
    expect(within(screen.getByRole('table',{name:'Primary allocation benchmark scenarios',hidden:true})).getAllByRole('row',{hidden:true})).toHaveLength(10);
  });
  it('does not show a completed-publication claim for failed execution evidence',async()=>{
    respond({workspace_execution:{...publication,pipeline_result:'FAILED'},evaluation_status:'stale'});
    render(<Evidence/>);await screen.findByText(/The stored benchmark does not match/);
    expect(screen.queryByRole('heading',{name:'Verified Databricks publication'})).not.toBeInTheDocument();
  });
});
