import {ArrowLeft, ArrowRight, Bookmark, BriefcaseBusiness, CircleDollarSign, Clock3, Filter, Globe2, ListFilter, Search, ShieldAlert, Sparkles, Target, Zap} from 'lucide-react'
import {useMemo, useState} from 'react'
import {Link, useParams} from 'react-router-dom'
import {Badge, Empty, EvidenceHover, Header, Loading, Notice, RunLink} from '../components/ui'
import {active, api, categories, errorText, result, usd, type Job, type Run, type User} from '../lib/api/client'
import {useLoad, useRun} from '../lib/hooks'

export function Inbox({user, runs}: {user: User; runs: Run[]}) {
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('')
  const [filter, setFilter] = useState('all')
  const [page, setPage] = useState(1)
  const [bookmarks, setBookmarks] = useState<string[]>(() => JSON.parse(localStorage.getItem(`gigbid.saved.${user.id}`) ?? '[]'))
  const jobs = useLoad(async () => {
    const reply = await api.GET('/api/jobs')
    if (reply.error) throw reply.error
    return reply.data ?? []
  }, [] as Job[], user.id)
  const balance = useLoad(async () => (await api.GET('/api/balance')).data?.remaining, undefined as number | undefined, runs.length)
  const byJob = useMemo(() => new Map(runs.filter(run => run.kind === 'bid').map(run => [run.job_id, run])), [runs])
  const visible = jobs.data.filter(job =>
    (!category || job.category === category) &&
    (!query || `${job.title} ${job.client} ${job.skills.join(' ')}`.toLowerCase().includes(query.trim().toLowerCase())) &&
    (filter === 'all' || filter === 'review' && byJob.get(job.id)?.status === 'pending' || filter === 'saved' && bookmarks.includes(job.id)))
    .sort((a, b) => (result(byJob.get(b.id)).fit_report?.score ?? 0) - (result(byJob.get(a.id)).fit_report?.score ?? 0))
  const reviewCount = runs.filter(run => run.kind === 'bid' && run.status === 'pending').length
  const totalPages = Math.max(1, Math.ceil(visible.length / 8))
  const currentPage = Math.min(page, totalPages)
  function bookmark(id: string) {
    const updated = bookmarks.includes(id) ? bookmarks.filter(value => value !== id) : [...bookmarks, id]
    setBookmarks(updated)
    localStorage.setItem(`gigbid.saved.${user.id}`, JSON.stringify(updated))
  }
  return <>
    <Header title="Job inbox" subtitle="Find opportunities, assess fit, and review what GigBid drafts." actions={<span className="market-label"><span/> Simulator connected</span>}/>
    <div className="metrics">
      <Metric label="Jobs in feed" value={jobs.data.length} icon={<BriefcaseBusiness size={19}/>} description="Available in the simulator"/>
      <Metric label="Ready for review" value={reviewCount} icon={<FileIcon/>} description="Proposals awaiting approval" style="peach"/>
      <Metric label="Connects balance" value={balance.data ?? '—'} icon={<Zap size={19}/>} description={`${user.settings.weekly_limit ?? 30} weekly spending limit`} style="lavender"/>
    </div>
    <section className="list-section">
      <div className="section-title"><div><h2>Opportunities</h2><p>Open a job to see the fit, risk, and bid rationale.</p></div><span className="small muted">{visible.length} results</span></div>
      <div className="filter-bar">
        <div className="tabs" aria-label="Inbox filter">{[['all','All jobs'], ['review','Needs review'], ['saved','Saved']].map(([key,label]) =>
          <button className={filter === key ? 'active-tab' : ''} aria-pressed={filter === key} onClick={() => {setFilter(key); setPage(1)}} key={key}>{label}</button>)}</div>
        <div className="filter-controls"><label className="search"><Search size={16}/><input aria-label="Search jobs" placeholder="Search jobs" value={query} onChange={event => {setQuery(event.target.value); setPage(1)}}/></label>
          <label className="select-icon"><ListFilter size={16}/><select aria-label="Category" value={category} onChange={event => {setCategory(event.target.value); setPage(1)}}><option value="">All categories</option>{Object.entries(categories).slice(0,3).map(([key,value]) => <option value={key} key={key}>{value}</option>)}</select></label>
        </div>
      </div>
      {jobs.loading ? <Loading text="Loading opportunities"/> : jobs.error ? <Notice>{jobs.error} <button className="text-button" onClick={jobs.refresh}>Retry</button></Notice> :
        !visible.length ? <Empty title="No matching jobs">Try a different search or filter.</Empty> :
        <div className="job-list">{visible.slice((currentPage-1)*8,currentPage*8).map(job => {
          const run = byJob.get(job.id)
          const insight = result(run)
          return <article className="job-row" key={job.id}>
            <span className={`job-icon ${job.category}`}>{job.category === 'ai' ? <Sparkles size={20}/> : job.category === 'web' ? <Globe2 size={20}/> : <Target size={20}/>}</span>
            <div className="job-copy"><div className="job-title"><Link to={`/jobs/${job.id}`}>{job.title}</Link>{run && <Badge status={run.status}/>}</div>
              <div className="job-meta"><span>{categories[job.category]}</span><span>{job.client}</span><span>{job.duration_days} days</span></div>
              <div className="tags">{job.skills.slice(0,3).map(skill => <span key={skill}>{skill}</span>)}</div>
            </div>
            <div className="job-price"><strong>{insight.price_quote ? usd(insight.price_quote.amount) : `${usd(job.budget_min)}–${usd(job.budget_max)}`}</strong><span><Zap size={13}/>{job.connects} Connects</span>{insight.fit_report && <span className="success-text">{Math.round(insight.fit_report.score*100)}% fit</span>}</div>
            <button className={`icon-button ${bookmarks.includes(job.id) ? 'saved' : ''}`} aria-label={bookmarks.includes(job.id) ? `Unsave ${job.title}` : `Save ${job.title}`} onClick={() => bookmark(job.id)}><Bookmark size={19}/></button>
          </article>
        })}</div>}
      {totalPages > 1 && <div className="pagination"><span>Page {currentPage} of {totalPages}</span><div><button className="icon-button" aria-label="Previous page" disabled={currentPage === 1} onClick={() => setPage(currentPage - 1)}><ArrowLeft size={17}/></button><button className="icon-button" aria-label="Next page" disabled={currentPage === totalPages} onClick={() => setPage(currentPage + 1)}><ArrowRight size={17}/></button></div></div>}
    </section>
  </>
}
function FileIcon() {return <Filter size={19}/>}
export function Metric({label, value, description, icon, style = ''}: {label: string; value: string | number; description?: string; icon: React.ReactNode; style?: string}) {
  return <section className="metric"><span className={`square-icon ${style}`}>{icon}</span><div><span>{label}</span><strong>{value}</strong>{description && <small>{description}</small>}</div></section>
}
export function JobDetail({runs, refresh}: {runs: Run[]; refresh: () => void}) {
  const {jobId = ''} = useParams()
  const [started, setStarted] = useState<Run>()
  const [problem, setProblem] = useState('')
  const [busy, setBusy] = useState(false)
  const job = useLoad(async () => {
    const response = await api.GET('/api/jobs/{job_id}', {params: {path: {job_id: jobId, strategy: 'evidence_first'}}})
    if (response.error) throw response.error
    return response.data
  }, undefined as Job | undefined, jobId)
  const id = started?.job_id === jobId ? started.id : runs.find(run => run.kind === 'bid' && run.job_id === jobId)?.id
  const poll = useRun(id)
  const run = poll.run
  const insight = result(run)
  async function analyze() {
    setBusy(true)
    setProblem('')
    try {
      const response = await api.POST('/api/runs', {body: {job_id: jobId, strategy: 'evidence_first'}})
      if (response.error || !response.data) setProblem(errorText(response.error))
      else {setStarted(response.data); refresh()}
    } catch (error) {setProblem(errorText(error))} finally {setBusy(false)}
  }
  return <>
    <Link className="back" to="/inbox"><ArrowLeft size={16}/> Job inbox</Link>
    {job.loading && <Loading/>}{job.error && <Notice>{job.error}</Notice>}
    {job.data && <>
      <Header title={job.data.title} subtitle={`${job.data.id} · ${job.data.client} · ${categories[job.data.category]}`}
        actions={id ? <RunLink id={id}/> : <button className="button primary" disabled={busy} onClick={() => void analyze()}><Sparkles size={17}/> Analyze job</button>}/>
      {problem && <Notice>{problem}</Notice>}
      {run?.error && <Notice>{run.error}</Notice>}
      {run && active.has(run.status) && <Loading text="Analyzing job"/>}
      {insight.decision && <Notice tone={insight.decision.action === 'skip' ? 'warn' : 'neutral'}><Badge status={insight.decision.action}/> {insight.decision.reason}</Notice>}
      <div className="detail-grid">
        <div className="stack">
          <section className="panel"><div className="panel-head"><h2>Job brief</h2><span className="small muted">{job.data.source}</span></div><p>{job.data.description}</p>
            <div className="tags">{job.data.skills.map(skill => <span key={skill}>{skill}</span>)}</div></section>
          {insight.fit_report && <section className="panel"><div className="panel-head"><h2>Requirement evidence</h2><span className="badge green">{Math.round(insight.fit_report.score * 100)}% fit</span></div>
            {Object.entries(insight.fit_report.matrix).map(([skill, ids]) => <div className="claim-row" key={skill}><strong>{skill}</strong><div className="tags">
              {ids.length ? ids.slice(0, 3).map(value => {
                const item = insight.evidence?.find(evidence => evidence.id === value)
                return item && <EvidenceHover item={item} key={value}/>
              }) : <span>Missing evidence</span>}</div></div>)}
          </section>}
          {insight.risk_report && <section className="panel"><h2><ShieldAlert size={17}/> Risk assessment</h2><p>{insight.risk_report.explanation}</p><div className="tags">{insight.risk_report.flags.map(flag => <span className="flag" key={flag}>{flag.replaceAll('_',' ')}</span>)}</div></section>}
        </div>
        <aside className="stack">
          <section className="panel"><h2>Contract details</h2>
            <dl className="facts"><div><dt><CircleDollarSign size={16}/> Client budget</dt><dd>{usd(job.data.budget_min)}–{usd(job.data.budget_max)}</dd></div>
              <div><dt><Clock3 size={16}/> Timeline</dt><dd>{job.data.duration_days} days</dd></div>
              <div><dt><Zap size={16}/> Connects</dt><dd>{job.data.connects}</dd></div>
              <div><dt><Globe2 size={16}/> Location</dt><dd>{job.data.country}</dd></div></dl>
          </section>
          {insight.price_quote && <section className="panel price-panel"><h2>Suggested bid</h2><strong>{usd(insight.price_quote.amount)}</strong><p>{insight.price_quote.rationale}</p>
            {insight.selected_persona && <p>Portfolio · {categories[insight.selected_persona]}</p>}
            {id && insight.proposal_draft && <Link className="button primary" to={`/studio/${id}`}>Open proposal studio <ArrowRight size={16}/></Link>}
          </section>}
        </aside>
      </div>
    </>}
  </>
}

