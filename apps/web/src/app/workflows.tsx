import {ArrowLeft, ArrowRight, Clock3, MessageSquareText, Play, Send, ShieldCheck, Zap} from 'lucide-react'
import {useEffect, useState} from 'react'
import {Link, useParams} from 'react-router-dom'
import {ApprovalPanel, Badge, Empty, Header, Loading, Notice, RunLink} from '../components/ui'
import {active, api, categories, errorText, result, usd, type Message, type PipelineCard, type Run} from '../lib/api/client'
import {useLoad, useRun} from '../lib/hooks'
import {Metric} from './inbox'

export function Studio({refresh}: {refresh: () => void}) {
  const {runId} = useParams()
  const {run, error, reload} = useRun(runId)
  return <>
    <Link className="back" to={run ? `/jobs/${run.job_id}` : '/inbox'}><ArrowLeft size={16}/> Job details</Link>
    <Header title="Proposal studio" subtitle={run ? `${run.job_id} · Review the draft and preview the Connects cost.` : undefined} actions={runId && <RunLink id={runId}/>}/>
    {error && <Notice>{error}</Notice>}
    {!run && !error && <Loading/>}
    {run && <ApprovalPanel key={`${run.id}-${run.status}`} run={run} onUpdate={() => {reload(); refresh()}}/>}
  </>
}

const stages = ['drafted','submitted','viewed','replied','interview','hired','lost']
export function Pipeline() {
  const board = useLoad(async () => {
    const response = await api.GET('/api/pipeline')
    if (!response.response.ok) throw new Error("The marketplace data could not be loaded.")
    return response.data ?? []
  }, [] as PipelineCard[], 'pipeline')
  return <>
    <Header title="Pipeline" subtitle="Track proposals from draft through the client’s decision." actions={<button className="button secondary" onClick={board.refresh}>Refresh stages</button>}/>
    {board.error && <Notice>{board.error}</Notice>}
    {board.loading ? <Loading/> : <div className="kanban">{stages.map(stage => {
      const cards = board.data.filter(card => card.stage === stage)
      return <section className="lane" key={stage}><h2>{stage}<span>{cards.length}</span></h2>
        {cards.map(card => <Link key={card.job_id} className="kanban-card" to={card.run_id ? `/studio/${card.run_id}` : `/jobs/${card.job_id}`}>
          <span className="small muted">{card.job_id}</span><strong>{card.title}</strong><span>{usd(card.amount)} · {card.connects} Connects</span></Link>)}
        {!cards.length && <p className="small muted">No proposals</p>}
      </section>
    })}</div>}
  </>
}

export function Messages({runs, refresh}: {runs: Run[]; refresh: () => void}) {
  const messages = useLoad(async () => {
    const response = await api.GET('/api/messages')
    if (!response.response.ok) throw new Error("The marketplace data could not be loaded.")
    return response.data ?? []
  }, [] as Message[], 'messages')
  const [thread, setThread] = useState('')
  const [runId, setRunId] = useState<string>()
  const [problem, setProblem] = useState('')
  const [busy, setBusy] = useState(false)
  const jobIds = [...new Set(messages.data.map(item => item.job_id))]
  const selected = thread || jobIds[0] || ''
  const id = runId ?? runs.find(run => run.kind === 'conversation' && run.job_id === selected)?.id
  const {run, reload, error} = useRun(id)
  useEffect(() => {if (run?.status === 'complete') messages.refresh()}, [run?.status])
  async function draft() {
    setBusy(true)
    setProblem('')
    try {
      const response = await api.POST('/api/messages/runs', {body: {job_id: selected, strategy: 'evidence_first'}})
      if (response.error) setProblem(errorText(response.error))
      else {setRunId(response.data?.id); refresh()}
    } catch (error) {setProblem(errorText(error))} finally {setBusy(false)}
  }
  return <>
    <Header title="Messages" subtitle="Review client conversations and approve replies." actions={<button className="button secondary" onClick={messages.refresh}>Refresh inbox</button>}/>
    {messages.error && <Notice>{messages.error}</Notice>}
    {messages.loading ? <Loading/> : !selected ? <Empty title="No client conversations yet">Approved proposals may receive a simulated client reply. <Link to="/inbox">Open the job inbox</Link></Empty> :
      <div className="detail-grid messages-grid">
        <aside className="panel threads"><h2>Conversations</h2>{jobIds.map(jobId => <button key={jobId} className={jobId === selected ? 'selected' : ''} onClick={() => {setThread(jobId); setRunId(undefined)}}><MessageSquareText size={16}/> {jobId}</button>)}</aside>
        <div className="stack"><section className="panel"><div className="panel-head"><div><h2>Client thread</h2><Link to={`/jobs/${selected}`}>{selected}</Link></div>
          {!run && <button className="button primary small" disabled={busy} onClick={() => void draft()}><Send size={15}/> Draft reply</button>}</div>
          {messages.data.filter(item => item.job_id === selected).map(item => <article key={item.id} className={`message ${item.direction}`}><span>{item.direction === 'inbound' ? 'Simulated client' : 'Approved reply'}</span><p>{item.body}</p></article>)}</section>
          {problem && <Notice>{problem}</Notice>}{error && <Notice>{error}</Notice>}
          {run && <ApprovalPanel key={`${run.id}-${run.status}`} run={run} onUpdate={() => {reload(); refresh()}}/>}
        </div>
      </div>}
  </>
}

interface Event {seq: number; node: string; status: string; duration_ms?: number; tokens?: number}
export function Runs({runs}: {runs: Run[]}) {
  const {runId} = useParams()
  const {run, reload} = useRun(runId)
  const [events, setEvents] = useState<Event[]>([])
  const [problem, setProblem] = useState('')
  const [revision, setRevision] = useState(0)
  useEffect(() => {
    setEvents([])
    if (!runId) return
    const source = new EventSource(`/api/runs/${encodeURIComponent(runId)}/events`)
    source.addEventListener('node', (event: MessageEvent<string>) => {
      const item = JSON.parse(event.data) as Event
      setEvents(previous => previous.some(entry => entry.seq === item.seq) ? previous : [...previous, item])
    })
    source.addEventListener('complete', () => {source.close(); reload()})
    return () => source.close()
  }, [runId, revision])
  return <>
    <Header title={runId ? 'Agent run' : 'Agent runs'} subtitle={runId ? `Trace ${runId}` : 'Inspect node execution, approval pauses, and errors.'}
      actions={runId && <a className="button secondary" target="_blank" rel="noreferrer" href={`/api/runs/${runId}/trace`}>Raw trace <ArrowRight size={16}/></a>}/>
    {runId ? <div className="stack">
      {problem && <Notice>{problem}</Notice>}{run?.error && <Notice>{run.error}</Notice>}
      <section className="panel"><div className="panel-head"><h2>Run timeline</h2>{run && <Badge status={run.status}/>}</div>
        {events.length ? events.map(item => <div className="trace-row" key={item.seq}><span className="trace-icon">{item.node === '__interrupt__' ? <ShieldCheck size={17}/> : <Play size={15}/>}</span><strong>{item.node === '__interrupt__' ? 'Awaiting human approval' : item.node.replaceAll('_', ' ')}</strong><span>{item.status}</span><span>{item.duration_ms ?? '—'} ms</span><span>{item.tokens ?? 0} tokens</span></div>) : <Loading text="Connecting to the trace"/>}
        {run && ['needs_attention','marketplace_unavailable'].includes(run.status) && <button className="button secondary" onClick={async () => {
          const response = await api.POST('/api/runs/{run_id}/retry', {params: {path: {run_id: run.id}}})
          if (response.error) setProblem(errorText(response.error)); else {reload(); setRevision(value => value + 1)}
        }}>Retry run</button>}
        {run?.kind === 'bid' && result(run).proposal_draft && <Link className="button primary" to={`/studio/${run.id}`}>Open proposal studio <ArrowRight size={16}/></Link>}
      </section>
    </div> : !runs.length ? <Empty title="No runs yet"><Link to="/inbox">Analyze a job to start a run</Link></Empty> :
      <section className="panel">{runs.map(item => <div key={item.id} className="claim-row"><Link to={`/runs/${item.id}`}>{item.job_id} · {item.kind}</Link><Badge status={item.status}/></div>)}</section>}
  </>
}

type Stats = {sent: number; replied: number; hired: number; connects: number; average_proposal_ms: number; model_cost_usd: number; rejection_reasons: Record<string,number>; categories: Record<string,{sent:number;replied:number;hired:number}>}
export function Analytics() {
  const stats = useLoad(async () => {
    const response = await api.GET('/api/analytics')
    if (!response.response.ok) throw new Error("The marketplace data could not be loaded.")
    return response.data as Stats
  }, undefined as Stats | undefined, 'stats')
  const data = stats.data
  return <>
    <Header title="Analytics" subtitle="Review simulated client outcomes, spending, and draft performance."/>
    {stats.loading && <Loading/>}{stats.error && <Notice>{stats.error}</Notice>}
    {data && <>
      <div className="metrics"><Metric label="Proposals submitted" value={data.sent} icon={<Send size={18}/>}/><Metric label="Client reply rate" value={data.sent ? `${Math.round(data.replied/data.sent*100)}%` : '—'} icon={<MessageSquareText size={18}/>} style="peach"/><Metric label="Connects spent" value={data.connects} icon={<Zap size={18}/>} style="lavender"/></div>
      <div className="detail-grid"><section className="panel"><h2>Outcomes by category</h2>{Object.keys(data.categories).length ? Object.entries(data.categories).map(([key, metrics]) => <div className="chart-row" key={key}>
        <strong>{categories[key] ?? key}</strong><progress max={metrics.sent} value={metrics.replied}/><span>{metrics.replied}/{metrics.sent} replied · {metrics.hired} hired</span>
      </div>) : <p className="muted">Outcome data appears after the first approved proposal.</p>}</section>
      <section className="panel"><h2><Clock3 size={17}/> Proposal performance</h2><dl className="facts"><div><dt>Average node time</dt><dd>{data.average_proposal_ms} ms</dd></div><div><dt>Model API spend</dt><dd>{usd(data.model_cost_usd)}</dd></div><div><dt>Hires</dt><dd>{data.hired}</dd></div></dl></section>
      <section className="panel"><h2>Rejection reasons</h2>{Object.keys(data.rejection_reasons).length ? Object.entries(data.rejection_reasons).map(([reason,n]) => <div className="claim-row" key={reason}>{reason}<strong>{n}</strong></div>) : <p className="muted">No rejections recorded.</p>}</section></div>
    </>}
  </>
}

