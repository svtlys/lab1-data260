import { JOB_CATEGORIES, EVENT_TYPES } from '../constants'

// Client-side validation. The backend must enforce the same rules (see
// docs/company-api-contract.md) -- this just gives users instant feedback.
// Every validator returns an object of { fieldName: 'message' }; empty means valid.

const PHONE_RE = /^[0-9+()\-.\s]{7,30}$/
const URL_RE = /^https?:\/\/\S+$/i
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/

function str(value) {
  return value === null || value === undefined ? '' : String(value).trim()
}

export function hasErrors(errors) {
  return Object.keys(errors).length > 0
}

// Trim strings and turn blanks into null. FastAPI rejects '' for numeric and
// date fields (422), and null is what an optional field should send anyway.
export function cleanPayload(values) {
  const out = {}
  Object.entries(values).forEach(([key, value]) => {
    if (typeof value === 'string') {
      const trimmed = value.trim()
      out[key] = trimmed === '' ? null : trimmed
    } else {
      out[key] = value
    }
  })
  return out
}

export function validateJob(form) {
  const errors = {}
  const title = str(form.title)
  const description = str(form.description)
  const min = str(form.salary_min)
  const max = str(form.salary_max)

  if (title.length < 2 || title.length > 150) {
    errors.title = 'Title must be 2-150 characters.'
  }
  if (!JOB_CATEGORIES.includes(form.employment_type)) {
    errors.employment_type = 'Choose a job type.'
  }
  if (!str(form.city)) {
    errors.city = 'Choose a city.'
  } else if (str(form.city).length > 100) {
    errors.city = 'City must be 100 characters or fewer.'
  }
  if (description.length < 10) {
    errors.description = 'Describe the role in at least 10 characters.'
  } else if (description.length > 5000) {
    errors.description = 'Description must be 5000 characters or fewer.'
  }
  const inRange = (v) => Number.isFinite(Number(v)) && Number(v) >= 0 && Number(v) <= 10000000
  if (min !== '' && !inRange(min)) {
    errors.salary_min = 'Enter a salary between 0 and 10,000,000.'
  }
  if (max !== '' && !inRange(max)) {
    errors.salary_max = 'Enter a salary between 0 and 10,000,000.'
  }
  if (!errors.salary_min && !errors.salary_max && min !== '' && max !== '' && Number(max) < Number(min)) {
    errors.salary_max = 'Maximum salary cannot be below the minimum.'
  }
  if (str(form.required_skills).length > 500) {
    errors.required_skills = 'Skills must be 500 characters or fewer.'
  }
  if (!DATE_RE.test(str(form.deadline))) {
    errors.deadline = 'Choose an application deadline.'
  }
  return errors
}

// Events: title, type, city, when, capacity, and optional eligibility rules.
export function validateEvent(form) {
  const errors = {}
  const title = str(form.title)
  const cap = str(form.capacity)
  const cgpa = str(form.min_cgpa)
  const lo = str(form.min_grad_year)
  const hi = str(form.max_grad_year)

  if (title.length < 2 || title.length > 150) {
    errors.title = 'Title must be 2-150 characters.'
  }
  if (!EVENT_TYPES.includes(form.event_type)) {
    errors.event_type = 'Choose an event type.'
  }
  if (!str(form.city)) {
    errors.city = 'Choose a city.'
  }
  if (!form.is_virtual && !str(form.location)) {
    errors.location = 'Enter a venue, or tick "Online event".'
  }
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(str(form.event_date))) {
    errors.event_date = 'Choose a date and time.'
  }
  if (!/^\d+$/.test(cap) || Number(cap) < 1 || Number(cap) > 10000) {
    errors.capacity = 'Capacity must be a whole number from 1 to 10,000.'
  }
  if (str(form.description).length > 5000) {
    errors.description = 'Description must be 5000 characters or fewer.'
  }
  if (cgpa !== '' && !(Number(cgpa) >= 0 && Number(cgpa) <= 4)) {
    errors.min_cgpa = 'CGPA must be between 0 and 4.'
  }
  const isYear = (v) => /^\d{4}$/.test(v) && Number(v) >= 2000 && Number(v) <= 2100
  if (lo !== '' && !isYear(lo)) errors.min_grad_year = 'Enter a 4-digit year.'
  if (hi !== '' && !isYear(hi)) errors.max_grad_year = 'Enter a 4-digit year.'
  if (!errors.min_grad_year && !errors.max_grad_year && lo !== '' && hi !== '' && Number(hi) < Number(lo)) {
    errors.max_grad_year = 'The latest year cannot be before the earliest year.'
  }
  return errors
}

export function validateCompanyProfile(form) {
  const errors = {}
  const name = str(form.company_name)
  const location = str(form.location)
  const phone = str(form.contact_phone)
  const picture = str(form.profile_picture_url)

  if (name.length < 2 || name.length > 150) {
    errors.company_name = 'Company name must be 2-150 characters.'
  }
  if (!location) {
    errors.location = 'Location is required.'
  } else if (location.length > 150) {
    errors.location = 'Location must be 150 characters or fewer.'
  }
  if (str(form.description).length > 2000) {
    errors.description = 'Description must be 2000 characters or fewer.'
  }
  if (phone && !PHONE_RE.test(phone)) {
    errors.contact_phone = 'Use 7-30 digits, spaces, +, -, ( or ).'
  }
  if (picture && (!URL_RE.test(picture) || picture.length > 500)) {
    errors.profile_picture_url = 'Must be an http(s) link of 500 characters or fewer.'
  }
  return errors
}
