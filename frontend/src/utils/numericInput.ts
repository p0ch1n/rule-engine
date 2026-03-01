/**
 * Utilities for stable numeric <input type="number"> handling.
 *
 * Root cause of "jumping numbers":
 *   parseFloat("0.1") + step(0.01) = 0.10999999999999999 (IEEE 754)
 *
 * Fix: after every onChange round the value to the number of decimal
 * places implied by the step attribute before storing it in state.
 */

/**
 * Count the decimal places that a given step value implies.
 * e.g. step=0.01 → 2,  step=0.1 → 1,  step=1 → 0
 */
function decimalsForStep(step: number): number {
  const s = step.toString()
  const dot = s.indexOf('.')
  return dot === -1 ? 0 : s.length - dot - 1
}

/**
 * Parse a raw string from an <input type="number"> and round the result
 * to the precision implied by `step`.
 *
 * Returns `null` when the input is empty or not a finite number so callers
 * can skip the state update and avoid clobbering a value the user is
 * still typing.
 */
export function parseNumericInput(
  raw: string,
  step: number,
  min?: number,
  max?: number
): number | null {
  const v = parseFloat(raw)
  if (!isFinite(v)) return null

  const rounded = parseFloat(v.toFixed(decimalsForStep(step)))

  if (min !== undefined && rounded < min) return null
  if (max !== undefined && rounded > max) return null

  return rounded
}

/**
 * Parse an integer from a numeric input.
 * Returns `null` when invalid or outside optional bounds.
 */
export function parseIntInput(
  raw: string,
  min?: number,
  max?: number
): number | null {
  const v = parseInt(raw, 10)
  if (!isFinite(v)) return null
  if (min !== undefined && v < min) return null
  if (max !== undefined && v > max) return null
  return v
}
