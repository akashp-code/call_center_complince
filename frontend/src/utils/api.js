const API_BASE =
  import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000"
const API_KEY = import.meta.env.VITE_API_KEY || 'sk_intel_987654321'

export async function analyzeCall({ audioBase64, language, audioFormat }) {
  const res = await fetch(`${API_BASE}/api/v1/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': API_KEY,
    },
    body: JSON.stringify({ audioBase64, language, audioFormat }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result.split(',')[1])
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

export function getAudioFormat(file) {
  const name = file.name.toLowerCase()
  if (name.endsWith('.ogg')) return 'ogg'
  if (name.endsWith('.wav')) return 'wav'
  if (name.endsWith('.m4a')) return 'm4a'
  if (name.endsWith('.webm')) return 'webm'
  if (name.endsWith('.flac')) return 'flac'
  return 'mp3'
}
