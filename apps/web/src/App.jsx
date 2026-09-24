import { useEffect, useState } from 'react'
import {
  CalendarDays,
  CheckCircle2,
  Clock,
  ExternalLink,
  RefreshCw,
  XCircle,
} from 'lucide-react'
import { Card, Eyebrow, Reveal, Section } from './components/ui.jsx'

const ACTIONS_URL =
  'https://github.com/espinosacodes/automaticStudyRoomReservation/actions/workflows/reserve.yml'

const STATUS = {
  success: { label: 'Success', color: 'text-[#22C55E]', Icon: CheckCircle2 },
  'dry-run': { label: 'Dry run', color: 'text-[#F59E0B]', Icon: Clock },
  unavailable: { label: 'Unavailable', color: 'text-[#F59E0B]', Icon: Clock },
  failed: { label: 'Failed', color: 'text-[#EF4444]', Icon: XCircle },
}

function formatBogota(iso) {
  if (!iso) return 'never'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Bogota',
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

function runStatus(run) {
  if (!run.summary || run.summary.total === 0) return 'failed'
  if (run.summary.failed > 0) return 'failed'
  return run.dry_run ? 'dry-run' : 'success'
}

function StatusBadge({ status }) {
  const meta = STATUS[status] ?? STATUS.failed
  const Icon = meta.Icon
  return (
    <span className={`inline-flex items-center gap-1.5 text-sm font-semibold ${meta.color}`}>
      <Icon className="h-4 w-4" />
      {meta.label}
    </span>
  )
}

function Nav() {
  return (
    <header className="border-b border-hairline bg-white">
      <Section className="flex items-center justify-between py-4">
        <span className="font-mono text-sm text-charcoal-700">reservation.getcuria.us</span>
        <span className="rounded-full bg-primary-light px-3 py-1 text-xs font-bold text-primary">
          ICESI
        </span>
      </Section>
    </header>
  )
}

function Hero({ run }) {
  if (!run) {
    return (
      <Card>
        <Eyebrow>Status</Eyebrow>
        <h1 className="mt-2 text-2xl font-extrabold tracking-tight">No runs yet</h1>
        <p className="mt-2 text-charcoal-700">
          The cron has not completed a reservation run. Trigger it manually from GitHub Actions.
        </p>
        <a
          href={ACTIONS_URL}
          className="mt-4 inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white transition hover:bg-primary-hover"
        >
          <RefreshCw className="h-4 w-4" />
          Run workflow
        </a>
      </Card>
    )
  }

  const status = runStatus(run)
  return (
    <Card>
      <Eyebrow>Last run</Eyebrow>
      <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-extrabold tracking-tight">{formatBogota(run.run_at)}</h1>
        <StatusBadge status={status} />
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <div className="flex items-center gap-2 text-sm text-charcoal-700">
          <CalendarDays className="h-4 w-4 text-primary" />
          Booking {run.target_date}
        </div>
        <div className="flex items-center gap-2 text-sm text-charcoal-700">
          <Clock className="h-4 w-4 text-primary" />
          {run.summary?.succeeded ?? 0}/{run.summary?.total ?? 0} blocks ok
        </div>
        <a
          href={ACTIONS_URL}
          className="inline-flex items-center gap-2 text-sm font-semibold text-primary hover:text-primary-hover"
        >
          View screenshots
          <ExternalLink className="h-4 w-4" />
        </a>
      </div>
    </Card>
  )
}

function BlockTable({ run }) {
  const blocks = run.blocks ?? []
  if (blocks.length === 0) return null
  return (
    <div className="mt-4 overflow-hidden rounded-xl border border-hairline">
      <table className="w-full text-left text-sm">
        <thead className="bg-surface text-xs uppercase tracking-wide text-charcoal-700">
          <tr>
            <th className="px-4 py-2 font-semibold">Block</th>
            <th className="px-4 py-2 font-semibold">Account</th>
            <th className="px-4 py-2 font-semibold">Room</th>
            <th className="px-4 py-2 font-semibold">Result</th>
          </tr>
        </thead>
        <tbody>
          {blocks.map((block) => (
            <tr key={`${block.start}-${block.end}`} className="border-t border-hairline">
              <td className="px-4 py-2 font-mono text-charcoal-900">
                {block.start} - {block.end}
              </td>
              <td className="px-4 py-2 font-mono text-charcoal-700">{block.account || '-'}</td>
              <td className="px-4 py-2 text-charcoal-700">{block.room || '-'}</td>
              <td className="px-4 py-2">
                <StatusBadge status={block.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function History({ runs }) {
  if (runs.length === 0) return null
  return (
    <Reveal>
      <Card>
        <Eyebrow>Recent runs</Eyebrow>
        <div className="mt-3 space-y-6">
          {runs.slice(0, 5).map((run) => (
            <div key={run.run_at}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-semibold text-charcoal-900">
                  {formatBogota(run.run_at)}
                  {run.dry_run && (
                    <span className="ml-2 rounded-full bg-[#FEF3C7] px-2 py-0.5 text-xs font-semibold text-[#B45309]">
                      dry run
                    </span>
                  )}
                </span>
                <StatusBadge status={runStatus(run)} />
              </div>
              <BlockTable run={run} />
            </div>
          ))}
        </div>
      </Card>
    </Reveal>
  )
}

export default function App() {
  const [state, setState] = useState({ loading: true, runs: [] })

  useEffect(() => {
    let active = true
    fetch('/status.json', { cache: 'no-store' })
      .then((response) => (response.ok ? response.json() : { runs: [] }))
      .catch(() => ({ runs: [] }))
      .then((data) => {
        if (active) setState({ loading: false, runs: data.runs ?? [] })
      })
    return () => {
      active = false
    }
  }, [])

  if (state.loading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-charcoal-700">Loading...</div>
    )
  }

  return (
    <div className="min-h-screen">
      <Nav />
      <main className="space-y-6 py-10">
        <Section>
          <Reveal>
            <Hero run={state.runs[0]} />
          </Reveal>
        </Section>
        <Section>
          <History runs={state.runs} />
        </Section>
      </main>
      <footer className="border-t border-hairline bg-white py-6">
        <Section className="text-center text-xs text-charcoal-700">
          Automated reservations for the ICESI library study room. Screenshots are stored as
          GitHub Actions artifacts.
        </Section>
      </footer>
    </div>
  )
}
