import { useEffect, useState } from 'react'
import { Archive, Cloud, Database, FileJson, Github, Monitor, Terminal } from 'lucide-react'

import { ArchitectureDiagram } from './components/ArchitectureDiagram.jsx'
import { BookingsTable, collectBookings } from './components/BookingsTable.jsx'
import { RunsHistory, runStatus } from './components/RunsHistory.jsx'
import { Section, StatCard, StatusPill } from './components/ui.jsx'
import { Topbar } from './components/Topbar.jsx'
import { WeekCalendar } from './components/WeekCalendar.jsx'

const ACTIONS_URL =
  'https://github.com/espinosacodes/automaticStudyRoomReservation/actions/workflows/reserve.yml'

function formatBogota(value) {
  if (!value) return 'never'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Bogota',
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
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
      <div className="page">
        <Topbar />
        <div className="empty">Loading status...</div>
      </div>
    )
  }

  const runs = state.runs
  const latest = runs[0]
  const bookings = collectBookings(runs)
  const bookedSlots = bookings.length
  const capacity = 6
  const coverage = latest ? Math.round((bookedSlots / capacity) * 100) : 0

  return (
    <>
      <Topbar />
      <main className="page">
        <section className="hero">
          <p className="eyebrow">Reservation automation</p>
          <h1>
            A quiet room, booked <em>every weekday</em>.
          </h1>
          <p>
            The ICESI library study room is reserved the night before, 08:00 to 20:00, split into
            six two hour blocks so no account exceeds the portal's per user limit. When the ten
            person room is gone, the largest available room is taken instead.
          </p>
        </section>

        <section className="section" style={{ marginTop: 32 }}>
          <div className="card-grid">
            <StatCard
              label="Last run"
              value={latest ? formatBogota(latest.run_at) : 'never'}
              hint={latest ? `for ${latest.target_date}` : 'waiting for the first run'}
            />
            <StatCard
              label="Rooms held"
              value={`${bookedSlots}`}
              hint={`of ${capacity} weekday blocks`}
            />
            <StatCard label="Coverage" value={`${coverage}%`} hint="08:00 to 20:00 window" />
            <StatCard
              label="Last result"
              value={latest ? <StatusPill status={runStatus(latest)} /> : '-'}
              hint={
                latest
                  ? `${latest.summary?.succeeded ?? 0} of ${latest.summary?.total ?? 0} blocks ok`
                  : ''
              }
            />
          </div>
        </section>

        <Section
          id="bookings"
          eyebrow="Bookings"
          title="Reserved slots and confirmations"
          description="Every confirmed reservation, including the confirmation PDF the portal generates when the booking is created."
        >
          <BookingsTable bookings={bookings} generatedAt={latest?.run_at} formatStamp={formatBogota} />
        </Section>

        <Section
          id="calendar"
          eyebrow="Week"
          title="The week at a glance"
          description="Booked blocks per weekday and hour, so gaps in the day are obvious."
        >
          <WeekCalendar bookings={bookings} />
        </Section>

        <Section
          id="architecture"
          eyebrow="Architecture"
          title="How this runs"
          description="A cron wakes a headless browser, the run writes its state, and a Cloudflare Worker delivers this page."
        >
          <ArchitectureDiagram
            Github={Github}
            Terminal={Terminal}
            FileJson={FileJson}
            Cloud={Cloud}
            Database={Database}
            Archive={Archive}
            Monitor={Monitor}
          />
        </Section>

        <Section
          id="runs"
          eyebrow="History"
          title="Recent runs"
          description="Each run in order, with the status of every block."
        >
          <RunsHistory runs={runs} formatStamp={formatBogota} actionsUrl={ACTIONS_URL} />
        </Section>

        <footer className="footer">
          <span>
            Automated reservations for the ICESI library study room. Screenshots are kept as GitHub
            Actions artifacts.
          </span>
          <span className="mono">America/Bogota</span>
        </footer>
      </main>
    </>
  )
}
