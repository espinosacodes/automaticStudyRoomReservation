/**
 * Architecture of the system, drawn inline as SVG in the Cloudflare
 * engineering-diagram style from the reference screenshots: labelled groups,
 * small boxed nodes, dashed request/flow edges, and one highlighted node.
 *
 * Data flow, left to right:
 *   scheduler -> automation -> status.json -> Worker -> visitor
 * with Database (D1) for auth and Object storage (R2) for the confirmation PDFs.
 */

const GROUP_LABEL_Y = 24
const NODE_Y = 54
const NODE_H = 56

function Node({ x, y = NODE_Y, w = 132, title, sub, accent = false, Icon }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <rect className={`node-box${accent ? ' accent' : ''}`} width={w} height={NODE_H} />
      {Icon && (
        <g transform="translate(12 16)">
          <Icon size={16} strokeWidth={1.7} className="node-icon" />
        </g>
      )}
      <text className="d-node-title" x={Icon ? 38 : 12} y="25">
        {title}
      </text>
      <text className="d-node-sub" x={Icon ? 38 : 12} y="41">
        {sub}
      </text>
    </g>
  )
}

function Edge({ x1, y1, x2, y2, dashed = false }) {
  const mid = (x1 + x2) / 2
  return (
    <path
      className={dashed ? 'd-edge-container' : 'd-edge'}
      d={`M ${x1} ${y1} C ${mid} ${y1}, ${mid} ${y2}, ${x2} ${y2}`}
      markerEnd="url(#arrow)"
    />
  )
}

function Group({ x, w, label }) {
  return (
    <>
      <rect
        x={x}
        y={10}
        width={w}
        height={128}
        rx={12}
        fill="none"
        stroke="var(--line)"
        strokeDasharray="4 4"
      />
      <text className="d-label" x={x + 12} y={GROUP_LABEL_Y}>
        {label}
      </text>
    </>
  )
}

export function ArchitectureDiagram({ Github, Terminal, FileJson, Cloud, Database, Archive, Monitor }) {
  return (
    <div className="diagram">
      <svg viewBox="0 0 1020 200" role="img" aria-label="How the reservation system runs">
        <defs>
          <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--line-strong)" />
          </marker>
        </defs>

        <Group x={4} w={180} label="Schedule" />
        <Group x={204} w={300} label="Compute" />
        <Group x={524} w={200} label="State" />
        <Group x={744} w={272} label="Delivery" />

        <Node x={22} title="Cron" sub="23:59 Bogota" Icon={Github} />
        <Node x={222} title="Playwright run" sub="6 blocks, 6 accounts" Icon={Terminal} />
        <Node x={374} title="Portal" sub="banner9.icesi.edu.co" Icon={Monitor} />
        <Node x={542} title="status.json" sub="bookings + pdfs" Icon={FileJson} />
        <Node x={762} title="Worker" sub="static + API" accent Icon={Cloud} />

        <Node x={542} y={132} w={88} title="D1" sub="auth" Icon={Database} />
        <Node x={644} y={132} w={92} title="R2" sub="pdfs" Icon={Archive} />

        <Edge x1={154} y1={82} x2={222} y2={82} />
        <Edge x1={354} y1={82} x2={374} y2={82} />
        <Edge x1={506} y1={82} x2={542} y2={82} />
        <Edge x1={674} y1={82} x2={762} y2={82} />
        <Edge x1={590} y1={110} x2={586} y2={132} />
        <Edge x1={690} y1={82} x2={690} y2={132} dashed />

        <text className="d-note" x={762} y={186}>
          reservation.getcuria.us
        </text>
        <text className="d-note" x={222} y={186}>
          GitHub Actions runner, no server to babysit
        </text>
      </svg>
    </div>
  )
}
