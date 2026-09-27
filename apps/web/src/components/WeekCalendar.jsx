/**
 * Week view of booked slots, following the week-calendar reference: weekday
 * columns, hour rows, and booked blocks rendered as solid chips.
 *
 * The layout deliberately avoids CSS grid auto-placement. An earlier version
 * emitted header cells and body cells independently, so the browser placed them
 * into the wrong tracks and booked slots drifted into the wrong day columns.
 * Here every day column owns its own cells, so a slot can only ever render in
 * the column it was placed in.
 */
import { FileText } from 'lucide-react'

const DAY_LABELS = ['MON', 'TUE', 'WED', 'THU', 'FRI']
const HOURS = ['08:00', '10:00', '12:00', '14:00', '16:00', '18:00']

function parseDate(value) {
  const [year, month, day] = (value || '').split('-').map(Number)
  if (!year || !month || !day) return null
  return new Date(Date.UTC(year, month - 1, day))
}

function isoDate(date) {
  return date.toISOString().slice(0, 10)
}

/**
 * The week holding the latest booking. Without pinning to one week, slots from
 * different dates would collapse into the same columns.
 */
function weekOf(bookings, targetDate) {
  const latest = bookings.reduce(
    (max, booking) => (booking.date > max ? booking.date : max),
    bookings[0]?.date ?? '',
  )
  const date = parseDate(targetDate || latest)
  if (!date) return null
  const day = date.getUTCDay() // 0 Sunday to 6 Saturday
  const monday = new Date(date.getTime())
  monday.setUTCDate(monday.getUTCDate() - ((day + 6) % 7))
  return monday
}

export function WeekCalendar({ bookings, targetDate }) {
  if (bookings.length === 0 && !targetDate) {
    return (
      <div className="calendar">
        <div className="empty">No bookings yet. The next scheduled run will fill this in.</div>
      </div>
    )
  }

  const monday = weekOf(bookings, targetDate)
  const days = monday
    ? DAY_LABELS.map((label, offset) => {
        const date = new Date(monday.getTime())
        date.setUTCDate(date.getUTCDate() + offset)
        return { label, iso: isoDate(date) }
      })
    : []

  return (
    <div className="calendar">
      <div className="calendar-scroll">
        <div className="calendar-week">
          <div className="calendar-col calendar-col-hours">
            <div className="calendar-head" />
            {HOURS.map((hour) => (
              <div className="calendar-hour" key={hour}>
                {hour}
              </div>
            ))}
          </div>

          {days.map((day) => (
            <div className="calendar-col" key={day.iso}>
              <div className="calendar-head">
                <strong>{day.label}</strong>
                <span>{day.iso.slice(5)}</span>
              </div>
              {HOURS.map((hour) => {
                const booking = bookings.find(
                  (item) => item.date === day.iso && item.start === hour,
                )
                return (
                  <div className="calendar-cell" key={`${day.iso}-${hour}`}>
                    {booking ? (
                      <div className="calendar-slot booked" title={`${booking.room} ${booking.start}-${booking.end}`}>
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

export { HOURS, DAY_LABELS }
