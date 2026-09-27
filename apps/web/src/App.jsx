import { useEffect, useMemo, useState } from 'react'
import {
  AlarmClock,
  Archive,
  CalendarRange,
  ChevronLeft,
  ChevronRight,
  Cloud,
  Database,
  FileJson,
  Monitor,
  Terminal,
  Users,
} from 'lucide-react'

import { ArchitectureDiagram } from './components/ArchitectureDiagram.jsx'
import { BookingsTable, collectBookings } from './components/BookingsTable.jsx'
import { RunsHistory, runStatus } from './components/RunsHistory.jsx'
import { Section, StatCard, StatusPill } from './components/ui.jsx'
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

/** Today in Bogota as YYYY-MM-DD, so the default week is the local one. */
function bogotaToday() {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Bogota',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date())
}

function shiftDays(iso, days) {
  const date = new Date(`${iso}T12:00:00Z`)
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}

function weekRangeLabel(iso) {
  const date = new Date(`${iso}T12:00:00Z`)
  const sunday = new Date(date)
  sunday.setUTCDate(sunday.getUTCDate() - sunday.getUTCDay())
  const saturday = new Date(sunday)
  saturday.setUTCDate(saturday.getUTCDate() + 6)
  const fmt = new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC',
  })
  return `${fmt.format(sunday)} to ${fmt.format(saturday)}`
}

/** Highlight the section currently in view in the sidebar. */
function useActiveSection(ids) {
  const [active, setActive] = useState(ids[0])
  useEffect(() => {
    const sections = ids
      .map((id) => document.getElementById(id))
      .filter(Boolean)
    if (sections.length === 0) return undefined
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)
        if (visible[0]) setActive(visible[0].target.id)
      },
      { rootMargin: '-15% 0px -70% 0px', threshold: 0 },
    )
    sections.forEach((section) => observer.observe(section))
    return () => observer.disconnect()
  }, [ids.join('|')]) // eslint-disable-line react-hooks/exhaustive-deps
  return active
}

export default function App() {
  const [state, setState] = useState({ loading: true, runs: [], error: false })
  const [anchor, setAnchor] = useState('')
  const [selectedDay, setSelectedDay] = useState('')

  const sectionIds = useMemo(
    () => ['bookings', 'calendar', 'runs', 'architecture'],
    [],
  )
  const activeSection = useActiveSection(sectionIds)

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
    return <div className="empty">Loading status...</div>
  }

  const runs = state.runs
  const latest = runs[0]
  const bookings = collectBookings(runs)
  const bookedDays = [...new Set(bookings.map((booking) => booking.date))].sort().reverse()

  const viewAnchor = anchor || latest?.target_date || bogotaToday()
  const viewDay = selectedDay || viewAnchor
  const dayBookings = bookings.filter((booking) => booking.date === viewDay)
  const bookedSlots = dayBookings.length
  const capacity = 6

  const goToWeek = (iso) => {
    setAnchor(iso)
    setSelectedDay(iso)
  }
  const openDay = (iso) => {
    setSelectedDay(iso)
    setAnchor(iso)
  }

  return (
    <div className="page">
      {state.error && (
        <div className="notice" role="alert">
          Status could not be loaded.{' '}
          <button className="button ghost" onClick={() => window.location.reload()}>
            Retry
          </button>
        </div>
      )}

      <section className="hero">
        <p className="eyebrow">Reservation automation</p>
        <h1>
          Your study room, <em>at a glance</em>.
        </h1>
        <p>
          Track confirmed bookings, daily coverage, and official reservation receipts. The schedule
          targets six two hour blocks, Monday to Friday, 08:00 to 20:00 Bogota.
        </p>
      </section>

      <section className="section" style={{ marginTop: 28 }}>
        <div className="card-grid" data-optical>
          <StatCard
            label="Last run"
            value={latest ? formatBogota(latest.run_at) : 'never'}
            hint={latest ? `for ${latest.target_date}` : 'waiting for the first run'}
          />
          <StatCard
            label="Blocks held"
            value={`${bookedSlots}`}
            hint={`of ${capacity} on ${viewDay}`}
          />
          <StatCard
            label="Coverage"
            value={`${Math.min(100, Math.round((bookedSlots / capacity) * 100))}%`}
            hint="08:00 to 20:00 window"
          />
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
        eyebrow="Reservations"
        title="Reserved slots and confirmations"
        description="Every confirmed reservation, with its official confirmation PDF captured from the portal."
      >
        {bookedDays.length > 1 && (
          <div className="pill-tabs" role="group" aria-label="Reservation date">
            {bookedDays.map((date) => (
              <button
                key={date}
                type="button"
                className={date === viewDay ? 'active' : ''}
                aria-pressed={date === viewDay}
                onClick={() => openDay(date)}
              >
                {date}
              </button>
            ))}
          </div>
        )}
        <BookingsTable bookings={dayBookings} generatedAt={latest?.run_at} formatStamp={formatBogota} />
      </Section>

      <Section
        id="calendar"
        eyebrow="Week"
        title="The week at a glance"
        description="Booked blocks per weekday and hour, so gaps in the day are obvious. Move between weeks to see the past."
        action={
          <div className="week-nav">
            <button
              type="button"
              className="button ghost icon-only"
              aria-label="Previous week"
              onClick={() => goToWeek(shiftDays(viewAnchor, -7))}
            >
              <ChevronLeft size={16} />
            </button>
            <span className="week-range">
              <CalendarRange size={14} />
              {weekRangeLabel(viewAnchor)}
            </span>
            <button
              type="button"
              className="button ghost icon-only"
              aria-label="Next week"
              onClick={() => goToWeek(shiftDays(viewAnchor, 7))}
            >
              <ChevronRight size={16} />
            </button>
            <button type="button" className="button ghost" onClick={() => goToWeek(bogotaToday())}>
              This week
            </button>
          </div>
        }
      >
        <WeekCalendar
          bookings={bookings}
          targetDate={viewAnchor}
          selectedDay={viewDay}
          onSelectDay={openDay}
          actionsUrl={ACTIONS_URL}
        />
      </Section>

      <Section
        id="runs"
        eyebrow="History"
        title="Recent runs"
        description={`Every recorded run, newest first, all ${runs.length} of them. Each one shows the status of every block.`}
      >
        <RunsHistory runs={runs} formatStamp={formatBogota} actionsUrl={ACTIONS_URL} />
      </Section>

      <Section
        id="architecture"
        eyebrow="Architecture"
        title="How this runs"
        description="A cron wakes a headless browser, the run writes its state, and a Cloudflare Worker delivers this page."
      >
        <ArchitectureDiagram
          blocks={(latest?.blocks ?? []).map((block) => ({
            start: block.start,
            room: block.room,
          }))}
          Users={Users}
          Terminal={Terminal}
          Monitor={Monitor}
          AlarmClock={AlarmClock}
          FileJson={FileJson}
          Archive={Archive}
          Database={Database}
          Cloud={Cloud}
        />
      </Section>

      <footer className="footer">
        <span>
          Automated reservations for the ICESI library study room. Screenshots are kept as GitHub
          Actions artifacts.
        </span>
        <span className="mono">America/Bogota</span>
      </footer>
    </div>
  )
}
