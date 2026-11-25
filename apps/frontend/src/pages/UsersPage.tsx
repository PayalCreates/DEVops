import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { Role, User } from '../types'

export default function UsersPage() {
  const { user: me } = useAuth()
  const [users, setUsers] = useState<User[]>([])
  const [error, setError] = useState<string | null>(null)
  const isAdmin = me?.role === 'admin'

  const load = () =>
    api
      .listUsers()
      .then(setUsers)
      .catch((e: Error) => setError(e.message))
  useEffect(() => {
    load()
  }, [])

  const act = (p: Promise<unknown>) => p.then(load).catch((e: Error) => setError(e.message))

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Users</h1>
          <p className="muted">{isAdmin ? 'Manage roles and access.' : 'Read-only view (manager).'}</p>
        </div>
      </div>
      {error && <div className="alert">{error}</div>}
      <div className="card table-wrap">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>Status</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.full_name}</td>
                <td className="muted">{u.email}</td>
                <td>
                  {isAdmin && u.id !== me?.id ? (
                    <select
                      value={u.role}
                      aria-label={`Role for ${u.email}`}
                      onChange={(e) => act(api.setRole(u.id, e.target.value as Role))}
                    >
                      <option value="user">user</option>
                      <option value="manager">manager</option>
                      <option value="admin">admin</option>
                    </select>
                  ) : (
                    <span className={`role role-${u.role}`}>{u.role}</span>
                  )}
                </td>
                <td>{u.is_active ? <span className="ok">active</span> : <span className="overdue">disabled</span>}</td>
                <td>
                  {isAdmin && u.id !== me?.id && (
                    <button className="btn ghost sm" onClick={() => act(api.setActive(u.id, !u.is_active))}>
                      {u.is_active ? 'Disable' : 'Enable'}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
