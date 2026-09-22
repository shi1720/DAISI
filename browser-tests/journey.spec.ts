import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

async function guest(page: Page) {
  await page.goto('/');
  await page.getByRole('button',{name:'Explore as a guest'}).click();
  await expect(page.getByRole('button',{name:'Continuity planner',exact:true})).toBeVisible();
  await expect(page.locator('.metric-value').first()).toBeVisible();
  await page.getByLabel('Analysis date').fill('2026-09-28');
  await expect(page.locator('.updating-pill')).toHaveCount(0);
  await page.waitForLoadState('networkidle');
}
async function screenshot(page:Page, name:string, fullPage=true){
  await page.evaluate(()=>document.fonts.ready);
  await page.screenshot({path:`../output/screenshots/${name}.png`,fullPage,animations:'disabled'});
}

test('authenticated full journey, saved plan, review, exports and source evidence', async ({page})=>{
  const errors:string[]=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/');
  await screenshot(page,'01-welcome');
  await guest(page);
  await expect(page.getByText('Residents in flagged subzones',{exact:true})).toBeVisible();
  await screenshot(page,'02-overview');
  const violations=(await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa']).analyze()).violations;
  expect(violations.filter(v=>['serious','critical'].includes(v.impact??''))).toEqual([]);
  await page.getByRole('button',{name:'Continuity planner',exact:true}).click();
  await page.getByRole('button',{name:'Cost, capacity & priority settings'}).click();
  await expect(page.getByLabel('Setup cost per locality')).toHaveValue('300');
  expect(await page.locator('form.assumptions-form').evaluate((f:HTMLFormElement)=>f.checkValidity())).toBe(true);
  await page.getByRole('button',{name:'Generate support proposal'}).click();
  await expect(page.locator('.planner-result')).toContainText('225');
  await screenshot(page,'03-continuity-planner');
  await page.getByLabel('Daily support budget').fill('6000');
  await page.getByRole('button',{name:'Generate support proposal'}).click();
  await expect(page.locator('.planner-result')).toContainText('450');
  await page.getByLabel('Daily support budget').fill('1500');
  await page.getByRole('button',{name:'Generate support proposal'}).click();
  await expect(page.locator('.planner-result')).toContainText('225');
  await page.getByRole('button',{name:/Save.*proposal|Save.*plan/i}).first().click();
  await page.getByLabel('Plan title',{exact:true}).fill('28 September community continuity');
  await page.getByLabel(/Coordination notes/).fill('Verify accessible venues and confirm actual meal demand with local coordinators.');
  await page.getByRole('button',{name:'Save draft',exact:true}).click();
  await expect(page.getByRole('heading',{name:'28 September community continuity',exact:true})).toBeVisible();
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
  await expect(page.getByRole('heading',{name:/evidence|trust|sources|public|Know|show|Behind/i}).first()).toBeVisible();
  await expect(page.getByText('Census 2020',{exact:false}).first()).toBeVisible();
  await screenshot(page,'05-evidence');
  expect(errors).toEqual([]);
});

test('fresh account keeps plans private and supports sign in',async({page})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Create an account',exact:true}).click();
  await page.getByLabel('Full name',{exact:true}).fill('Browser test planner');
  const email=`browser-${Date.now()}@example.test`;
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
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(391);
  await page.getByRole('button',{name:'Open navigation',exact:true}).click();
  await page.getByRole('button',{name:'Continuity planner',exact:true}).click();
  await page.getByRole('button',{name:'Generate support proposal'}).click();
  await expect(page.locator('.planner-result')).toContainText('225');
  await screenshot(page,'08-mobile-planner');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(391);
});
