/**
 * Safely extracts a human-readable message from any error shape.
 * Handles:
 *  - FastAPI string detail:   { detail: "Not found" }
 *  - Pydantic validation arr: { detail: [{type,loc,msg,input,ctx}, ...] }
 *  - Plain JS Error objects
 *  - Network / unknown errors
 */
export function extractErrorMessage(err: unknown, fallback = "An unexpected error occurred."): string {
  if (!err) return fallback

  // Axios error with response
  const axiosErr = err as { response?: { data?: { detail?: unknown }; status?: number } }
  const detail = axiosErr?.response?.data?.detail

  if (detail !== undefined && detail !== null) {
    if (typeof detail === "string") return detail

    // Pydantic v2 validation errors — array of {type,loc,msg,input,ctx}
    if (Array.isArray(detail)) {
      const messages = detail
        .map((d) => {
          if (typeof d === "string") return d
          if (typeof d === "object" && d !== null) {
            const obj = d as { msg?: string; loc?: unknown[]; message?: string }
            const location = Array.isArray(obj.loc) ? obj.loc.join(" → ") : ""
            const message = obj.msg || obj.message || JSON.stringify(d)
            return location ? `${location}: ${message}` : message
          }
          return String(d)
        })
        .filter(Boolean)
      return messages.length > 0 ? messages.join(" | ") : fallback
    }

    // Unexpected object shape — don't render it; stringify safely
    if (typeof detail === "object") {
      return "Validation error. Please check your input."
    }
  }

  // Plain JS Error
  if (err instanceof Error) return err.message

  // Network error (no response)
  const networkErr = err as { message?: string }
  if (networkErr?.message) return networkErr.message

  return fallback
}
