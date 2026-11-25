import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { BarChart, DistributionBar } from '../components/Charts'
import type { Analytics, Task } from '../types'
import { PRIORITY_LABEL, STATUS_LABEL } from '../types'

const STATUS_COLORS = { todo: '#94a3b8', in_progress: '#3b82f6', done: '#10b981' }
const PRIORITY_COLORS = { low: '#a3e635', medium: '#facc15', high: '#fb923c', critical: '#ef4444' }

export default function DashboardPage() {
  const { user } = useAuth()
  const canSeeAll = user?.role !== 'user'
  const [allUsers, setAllUsers] = useState(false)
  const [stats, setStats] = useState<Analytics | null>(null)
  const [upcoming, setUpcoming] = useState<Task[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([
      api.analytics(allUsers),
      api.listTasks({ sort: 'due_date', order: 'asc', size: 5, status: 'todo', all_users: allUsers }),
    ])
      .then(([a, t]) => {
        setStats(a)
        setUpcoming(t.items.filter((x) => x.due_date))
        setError(null)
      })
      .catch((e: Error) => setError(e.message))
  }, [allUsers])

  if (error) return <div className="alert">{error}</div>
  if (!stats) return <div className="muted">Loading dashboard…</div>

  const today = new Date().toISOString().slice(0, 10)
  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Dashboard</h1>
          <p className="muted">
            {allUsers ? 'Team-wide overview' : `Hello ${user?.full_name.split(' ')[0]}, here's your work at a glance.`}
          </p>
        </div>
        {canSeeAll && (
          <label className="toggle">
            <input type="checkbox" checked={allUsers} onChange={(e) => setAllUsers(e.target.checked)} />
            All users
          </label>
        )}
      </div>

      <div className="stats">
        <Stat label="Total tasks" value={stats.total} />
        <Stat label="Completion rate" value={`${stats.completion_rate}%`} tone="good" />
        <Stat label="Due this week" value={stats.due_this_week} />
        <Stat label="Overdue" value={stats.overdue} tone={stats.overdue ? 'bad' : undefined} />
      </div>

      <div className="grid-2">
        <section className="card">
          <h3>Completed — last 7 days</h3>
          <BarChart
            data={stats.completed_last_7_days.map((d) => ({
              label: new Date(d.date + 'T00:00:00').toLocaleDateString(undefined, { weekday: 'short' }),
              value: d.count,
            }))}
          />
        </section>
        <section className="card">
          <h3>By status</h3>
          <DistributionBar
            data={(Object.keys(STATUS_LABEL) as (keyof typeof STATUS_LABEL)[]).map((k) => ({
              label: STATUS_LABEL[k],
              value: stats.by_status[k],
              color: STATUS_COLORS[k],
            }))}
          />
          <h3 className="mt">By priority</h3>
          <DistributionBar
            data={(Object.keys(PRIORITY_LABEL) as (keyof typeof PRIORITY_LABEL)[]).map((k) => ({
              label: PRIORITY_LABEL[k],
              value: stats.by_priority[k],
              color: PRIORITY_COLORS[k],
            }))}
          />
        </section>
      </div>

      <section className="card">
        <div className="row-between">
          <h3>Upcoming deadlines</h3>
          <Link to="/tasks">View all →</Link>
        </div>
        {upcoming.length === 0 ? (
          <p className="muted">Nothing scheduled. 🎉</p>
        ) : (
          <ul className="upcoming">
            {upcoming.map((t) => (
              <li key={t.id}>
                <span className={`pill p-${t.priority}`}>{PRIORITY_LABEL[t.priority]}</span>
                <span className="grow">{t.title}</span>
                <span className={t.due_date! < today ? 'overdue' : 'muted'}>{t.due_date}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}

function Stat({ label, value, tone }: { label: string; value: number | string; tone?: 'good' | 'bad' }) {
  return (
    <div className={`card stat ${tone ?? ''}`}>
      <span className="muted small">{label}</span>
      <strong>{value}</strong>
    </div>
  )
}
