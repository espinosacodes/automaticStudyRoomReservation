/**
 * Left sidebar navigation. Vertical rail with the brand, section links, the
 * signed-in member, and sign out. Marked `data-optical` so the liquid glass
 * layer refracts the drifting mesh gradient behind it while the labels stay
 * crisp in the DOM above.
 */
import {
  BookOpen,
  CalendarDays,
  CalendarRange,
  History,
  LogOut,
  Network,
  ExternalLink,
} from 'lucide-react'

const PORTAL_URL = 'https://banner9.icesi.edu.co/ic_reservas/login'

const LINKS = [
  { href: '#bookings', label: 'Reservations', hint: 'Slots and receipts', Icon: CalendarDays },
  { href: '#calendar', label: 'Week', hint: 'Blocks per day', Icon: CalendarRange },
  { href: '#runs', label: 'Run history', hint: 'Every nightly run', Icon: History },
  { href: '#architecture', label: 'How it works', hint: 'Pipeline and hosts', Icon: Network },
]

export function Sidebar({ user, onLogout, active }) {
  return (
    <aside className="sidebar" data-optical>
      <div className="sidebar-glass" aria-hidden="true" />
      <div className="sidebar-inner">
        <a className="sidebar-brand" href="/" aria-label="Study rooms home">
          <span className="brand-mark">
            <BookOpen size={20} strokeWidth={1.8} />
          </span>
          <span className="brand-copy">
            Study rooms
            <small>Valance · ICESI library</small>
          </span>
        </a>

        <p className="sidebar-label">Dashboard</p>
        <nav className="sidebar-nav" aria-label="Dashboard sections">
          {LINKS.map(({ href, label, hint, Icon }) => (
            <a
              key={href}
              href={href}
              className={active === href.slice(1) ? 'active' : undefined}
            >
              <Icon size={17} strokeWidth={1.7} />
              <span>
                {label}
                <small>{hint}</small>
              </span>
            </a>
          ))}
        </nav>

        <div className="sidebar-foot">
          <a className="sidebar-link" href={PORTAL_URL} target="_blank" rel="noreferrer">
            <ExternalLink size={15} />
            ICESI portal
          </a>
          {user && (
            <>
              <p className="sidebar-member" title={user.email}>
                {user.email}
              </p>
              <button type="button" className="button ghost sidebar-signout" onClick={onLogout}>
                <LogOut size={15} />
                Sign out
              </button>
            </>
          )}
        </div>
      </div>
    </aside>
  )
}
