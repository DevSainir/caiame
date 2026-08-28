import { beforeEach, describe, expect, it, vi } from 'vitest'
import client, { configureAuth, setAccessToken } from '@/core/api/client'

/**
 * The queue in front of the refresh call.
 *
 * A lesson page fires several requests at once. When the access token has expired they all
 * come back 401 together, and without the queue each one would refresh on its own. The
 * second and third would present an already-rotated token, the backend would read that as
 * a replay and kill the whole family — signing the user out for doing nothing wrong.
 */
describe('the axios client', () => {
  let refreshCalls
  let sessionLost

  beforeEach(() => {
    refreshCalls = 0
    sessionLost = vi.fn()
    setAccessToken('expired')

    client.defaults.adapter = async (config) => {
      if (config.headers.Authorization === 'Bearer fresh') {
        return { status: 200, data: { url: config.url }, headers: {}, config }
      }
      const error = new Error('unauthorized')
      error.config = config
      error.response = { status: 401, data: { detail: 'invalid_credentials' } }
      throw error
    }

    configureAuth({
      refresh: async () => {
        refreshCalls += 1
        await new Promise((resolve) => setTimeout(resolve, 10))
        setAccessToken('fresh')
        return 'fresh'
      },
      sessionLost,
    })
  })

  it('refreshes once for a burst of simultaneous 401s', async () => {
    const responses = await Promise.all([
      client.get('/courses'),
      client.get('/catalog/filters'),
      client.get('/profile'),
    ])

    expect(refreshCalls).toBe(1)
    expect(responses.map((response) => response.status)).toEqual([200, 200, 200])
  })

  it('retries the original request after a successful refresh', async () => {
    const response = await client.get('/courses')

    expect(response.data.url).toBe('/courses')
  })

  it('gives up after one retry instead of looping', async () => {
    configureAuth({
      refresh: async () => {
        refreshCalls += 1
        return null
      },
      sessionLost,
    })

    await expect(client.get('/courses')).rejects.toMatchObject({ status: 401 })
    expect(refreshCalls).toBe(1)
    expect(sessionLost).toHaveBeenCalledOnce()
  })

  it('does not try to refresh a failing auth call', async () => {
    await expect(client.post('/auth/login')).rejects.toMatchObject({ status: 401 })

    expect(refreshCalls).toBe(0)
  })
})
