import { JOB_CATEGORIES } from '../constants'

// Client-side validation. The backend must enforce the same rules (see
// docs/company-api-contract.md) -- this just gives users instant feedback.
// Every validator returns an object of { fieldName: 'message' }; empty means valid.

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
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
  const location = str(form.location)
  const description = str(form.description)
  const salary = str(form.salary)

  if (title.length < 2 || title.length > 150) {
    errors.title = 'Title must be 2-150 characters.'
  }
  if (!JOB_CATEGORIES.includes(form.category)) {
    errors.category = 'Choose a category.'
  }
  if (!location) {
    errors.location = 'Location is required.'
  } else if (location.length > 150) {
    errors.location = 'Location must be 150 characters or fewer.'
  }
  if (description.length < 10) {
    errors.description = 'Describe the role in at least 10 characters.'
  } else if (description.length > 5000) {
    errors.description = 'Description must be 5000 characters or fewer.'
  }
  if (salary !== '') {
    const amount = Number(salary)
    if (!Number.isFinite(amount) || amount < 0 || amount > 10000000) {
      errors.salary = 'Enter a salary between 0 and 10,000,000.'
    }
  }
  if (!DATE_RE.test(str(form.posting_date))) {
    errors.posting_date = 'Choose a posting date.'
  }
  if (!DATE_RE.test(str(form.deadline))) {
    errors.deadline = 'Choose an application deadline.'
  } else if (!errors.posting_date && str(form.deadline) < str(form.posting_date)) {
    errors.deadline = 'The deadline cannot be before the posting date.'
  }
  return errors
}

export function validateCompanyProfile(form) {
  const errors = {}
  const name = str(form.company_name)
  const location = str(form.location)
  const email = str(form.contact_email)
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
  if (email && !EMAIL_RE.test(email)) {
    errors.contact_email = 'Enter a valid email address.'
  }
  if (phone && !PHONE_RE.test(phone)) {
    errors.contact_phone = 'Use 7-30 digits, spaces, +, -, ( or ).'
  }
  if (picture && (!URL_RE.test(picture) || picture.length > 500)) {
    errors.profile_picture_url = 'Must be an http(s) link of 500 characters or fewer.'
  }
  return errors
}
