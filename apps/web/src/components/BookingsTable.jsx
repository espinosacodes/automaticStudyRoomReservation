/**
 * Every confirmed reservation with a link to its confirmation PDF, plus a
 * print-to-PDF export of the list itself.
 */
import { Download, FileText, Printer } from 'lucide-react'

/** Flat list of confirmed slots across all runs, newest run first. */
export function collectBookings(runs) {
  const seen = new Set()
  const rows = []
  for (const run of runs) {
    for (const block of run.blocks ?? []) {
      if (block.status !== 'success') continue
      const key = `${run.target_date}|${block.start}|${block.room}`
      if (seen.has(key)) continue
      seen.add(key)
      rows.push({
        date: run.target_date,
        start: block.start,
        end: block.end,
        account: block.account,
        room: block.room,
        pdf: block.pdf || '',
      })
    }
  }
  return rows.sort((a, b) => `${a.date} ${a.start}`.localeCompare(`${b.date} ${b.start}`))
}

export function BookingsTable({ bookings, generatedAt, formatStamp }) {
  return (
    <div className="stack">
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <p className="muted">
          {bookings.length} slot{bookings.length === 1 ? '' : 's'} confirmed
          {generatedAt ? `, updated ${formatStamp(generatedAt)}` : ''}.
        </p>
        <button
          type="button"
          className="button ghost no-print"
          onClick={() => window.print()}
          disabled={bookings.length === 0}
        >
          <Printer size={15} />
          Download PDF
        </button>
      </div>

      {bookings.length === 0 ? (
        <div className="table-wrap">
          <div className="empty">No confirmed reservations yet.</div>
        </div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Block</th>
                <th>Account</th>
                <th>Room</th>
                <th>Confirmation</th>
              </tr>
            </thead>
            <tbody>
              {bookings.map((booking) => (
                <tr key={`${booking.date}-${booking.start}-${booking.room}`}>
                  <td>{booking.date}</td>
                  <td className="mono">
                    {booking.start} - {booking.end}
                  </td>
                  <td className="mono">{booking.account}</td>
                  <td>{booking.room}</td>
                  <td>
                    {booking.pdf ? (
                      <a className="pill ok" href={`/${booking.pdf}`} target="_blank" rel="noreferrer">
                        <FileText size={13} />
                        PDF
                      </a>
                    ) : (
                      <span className="pill busy">
                        <Download size={13} />
                        pending
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
