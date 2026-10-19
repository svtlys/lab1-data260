import React from 'react'

// One labelled form control with inline validation feedback.
// <FormField label="Title" name="title" value={...} onChange={...} error={errors.title} />
// Use as="textarea" or as="select" (pass <option>s as children) for other controls.
export default function FormField({
  label,
  name,
  value,
  onChange,
  error,
  help,
  required = false,
  as = 'input',
  type = 'text',
  rows = 3,
  children,
  ...rest
}) {
  const id = `field-${name}`
  const className = `${as === 'select' ? 'form-select' : 'form-control'}${error ? ' is-invalid' : ''}`
  const shared = {
    id,
    name,
    value: value ?? '',
    onChange,
    className,
    'aria-invalid': error ? 'true' : undefined,
    ...rest,
  }

  let control
  if (as === 'textarea') {
    control = <textarea rows={rows} {...shared} />
  } else if (as === 'select') {
    control = <select {...shared}>{children}</select>
  } else {
    control = <input type={type} {...shared} />
  }

  return (
    <div className="mb-3">
      <label htmlFor={id} className="form-label">
        {label}
        {required && <span className="text-danger"> *</span>}
      </label>
      {control}
      {error && <div className="invalid-feedback">{error}</div>}
      {help && !error && <div className="form-text">{help}</div>}
    </div>
  )
}
