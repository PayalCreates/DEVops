import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import App from '../App'
import { tokenStore } from '../api/client'
import { AuthProvider } from '../auth/AuthContext'

const user = {
  id: 1,
  email: 'alice@example.com',
  full_name: 'Alice Dev',
  role: 'user',
  is_active: true,
  created_at: '2026-11-25T00:00:00Z',
}
const task = {
  id: 7,
  title: 'Write runbook',
  description: 'for db outage',
  status: 'todo',
  priority: 'high',
  due_date: '2020-01-01',
  owner_id: 1,
  created_at: '2026-11-25T00:00:00Z',
  updated_at: '2026-11-25T00:00:00Z',
  completed_at: null,
}
const analytics = {
  total: 1,
  by_status: { todo: 1, in_progress: 0, done: 0 },
  by_priority: { low: 0, medium: 0, high: 1, critical: 0 },
  overdue: 1,
  due_this_week: 0,
  completion_rate: 0,
  completed_last_7_days: Array.from({ length: 7 }, (_, i) => ({ date: `2026-11-${19 + i}`, count: i % 2 })),
}

/** Route-aware fetch mock: returns JSON per URL prefix and records calls. */
function mockApi(overrides: Record<string, unknown> = {}) {
  const routes: Record<string, unknown> = {
    '/api/v1/auth/login': { access_token: 'tok', token_type: 'bearer', expires_in: 3600, user },
    '/api/v1/auth/me': user,
    '/api/v1/version': { version: '1.0.0', color: 'green', environment: 'test', status: 'ok' },
    '/api/v1/analytics/summary': analytics,
    '/api/v1/tasks': { items: [task], total: 1, page: 1, size: 10 },
    ...overrides,
  }
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)
    const key = Object.keys(routes)
      .sort((a, b) => b.length - a.length)
      .find((k) => url.startsWith(k))
    const method = init?.method ?? 'GET'
    if (method === 'PATCH' && url.startsWith('/api/v1/tasks/')) {
      return new Response(JSON.stringify({ ...task, status: 'in_progress' }), { status: 200 })
    }
    return new Response(JSON.stringify(key ? routes[key] : {}), { status: key ? 200 : 404 })
  })
}

const renderAt = (path: string) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </MemoryRouter>,
  )

describe('pages', () => {
  it('logs in and lands on the dashboard with analytics', async () => {
    mockApi()
    renderAt('/login')
    await userEvent.type(screen.getByLabelText('Email'), 'alice@example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'Secret123')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
    expect(tokenStore.get()).toBe('tok')
    expect(await screen.findByText('Write runbook')).toBeInTheDocument()
    expect(screen.getByText('v1.0.0 · green')).toBeInTheDocument() // blue-green badge
    expect(screen.queryByRole('link', { name: 'Users' })).not.toBeInTheDocument() // RBAC: plain user
  })

  it('shows a server error message on failed login', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Incorrect email or password' }), { status: 401 }),
    )
    renderAt('/login')
    await userEvent.type(screen.getByLabelText('Email'), 'x@example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'nope')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Incorrect email or password')
  })

  it('lists tasks, flags overdue ones and advances status', async () => {
    tokenStore.set('tok')
    const f = mockApi()
    renderAt('/tasks')
    expect(await screen.findByText('Write runbook')).toBeInTheDocument()
    expect(screen.getByText('Due 2020-01-01')).toHaveClass('overdue')
    await userEvent.click(screen.getByRole('button', { name: /Advance status of Write runbook/ }))
    await waitFor(() =>
      expect(f.mock.calls.some(([u, i]) => String(u) === '/api/v1/tasks/7' && i?.method === 'PATCH')).toBe(true),
    )
  })

  it('creates a task from the modal', async () => {
    tokenStore.set('tok')
    const f = mockApi()
    renderAt('/tasks')
    await userEvent.click(await screen.findByRole('button', { name: '+ New task' }))
    const form = screen.getByRole('form', { name: 'Task form' })
    await userEvent.type(form.querySelector('input')!, 'New from test')
    await userEvent.click(screen.getByRole('button', { name: 'Save task' }))
    await waitFor(() =>
      expect(f.mock.calls.some(([u, i]) => String(u) === '/api/v1/tasks' && i?.method === 'POST')).toBe(true),
    )
  })

  it('redirects a plain user away from the admin users page', async () => {
    tokenStore.set('tok')
    mockApi()
    renderAt('/users')
    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
  })

  it('lets an admin see the users table', async () => {
    tokenStore.set('tok')
    const admin = { ...user, role: 'admin', id: 9, email: 'root@example.com' }
    mockApi({ '/api/v1/auth/me': admin, '/api/v1/users': [admin, user] })
    renderAt('/users')
    expect(await screen.findByRole('heading', { name: 'Users' })).toBeInTheDocument()
    expect(await screen.findByLabelText('Role for alice@example.com')).toBeInTheDocument()
  })
})
