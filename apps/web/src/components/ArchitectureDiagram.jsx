/**
 * Architecture of the system as an infrastructure flow, following the
 * reference diagram: users on the left, compute, a dashed routes box listing
 * the six blocks, the dispatch namespace, a Data & Storage column, the
 * coordinator, and a browser mock showing this page on the right.
 * Dashed gray connectors run left to right; each column has its own accent.
 */

const STANDARD_BLOCKS = [
  { start: '08:00', room: '204BI' },
  { start: '10:00', room: '204BI' },
  { start: '12:00', room: '204BI' },
  { start: '14:00', room: '204BI' },
  { start: '16:00', room: '204BI' },
]

function shortRoom(room) {
  if (!room) return '204BI'
  const code = String(room).match(/\d+[A-Z]+/)
  return code ? code[0] : String(room).slice(0, 12)
}

function Tag({ x, y, tone, children }) {
  return (
    <text className={`d-tag d-tag-${tone}`} x={x} y={y}>
      {children}
    </text>
  )
}

function Node({ x, y, w = 120, h = 52, tone = '', title, sub, Icon }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <rect className={`d-node${tone ? ` d-node-${tone}` : ''}`} width={w} height={h} rx={10} />
      {Icon && (
        <g transform="translate(12 14)">
          <Icon size={16} strokeWidth={1.7} className={`d-node-icon${tone ? ` d-node-icon-${tone}` : ''}`} />
        </g>
      )}
      <text className="d-node-title" x={Icon ? 38 : 12} y="23">
        {title}
      </text>
      {sub && (
        <text className="d-node-sub" x={Icon ? 38 : 12} y="39">
          {sub}
        </text>
      )}
    </g>
  )
}

function Column({ x, w, label, children }) {
  return (
    <>
      <rect
        x={x}
        y={40}
        width={w}
        height={190}
        rx={12}
        fill="none"
        stroke="var(--line)"
        strokeDasharray="4 4"
      />
      <text className="d-label" x={x + 12} y={62}>
        {label}
      </text>
      {children}
    </>
  )
}

function Edge({ x1, y1, x2, y2 }) {
  const mid = (x1 + x2) / 2
  return (
    <path
      className="d-edge-flow"
      d={`M ${x1} ${y1} C ${mid} ${y1}, ${mid} ${y2}, ${x2} ${y2}`}
      markerEnd="url(#flow-arrow)"
    />
  )
}

export function ArchitectureDiagram({
  blocks,
  Users,
  Terminal,
  Monitor,
  AlarmClock,
  FileJson,
  Archive,
  Database,
  Cloud,
}) {
  const routes = (blocks?.length ? blocks : STANDARD_BLOCKS).slice(0, 6).map((block) => ({
    start: block.start,
    room: shortRoom(block.room),
  }))
  while (routes.length < 6) routes.push({ start: '--:--', room: '-' })

  const stages = [
    { label: 'Accounts', detail: 'Six Banner logins, one block each' },
    { label: 'Viewer', detail: 'Google sign-in, allow-listed emails' },
    { label: 'Compute', detail: 'Playwright drives banner9.icesi.edu.co' },
    { label: 'Routes', detail: routes.map((r) => `${r.start} → ${r.room}`).join('  ·  ') },
    { label: 'Dispatch', detail: 'Cron fires 23:59 Bogota' },
    { label: 'Data & Storage', detail: 'status.json, confirmation PDFs, D1 for auth' },
    { label: 'Coordinator', detail: 'Cloudflare Worker serves the dashboard' },
  ]

  return (
    <div className="diagram" data-optical>
      <div className="diagram-wide">
        <svg viewBox="0 0 1180 300" role="img" aria-label="How the reservation system runs">
        <defs>
          <marker
            id="flow-arrow"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--line-strong)" />
          </marker>
        </defs>

        {/* Users */}
        <Tag x={16} y={66} tone="user">
          Accounts
        </Tag>
        <Node x={16} y={76} w={112} h={48} tone="user" title="6 accounts" Icon={Users} />
        <Tag x={16} y={140} tone="user">
          Viewer
        </Tag>
        <Node x={16} y={150} w={112} h={48} tone="user" title="Google login" />

        {/* Compute */}
        <Column x={150} w={120} label="Compute">
          <Node x={160} y={80} w={108} h={52} tone="compute" title="Playwright" Icon={Terminal} />
          <Node x={160} y={142} w={108} h={52} tone="compute" title="Portal" sub="banner9" Icon={Monitor} />
        </Column>

        {/* Routes */}
        <Column x={300} w={180} label="Routes">
          {routes.map((route, index) => (
            <text key={route.start} className="d-route" x={316} y={92 + index * 22}>
              {route.start} → {route.room}
            </text>
          ))}
        </Column>

        {/* Dispatch */}
        <Column x={510} w={110} label="Dispatch">
          <Node x={520} y={120} w={90} h={52} tone="compute" title="Cron" sub="23:59" Icon={AlarmClock} />
        </Column>

        {/* Data & Storage */}
        <Column x={650} w={150} label="Data & Storage">
          <Node x={660} y={76} w={130} h={44} tone="data" title="status.json" Icon={FileJson} />
          <Node x={660} y={128} w={130} h={44} tone="data" title="PDFs" Icon={Archive} />
          <Node x={660} y={180} w={130} h={44} tone="data" title="D1" sub="auth" Icon={Database} />
        </Column>

        {/* Coordinator */}
        <Column x={830} w={110} label="Coordinator">
          <Node x={838} y={120} w={94} h={52} tone="compute" title="Worker" Icon={Cloud} />
        </Column>

        {/* Browser mock */}
        <g transform="translate(970 60)">
          <rect width={190} height={160} rx={12} fill="#fff" stroke="var(--line-strong)" />
          <line x1={0} y1={28} x2={190} y2={28} stroke="var(--line)" />
          <circle cx={14} cy={14} r={4} fill="var(--line-strong)" />
          <circle cx={27} cy={14} r={4} fill="var(--line-strong)" />
          <circle cx={40} cy={14} r={4} fill="var(--line-strong)" />
          <rect x={54} y={7} width={126} height={15} rx={7} fill="var(--paper-deep)" />
          <text className="d-browser-url" x={62} y={18}>
            reservation.getcuria.us
          </text>
          <rect x={14} y={44} width={120} height={10} rx={5} fill="var(--orange-soft)" />
          <rect x={14} y={62} width={162} height={8} rx={4} fill="var(--paper-deep)" />
          <rect x={14} y={78} width={162} height={8} rx={4} fill="var(--paper-deep)" />
          <rect x={14} y={94} width={100} height={8} rx={4} fill="var(--paper-deep)" />
          <rect x={14} y={116} width={162} height={26} rx={8} fill="var(--orange-soft)" stroke="var(--orange-line)" />
        </g>

        <Edge x1={120} y1={100} x2={150} y2={106} />
        <Edge x1={270} y1={132} x2={300} y2={132} />
        <Edge x1={480} y1={132} x2={510} y2={146} />
        <Edge x1={620} y1={146} x2={650} y2={140} />
        <Edge x1={800} y1={140} x2={830} y2={146} />
        <Edge x1={940} y1={146} x2={970} y2={140} />

        <text className="d-note" x={150} y={262}>
          GitHub Actions runner, no server to babysit
        </text>
        </svg>
      </div>

      {/* Narrow screens get a readable stack instead of a shrunken SVG. */}
      <ol className="diagram-stack">
        {stages.map((stage) => (
          <li key={stage.label}>
            <span className="diagram-stage">{stage.label}</span>
            <span className="diagram-detail">{stage.detail}</span>
          </li>
        ))}
      </ol>
    </div>
  )
}
