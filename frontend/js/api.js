/**
 * REST API mijozi.
 *
 * Frontend faqat `/api/v1/` bilan ishlaydi. Autentifikatsiya — Django
 * session cookie. Har bir o'zgartiruvchi so'rovda CSRF token yuboriladi.
 *
 * Pul qiymatlari hech qachon `Number`ga aylantirilmaydi: API ularni string
 * ko'rinishida qaytaradi va shundayligicha saqlanadi.
 */

const BASE = "/api/v1";
const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

export class ApiError extends Error {
  constructor({ code = "error", message = "Xatolik yuz berdi.", fields = {}, status = 0 }) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.fields = fields || {};
    this.status = status;
  }
}

let csrfToken = null;
let unauthorizedHandler = null;

/** 401 (yoki session tugagan) holatida app.js shu callback'ni oladi. */
export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = handler;
}

/** Login/logout'dan keyin Django CSRF tokenini almashtiradi. */
export function resetCsrf() {
  csrfToken = null;
}

function readCookie(name) {
  const target = `${name}=`;
  const parts = document.cookie ? document.cookie.split(";") : [];
  for (const part of parts) {
    const value = part.trim();
    if (value.startsWith(target)) {
      return decodeURIComponent(value.slice(target.length));
    }
  }
  return null;
}

function buildUrl(path, params) {
  const url = new URL(BASE + path, window.location.origin);
  if (params && typeof params === "object") {
    for (const [key, value] of Object.entries(params)) {
      if (value === undefined || value === null || value === "") continue;
      url.searchParams.set(key, String(value));
    }
  }
  return url.pathname + url.search;
}

export async function refreshCsrf() {
  const response = await fetch(BASE + "/auth/csrf/", {
    method: "GET",
    credentials: "same-origin",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new ApiError({
      code: "csrf_error",
      message: "Xavfsizlik tokenini olib bo'lmadi. Sahifani yangilang.",
      status: response.status,
    });
  }
  const data = await response.json();
  csrfToken = data.csrfToken || readCookie("csrftoken");
  return csrfToken;
}

async function ensureCsrf() {
  if (csrfToken) return csrfToken;
  const cookie = readCookie("csrftoken");
  if (cookie) {
    csrfToken = cookie;
    return cookie;
  }
  return refreshCsrf();
}

async function request(method, path, { body, params } = {}) {
  const headers = { Accept: "application/json" };
  const options = { method, credentials: "same-origin", headers };

  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }

  if (!SAFE_METHODS.has(method)) {
    headers["X-CSRFToken"] = await ensureCsrf();
  }

  let response;
  try {
    response = await fetch(buildUrl(path, params), options);
  } catch (error) {
    throw new ApiError({
      code: "network_error",
      message: "Server bilan bog'lanib bo'lmadi. Internet aloqasini tekshiring.",
      status: 0,
    });
  }

  if (response.status === 204) return null;

  const contentType = response.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");
  const data = isJson ? await response.json().catch(() => null) : null;

  if (!response.ok) {
    const payload = data && data.error ? data.error : {};
    const code = payload.code || "http_error";

    if (
      unauthorizedHandler &&
      (response.status === 401 ||
        (response.status === 403 && code === "not_authenticated"))
    ) {
      unauthorizedHandler();
    }

    throw new ApiError({
      code,
      message: payload.message || `So'rov bajarilmadi (HTTP ${response.status}).`,
      fields: payload.fields || {},
      status: response.status,
    });
  }

  return data;
}

export const api = {
  auth: {
    csrf: () => request("GET", "/auth/csrf/"),
    register: (payload) => request("POST", "/auth/register/", { body: payload }),
    login: (payload) => request("POST", "/auth/login/", { body: payload }),
    logout: () => request("POST", "/auth/logout/"),
    me: () => request("GET", "/auth/me/"),
    updateMe: (payload) => request("PATCH", "/auth/me/", { body: payload }),
  },

  business: {
    get: () => request("GET", "/business/"),
    update: (payload) => request("PATCH", "/business/", { body: payload }),
  },

  meta: () => request("GET", "/meta/"),

  contacts: {
    list: (params) => request("GET", "/contacts/", { params }),
    create: (payload) => request("POST", "/contacts/", { body: payload }),
    get: (id) => request("GET", `/contacts/${id}/`),
    update: (id, payload) => request("PATCH", `/contacts/${id}/`, { body: payload }),
    remove: (id) => request("DELETE", `/contacts/${id}/`),
    summary: (id, params) => request("GET", `/contacts/${id}/summary/`, { params }),
  },

  debts: {
    list: (params) => request("GET", "/debts/", { params }),
    create: (payload) => request("POST", "/debts/", { body: payload }),
    get: (id) => request("GET", `/debts/${id}/`),
    update: (id, payload) => request("PATCH", `/debts/${id}/`, { body: payload }),
    remove: (id) => request("DELETE", `/debts/${id}/`),
    archive: (id) => request("POST", `/debts/${id}/archive/`),
    unarchive: (id) => request("POST", `/debts/${id}/unarchive/`),
    payments: (id, params) => request("GET", `/debts/${id}/payments/`, { params }),
    addPayment: (id, payload) =>
      request("POST", `/debts/${id}/payments/`, { body: payload }),
  },

  payments: {
    list: (params) => request("GET", "/payments/", { params }),
    get: (id) => request("GET", `/payments/${id}/`),
    reverse: (id, payload) =>
      request("POST", `/payments/${id}/reverse/`, { body: payload }),
  },

  reports: {
    dashboard: () => request("GET", "/reports/dashboard/"),
    debts: (params) => request("GET", "/reports/debts/", { params }),
    payments: (params) => request("GET", "/reports/payments/", { params }),
    overdue: (params) => request("GET", "/reports/overdue/", { params }),
  },
};
