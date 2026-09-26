import { useEffect, useState } from 'react'
import { Archive, Cloud, FileJson, Github, Monitor, Terminal } from 'lucide-react'

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
  const [state, setState] = useState({ loading: true, runs: [], error: false })
  const [selectedDate, setSelectedDate] = useState('')

  useEffect(() => {
    let active = true
    fetch('/status.json', { cache: 'no-store' })
      .then((response) => {
        if (!response.ok) throw new Error('Status unavailable')
        return response.json()
      })
      .then((data) => {
        if (!Array.isArray(data.runs)) throw new Error('Invalid status')
        if (active) setState({ loading: false, runs: data.runs, error: false })
      })
      .catch(() => {
        if (active) setState({ loading: false, runs: [], error: true })
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
  const dates = [...new Set(runs.map((run) => run.target_date))].sort().reverse()
  const activeDate = selectedDate || latest?.target_date
  const dailyBookings = bookings.filter((booking) => booking.date === activeDate)
  const bookedSlots = new Set(dailyBookings.map((booking) => booking.start)).size
  const capacity = 6
  const coverage = latest ? Math.min(100, Math.round((bookedSlots / capacity) * 100)) : 0

  return (
    <>
      <Topbar />
      <main className="page">
        {state.error && <div className="notice" role="alert">Status could not be loaded. <button className="button ghost" onClick={() => window.location.reload()}>Retry</button></div>}
        <section className="hero">
          <p className="eyebrow">Reservation automation</p>
          <h1>
            Your study room, <em>at a glance</em>.
          </h1>
          <p>
            Track confirmed bookings, daily coverage, and official reservation receipts.
            The schedule targets six two hour blocks, Monday to Friday, 08:00 to 20:00 Bogota.
          </p>
        </section>

        <nav className="dashboard-nav" aria-label="Dashboard sections">
          <a href="#bookings">Reservations</a><a href="#calendar">Week</a><a href="#runs">Run history</a><a href="#architecture">How it works</a>
        </nav>
        <div className="date-toolbar">
          <label htmlFor="booking-date">Reservation date</label>
          <select id="booking-date" value={activeDate || ''} onChange={(event) => setSelectedDate(event.target.value)} disabled={!dates.length}>
            {!dates.length && <option value="">No runs yet</option>}
            {dates.map((date) => <option key={date} value={date}>{date}</option>)}
          </select>
        </div>
        <section className="section" style={{ marginTop: 24 }}>
          <div className="card-grid">
            <StatCard
              label="Last run"
              value={latest ? formatBogota(latest.run_at) : 'never'}
              hint={latest ? `for ${latest.target_date}` : 'waiting for the first run'}
            />
            <StatCard
              label="Blocks confirmed"
              value={`${bookedSlots}`}
              hint={`of ${capacity} blocks on ${activeDate || 'the selected date'}`}
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
          description="Every confirmed reservation, with official PDFs available in private run artifacts when captured."
        >
          <BookingsTable bookings={dailyBookings} generatedAt={latest?.run_at} formatStamp={formatBogota} />
        </Section>

        <Section
          id="calendar"
          eyebrow="Week"
          title="The week at a glance"
          description="Booked blocks per weekday and hour, so gaps in the day are obvious."
        >
          <WeekCalendar bookings={bookings} targetDate={activeDate} />
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
