/**
 * Confirmed reservations and links to private run artifacts containing
 * the original university-issued confirmation PDFs.
 */
import { FileText } from 'lucide-react'

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
        pdf: block.pdf_status === 'captured' ? block.pdf : '',
        confirmationUrl: /^https:\/\/github\.com\/espinosacodes\/automaticStudyRoomReservation\/actions\/runs\/\d+$/.test(block.confirmation_run_url || '') ? block.confirmation_run_url : '',
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

      </div>

      {bookings.length === 0 ? (
        <div className="table-wrap" data-optical>
          <div className="empty">No confirmed reservations yet.</div>
        </div>
      ) : (
        <div className="table-wrap" data-optical>
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
                  <td data-label="Date">{booking.date}</td>
                  <td className="mono" data-label="Block">
                    {booking.start} - {booking.end}
                  </td>
                  <td className="mono" data-label="Account">
                    {booking.account}
                  </td>
                  <td data-label="Room">{booking.room}</td>
                  <td data-label="Confirmation">
                    {booking.pdf ? (
                      <a className="pill ok" href={`/${booking.pdf}`} target="_blank" rel="noreferrer">
                        <FileText size={13} />
                        PDF
                      </a>
                    ) : booking.confirmationUrl ? (
                      <a className="pill ok" href={booking.confirmationUrl} target="_blank" rel="noreferrer">
                        <FileText size={13} />
                        Run artifact
                      </a>
                    ) : (
                      <span className="pill busy">Not captured</span>
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
