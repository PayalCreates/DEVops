export type Role = 'admin' | 'manager' | 'user'
export type TaskStatus = 'todo' | 'in_progress' | 'done'
export type TaskPriority = 'low' | 'medium' | 'high' | 'critical'

export interface User {
  id: number
  email: string
  full_name: string
  role: Role
  is_active: boolean
  created_at: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: User
}

export interface Task {
  id: number
  title: string
  description: string | null
  status: TaskStatus
  priority: TaskPriority
  due_date: string | null
  owner_id: number
  created_at: string
  updated_at: string
  completed_at: string | null
}

export interface TaskPage {
  items: Task[]
  total: number
  page: number
  size: number
}

export interface TaskInput {
  title: string
  description?: string | null
  status?: TaskStatus
  priority?: TaskPriority
  due_date?: string | null
}

export interface Analytics {
  total: number
  by_status: Record<TaskStatus, number>
  by_priority: Record<TaskPriority, number>
  overdue: number
  due_this_week: number
  completion_rate: number
  completed_last_7_days: { date: string; count: number }[]
}

export const STATUS_LABEL: Record<TaskStatus, string> = {
  todo: 'To do',
  in_progress: 'In progress',
  done: 'Done',
}

export const PRIORITY_LABEL: Record<TaskPriority, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
  critical: 'Critical',
}
