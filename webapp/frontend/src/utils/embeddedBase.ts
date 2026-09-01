function normalise(pathname: string): string {
  return pathname.replace(/\/+$/, '') || '/'
}

export function embeddedBasePath(pathname: string = window.location.pathname): string {
  const trimmed = normalise(pathname)
  const parts = trimmed.split('/').filter(Boolean)

  // DSS backend iframe paths look like:
  //   /web-apps-backends/PROJECT/WEBAPP_ID
  // Optional SPA routes are appended after that root. Keep only the backend root.
  if (parts[0] === 'web-apps-backends' && parts.length >= 3) {
    return `/${parts.slice(0, 3).join('/')}`
  }

  return trimmed
}
