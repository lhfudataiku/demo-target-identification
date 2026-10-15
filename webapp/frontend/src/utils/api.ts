// Every API call goes through apiUrl(). Inside DSS the frontend and its FastAPI
// backend live on different URLs; bs-blueprint's apiUrl() resolves the backend
// URL through the DSS-injected `dataiku.getWebAppBackendUrl()`. Locally there is
// no `dataiku` global and Vite proxies /api, so the path is returned unchanged.
export { apiUrl } from 'bs-blueprint'
