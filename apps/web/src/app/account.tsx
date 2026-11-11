import {ArrowRight, BriefcaseBusiness, FileUp, KeyRound, ShieldCheck, Trash2} from 'lucide-react'
import {useState, type FormEvent} from 'react'
import {Brand, Empty, Header, Notice} from '../components/ui'
import {api, categories, errorText, type Evidence, type Preferences, type User} from '../lib/api/client'
import {useLoad} from '../lib/hooks'

export function SignIn({demo, onAuth}: {demo: boolean; onAuth: (user?: User) => void}) {
  const [signup, setSignup] = useState(false)
  const [problem, setProblem] = useState('')
  const [busy, setBusy] = useState(false)
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setProblem('')
    const form = new FormData(event.currentTarget)
    const body = {email: String(form.get('email')), password: String(form.get('password'))}
    try {
      const response = signup ? await api.POST('/api/auth/register', {body: {...body, name: String(form.get('name'))}}) :
        await api.POST('/api/auth/login', {body})
      if (response.error) setProblem(errorText(response.error))
      else onAuth()
    } catch (error) {setProblem(errorText(error))} finally {setBusy(false)}
  }
  return <div className="auth-layout">
    <section className="auth-brand"><Brand/><div><div className="auth-symbol"><BriefcaseBusiness size={46}/></div><h1>Find work worth bidding on.</h1><p>Qualify freelance jobs, draft with portfolio evidence, and approve every proposal before it goes out.</p></div><span><ShieldCheck size={16}/> Human approval for every send</span></section>
    <main className="auth-main"><div className="auth-form">
      <div className="square-icon"><KeyRound size={20}/></div><h2>{signup ? 'Create an account' : 'Sign in to GigBid'}</h2><p>{signup ? 'Set up your freelance workspace.' : 'Access your job inbox and proposal studio.'}</p>
      {problem && <Notice>{problem}</Notice>}
      <form className="stack compact" onSubmit={submit}>
        {signup && <label>Name<input name="name" minLength={2} maxLength={60} required autoComplete="name"/></label>}
        <label>Email<input name="email" required type="email" autoComplete="email" placeholder="you@example.com"/></label>
        <label>Password<input name="password" required type="password" minLength={10} maxLength={128} autoComplete={signup ? 'new-password' : 'current-password'}/></label>
        <button className="button primary" disabled={busy}>{signup ? 'Create account' : 'Sign in'} <ArrowRight size={16}/></button>
      </form>
      <button className="text-button auth-toggle" onClick={() => {setSignup(!signup); setProblem('')}}>{signup ? 'Already have an account? Sign in' : 'New to GigBid? Create an account'}</button>
      {demo && <button className="button secondary demo" disabled={busy} onClick={async () => {
        setBusy(true)
        try {const reply = await api.POST('/api/auth/demo'); if (reply.data) onAuth(reply.data); else setProblem(errorText(reply.error))}
        catch (error) {setProblem(errorText(error))} finally {setBusy(false)}
      }}>Explore simulator demo <ArrowRight size={16}/></button>}
    </div></main>
  </div>
}

type Memory = {kind: 'style' | 'outcome'; key: string; value: Record<string, unknown>}
export function Settings({user, onSave, onboarding = false}: {user: User; onSave: (preferences: Preferences) => void; onboarding?: boolean}) {
  const [form, setForm] = useState<Preferences>(user.settings)
  const [notice, setNotice] = useState('')
  const [problem, setProblem] = useState('')
  const [busy, setBusy] = useState(false)
  const evidence = useLoad(async () => {
    const response = await api.GET('/api/portfolio')
    return (response.data ?? []) as Evidence[]
  }, [] as Evidence[], user.settings.persona)
  const memory = useLoad(async () => (await api.GET('/api/memory')).data as Memory[] ?? [], [] as Memory[], user.id)
  const market = useLoad(async () => (await api.GET('/api/settings/upwork')).data as {configured: boolean; connected: boolean; mode: string}, undefined, user.id)
  const update = (value: Partial<Preferences>) => setForm(previous => ({...previous, ...value}))
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setProblem('')
    setBusy(true)
    try {
      const response = await api.PUT('/api/settings', {body: {...form, onboarded: true}})
      if (response.error || !response.data) setProblem(errorText(response.error))
      else {onSave(response.data); setNotice('Workspace preferences saved.')}
    } catch (error) {setProblem(errorText(error))} finally {setBusy(false)}
  }
  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setProblem('')
    setNotice('')
    const data = new FormData(event.currentTarget)
    try {
      const response = await fetch('/api/portfolio', {method: 'POST', body: data})
      if (!response.ok) setProblem(errorText(await response.json()))
      else {setNotice('Portfolio evidence indexed.'); evidence.refresh()}
    } catch (error) {setProblem(errorText(error))}
  }
  return <>
    <Header title={onboarding ? 'Set up your workspace' : 'Settings'} subtitle="Manage the portfolio, saved search, and limits used by your agents."/>
    <div className="stack">
      {problem && <Notice>{problem}</Notice>}{notice && <Notice tone="good">{notice}</Notice>}
      <section className="panel"><div className="panel-head"><div><h2>Workspace preferences</h2><p>Choose a starting portfolio and configure scouting.</p></div></div>
        <form className="stack compact" onSubmit={save}>
          <div className="form-grid">
            <label>Persona<select value={form.persona} onChange={event => update({persona: event.target.value as Preferences['persona']})}>
              {Object.entries(categories).map(([key,label]) => <option value={key} key={key}>{label}</option>)}</select></label>
            <label>Minimum project budget (USD)<input required type="number" min={0} max={100000} value={form.floor} onChange={event => update({floor: Number(event.target.value)})}/></label>
            <label>Weekly Connects limit<input required type="number" min={0} max={100} value={form.weekly_limit} onChange={event => update({weekly_limit: Number(event.target.value)})}/></label>
            <label>Saved search<input value={form.filters} onChange={event => update({filters: event.target.value})} placeholder="e.g. dashboard" maxLength={120}/></label>
            <label>Search interval (hours)<input required type="number" min={2} max={48} value={form.scout_hours} onChange={event => update({scout_hours: Number(event.target.value)})}/></label>
            <label>Autonomy<select value={form.autonomy} onChange={event => update({autonomy: event.target.value as Preferences['autonomy']})}><option value="review">Review recommendations</option><option value="auto_skip">Auto-skip low fit</option></select></label>
          </div>
          <div><button className="button primary" disabled={busy}>{onboarding ? 'Continue to job inbox' : 'Save preferences'} <ArrowRight size={16}/></button></div>
        </form>
      </section>
      {!onboarding && <>
        <section className="panel"><div className="panel-head"><div><h2>Marketplace connection</h2><p>{market.data?.mode === 'upwork' ? 'Upwork live draft mode' : 'Local GigSim-compatible simulator'}</p></div>
          {market.data?.configured && <a className="button secondary" href="/api/oauth/upwork/start">{market.data.connected ? 'Reconnect Upwork' : 'Connect Upwork'}</a>}</div>
          <span className="badge green">Marketplace · {market.data?.mode ?? 'gigsim'}</span>
        </section>
        <section className="panel"><div className="panel-head"><div><h2>Portfolio evidence</h2><p>Upload PDFs, case studies, source files, reviews, or proposals.</p></div><FileUp size={20}/></div>
          <form className="stack compact" onSubmit={upload}><div className="form-grid">
            <label>Evidence file<input name="file" type="file" required accept=".pdf,.md,.txt,.py,.ts,.tsx,.js,.sql,.json"/></label>
            <label>Skills (comma separated)<input name="skills" placeholder="Python, RAG"/></label>
            <label>Document type<select name="kind"><option value="case_study">Case study</option><option value="cv">CV</option><option value="readme">README</option><option value="code">Source code</option><option value="review">Review</option><option value="proposal">Past proposal</option></select></label>
            <label>Industry<input name="industry" placeholder="SaaS"/></label>
          </div><div><button className="button secondary"><FileUp size={16}/> Index file</button></div></form>
          <div className="evidence-list">{evidence.data.map(item => <div className="claim-row" key={item.id}><div><strong>{item.title}</strong><div className="small muted">{item.id} · {item.type.replaceAll('_',' ')}</div></div>
            {item.id.startsWith('upload-') && <button className="icon-button" aria-label={`Delete ${item.id}`} onClick={async () => {
              const response = await api.DELETE('/api/portfolio/{evidence_id}', {params: {path: {evidence_id: item.id}}})
              if (response.error) setProblem(errorText(response.error)); else evidence.refresh()
            }}><Trash2 size={17}/></button>}</div>)}</div>
        </section>
        <section className="panel"><h2>Learned memory</h2>{memory.data.length ? memory.data.map(item => <div className="claim-row" key={item.key}>
          <div><strong>{item.kind}</strong><p>{Object.values(item.value).join(' · ')}</p></div>
          <button className="icon-button" aria-label={`Forget ${item.kind} ${item.key}`} onClick={async () => {
            const response = await api.DELETE('/api/memory/{kind}/{key}', {params: {path: {kind: item.kind, key: item.key}}})
            if (response.error) setProblem(errorText(response.error)); else memory.refresh()
          }}><Trash2 size={17}/></button>
        </div>) : <Empty title="No learned patterns yet">Approved outcomes and repeated shorter edits appear here.</Empty>}</section>
      </>}
    </div>
  </>
}
