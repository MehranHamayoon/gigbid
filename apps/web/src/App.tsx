import {BarChart3, ChevronDown, ChevronsUpDown, CircleHelp, Inbox as InboxIcon, LayoutGrid, LogOut, Menu, MessageSquareText, Route as RouteIcon, Settings as SettingsIcon, X} from 'lucide-react'
import {useEffect, useState} from 'react'
import {BrowserRouter, Link, Navigate, NavLink, Route, Routes, useLocation, useNavigate} from 'react-router-dom'
import {Settings, SignIn} from './app/account'
import {Inbox, JobDetail} from './app/inbox'
import {Analytics, Messages, Pipeline, Runs, Studio} from './app/workflows'
import {Brand, Loading, Notice} from './components/ui'
import {api, categories, type Run, type User} from './lib/api/client'

const nav = [
  {href:'/inbox', label:'Job inbox', icon:InboxIcon},
  {href:'/pipeline', label:'Pipeline', icon:LayoutGrid},
  {href:'/messages', label:'Messages', icon:MessageSquareText},
  {href:'/runs', label:'Agent runs', icon:RouteIcon},
  {href:'/analytics', label:'Analytics', icon:BarChart3},
  {href:'/settings', label:'Settings', icon:SettingsIcon},
]

function Workspace() {
  const [user, setUser] = useState<User>()
  const [loading, setLoading] = useState(true)
  const [status, setStatus] = useState({marketplace: 'available', demo_access: false, mode: 'gigsim'})
  const [runs, setRuns] = useState<Run[]>([])
  const [mobile, setMobile] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()
  async function loadUser() {
    try {setUser((await api.GET('/api/auth/me')).data)} finally {setLoading(false)}
  }
  async function health() {
    const response = await api.GET('/api/status')
    if (response.data) setStatus(response.data)
  }
  async function refresh() {
    if (!user) return
    const reply = await api.GET('/api/runs')
    if (reply.data) setRuns(reply.data)
  }
  useEffect(() => {void loadUser(); void health()}, [])
  useEffect(() => {
    if (!user) return
    void refresh()
    void health()
    const interval = window.setInterval(() => {void refresh(); void health()}, 3500)
    return () => window.clearInterval(interval)
  }, [user?.id, location.pathname])
  useEffect(() => setMobile(false), [location.pathname])
  if (loading) return <div className="splash"><Loading text="Opening workspace"/></div>
  if (!user) return <SignIn demo={status.demo_access} onAuth={next => {if (next) setUser(next); else void loadUser()}}/>
  const reviewer = user.name.split(' ').map(part => part[0]).join('').slice(0,2).toUpperCase()
  const current = nav.find(item => location.pathname.startsWith(item.href))?.label ?? 'Job inbox'
  const waiting = runs.filter(run => run.status === 'pending').length
  return <div className="workspace">
    <aside className={`sidebar ${mobile ? 'is-open' : ''}`}>
      <Link className="brand-link" to="/inbox"><Brand/></Link>
      <button className="mobile-close icon-button" aria-label="Close menu" onClick={() => setMobile(false)}><X size={21}/></button>
      <div className="workspace-card"><span className="workspace-avatar">G</span><div><strong>My workspace</strong><small>{categories[user.settings.persona ?? 'ai']}</small></div><ChevronsUpDown size={15}/></div>
      <nav aria-label="Workspace navigation">
        <span className="nav-title">WORKSPACE</span>
        {nav.map(({href,label,icon: Icon}) => <NavLink key={href} to={href}><Icon size={18}/><span>{label}</span>{href === '/inbox' && waiting > 0 && <span className="nav-count">{waiting}</span>}</NavLink>)}
      </nav>
      <div className="sidebar-footer"><a href="/health" target="_blank" rel="noreferrer"><CircleHelp size={17}/> Service status</a>
        <div className="user-card"><span>{reviewer}</span><div><strong>{user.name}</strong><small>{status.mode === 'gigsim' ? 'Simulator workspace' : 'Upwork workspace'}</small></div>
          <button className="icon-button" aria-label="Sign out" onClick={async () => {await api.POST('/api/auth/logout'); setUser(undefined); setRuns([]); navigate('/inbox')}}><LogOut size={17}/></button>
        </div>
      </div>
    </aside>
    {mobile && <button className="overlay" aria-label="Close navigation" onClick={() => setMobile(false)}/>}
    <div className="work-area">
      <div className="topbar"><div><button className="icon-button mobile-menu" aria-label="Open menu" onClick={() => setMobile(true)}><Menu size={20}/></button><span className="top-root">Workspace</span><span className="slash">/</span><strong>{current}</strong></div><Link to="/settings" className="top-user"><span>{reviewer}</span><ChevronDown size={13}/></Link></div>
      <main id="main" className="main">
        {status.marketplace === 'unavailable' && <Notice><strong>Marketplace unavailable.</strong> Queued runs will retry when the connection returns.</Notice>}
        {!user.settings.onboarded ? <Settings user={user} onboarding onSave={settings => {setUser({...user,settings}); navigate('/inbox')}}/> :
        <Routes>
          <Route path="/inbox" element={<Inbox key={user.id} user={user} runs={runs}/>}/>
          <Route path="/jobs/:jobId" element={<JobDetail runs={runs} refresh={refresh}/>}/>
          <Route path="/studio/:runId" element={<Studio refresh={refresh}/>}/>
          <Route path="/pipeline" element={<Pipeline/>}/>
          <Route path="/messages" element={<Messages runs={runs} refresh={refresh}/>}/>
          <Route path="/runs" element={<Runs runs={runs}/>}/>
          <Route path="/runs/:runId" element={<Runs runs={runs}/>}/>
          <Route path="/analytics" element={<Analytics/>}/>
          <Route path="/settings" element={<Settings user={user} onSave={settings => setUser({...user,settings})}/>}/>
          <Route path="*" element={<Navigate to="/inbox" replace/>}/>
        </Routes>}
      </main>
    </div>
  </div>
}

export default function App() {return <BrowserRouter><Workspace/></BrowserRouter>}
