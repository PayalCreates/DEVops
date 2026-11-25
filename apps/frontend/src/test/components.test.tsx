import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import App from '../App'
import { AuthProvider } from '../auth/AuthContext'
import { BarChart, DistributionBar } from '../components/Charts'
import TaskForm from '../components/TaskForm'
import { validatePassword } from '../lib/validation'

describe('validatePassword', () => {
  it.each([
    ['short1A', 'At least 8 characters'],
    ['alllower1', 'Use upper and lower case letters and a digit'],
    ['GoodPass1', null],
  ])('%s -> %s', (pw, expected) => expect(validatePassword(pw)).toBe(expected))
})

describe('TaskForm', () => {
  it('requires a title', async () => {
    const onSubmit = vi.fn()
    render(<TaskForm onSubmit={onSubmit} onCancel={() => {}} />)
    await userEvent.click(screen.getByRole('button', { name: /save task/i }))
    expect(screen.getByRole('alert')).toHaveTextContent('Title is required')
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('submits trimmed values', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    render(<TaskForm onSubmit={onSubmit} onCancel={() => {}} />)
    await userEvent.type(screen.getByLabelText('Title'), '  Deploy green  ')
    await userEvent.selectOptions(screen.getByLabelText('Priority'), 'critical')
    await userEvent.click(screen.getByRole('button', { name: /save task/i }))
    expect(onSubmit).toHaveBeenCalledWith({
      title: 'Deploy green',
      description: null,
      status: 'todo',
      priority: 'critical',
      due_date: null,
    })
  })
})

describe('Charts', () => {
  it('renders one bar per datum with accessible label', () => {
    render(<BarChart data={[{ label: 'Mon', value: 2 }, { label: 'Tue', value: 0 }]} />)
    expect(screen.getAllByTestId('bar')).toHaveLength(2)
    expect(screen.getByRole('img')).toHaveAttribute('aria-label', 'Mon: 2, Tue: 0')
  })

  it('distribution legend shows counts', () => {
    render(<DistributionBar data={[{ label: 'Done', value: 3, color: 'green' }]} />)
    expect(screen.getByText('3')).toBeInTheDocument()
  })
})

describe('routing', () => {
  it('redirects anonymous users to the login page', async () => {
    render(
      <MemoryRouter initialEntries={['/tasks']}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </MemoryRouter>,
    )
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Welcome back' })).toBeInTheDocument())
  })
})
