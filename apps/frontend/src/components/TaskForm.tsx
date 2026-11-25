import { useState } from 'react'
import type { FormEvent } from 'react'
import type { Task, TaskInput, TaskPriority, TaskStatus } from '../types'
import { PRIORITY_LABEL, STATUS_LABEL } from '../types'

interface Props {
  initial?: Task | null
  onSubmit: (input: TaskInput) => Promise<void>
  onCancel: () => void
}

export default function TaskForm({ initial, onSubmit, onCancel }: Props) {
  const [title, setTitle] = useState(initial?.title ?? '')
  const [description, setDescription] = useState(initial?.description ?? '')
  const [status, setStatus] = useState<TaskStatus>(initial?.status ?? 'todo')
  const [priority, setPriority] = useState<TaskPriority>(initial?.priority ?? 'medium')
  const [dueDate, setDueDate] = useState(initial?.due_date ?? '')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!title.trim()) return setError('Title is required')
    if (title.length > 200) return setError('Title must be at most 200 characters')
    setBusy(true)
    setError(null)
    try {
      await onSubmit({
        title: title.trim(),
        description: description.trim() || null,
        status,
        priority,
        due_date: dueDate || null,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="task-form" onSubmit={submit} noValidate aria-label="Task form">
      <h3>{initial ? 'Edit task' : 'New task'}</h3>
      {error && (
        <div className="alert" role="alert">
          {error}
        </div>
      )}
      <label>
        Title
        <input value={title} onChange={(e) => setTitle(e.target.value)} maxLength={200} autoFocus />
      </label>
      <label>
        Description
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
          maxLength={5000}
        />
      </label>
      <div className="grid-3">
        <label>
          Status
          <select value={status} onChange={(e) => setStatus(e.target.value as TaskStatus)}>
            {Object.entries(STATUS_LABEL).map(([v, l]) => (
              <option key={v} value={v}>
                {l}
              </option>
            ))}
          </select>
        </label>
        <label>
          Priority
          <select value={priority} onChange={(e) => setPriority(e.target.value as TaskPriority)}>
            {Object.entries(PRIORITY_LABEL).map(([v, l]) => (
              <option key={v} value={v}>
                {l}
              </option>
            ))}
          </select>
        </label>
        <label>
          Due date
          <input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
        </label>
      </div>
      <div className="row-end">
        <button type="button" className="btn ghost" onClick={onCancel}>
          Cancel
        </button>
        <button className="btn primary" disabled={busy}>
          {busy ? 'Saving…' : 'Save task'}
        </button>
      </div>
    </form>
  )
}
