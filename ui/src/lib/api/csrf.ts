/**
 * CSRF token storage for participant Study API mutations.
 */

export const CSRF_HEADER_NAME = "X-CSRF-Token";
export const CSRF_COOKIE_NAME = "participant_csrf";
export const CAPABILITY_COOKIE_NAME = "participant_capability";

const CSRF_STORAGE_KEY = "idp-participant-csrf";

/**
 * Persist the CSRF token for browser-side Study API calls.
 */
export function storeCsrfToken(token: string): void {
  if (typeof document !== "undefined") {
    document.cookie = `${CSRF_COOKIE_NAME}=${encodeURIComponent(token)}; path=/; SameSite=Lax`;
  }
  if (typeof sessionStorage !== "undefined") {
    sessionStorage.setItem(CSRF_STORAGE_KEY, token);
  }
}

/**
 * Read the CSRF token from sessionStorage or cookie.
 */
export function getCsrfToken(): string | null {
  if (typeof sessionStorage !== "undefined") {
    const stored = sessionStorage.getItem(CSRF_STORAGE_KEY);
    if (stored) {
      return stored;
    }
  }
  if (typeof document === "undefined") {
    return null;
  }
  const match = document.cookie
    .split("; ")
    .find((entry) => entry.startsWith(`${CSRF_COOKIE_NAME}=`));
  if (!match) {
    return null;
  }
  return decodeURIComponent(match.split("=")[1] ?? "");
}

/**
 * Build headers for a state-changing Study API request.
 */
export function withCsrfHeaders(
  headers: HeadersInit = {},
  csrfToken?: string | null,
): HeadersInit {
  const token = csrfToken ?? getCsrfToken();
  const next = new Headers(headers);
  if (token) {
    next.set(CSRF_HEADER_NAME, token);
  }
  return next;
}
