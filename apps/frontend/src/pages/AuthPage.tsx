import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { validatePassword } from '../lib/validation'

export default function AuthPage({ mode }: { mode: 'login' | 'register' }) {
  const { user, login, register } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)
  const isLogin = mode === 'login'

  if (user) return <Navigate to="/" replace />

  async function submit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setFieldErrors({})
    if (!isLogin) {
      const pwErr = validatePassword(password)
      if (pwErr) return setFieldErrors({ password: pwErr })
    }
    setBusy(true)
    try {
      if (isLogin) await login(email, password)
      else await register(email, password, fullName)
      const from = (location.state as { from?: string } | null)?.from ?? '/'
      navigate(from, { replace: true })
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
        setFieldErrors(err.fieldErrors)
      } else setError('Unexpected error')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-hero">
        <h1>DevSecOps360</h1>
        <p>Secure, observable task management — shipped through a fully automated pipeline.</p>
        <ul>
          <li>JWT authentication &amp; role-based access</li>
          <li>Blue-green deployments with instant rollback</li>
          <li>Prometheus · Grafana · Loki observability</li>
        </ul>
      </div>
      <form className="card auth-card" onSubmit={submit} noValidate>
        <h2>{isLogin ? 'Welcome back' : 'Create your account'}</h2>
        {error && (
          <div className="alert" role="alert">
            {error}
          </div>
        )}
        {!isLogin && (
          <label>
            Full name
            <input
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
              minLength={2}
              autoComplete="name"
            />
            {fieldErrors.full_name && <small className="err">{fieldErrors.full_name}</small>}
          </label>
        )}
        <label>
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
          {fieldErrors.email && <small className="err">{fieldErrors.email}</small>}
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete={isLogin ? 'current-password' : 'new-password'}
          />
          {fieldErrors.password && <small className="err">{fieldErrors.password}</small>}
        </label>
        <button className="btn primary block" disabled={busy}>
          {busy ? 'Please wait…' : isLogin ? 'Sign in' : 'Create account'}
        </button>
        <p className="muted small">
          {isLogin ? (
            <>
              No account? <Link to="/register">Register</Link>
            </>
          ) : (
            <>
              Already registered? <Link to="/login">Sign in</Link>
            </>
          )}
        </p>
      </form>
    </div>
  )
}
