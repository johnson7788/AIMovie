/** Shared API base URL for axios, SSE, and static task file URLs. */
export function getApiBaseUrl(): string {
    if (import.meta.env.DEV) {
        return `${globalThis.location.origin}/local`;
    }
    if (import.meta.env.VITE_REQUEST_BASE_URL) {
        return import.meta.env.VITE_REQUEST_BASE_URL.replace(/\/$/, '');
    }
    const metaBase = document.querySelector('meta[name="base-url"]')?.getAttribute('content');
    if (metaBase) {
        return metaBase.replace(/\/$/, '');
    }
    return globalThis.location.origin;
}

/** Build a full URL for a backend API path (with or without leading slash). */
export function buildApiUrl(path: string): string {
    const base = getApiBaseUrl();
    const normalized = path.startsWith('/') ? path.slice(1) : path;
    return `${base}/${normalized}`;
}
