import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

let syntheticAccount:{email:string;password:string}|null=null;
test.beforeEach(()=>{syntheticAccount=null;});

async function checkAccessibility(page:Page,screen:string){
  const violations=(await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa']).analyze()).violations;
  console.log(`AXE_${screen}`,JSON.stringify(violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}))));
  expect.soft(violations.filter(v=>['serious','critical'].includes(v.impact??''))).toEqual([]);
}

async function guest(page: Page) {
  await page.goto('/');
  // The hosted identity, snapshot and first analysis requests can take longer
  // than Playwright's 5s visual-assertion default. Wait for the actual successful
  // analysis once, with a bounded allowance, rather than retrying the journey.
  const [initialAnalysis]=await Promise.all([
    page.waitForResponse(response=>response.url().endsWith('/api/analyse')&&response.request().method()==='POST',{timeout:process.env.HAWKERBRIDGE_BASE_URL?20000:10000}),
    page.getByRole('button',{name:'Explore as a guest'}).click(),
  ]);
  expect(initialAnalysis.ok(),`Initial access analysis returned HTTP ${initialAnalysis.status()}`).toBe(true);
  await expect(page.getByRole('button',{name:'Continuity planner',exact:true,includeHidden:true})).toBeAttached();
  await expect(page.locator('.metric-value').first()).toBeVisible();
  const date=page.getByLabel('Analysis date');
  if(await date.inputValue()!=='2026-09-28'){
    const refreshed=page.waitForResponse(response=>response.url().endsWith('/api/analyse')&&response.request().method()==='POST'&&response.request().postDataJSON().date==='2026-09-28');
    await date.fill('2026-09-28');
    expect((await refreshed).ok()).toBe(true);
  }
  await expect(page.locator('.context-line')).toContainText('28 September 2026');
  await expect(page.locator('.updating-pill')).toHaveCount(0);
}
async function screenshot(page:Page, name:string, fullPage=true){
  await page.evaluate(()=>document.fonts.ready);
  if(fullPage) await page.evaluate(()=>window.scrollTo({top:0,behavior:'instant'}));
  await page.locator('input:focus').evaluateAll(inputs=>inputs.forEach(input=>(input as HTMLInputElement).blur()));
  await page.screenshot({path:`../output/screenshots/${name}.png`,fullPage,animations:'disabled'});
}
async function heroScreenshot(page:Page,name:string){
  const viewport=page.viewportSize();
  await page.setViewportSize({width:1440,height:1000});
  await page.evaluate(()=>window.scrollTo({top:0,behavior:'instant'}));
  await screenshot(page,name,false);
  if(viewport)await page.setViewportSize(viewport);
}

// Hosted runs use synthetic identities only. Delete their private workspaces after
// every journey, including failures, while leaving real account data untouched.
test.afterEach(async({page,baseURL})=>{
  const response=await page.request.get('/api/auth/session');
  if(!response.ok())return;
  let session=await response.json();
  if(!session.user&&syntheticAccount){
    const login=await page.request.post('/api/auth/login',{data:syntheticAccount,headers:{Origin:baseURL!}});
    if(login.ok())session=await login.json();
  }
  if(!session.user)return;
  const headers={'X-CSRF-Token':session.csrf_token,Origin:baseURL!};
  if(session.user.mode==='guest'){
    expect((await page.request.post('/api/auth/logout',{headers,data:{}})).ok()).toBe(true);
  }else if(['local','firebase'].includes(session.user.mode)&&/^browser-.*@example\.test$/.test(session.user.email)){
    expect((await page.request.delete('/api/auth/account',{headers})).ok()).toBe(true);
  }
});

test('authenticated full journey, saved plan, review, exports and source evidence', async ({page})=>{
  const errors:string[]=[];
  page.on('pageerror',e=>errors.push(e.stack || e.message));
  await page.goto('/');
  await expect(page.getByRole('button',{name:'Explore as a guest',exact:true})).toBeVisible();
  await screenshot(page,'01-welcome');
  expect(await page.title()).not.toContain('\u2014');
  await checkAccessibility(page,'AUTH');
  await guest(page);
  await expect(page.locator('.metric-top').getByText('Residents in flagged subzones',{exact:true})).toBeVisible();
  await screenshot(page,'02-overview');
  await heroScreenshot(page,'02-overview-hero');
  await checkAccessibility(page,'OVERVIEW');
  await page.locator('.centre-marker.closed').first().click({timeout:10000});
  await expect(page.locator('.map-detail')).toContainText('Scheduled closure');
  await page.getByRole('button',{name:'Close map detail',exact:true}).click();
  const alternatives=await page.locator('.map-panel .centre-marker.open').count();
  await page.locator('.closure-row').first().click();
  await expect(page.locator('.map-area-chip')).toBeVisible();
  await expect(page.locator('.map-panel .centre-marker.open')).toHaveCount(alternatives);
  await page.getByRole('button',{name:'Show all of Singapore',exact:true}).click();
  // Exercise removal immediately after changing map bounds. Leaflet previously
  // left a zoom-transition timer running against the detached map pane.
  for(let cycle=0;cycle<3;cycle++){
    await page.locator('.closure-row').first().click();
    await page.getByRole('button',{name:'Show all of Singapore',exact:true}).click();
    await page.getByRole('button',{name:'Evidence & methods',exact:true}).click();
    await expect(page.getByRole('heading',{name:'A clear line from data to decision.',exact:true})).toBeVisible();
    await page.getByRole('button',{name:'Overview',exact:true}).click();
    await expect(page.locator('.map-panel .centre-marker.closed').first()).toBeVisible();
  }
  await page.getByRole('button',{name:'Continuity planner',exact:true}).click();
  await page.getByRole('button',{name:/What if cleaning moved/}).click();
  await page.getByRole('checkbox',{name:/Bedok Reservoir Road Blk\s*630/i}).check();
  await expect(page.locator('.scenario-comparison')).toContainText('54,030');
  await checkAccessibility(page,'SCHEDULE_COMPARISON');
  await page.getByRole('button',{name:/Reset scenario/}).click();
  await page.getByRole('button',{name:/What if cleaning moved/}).click();
  await page.getByRole('button',{name:'Cost, capacity & priority settings'}).click();
  await expect(page.getByLabel('Setup cost per locality')).toHaveValue('300');
  expect(await page.locator('form.assumptions-form').evaluate((f:HTMLFormElement)=>f.checkValidity())).toBe(true);
  await page.getByRole('button',{name:'Cost, capacity & priority settings'}).click();
  await page.getByRole('button',{name:'Generate support proposal'}).click();
  await expect(page.locator('.planner-result')).toContainText('225');
  await screenshot(page,'03-continuity-planner');
  await heroScreenshot(page,'03-continuity-planner-hero');
  await checkAccessibility(page,'PLANNER');
  await page.getByRole('button',{name:'Evidence & methods',exact:true}).click();
  await expect(page.getByRole('heading',{name:'A clear line from data to decision.',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Continuity planner',exact:true}).click();
  await expect(page.locator('.proposal-banner')).toContainText('225');
  await expect(page.getByLabel('Daily support budget')).toHaveValue('1500');
  await page.getByLabel('Daily support budget').fill('6000');
  await page.getByRole('button',{name:'Generate support proposal'}).click();
  await expect(page.locator('.planner-result')).toContainText('450');
  await screenshot(page,'03b-capacity-450');
  await heroScreenshot(page,'03b-capacity-450-hero');
  await page.getByLabel('Daily support budget').fill('1500');
  await page.getByRole('button',{name:'Generate support proposal'}).click();
  await expect(page.locator('.planner-result')).toContainText('225');
  await page.getByRole('button',{name:'Save proposal',exact:true}).click();
  await page.getByLabel('Plan title',{exact:true}).fill('28 September community continuity');
  await page.getByLabel(/Coordination notes/).fill('Verify accessible venues and confirm actual meal demand with local coordinators.');
  await page.getByRole('button',{name:'Save draft',exact:true}).click();
  await expect(page.getByRole('heading',{name:'28 September community continuity',exact:true})).toBeVisible();
  // Simulate another authenticated tab updating this plan after our screen loaded.
  const session=await(await page.request.get('/api/auth/session')).json();
  const saved=(await(await page.request.get('/api/plans')).json()).plans[0];
  const changed=await page.request.patch(`/api/plans/${saved.id}`,{headers:{Origin:new URL(page.url()).origin,'X-CSRF-Token':session.csrf_token},data:{notes:'A newer operational note from another session.',expected_updated_at:saved.updated_at}});
  expect(changed.ok()).toBe(true);
  await page.getByRole('button',{name:'Edit details',exact:true}).click();
  const editor=page.getByRole('dialog');
  await editor.getByLabel('Coordination notes').fill('My unsaved planning notes.');
  await editor.getByRole('button',{name:'Save changes',exact:true}).click();
  await expect(editor.getByRole('button',{name:'Load latest and compare',exact:true})).toBeVisible();
  await expect(editor.getByLabel('Coordination notes')).toHaveValue('My unsaved planning notes.');
  await expect(editor.getByRole('button',{name:'Save changes',exact:true})).toBeDisabled();
  await editor.getByRole('button',{name:'Load latest and compare',exact:true}).click();
  await expect(editor.getByText('A newer operational note from another session.',{exact:true})).toBeVisible();
  await editor.getByLabel('Coordination notes').fill('Merged notes: verify accessible venues and confirm actual meal demand with local coordinators.');
  await editor.getByRole('button',{name:'Save changes',exact:true}).click();
  await expect(editor).toHaveCount(0);
  await page.getByRole('button',{name:'Mark as reviewed',exact:true}).click();
  for (const box of await page.getByRole('dialog').getByRole('checkbox').all()) await box.check();
  await page.getByRole('button',{name:'Mark reviewed',exact:true}).click();
  await expect(page.getByText('Reviewed planning proposal',{exact:true})).toBeVisible();
  const downloadPromise=page.waitForEvent('download');
  await page.getByRole('button',{name:'Export PDF',exact:true}).click();
  const download=await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/\.pdf$/);
  await download.saveAs('../output/screenshots/browser-exported-plan.pdf');
  await page.getByRole('button',{name:'Prepare brief',exact:true}).click();
  await expect(page.locator('.brief-copy')).toContainText('225');
  await screenshot(page,'04-saved-plan');
  await page.getByRole('button',{name:'Evidence & methods',exact:true}).click();
  await expect(page.getByRole('heading',{name:'A clear line from data to decision.',exact:true})).toBeVisible();
  await expect(page.locator('.evidence-hero').getByText('2020',{exact:true})).toBeVisible();
  await screenshot(page,'05-evidence');
  if(process.env.HAWKERBRIDGE_BASE_URL){
    const record=await(await page.request.get('/api/evidence')).json();
    expect(record.evaluation_status).toBe('current');
    expect(record.workspace_execution?.pipeline_result).toBe('SUCCESS');
    expect(record.workspace_execution?.scenarios_evaluated).toBe(9);
    expect(record.cloud_evaluation?.results).toHaveLength(9);
    expect(record.evaluation_execution).toBe('local');
    expect(record.evaluation?.summary.unique_runs).toBe(15);
    await expect(page.getByRole('heading',{name:'Verified Databricks publication',exact:true})).toBeVisible();
    await expect(page.locator('.publication-panel .metric-value')).toHaveText(['9','12 / 12','5']);
    await expect(page.locator('.benchmark-panel .metric-value').first()).toHaveText('15');
    await expect(page.locator('.toast')).toHaveCount(0);
    await page.locator('.publication-panel').scrollIntoViewIfNeeded();
    await screenshot(page,'05b-databricks-publication',false);
  }
  await checkAccessibility(page,'EVIDENCE');
  expect(errors).toEqual([]);
});

test('fresh account keeps plans private and supports sign in',async({page})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Create an account',exact:true}).click();
  await page.getByLabel('Full name',{exact:true}).fill('Browser test planner');
  const email=`browser-${Date.now()}@example.test`;
  syntheticAccount={email,password:'A-long-test-password-2026'};
  await page.getByLabel('Email address',{exact:true}).fill(email);
  await page.getByLabel('Password',{exact:true}).fill('A-long-test-password-2026');
  await page.getByRole('button',{name:'Create account',exact:true}).click();
  await expect(page.getByRole('button',{name:'Saved plans',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Saved plans',exact:true}).click();
  await expect(page.getByText('Your next good idea belongs here.',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Sign out',exact:true}).click();
  await page.getByLabel('Email address',{exact:true}).fill(email);
  await page.getByLabel('Password',{exact:true}).fill('A-long-test-password-2026');
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await expect(page.getByRole('button',{name:'Continuity planner',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Account settings',exact:true}).click();
  await checkAccessibility(page,'ACCOUNT_SETTINGS');
  await page.getByRole('button',{name:'Delete account',exact:true}).click();
  await page.getByRole('button',{name:'Delete account and plans',exact:true}).click();
  await expect(page.getByRole('button',{name:'Sign in',exact:true})).toBeVisible();
  syntheticAccount=null;
});

test('planning-area scope, cleaning counterfactual and zero-budget state',async({page})=>{
  await guest(page);
  await page.getByLabel('Planning area scope',{exact:true}).selectOption('Clementi');
  await page.waitForLoadState('networkidle');
  await page.getByRole('button',{name:'Continuity planner',exact:true}).click();
  await expect(page.locator('.planner-date-summary')).toContainText('Clementi');
  await page.getByRole('button',{name:/What if cleaning moved/}).click();
  const checks=page.locator('.closure-checkbox input');
  if(await checks.count()){
    await checks.first().check();
    await expect(page.getByText('What-if scenario',{exact:true})).toBeVisible();
    await page.getByRole('button',{name:/Reset scenario/}).click();
  }
  await page.getByLabel('Daily support budget').fill('0');
  await page.getByRole('button',{name:'Generate support proposal'}).click();
  await expect(page.locator('.planner-result')).toContainText(/No|zero|0/);
  await screenshot(page,'06-local-planning');
});

test('mobile navigation and accessible layout',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await guest(page);
  await screenshot(page,'07-mobile-overview');
  console.log('MOBILE_OVERVIEW_OVERFLOW',JSON.stringify(await page.evaluate(()=>Array.from(document.querySelectorAll('body *')).filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&r.right>innerWidth+1&&getComputedStyle(e).position!=='absolute';}).slice(0,25).map(e=>({tag:e.tagName,class:e.className,width:e.getBoundingClientRect().width,right:e.getBoundingClientRect().right})))));
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(391);
  await expect(page.getByRole('navigation',{name:'Main navigation'})).toHaveCount(0);
  await page.getByRole('button',{name:'Open navigation',exact:true}).click();
  await expect(page.getByRole('button',{name:'Overview',exact:true})).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('button',{name:'Open navigation',exact:true})).toBeFocused();
  await page.getByRole('button',{name:'Open navigation',exact:true}).click();
  await page.getByRole('button',{name:'Continuity planner',exact:true}).click();
  await page.getByRole('button',{name:'Generate support proposal'}).click();
  await expect(page.locator('.planner-result')).toContainText('225');
  await screenshot(page,'08-mobile-planner');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(391);
  await page.setViewportSize({width:320,height:720});
  await expect(page.getByLabel('Planning area scope')).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(321);
  expect(await page.locator('.budget-presets').evaluate(container=>{
    const bounds=container.getBoundingClientRect();
    return Array.from(container.children).every(button=>{
      const rect=button.getBoundingClientRect();
      return rect.left>=bounds.left-1&&rect.right<=bounds.right+1;
    });
  })).toBe(true);
  await screenshot(page,'09-small-mobile-planner');
});
