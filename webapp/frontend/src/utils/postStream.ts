import { apiUrl } from '@/utils/api'

/**
 * POST a JSON body and read the server-sent events it answers with. The browser's EventSource is
 * GET-only, so a stream started by a POST is read from the fetch body. Each `data:` line carries one
 * JSON event; a malformed frame is skipped rather than ending the stream.
 */
export async function postStream(path: string, body: unknown, onEvent: (e: Record<string, unknown>) => void,
  signal?: AbortSignal): Promise<void> {
  const res = await fetch(apiUrl(path), {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal,
  })
  if (!res.ok || !res.body) {
    const detail = await res.json().catch(() => null)
    throw new Error(detail?.detail ?? `HTTP ${res.status}`)
  }
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    let cut: number
    while ((cut = buffer.indexOf('\n\n')) >= 0) {
      const frame = buffer.slice(0, cut)
      buffer = buffer.slice(cut + 2)
      const data = frame.split('\n').filter((l) => l.startsWith('data:')).map((l) => l.slice(5).trim()).join('')
      if (!data) continue
      try {
        onEvent(JSON.parse(data))
      } catch {
        console.warn('[assistant] dropped a malformed frame:', data.slice(0, 200))
      }
    }
  }
}
