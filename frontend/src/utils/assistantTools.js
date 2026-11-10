// helpers that read the tool calls the assistant API returns

// tool-call arguments can arrive as an object or as a JSON string
export function parseArguments(argumentsValue) {
  if (argumentsValue && typeof argumentsValue === 'object') return argumentsValue
  try {
    return JSON.parse(argumentsValue)
  } catch {
    return {}
  }
}

function outcomeText(call) {
  const result = typeof call.result === 'string' ? call.result : JSON.stringify(call.result ?? '')
  return `${result} ${call.error ?? ''}`
}

function savedItemFrom(call) {
  const args = parseArguments(call.arguments)
  const itemType = args.item_type || args.type || (args.job_id ? 'job' : args.event_id ? 'event' : '')
  const itemId = args.item_id ?? args.job_id ?? args.event_id ?? args.id ?? ''
  return { itemType, itemId }
}

// Did the backend's confirmation gate refuse a save in this answer? If so, return what it wanted to save.
// Tolerant on purpose: the result may be a string or an object, and the model may name the arguments differently.
export function findDeclinedSave(toolCalls) {
  for (const call of toolCalls || []) {
    if (call.tool_name !== 'save_job_or_event') continue
    if (!/cancelled|confirmation required/i.test(outcomeText(call))) continue
    return savedItemFrom(call)
  }
  return null
}

// Which items did this answer actually save? (a save call that was not cancelled and had no error)
export function extractSavedItems(toolCalls) {
  const saved = []
  for (const call of toolCalls || []) {
    if (call.tool_name !== 'save_job_or_event') continue
    if (/cancelled|confirmation required|error/i.test(outcomeText(call))) continue
    const { itemType, itemId } = savedItemFrom(call)
    if (itemType && itemId) saved.push({ item_type: itemType, item_id: Number(itemId) })
  }
  return saved
}
