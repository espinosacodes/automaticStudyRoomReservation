/**
 * Run history as pricing-style cards: the latest run is highlighted like the
 * featured tier, and each block reads as a feature row with a green check for
 * booked slots, a dash for skipped ones, and a cross for failures.
 */
import { Check, Clock, Minus, X } from 'lucide-react'

import { StatusPill } from './ui.jsx'

export function runStatus(run) {
  const blocks = run.blocks ?? []
  if (blocks.some((block) => block.status === 'unconfirmed')) return 'unconfirmed'
  if (blocks.length === 0) return 'failed'
  if (blocks.some((block) => block.status === 'failed' || block.status === 'no-account')) {
    return 'failed'
  }
  if (blocks.every((block) => block.status === 'skipped')) return 'skipped'
  if (
    blocks.some((block) => block.status === 'unavailable' || block.status === 'skipped')
  ) {
    return 'partial'
  }
  return run.dry_run ? 'dry-run' : 'success'
}

function BlockMark({ status }) {
  if (status === 'success') return <Check size={15} className="mark ok" aria-label="booked" />
  if (status === 'failed' || status === 'no-account') {
    return <X size={15} className="mark bad" aria-label="failed" />
  }
  if (status === 'dry-run' || status === 'unconfirmed') {
    return <Clock size={15} className="mark warn" aria-label={status} />
  }
  return <Minus size={15} className="mark muted" aria-label={status} />
}

function shortRoom(room) {
  if (!room) return '-'
  const code = room.match(/\d+[A-Z]+/)
  return code ? code[0] : room
}

export function RunsHistory({ runs, formatStamp, actionsUrl }) {
  if (runs.length === 0) {
    return (
      <div className="table-wrap">
        <div className="empty">
          No runs yet. Trigger one from GitHub Actions.
          {actionsUrl && (
            <>
              {' '}
              <a href={actionsUrl} target="_blank" rel="noreferrer">
                Open workflow
              </a>
            </>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="run-grid">
      {runs.map((run, index) => (
        <article className={`run-card${index === 0 ? ' featured' : ''}`} key={run.run_at}>
          <header>
            <div>
              <p className="run-date">{formatStamp(run.run_at)}</p>
              <p className="muted mono">For {run.target_date}</p>
            </div>
            <StatusPill status={runStatus(run)} />
          </header>
          <p className="run-count">
            {run.summary?.succeeded ?? 0}/{run.summary?.total ?? 0} blocks
            {index === 0 && <span className="run-latest">Latest</span>}
          </p>
          <ul>
            {(run.blocks ?? []).map((block) => (
              <li key={`${block.start}-${block.end}`}>
                <BlockMark status={block.status} />
                <span className="mono">
                  {block.start} - {block.end}
                </span>
                <span className="run-room">{shortRoom(block.room)}</span>
              </li>
            ))}
          </ul>
        </article>
      ))}
    </div>
  )
}
