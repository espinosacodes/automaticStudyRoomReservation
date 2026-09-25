/**
 * Per-run history. Each run shows its blocks with a status pill, so a dry run,
 * a taken room, and a real failure are all distinguishable.
 */
import { StatusPill } from './ui.jsx'

export function runStatus(run) {
  const blocks = run.blocks ?? []
  if (blocks.length === 0) return 'failed'
  if (blocks.some((block) => block.status === 'failed' || block.status === 'no-account')) {
    return 'failed'
  }
  if (blocks.some((block) => block.status === 'unavailable')) return 'partial'
  return run.dry_run ? 'dry-run' : 'success'
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
    <div className="stack">
      {runs.slice(0, 6).map((run) => (
        <div className="table-wrap" key={run.run_at}>
          <table>
            <thead>
              <tr>
                <th>{formatStamp(run.run_at)}</th>
                <th>For {run.target_date}</th>
                <th>{run.summary?.succeeded ?? 0}/{run.summary?.total ?? 0} blocks</th>
                <th>
                  <StatusPill status={runStatus(run)} />
                </th>
              </tr>
              <tr>
                <th>Block</th>
                <th>Account</th>
                <th>Room</th>
                <th>Result</th>
              </tr>
            </thead>
            <tbody>
              {(run.blocks ?? []).map((block) => (
                <tr key={`${block.start}-${block.end}`}>
                  <td className="mono">
                    {block.start} - {block.end}
                  </td>
                  <td className="mono">{block.account || '-'}</td>
                  <td>{block.room || '-'}</td>
                  <td>
                    <StatusPill status={block.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  )
}
