/**
 * Small presentational primitives shared by the page sections.
 * Everything here is React, no separate markup layer.
 */
import { Reveal } from './Reveal.jsx'

export function Section({ id, eyebrow, title, description, action, children }) {
  return (
    <section className="section" id={id}>
      <div className="section-head">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h2>{title}</h2>
          {description && <p>{description}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  )
}

export function StatCard({ label, value, hint, mono = false }) {
  return (
    <dl className="stat">
      <dt>{label}</dt>
      <dd className={mono ? 'mono' : undefined}>{value}</dd>
      {hint && <small>{hint}</small>}
    </dl>
  )
}

export function StatusPill({ status }) {
  const map = {
    success: ['ok', 'Booked'],
    'dry-run': ['warn', 'Dry run'],
    partial: ['warn', 'Partial'],
    unavailable: ['busy', 'Unavailable'],
    'no-account': ['busy', 'No account'],
    failed: ['bad', 'Failed'],
  }
  const [tone, label] = map[status] ?? map.failed
  return <span className={`pill ${tone}`}>{label}</span>
}

export function Field({ label, value, mono = false }) {
  return (
    <div>
      <p className="eyebrow">{label}</p>
      <p className={mono ? 'mono' : undefined} style={{ marginTop: 6 }}>
        {value}
      </p>
    </div>
  )
}

export { Reveal }
