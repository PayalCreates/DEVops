import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { TaskQuery } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import TaskForm from '../components/TaskForm'
import type { Task, TaskInput, TaskPage, TaskStatus } from '../types'
import { PRIORITY_LABEL, STATUS_LABEL } from '../types'

const NEXT: Record<TaskStatus, TaskStatus> = { todo: 'in_progress', in_progress: 'done', done: 'todo' }

export default function TasksPage() {
  const { user } = useAuth()
  const [query, setQuery] = useState<TaskQuery>({ sort: 'created_at', order: 'desc', page: 1, size: 10 })
  const [search, setSearch] = useState('')
  const [data, setData] = useState<TaskPage | null>(null)
  const [editing, setEditing] = useState<Task | null | undefined>(undefined) // undefined = closed
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    api
      .listTasks(query)
      .then((d) => {
        setData(d)
        setError(null)
      })
      .catch((e: Error) => setError(e.message))
  }, [query])

  useEffect(load, [load])

  // Debounce search input
  useEffect(() => {
    const id = setTimeout(() => setQuery((q) => ({ ...q, q: search || undefined, page: 1 })), 300)
    return () => clearTimeout(id)
  }, [search])

  const save = async (input: TaskInput) => {
    if (editing) await api.updateTask(editing.id, input)
    else await api.createTask(input)
    setEditing(undefined)
    load()
  }

  const advance = async (t: Task) => {
    await api.updateTask(t.id, { status: NEXT[t.status] }).catch((e: Error) => setError(e.message))
    load()
  }

  const remove = async (t: Task) => {
    if (!window.confirm(`Delete "${t.title}"?`)) return
    await api.deleteTask(t.id).catch((e: Error) => setError(e.message))
    load()
  }

  const pages = data ? Math.max(1, Math.ceil(data.total / data.size)) : 1
  const today = new Date().toISOString().slice(0, 10)
  const set = (patch: TaskQuery) => setQuery((q) => ({ ...q, ...patch, page: 1 }))

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Tasks</h1>
          <p className="muted">{data ? `${data.total} task${data.total === 1 ? '' : 's'}` : '…'}</p>
        </div>
        <button className="btn primary" onClick={() => setEditing(null)}>
          + New task
        </button>
      </div>

      <div className="card filters">
        <input
          placeholder="Search title or description…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Search tasks"
        />
        <select aria-label="Filter by status" onChange={(e) => set({ status: e.target.value || undefined })}>
          <option value="">All statuses</option>
          {Object.entries(STATUS_LABEL).map(([v, l]) => (
            <option key={v} value={v}>
              {l}
            </option>
          ))}
        </select>
        <select aria-label="Filter by priority" onChange={(e) => set({ priority: e.target.value || undefined })}>
          <option value="">All priorities</option>
          {Object.entries(PRIORITY_LABEL).map(([v, l]) => (
            <option key={v} value={v}>
              {l}
            </option>
          ))}
        </select>
        <select
          aria-label="Sort"
          value={`${query.sort}:${query.order}`}
          onChange={(e) => {
            const [sort, order] = e.target.value.split(':')
            set({ sort, order: order as 'asc' | 'desc' })
          }}
        >
          <option value="created_at:desc">Newest</option>
          <option value="due_date:asc">Due date</option>
          <option value="priority:desc">Priority</option>
          <option value="title:asc">Title A–Z</option>
        </select>
        {user?.role !== 'user' && (
          <label className="toggle">
            <input type="checkbox" onChange={(e) => set({ all_users: e.target.checked })} /> All users
          </label>
        )}
      </div>

      {error && (
        <div className="alert" role="alert">
          {error}
        </div>
      )}

      {editing !== undefined && (
        <div className="modal-backdrop" onClick={() => setEditing(undefined)}>
          <div className="card modal" onClick={(e) => e.stopPropagation()}>
            <TaskForm initial={editing} onSubmit={save} onCancel={() => setEditing(undefined)} />
          </div>
        </div>
      )}

      <div className="task-list">
        {data?.items.length === 0 && <div className="card muted center">No tasks match. Create one!</div>}
        {data?.items.map((t) => (
          <article key={t.id} className={`card task ${t.status}`}>
            <button
              className={`status-btn s-${t.status}`}
              onClick={() => advance(t)}
              title={`Move to ${STATUS_LABEL[NEXT[t.status]]}`}
              aria-label={`Advance status of ${t.title}`}
            >
              {t.status === 'done' ? '✓' : t.status === 'in_progress' ? '◐' : '○'}
            </button>
            <div className="grow">
              <div className="task-title">{t.title}</div>
              {t.description && <div className="muted small clamp">{t.description}</div>}
              <div className="meta">
                <span className={`pill p-${t.priority}`}>{PRIORITY_LABEL[t.priority]}</span>
                <span className="pill">{STATUS_LABEL[t.status]}</span>
                {t.due_date && (
                  <span className={t.status !== 'done' && t.due_date < today ? 'overdue small' : 'muted small'}>
                    Due {t.due_date}
                  </span>
                )}
              </div>
            </div>
            <div className="actions">
              <button className="btn ghost sm" onClick={() => setEditing(t)}>
                Edit
              </button>
              <button className="btn danger sm" onClick={() => remove(t)}>
                Delete
              </button>
            </div>
          </article>
        ))}
      </div>

      {pages > 1 && (
        <div className="pager">
          <button
            className="btn ghost sm"
            disabled={query.page === 1}
            onClick={() => setQuery((q) => ({ ...q, page: (q.page ?? 1) - 1 }))}
          >
            ← Prev
          </button>
          <span className="muted small">
            Page {query.page} of {pages}
          </span>
          <button
            className="btn ghost sm"
            disabled={query.page === pages}
            onClick={() => setQuery((q) => ({ ...q, page: (q.page ?? 1) + 1 }))}
          >
            Next →
          </button>
        </div>
      )}
    </div>
  )
}
