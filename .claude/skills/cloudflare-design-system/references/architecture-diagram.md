# Architecture diagram

Inline SVG in the Cloudflare engineering style. The goal is that the diagram
reads as a real system, so boxes name a technology and its job, groups are
labelled with a phase, and edges show direction.

## Layout

Draw in a wide viewBox, for example `0 0 1120 214`, and let the SVG scale with
`width: 100%`. Wrap it so narrow screens can scroll horizontally rather than
squash the diagram:

```css
.diagram { overflow-x: auto; }
.diagram svg { min-width: 900px; width: 100%; height: auto; }
```

## Groups

A group is a dashed rounded rect with a small uppercase label sitting on its top
edge. Groups describe phases left to right, for example `Schedule`, `Compute`,
`State`, `Delivery`. One group per phase, with the nodes for that phase inside.

```jsx
function Group({ x, w, label }) {
  return (
    <>
      <rect x={x} y={10} width={w} height={128} rx={12}
        fill="none" stroke="var(--line)" strokeDasharray="4 4" />
      <text className="d-label" x={x + 12} y={24}>{label}</text>
    </>
  )
}
```

## Nodes

A node is a `132` by `56` rounded rect with an optional Lucide icon, a title,
and a sub-label. The sub-label is where the honesty lives: name the real thing,
`23:59 Bogota`, `banner9.icesi.edu.co`, `static + API`, not a vague label.

```jsx
function Node({ x, y = 54, w = 132, title, sub, accent = false, Icon }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <rect className={`node-box${accent ? ' accent' : ''}`} width={w} height={56} />
      {Icon && (
        <g transform="translate(12 16)">
          <Icon size={16} strokeWidth={1.7} className="node-icon" />
        </g>
      )}
      <text className="d-node-title" x={Icon ? 38 : 12} y="25">{title}</text>
      <text className="d-node-sub" x={Icon ? 38 : 12} y="41">{sub}</text>
    </g>
  )
}
```

Nodes are initially placed on a grid so edges stay clean. In the reference,
nodes sit at `x` of 20, 206, 386, 602 and 818, all with `y = 54`, and the two
supporting services drop to `y = 140`. Size each box to its longest label:
a 132 wide box overflows on labels like `6 blocks, 6 accounts` or
`banner9.icesi.edu.co`, so measure the text and widen the box and its group
rather than letting labels bleed into the next node.

## Edges

Edges are cubic curves with an arrow marker, so a line leaving a box arrives
pointing at the next one. Use a dashed edge (`d-edge-container`) for a secondary
relationship such as optional storage, and a solid edge for the main flow.

```jsx
function Edge({ x1, y1, x2, y2, dashed = false }) {
  const mid = (x1 + x2) / 2
  return (
    <path className={dashed ? 'd-edge-container' : 'd-edge'}
      d={`M ${x1} ${y1} C ${mid} ${y1}, ${mid} ${y2}, ${x2} ${y2}`}
      markerEnd="url(#arrow)" />
  )
}
```

Define the marker once in `<defs>`:

```jsx
<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5"
  markerWidth="6" markerHeight="6" orient="auto">
  <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--line-strong)" />
</marker>
```

## Emphasis

Exactly one node is accented: the one the reader most needs to identify, usually
the delivery point or the actor that starts the flow. It takes `.accent`, which
fills `--orange-soft` and borders `--orange-line`. More than one accent and the
diagram stops communicating priority.

## Telling the truth in the diagram

Two short notes under the diagram carry context that would clutter a node, for
example the public hostname and a one-line tradeoff. Keep them to one line each.
If a component is not real yet, either label it as planned or leave it out.
A diagram that shows infrastructure that does not exist is worse than no
diagram, because people plan against it.
