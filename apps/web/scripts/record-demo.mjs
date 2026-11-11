import {chromium} from '@playwright/test'
import {spawn} from 'node:child_process'
import {mkdir, rename} from 'node:fs/promises'
import path from 'node:path'

const dest = path.resolve(process.argv[2] || '../../.state/demo')
await mkdir(dest, {recursive:true})
const origin = 'http://127.0.0.1:8020'
const child = spawn('python', ['-m','uvicorn','apps.api.main:app','--host','127.0.0.1','--port','8020','--log-level','warning','--no-access-log'], {
  cwd: '../..', env:{...process.env,GIGBID_STATE_DIR: path.join(dest,'state'),GIGBID_DEMO_ACCESS:'1'},
  stdio:'inherit', windowsHide:true,
})
const wait = ms => new Promise(resolve => setTimeout(resolve, ms))
let browser, context, video
try {
  let ready = false
  for (let index=0; index<80; index++) {
    try {ready=(await fetch(origin+'/health')).ok} catch {}
    if (ready) break
    await wait(300)
  }
  if (!ready) throw new Error('Demo server did not start')
  browser = await chromium.launch()
  const viewport = {width:1280,height:800}
  context = await browser.newContext({viewport, recordVideo:{dir:dest, size:viewport}})
  const page = await context.newPage()
  page.setDefaultTimeout(13000)
  video = page.video()
  const start = Date.now()
  const hold = seconds => wait(Math.max(0, start + seconds*1000 - Date.now()))
  const caption = (heading, text) => page.evaluate(({heading,text}) => {
    document.getElementById('demo-caption')?.remove()
    const panel = document.createElement('aside')
    panel.id='demo-caption'
    panel.style.cssText='position:fixed;z-index:100;bottom:19px;left:18px;max-width:570px;padding:15px 18px;background:#102f26f5;border:1px solid #ccebd1;color:#fff;border-radius:11px;box-shadow:0 8px 25px #0d2b2350;font:15px/1.4 system-ui;pointer-events:none'
    const title = document.createElement('strong')
    title.style.cssText='display:block;color:#bce9c8;margin-bottom:4px'
    title.textContent=heading
    panel.append(title,document.createTextNode(text))
    document.body.append(panel)
  }, {heading,text})
  const link = (name, exact=true) => page.getByRole('link',{name,exact})
  const button = name => page.getByRole('button',{name,exact:true})
  await page.goto(origin)
  await button('Explore simulator demo').click()
  await link('Build a churn prediction baseline').waitFor()
  await page.screenshot({path:path.join(dest,'inbox.png')})
  await caption('GigBid · AI-4016', 'The marketplace and portfolios in this recording are simulated.')
  await hold(14)
  await link('Build a churn prediction baseline').click()
  await button('Analyze job').click()
  await link('Open proposal studio').waitFor()
  await caption('Analyze a job', 'The LangGraph runs job analysis, risk assessment and portfolio fit in parallel. Open the evidence to inspect the requirement mapping.')
  await hold(30)
  await link('Open proposal studio').click()
  await button('Approve proposal').waitFor()
  await page.screenshot({path:path.join(dest,'studio.png')})
  await caption('Review a grounded proposal', 'The draft cites a verified excerpt and the exact skill tags from the same portfolio record.')
  const evidence = page.getByLabel('Evidence ai-1-case').first()
  if (await evidence.isVisible()) await evidence.hover()
  await hold(49)
  await page.getByText('View exact text',{exact:true}).click()
  await caption('Check the dry-run preview', 'The approved draft is paired with its fixed price and Connects cost. This preview leaves the marketplace unchanged.')
  await hold(65)
  await button('Approve proposal').click()
  await page.getByText('Proposal approved.',{exact:false}).waitFor()
  await caption('Approve the simulator proposal', 'The graph resumes from its checkpoint. A tenant-scoped idempotency key prevents a duplicate submission or charge.')
  await hold(79)
  await link('Job inbox').click()
  await link('Unpaid trial: build a churn prediction baseline').click()
  await button('Analyze job').click()
  await page.getByRole('heading',{name:'Risk assessment'}).waitFor()
  await caption('Catch an unpaid-work scam', 'The risk branch flags unpaid work, off-platform contact, and unverified payment. The bid graph stops before drafting.')
  await hold(98)
  await link('Job inbox').last().click()
  await link('Prototype: build a churn prediction baseline').click()
  await button('Analyze job').click()
  await page.getByRole('heading',{name:'Risk assessment'}).waitFor()
  await caption('Ignore a planted instruction', 'The job post contains instructions to send a proposal. GigBid treats the text as data and routes the job to Skip.')
  await hold(118)
  await link('Messages').click()
  await page.getByText('Could we schedule a short interview',{exact:false}).waitFor()
  await caption('Read the client reply', 'The simulator returned an interview request. The conversation graph will read mock availability and draft a response.')
  await hold(133)
  await button('Draft reply').click()
  await button('Approve reply').waitFor()
  await caption('Review the interview reply', 'The client liaison suggests available UTC dates. The approval gate pauses the conversation before any response is sent.')
  await hold(153)
  await button('Approve reply').click()
  await page.getByText('Reply sent to the simulated conversation.').waitFor()
  await caption('Approve the reply', 'The sent response appears in the simulated client thread. The pipeline records the interview stage.')
  await hold(166)
  await link('Pipeline').click()
  await page.getByRole('heading',{name:'Pipeline',exact:true}).waitFor()
  await caption('GigBid · End of demo', 'The pipeline shows the current simulated stage. The source ZIP includes the report, reproducible results, and test evidence.')
  await hold(181)
  await context.close()
  context = undefined
  await rename(await video.path(), path.join(dest,'demo.webm'))
  console.log('Demo captured')
} finally {
  if (context) await context.close()
  if (browser) await browser.close()
  child.kill()
}

