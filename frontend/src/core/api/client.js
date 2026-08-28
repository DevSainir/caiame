import axios from 'axios'

/**
 * The single Axios instance for the whole app.
 *
 * withCredentials is on from the start: the refresh token travels in an HttpOnly cookie,
 * and turning this on later means debugging why the session dies on reload.
 */
const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  withCredentials: true,
})

let accessToken = null
let refreshSession = null
let onSessionLost = null
let refreshInFlight = null

/** Keep the access token in memory only — localStorage turns any XSS into a stolen session. */
export function setAccessToken(token) {
  accessToken = token
}

/** Wire the auth feature in without the client importing it, which would be a cycle. */
export function configureAuth({ refresh, sessionLost }) {
  refreshSession = refresh
  onSessionLost = sessionLost
}

/**
 * One refresh at a time.
 *
 * A page that fires three requests at once gets three 401s at once. Without this queue all
 * three would refresh in parallel, two of them presenting an already-rotated token — and
 * the backend, by its own replay rule, would kill the whole family and sign the user out.
 */
function refreshOnce() {
  refreshInFlight ??= Promise.resolve()
    .then(() => refreshSession?.())
    .finally(() => {
      refreshInFlight = null
    })
  return refreshInFlight
}

client.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`
  return config
})

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error.response?.status ?? 0
    const request = error.config ?? {}
    const isAuthCall = String(request.url ?? '').startsWith('/auth/')

    // Retried exactly once. A second 401 means the refresh itself failed, and looping on it
    // would hammer the endpoint that just told us the session is gone.
    if (status === 401 && !request.retried && !isAuthCall && refreshSession) {
      request.retried = true
      const renewed = await refreshOnce()
      if (renewed) return client(request)
      onSessionLost?.()
    }

    return Promise.reject({
      status,
      code: error.response?.data?.detail ?? error.code ?? 'unknown_error',
      original: error,
    })
  },
)

export default client
