import { ApiError, api, request, setUnauthorizedHandler, tokenStore } from '../api/client'

function mockFetch(status: number, body: unknown) {
  return vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(status === 204 ? null : JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
}

describe('api client', () => {
  it('attaches the bearer token when present', async () => {
    tokenStore.set('abc')
    const f = mockFetch(200, { ok: true })
    await request('/x')
    const headers = f.mock.calls[0][1]!.headers as Headers
    expect(headers.get('Authorization')).toBe('Bearer abc')
  })

  it('maps validation errors to field errors', async () => {
    mockFetch(422, { detail: 'Validation failed', errors: [{ field: 'email', message: 'bad email' }] })
    const err = (await request('/x').catch((e) => e)) as ApiError
    expect(err).toBeInstanceOf(ApiError)
    expect(err.status).toBe(422)
    expect(err.fieldErrors).toEqual({ email: 'bad email' })
  })

  it('calls the unauthorized handler on 401 with a token', async () => {
    tokenStore.set('expired')
    const handler = vi.fn()
    setUnauthorizedHandler(handler)
    mockFetch(401, { detail: 'Invalid or missing credentials' })
    await expect(request('/x')).rejects.toThrow('Invalid or missing credentials')
    expect(handler).toHaveBeenCalledOnce()
  })

  it('reports network failures clearly', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'))
    await expect(request('/x')).rejects.toMatchObject({ status: 0 })
  })

  it('builds task query strings without empty values', async () => {
    const f = mockFetch(200, { items: [], total: 0, page: 1, size: 10 })
    await api.listTasks({ status: 'todo', q: '', all_users: false, page: 2 })
    expect(f.mock.calls[0][0]).toBe('/api/v1/tasks?status=todo&page=2')
  })

  it('handles 204 No Content', async () => {
    mockFetch(204, null)
    await expect(api.deleteTask(1)).resolves.toBeUndefined()
  })
})
