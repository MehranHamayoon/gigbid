import {expect, test, type Page} from '@playwright/test'

async function demo(page: Page) {
  await page.goto('/')
  await page.getByRole('button', {name:'Explore simulator demo'}).click()
  await expect(page.getByRole('heading',{name:'Job inbox'})).toBeVisible()
}

async function studio(page: Page) {
  await demo(page)
  await page.getByRole('link',{name:'Build a churn prediction baseline', exact:true}).click()
  await page.getByRole('button',{name:'Analyze job'}).click()
  await page.getByRole('link',{name:'Open proposal studio'}).click()
  await expect(page.getByRole('heading',{name:'Marketplace preview'})).toBeVisible()
}

test('onboarding saves persona and budget', async ({page}) => {
  await page.goto('/')
  await page.getByRole('button',{name:'New to GigBid? Create an account'}).click()
  await page.getByLabel('Name',{exact:true}).fill('Local Reviewer')
  await page.getByLabel('Email',{exact:true}).fill(`test-${Date.now()}@example.invalid`)
  await page.getByLabel('Password',{exact:true}).fill('local-fixture-password')
  await page.getByRole('button',{name:'Create account',exact:true}).click()
  await page.getByRole('combobox',{name:'Persona',exact:true}).selectOption('web')
  await page.getByLabel('Weekly Connects limit').fill('25')
  await page.getByRole('button',{name:'Continue to job inbox'}).click()
  await expect(page.getByText('25 weekly spending limit')).toBeVisible()
  await expect(page.getByText('Web development',{exact:true}).first()).toBeVisible()
})

test('approve a proposal and reply to the simulated client', async ({page}) => {
  await studio(page)
  await page.reload()
  await expect(page.getByRole('button',{name:'Approve proposal'})).toBeVisible()
  await page.getByRole('button',{name:'Approve proposal'}).click()
  await expect(page.getByText('Proposal approved.',{exact:false})).toBeVisible()
  await page.getByRole('link',{name:'Messages',exact:true}).click()
  await expect(page.getByText('Could we schedule a short interview',{exact:false})).toBeVisible()
  await page.getByRole('button',{name:'Draft reply'}).click()
  await page.getByRole('button',{name:'Approve reply'}).click()
  await expect(page.getByText('Reply sent to the simulated conversation.')).toBeVisible()
})

test('rejecting records a reason and leaves Connects intact', async ({page}) => {
  await studio(page)
  await page.getByRole('button',{name:'Reject',exact:true}).click()
  await page.getByLabel('Rejection reason').fill('Outside this week’s focus.')
  await page.getByRole('button',{name:'Confirm rejection'}).click()
  await expect(page.getByText('Rejected. Outside this week’s focus.')).toBeVisible()
  const balance = await page.request.get('/api/balance')
  expect((await balance.json()).remaining).toBe(100)
})

test('edit and approve a verified proposal', async ({page}) => {
  await studio(page)
  await page.getByRole('button',{name:'Regenerate delivery paragraph'}).click()
  await expect(page.getByLabel('Draft text')).toHaveValue(/agree on acceptance criteria/)
  await page.getByRole('button',{name:'Approve edited draft'}).click()
  await expect(page.getByText('Proposal approved.',{exact:false})).toBeVisible()
  await expect(page.getByLabel('Draft text')).toHaveValue(/agree on acceptance criteria/)
})

test('reports degraded marketplace service', async ({page}) => {
  await page.setExtraHTTPHeaders({'x-gigbid-test-outage':'1'})
  await demo(page)
  await expect(page.getByRole('alert').getByText('Marketplace unavailable.',{exact:true})).toBeVisible()
})

test('opens navigation on a narrow screen and exposes the planted instruction risk', async ({page}) => {
  await page.setViewportSize({width:390,height:844})
  await demo(page)
  await page.getByRole('button',{name:'Open menu'}).click()
  await expect(page.getByRole('link',{name:'Settings',exact:true})).toBeVisible()
  await page.getByRole('button',{name:'Close menu'}).click()
  await page.getByRole('link',{name:'Prototype: build a churn prediction baseline',exact:true}).click()
  await page.getByRole('button',{name:'Analyze job'}).click()
  await expect(page.getByText('Flagged injection.',{exact:false}).first()).toBeVisible()
  await expect(page.getByRole('link',{name:'Open proposal studio'})).toHaveCount(0)
})

