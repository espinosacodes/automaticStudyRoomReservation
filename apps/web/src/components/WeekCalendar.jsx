/**
 * Week poll in the style of a meeting-poll calendar: a left rail with the
 * reservation facts, a SUN to SAT grid with hour rows, booked blocks rendered
 * as spanning chips, hatched weekends, and a bottom bar with the held count
 * and a Run now action.
 *
 * Each day column owns its own cells, so a slot can only ever render in the
 * column it was placed in. A two hour booking renders one chip in its start
 * cell sized to cover both hour rows; the covered cell stays empty.
 */
import { FileText } from 'lucide-react'

const DAY_LABELS = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
const HOURS = [
  '08:00',
  '09:00',
  '10:00',
  '11:00',
  '12:00',
  '13:00',
  '14:00',
  '15:00',
  '16:00',
  '17:00',
  '18:00',
  '19:00',
]
const BLOCK_HOURS = ['08:00', '10:00', '12:00', '14:00', '16:00', '18:00']

function parseDate(value) {
  const [year, month, day] = (value || '').split('-').map(Number)
  if (!year || !month || !day) return null
  return new Date(Date.UTC(year, month - 1, day))
}

function isoDate(date) {
  return date.toISOString().slice(0, 10)
}

function toMinutes(hhmm) {
  const [hours, minutes] = hhmm.split(':').map(Number)
  return hours * 60 + minutes
}

/** Sunday-start week holding the given date. */
function weekOf(targetDate) {
  const date = parseDate(targetDate)
  if (!date) return null
  const sunday = new Date(date.getTime())
  sunday.setUTCDate(sunday.getUTCDate() - date.getUTCDay())
  return DAY_LABELS.map((label, offset) => {
    const day = new Date(sunday.getTime())
    day.setUTCDate(day.getUTCDate() + offset)
    return { label, iso: isoDate(day), weekend: offset === 0 || offset === 6 }
  })
}

function monthLabel(days) {
  const first = parseDate(days[3]?.iso)
  if (!first) return ''
  return first.toLocaleDateString('en-US', { month: 'short', year: 'numeric', timeZone: 'UTC' })
}

export function WeekCalendar({ bookings, targetDate, actionsUrl }) {
  const days = weekOf(targetDate)
  if (!days) {
    return (
      <div className="calendar">
        <div className="empty">No bookings yet. The next scheduled run will fill this in.</div>
      </div>
    )
  }

  const held = new Set(
    bookings.filter((item) => item.date === targetDate).map((item) => item.start),
  ).size

  const bookingAt = (iso, hour) =>
    bookings.find((item) => item.date === iso && item.start === hour)
  const coveredAt = (iso, hour) =>
    bookings.some(
      (item) =>
        item.date === iso &&
        toMinutes(item.start) < toMinutes(hour) &&
        toMinutes(hour) < toMinutes(item.end),
    )

  return (
    <div className="calendar poll">
      <div className="poll-body">
        <aside className="poll-side" aria-label="Reservation facts">
          <div className="poll-fact">
            <p className="poll-fact-label">Reservation date</p>
            <p className="poll-fact-value">{targetDate}</p>
          </div>
          <div className="poll-fact">
            <p className="poll-fact-label">Window</p>
            <p className="poll-fact-value">Weekdays, 08:00 to 20:00</p>
          </div>
          <div className="poll-fact">
            <p className="poll-fact-label">Room</p>
            <p className="poll-fact-value">204BI preferred</p>
          </div>
        </aside>

        <div className="calendar-scroll">
          <div className="poll-month">{monthLabel(days)}</div>
          <div className="calendar-week poll-week">
            <div className="calendar-col calendar-col-hours">
              <div className="calendar-head" />
              {HOURS.map((hour) => (
                <div className="calendar-hour poll-hour" key={hour}>
                  {hour}
                </div>
              ))}
            </div>

            {days.map((day) => (
              <div
                className={`calendar-col${day.weekend ? ' weekend' : ''}`}
                key={day.iso}
              >
                <div className="calendar-head">
                  <strong>{day.label}</strong>
                  <span>{day.iso.slice(8)}</span>
                </div>
                {HOURS.map((hour) => {
                  const booking = bookingAt(day.iso, hour)
                  const covered = !booking && coveredAt(day.iso, hour)
                  return (
                    <div className="calendar-cell poll-cell" key={`${day.iso}-${hour}`}>
                      {booking ? (
                        <div
                          className="calendar-slot booked span2"
                          title={`${booking.room} ${booking.start}-${booking.end}`}
                        >
                          <strong>{booking.room}</strong>
                          <span className="mono">
                            {booking.start}-{booking.end}
                          </span>
                          {booking.pdf && (
                            <a
                              className="slot-pdf"
                              href={`/${booking.pdf}`}
                              target="_blank"
                              rel="noreferrer"
                              title="Official confirmation PDF"
                              onClick={(event) => event.stopPropagation()}
                            >
                              <FileText size={13} />
                              PDF
                            </a>
                          )}
                        </div>
                      ) : covered ? (
                        <div className="calendar-slot covered" aria-hidden="true" />
                      ) : (
                        <div className="calendar-slot empty">Not reserved</div>
                      )}
                    </div>
                  )
                })}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="poll-foot">
        <span>
          {held} / {BLOCK_HOURS.length} blocks held
        </span>
        {actionsUrl && (
          <a className="button dark" href={actionsUrl} target="_blank" rel="noreferrer">
            Run now
          </a>
        )}
      </div>

      <div className="calendar-legend">
        <span>
          <i className="swatch" aria-hidden="true" /> Booked, 204BI preferred
        </span>
        <span>
          <i className="swatch free" aria-hidden="true" /> Not reserved
        </span>
        <span>Weekdays only, 08:00 to 20:00 Bogota</span>
      </div>
    </div>
  )
}

export { HOURS, DAY_LABELS, BLOCK_HOURS }
