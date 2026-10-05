import React, { useEffect, useState } from 'react'
import * as companyService from '../services/companyService'
import { extractErrorMessage } from '../services/api'
import { cleanPayload, hasErrors, validateCompanyProfile } from '../utils/validation'
import FormField from '../components/FormField.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ErrorAlert from '../components/ErrorAlert.jsx'

// The editable fields. Only these are sent on save, never ids or timestamps.
const FIELDS = [
  'company_name',
  'location',
  'description',
  'contact_email',
  'contact_phone',
  'profile_picture_url',
]

const emptyForm = Object.fromEntries(FIELDS.map((field) => [field, '']))

function toForm(data) {
  const form = { ...emptyForm }
  FIELDS.forEach((field) => {
    form[field] = (data && data[field]) ?? ''
  })
  return form
}

export default function CompanyProfile() {
  const [form, setForm] = useState(emptyForm)
  const [errors, setErrors] = useState({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [loadError, setLoadError] = useState('')
  const [saveError, setSaveError] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    let cancelled = false
    companyService
      .getMyCompanyProfile()
      .then((data) => {
        if (!cancelled) setForm(toForm(data))
      })
      .catch((err) => {
        if (!cancelled) setLoadError(extractErrorMessage(err, 'Could not load your company profile.'))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  function handleChange(e) {
    setForm({ ...form, [e.target.name]: e.target.value })
    setSaved(false)
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSaveError('')
    setSaved(false)

    const found = validateCompanyProfile(form)
    setErrors(found)
    if (hasErrors(found)) return

    setSaving(true)
    try {
      const updated = await companyService.updateMyCompanyProfile(cleanPayload(form))
      setForm(toForm(updated))
      setSaved(true)
    } catch (err) {
      setSaveError(extractErrorMessage(err, 'Could not save your company profile.'))
    } finally {
      setSaving(false)
    }
  }

  const pictureUrl = String(form.profile_picture_url || '').trim()
  const showPicture = /^https?:\/\/\S+$/i.test(pictureUrl)

  return (
    <div className="page-container" style={{ maxWidth: 720 }}>
      <h2 className="mb-4">Company profile</h2>

      {loading && <LoadingSpinner label="Loading your company profile..." />}
      <ErrorAlert message={loadError} />

      {/* If loading failed, hide the form so an empty form can't overwrite real data. */}
      {!loading && !loadError && (
        <div className="card shadow-sm">
          <div className="card-body p-4">
            {saved && <div className="alert alert-success">Profile saved.</div>}
            <ErrorAlert message={saveError} />

            <form onSubmit={handleSubmit} noValidate>
              {showPicture && (
                <div className="mb-3">
                  {/* key forces a fresh <img> when the URL changes, so a bad URL doesn't stay hidden */}
                  <img
                    key={pictureUrl}
                    src={pictureUrl}
                    alt="Company logo preview"
                    width="72"
                    height="72"
                    className="rounded-circle border"
                    style={{ objectFit: 'cover' }}
                    onError={(e) => {
                      e.currentTarget.style.display = 'none'
                    }}
                  />
                </div>
              )}

              <div className="row">
                <div className="col-md-6">
                  <FormField
                    label="Company name"
                    name="company_name"
                    value={form.company_name}
                    onChange={handleChange}
                    error={errors.company_name}
                    required
                    maxLength={150}
                  />
                </div>
                <div className="col-md-6">
                  <FormField
                    label="Location"
                    name="location"
                    value={form.location}
                    onChange={handleChange}
                    error={errors.location}
                    required
                    maxLength={150}
                  />
                </div>
              </div>

              <FormField
                label="Description"
                name="description"
                as="textarea"
                rows={4}
                value={form.description}
                onChange={handleChange}
                error={errors.description}
                help="What your company does and who you hire."
                maxLength={2000}
              />

              <div className="row">
                <div className="col-md-6">
                  <FormField
                    label="Contact email"
                    name="contact_email"
                    type="email"
                    value={form.contact_email}
                    onChange={handleChange}
                    error={errors.contact_email}
                  />
                </div>
                <div className="col-md-6">
                  <FormField
                    label="Contact phone"
                    name="contact_phone"
                    type="tel"
                    value={form.contact_phone}
                    onChange={handleChange}
                    error={errors.contact_phone}
                    maxLength={30}
                  />
                </div>
              </div>

              <FormField
                label="Profile picture URL"
                name="profile_picture_url"
                value={form.profile_picture_url}
                onChange={handleChange}
                error={errors.profile_picture_url}
                help="A link to your logo (https://...)."
                maxLength={500}
              />

              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? 'Saving...' : 'Save profile'}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
