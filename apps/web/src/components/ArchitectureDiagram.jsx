/**
 * Architecture of the system, drawn inline as SVG in the Cloudflare
 * engineering-diagram style from the reference screenshots: labelled groups,
 * small boxed nodes, dashed request/flow edges, and one highlighted node.
 *
 * Data flow, left to right:
 *   scheduler -> automation -> status.json -> Worker -> visitor
 * with private GitHub run artifacts for official confirmation PDFs.
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

export function ArchitectureDiagram({ Github, Terminal, FileJson, Cloud, Archive, Monitor }) {
  return (
    <div className="diagram">
      <svg viewBox="0 0 1120 214" role="img" aria-label="How the reservation system runs">
        <defs>
          <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--line-strong)" />
          </marker>
        </defs>

        <Group x={4} w={170} label="Schedule" />
        <Group x={190} w={380} label="Compute" />
        <Group x={586} w={200} label="State" />
        <Group x={802} w={290} label="Delivery" />

        <Node x={20} w={140} title="Cron" sub="23:59 Bogota" Icon={Github} />
        <Node x={206} w={165} title="Playwright run" sub="6 blocks, 6 accounts" Icon={Terminal} />
        <Node x={386} w={170} title="Portal" sub="banner9.icesi.edu.co" Icon={Monitor} />
        <Node x={602} w={168} title="status.json" sub="booking outcomes" Icon={FileJson} />
        <Node x={818} w={200} title="Worker" sub="static dashboard" accent Icon={Cloud} />


        <Node x={602} y={140} w={180} title="Run artifacts" sub="Official PDFs, private" Icon={Archive} />

        <Edge x1={160} y1={82} x2={206} y2={82} />
        <Edge x1={371} y1={82} x2={386} y2={82} />
        <Edge x1={556} y1={82} x2={602} y2={82} />
        <Edge x1={770} y1={82} x2={818} y2={82} />

        <Edge x1={686} y1={110} x2={686} y2={140} dashed />

        <text className="d-note" x={818} y={206}>
          reservation.getcuria.us
        </text>
        <text className="d-note" x={206} y={206}>
          GitHub Actions runner, no server to babysit
        </text>
      </svg>
    </div>
  )
}
