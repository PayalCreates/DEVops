/** Dependency-free SVG charts (fewer packages = smaller supply-chain attack surface). */

export interface Datum {
  label: string
  value: number
  color?: string
}

export function BarChart({ data, height = 150 }: { data: Datum[]; height?: number }) {
  const max = Math.max(1, ...data.map((d) => d.value))
  const barW = 100 / Math.max(1, data.length)
  return (
    <div className="barchart">
      <svg
        className="chart"
        style={{ height }}
        viewBox="0 0 100 50"
        preserveAspectRatio="none"
        role="img"
        aria-label={data.map((d) => `${d.label}: ${d.value}`).join(', ')}
      >
        <line x1="0" y1="50" x2="100" y2="50" stroke="var(--line)" strokeWidth="0.6" />
        {data.map((d, i) => {
          const h = (d.value / max) * 46
          return (
            <rect
              key={d.label}
              data-testid="bar"
              x={i * barW + barW * 0.22}
              y={50 - h}
              width={barW * 0.56}
              height={h}
              fill={d.color ?? 'var(--accent)'}
            >
              <title>{`${d.label}: ${d.value}`}</title>
            </rect>
          )
        })}
      </svg>
      <div className="chart-axis">
        {data.map((d) => (
          <span key={d.label}>
            <strong>{d.value}</strong>
            {d.label}
          </span>
        ))}
      </div>
    </div>
  )
}

export function DistributionBar({ data }: { data: Datum[] }) {
  const total = data.reduce((s, d) => s + d.value, 0)
  return (
    <div>
      <div className="dist" role="img" aria-label={data.map((d) => `${d.label} ${d.value}`).join(', ')}>
        {total === 0 ? (
          <div className="dist-seg empty" style={{ width: '100%' }} />
        ) : (
          data.map((d) =>
            d.value ? (
              <div
                key={d.label}
                className="dist-seg"
                style={{ width: `${(d.value / total) * 100}%`, background: d.color }}
                title={`${d.label}: ${d.value}`}
              />
            ) : null,
          )
        )}
      </div>
      <ul className="legend">
        {data.map((d) => (
          <li key={d.label}>
            <span className="dot" style={{ background: d.color }} />
            {d.label} <strong>{d.value}</strong>
          </li>
        ))}
      </ul>
    </div>
  )
}
