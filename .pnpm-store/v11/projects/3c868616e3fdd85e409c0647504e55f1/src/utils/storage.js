const HISTORY_KEY = 'anti_fraud_recent_history'

export function loadHistory() {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]')
  } catch {
    return []
  }
}

export function saveHistoryItem(item) {
  const next = [item, ...loadHistory().filter((record) => record.id !== item.id)].slice(0, 10)
  localStorage.setItem(HISTORY_KEY, JSON.stringify(next))
  return next
}

export function clearHistory() {
  localStorage.removeItem(HISTORY_KEY)
  return []
}
