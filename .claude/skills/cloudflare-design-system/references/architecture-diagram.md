# Architecture diagram

Inline SVG in the Cloudflare engineering style. The goal is that the diagram
reads as a real system, so boxes name a technology and its job, columns are
labelled with a phase, and edges show direction.

## Layout

Draw in a wide viewBox, for example `0 0 1180 300`, and let the SVG scale with
`width: 100%`. Wrap it so narrow screens can scroll horizontally rather than
squash the diagram:

```css
.diagram { overflow-x: auto; }
.diagram svg { min-width: 900px; width: 100%; height: auto; }
```

Left to right: actors, compute, a dashed routes box listing the actual items
being processed, the dispatch namespace, a Data and Storage column, the
coordinator, and a browser mock showing the delivered page.

## Columns

A column is a dashed rounded rect with a small uppercase label sitting on its
top edge. Columns describe phases, for example `Compute`, `Routes`,
`Dispatch`, `Data & Storage`, `Coordinator`. One column per phase, with the
nodes for that phase inside.

```jsx
function Column({ x, w, label, children }) {
  return (
    <>
      <rect x={x} y={40} width={w} height={190} rx={12}
        fill="none" stroke="var(--line)" strokeDasharray="4 4" />
      <text className="d-label" x={x + 12} y={62}>{label}</text>
    </>
  )
}
```

## Nodes

A node is a rounded rect with an optional Lucide icon, a title, and a
sub-label. The sub-label is where the honesty lives: name the real thing,
`23:59 Bogota`, `banner9`, `static dashboard`, not a vague label.

```jsx
function Node({ x, y = 54, w = 120, h = 52, tone = '', title, sub, Icon }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <rect className={`d-node${tone ? ` d-node-${tone}` : ''}`} width={w} height={h} rx={10} />
      {Icon && (
        <g transform="translate(12 14)">
          <Icon size={16} strokeWidth={1.7} className={`d-node-icon${tone ? ` d-node-icon-${tone}` : ''}`} />
        </g>
      )}
      <text className="d-node-title" x={Icon ? 38 : 12} y="23">{title}</text>
      {sub && <text className="d-node-sub" x={Icon ? 38 : 12} y="39">{sub}</text>}
    </g>
  )
}
```

Tone classes color the border and icon per column: `user` is orange,
`compute` is blue, `data` is pink. Size each box to its longest label:
a box that fits the title but clips the sub-label is the most common way
these diagrams break, so measure the text and widen the box and its column
rather than letting labels bleed into the next node.

## Routes box

The routes box is a dashed column whose rows are the actual items flowing
through the system, rendered from props with static defaults as fallback.
Each row is one short mono line, for example `08:00 → 204BI`. Keep rows to
about six so the box stays readable.

## Browser mock

The flow ends in a browser mock: a white rounded rect with three dots, a URL
pill with the real hostname, a few content bars, and one accent block. It
tells the reader where the flow lands without a screenshot.

## Edges

Edges are dashed cubic curves with an arrow marker, so a line leaving a box
arrives pointing at the next one.

```jsx
function Edge({ x1, y1, x2, y2 }) {
  const mid = (x1 + x2) / 2
  return (
    <path className="d-edge-flow"
      d={`M ${x1} ${y1} C ${mid} ${y1}, ${mid} ${y2}, ${x2} ${y2}`}
      markerEnd="url(#flow-arrow)" />
  )
}
```

Define the marker once in `<defs>`:

```jsx
<marker id="flow-arrow" viewBox="0 0 10 10" refX="9" refY="5"
  markerWidth="6" markerHeight="6" orient="auto">
  <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--line-strong)" />
</marker>
```

## Telling the truth in the diagram

One short note under the diagram carries context that would clutter a node,
for example a one-line tradeoff. Keep it to one line. If a component is not
real yet, either label it as planned or leave it out. A diagram that shows
infrastructure that does not exist is worse than no diagram, because people
plan against it.
