import { Cloud, ExternalLink } from 'lucide-react'

const ACTIONS_URL =
  'https://github.com/espinosacodes/automaticStudyRoomReservation/actions/workflows/reserve.yml'

export function Topbar() {
  return (
    <header className="topbar">
      <div className="brand">
        <Cloud size={20} strokeWidth={1.8} />
        <div>
          reservation.getcuria.us
          <small>Automated study room booking</small>
        </div>
      </div>
      <div className="row">
        <span className="badge">ICESI library</span>
        <a className="button ghost" href={ACTIONS_URL} target="_blank" rel="noreferrer">
          <ExternalLink size={15} />
          Screenshots
        </a>
      </div>
    </header>
  )
}
