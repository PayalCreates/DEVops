import { useEffect, useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'

export default function Layout() {
  const { user, logout } = useAuth()
  const [build, setBuild] = useState<{ version: string; color: string } | null>(null)

  useEffect(() => {
    api.version().then(setBuild).catch(() => setBuild(null))
  }, [])

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="logo" aria-hidden>
            ✓
          </span>
          <span>DevSecOps360</span>
        </div>
        <nav>
          <NavLink to="/" end>
            Dashboard
          </NavLink>
          <NavLink to="/tasks">Tasks</NavLink>
          {user && user.role !== 'user' && <NavLink to="/users">Users</NavLink>}
        </nav>
        <div className="sidebar-foot">
          {build && (
            <span className={`deploy-badge ${build.color}`} title="Serving deployment">
              v{build.version} · {build.color}
            </span>
          )}
        </div>
      </aside>
      <div className="main">
        <header className="topbar">
          <div />
          <div className="user-chip">
            <div>
              <strong>{user?.full_name}</strong>
              <span className={`role role-${user?.role}`}>{user?.role}</span>
            </div>
            <button className="btn ghost" onClick={logout}>
              Sign out
            </button>
          </div>
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
