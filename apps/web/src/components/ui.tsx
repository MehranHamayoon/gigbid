import {AlertTriangle, ArrowUpRight, CircleHelp, FileText, Layers3, Loader2, ShieldCheck, Sparkles} from 'lucide-react'
import {useState, type ReactNode} from 'react'
import {Link} from 'react-router-dom'
import {active, api, errorText, result, usd, type Evidence, type Run} from '../lib/api/client'

export function Brand({muted = false}: {muted?: boolean}) {
  return <div className={muted ? 'brand dark' : 'brand'}><span className="brand-mark"><Layers3 size={21}/></span><span>GigBid<small>FREELANCE COPILOT</small></span></div>
}
export function Header({title, subtitle, actions}: {title: string; subtitle?: string; actions?: ReactNode}) {
  return <header className="page-header"><div><h1>{title}</h1>{subtitle && <p>{subtitle}</p>}</div>{actions}</header>
}
export function Notice({children, tone = 'warn'}: {children: ReactNode; tone?: 'warn' | 'good' | 'neutral'}) {
  return <div className={`notice ${tone}`} role={tone === 'warn' ? 'alert' : 'status'}>
    {tone === 'warn' ? <AlertTriangle size={18}/> : tone === 'good' ? <ShieldCheck size={18}/> : <CircleHelp size={18}/>}
    <div>{children}</div>
  </div>
}
export function Empty({title, children}: {title: string; children?: ReactNode}) {
  return <div className="empty"><span className="square-icon"><FileText size={23}/></span><h3>{title}</h3>{children && <div>{children}</div>}</div>
}
export function Loading({text = 'Loading'}: {text?: string}) {
  return <div className="loading" role="status"><Loader2 size={17}/>{text}…</div>
}
const labels: Record<string, string> = {pending: 'Needs review', complete: 'Approved', running: 'Running', queued: 'Queued', skip: 'Skip', watch: 'Watch', rejected: 'Rejected', blocked: 'Blocked', needs_attention: 'Needs attention', marketplace_unavailable: 'Marketplace unavailable', bid: 'Recommended', drafted: 'Drafted', submitted: 'Submitted', hired: 'Hired', replied: 'Replied', interview: 'Interview'}
export function Badge({status}: {status: string}) {
  const tone = ['pending','watch','queued','running','needs_attention'].includes(status) ? 'amber' :
    ['skip','rejected','blocked','marketplace_unavailable'].includes(status) ? 'red' :
    ['complete','bid','hired','replied','interview'].includes(status) ? 'green' : 'gray'
  return <span className={`badge ${tone}`}><span/>{labels[status] ?? status}</span>
}
export function EvidenceHover({item}: {item: Evidence}) {
  return <span className="evidence-hover" tabIndex={0} aria-label={`Evidence ${item.id}`}>
    <FileText size={13}/>{item.id}<span role="tooltip"><strong>{item.title}</strong><span>{item.text}</span><small>{item.source}</small></span>
  </span>
}
export function RunLink({id}: {id: string}) {
  return <Link className="subtle-link" to={`/runs/${id}`}>View trace <ArrowUpRight size={14}/></Link>
}
export function ApprovalPanel({run, onUpdate}: {run: Run; onUpdate: () => void}) {
  const data = result(run)
  const original = data.proposal_draft?.cover_letter ?? data.liaison?.draft ?? ''
  const [edit, setEdit] = useState<string | null>(null)
  const [reject, setReject] = useState(false)
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [problem, setProblem] = useState('')
  const conversation = run.kind === 'conversation'
  const text = edit ?? original
  async function submit(action: 'approve' | 'edit' | 'reject') {
    setProblem('')
    setBusy(true)
    try {
      const {error} = await api.POST('/api/runs/{run_id}/approval', {
        params: {path: {run_id: run.id}}, body: {action, text: action === 'edit' ? text : null, reason},
      })
      if (error) setProblem(errorText(error))
      else onUpdate()
    } catch (issue) {setProblem(errorText(issue))} finally {setBusy(false)}
  }
  return <div className="stack">
    {problem && <Notice>{problem}</Notice>}
    {run.error && <Notice>{run.error}</Notice>}
    {run.status === 'complete' && <Notice tone="good">{conversation ? 'Reply sent to the simulated conversation.' : `Proposal approved. Current stage: ${data.outcome?.stage ?? 'complete'}.`}</Notice>}
    {run.status === 'rejected' && <Notice tone="neutral">Rejected. {data.approval?.reason}</Notice>}
    {run.status === 'blocked' && <Notice>{data.compliance_verdict?.reasons.join(' ') ?? 'This draft was blocked.'}</Notice>}
    {active.has(run.status) && <Loading text="Agent run in progress"/>}
    {original && <section className="panel">
      <div className="panel-head"><div><h2>{conversation ? 'Suggested reply' : 'Cover letter'}</h2><p>{conversation ? data.liaison?.intent : 'Evidence and a delivery plan for this job.'}</p></div><Badge status={run.status}/></div>
      <label className="sr-only" htmlFor="draft">Draft text</label>
      <textarea id="draft" className="draft" readOnly={run.status !== 'pending'} value={text} maxLength={5000} onChange={event => setEdit(event.target.value)}/>
      {run.status === 'pending' && !conversation && <button className="button small secondary" type="button" onClick={() => {
        const plans = ['I propose to deliver a reproducible baseline and a documented handoff.','I propose to review the requirements with you and agree on acceptance criteria.']
        setEdit(text.includes(plans[0]) ? text.replace(plans[0], plans[1]) : text.includes(plans[1]) ? text.replace(plans[1], plans[0]) : `${text}\n\n${plans[1]}`)
      }}><Sparkles size={14}/> Regenerate delivery paragraph</button>}
    </section>}
    {data.claim_verification?.length ? <section className="panel">
      <div className="panel-head"><div><h2>Claim evidence</h2><p>Hover or focus a citation to inspect its source.</p></div></div>
      {data.claim_verification.map((claim, index) => {
        const item = data.evidence?.find(row => row.id === claim.evidence_id)
        return <div className="claim-row" key={index}><span>{claim.text}</span>{item && <EvidenceHover item={item}/>}</div>
      })}
      {data.critique && <p className="small muted">Critic · {data.critique.revision} revisions · {data.critique.feedback.join(' ') || 'Draft meets review criteria.'}</p>}
      {data.compliance_verdict?.allowed && <p className="small success-text">Compliance checks passed.</p>}
    </section> : null}
    {!!data.proposal_draft?.screening_answers.length && <section className="panel"><h2>Screening answers</h2>
      {data.proposal_draft.screening_answers.map((answer, index) => <p className="small" key={index}>{data.job_spec?.screening_questions[index]}<br/>{answer}</p>)}
    </section>}
    {data.preview && run.status === 'pending' && <section className="panel preview">
      <div className="panel-head"><div><h2>Marketplace preview</h2><p>{conversation ? 'Simulated client reply' : `Simulated proposal · ${usd(data.preview.payload.amount)} fixed price`}</p></div><strong>{data.preview.connects} Connects</strong></div>
      <details><summary>View exact text</summary><pre>{text}</pre></details>
      {reject ? <form onSubmit={event => {event.preventDefault(); void submit('reject')}} className="stack compact">
        <label>Rejection reason<textarea required value={reason} maxLength={500} onChange={event => setReason(event.target.value)}/></label>
        <div className="actions"><button className="button danger" disabled={busy}>Confirm rejection</button><button type="button" className="button secondary" onClick={() => setReject(false)}>Cancel</button></div>
      </form> : <div className="actions">
        <button className="button primary" disabled={busy || !text.trim()} onClick={() => void submit(text === original ? 'approve' : 'edit')}>
          <ShieldCheck size={17}/> {text !== original ? 'Approve edited draft' : conversation ? 'Approve reply' : 'Approve proposal'}
        </button><button className="button secondary" onClick={() => setReject(true)}>Reject</button>
      </div>}
    </section>}
  </div>
}
