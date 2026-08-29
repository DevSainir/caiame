// The backend sets a readable `has_session` cookie next to the HttpOnly refresh token.
// It carries no authority — it only answers "is there a session to restore", which the page
// cannot ask about the refresh cookie itself, because HttpOnly is the point of that cookie.
const HINT = 'has_session'

export function hasSessionHint() {
  return document.cookie.split('; ').some((entry) => entry.startsWith(`${HINT}=`))
}
