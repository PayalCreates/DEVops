/** Mirrors the backend's password policy so users get instant feedback. */
export function validatePassword(pw: string): string | null {
  if (pw.length < 8) return 'At least 8 characters'
  if (pw.length > 72) return 'At most 72 characters'
  if (!/[A-Z]/.test(pw) || !/[a-z]/.test(pw) || !/\d/.test(pw))
    return 'Use upper and lower case letters and a digit'
  return null
}
