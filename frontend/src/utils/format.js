// Today's date as YYYY-MM-DD in the user's local timezone.
// (toISOString() is UTC, which gives "tomorrow" for Pacific-time evenings.)
export function todayISO() {
  const d = new Date()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${month}-${day}`
}

// Accepts "YYYY-MM-DD" or a full ISO datetime. Date-only strings are parsed as
// local midnight so they don't slip back a day in US timezones.
export function formatDate(value) {
  if (!value) return '—'
  const dateOnly = /^\d{4}-\d{2}-\d{2}$/.test(value)
  const date = new Date(dateOnly ? `${value}T00:00:00` : value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}

export function formatSalary(value) {
  if (value === null || value === undefined || value === '') return 'Not listed'
  const amount = Number(value)
  if (Number.isNaN(amount)) return String(value)
  return amount.toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  })
}
