import { BookOpen, ExternalLink, LogOut } from 'lucide-react'

export function Topbar({ user, onLogout }) {
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <a className="brand" href="/" aria-label="Study rooms home">
          <span className="brand-mark"><BookOpen size={21} strokeWidth={1.8} /></span>
          <span>Study rooms<small>Valance · ICESI library</small></span>
        </a>
        <div className="topbar-actions">
          {user ? <>
            <span className="member-email" title={user.email}>{user.email}</span>
            <button className="button ghost" onClick={onLogout}><LogOut size={15} /> Sign out</button>
          </> : <a className="portal-link" href="https://banner9.icesi.edu.co/ic_reservas/login" target="_blank" rel="noreferrer">ICESI portal <ExternalLink size={14} /></a>}
        </div>
      </div>
    </header>
  )
}
