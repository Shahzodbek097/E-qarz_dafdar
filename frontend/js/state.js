/**
 * Ilova holati: joriy foydalanuvchi, biznes va meta ma'lumotlari.
 *
 * Bu modul faqat xotirada ishlaydi. Session cookie brauzerda saqlanadi.
 */

import { api } from "./api.js";
import {
  CONTACT_TYPE_LABELS,
  DIRECTION_LABELS,
  FALLBACK,
  METHOD_LABELS,
  STATUS_LABELS,
} from "./constants.js";

export const state = {
  user: null,
  business: null,
  meta: null,
};

export function setSession(payload) {
  state.user = payload && payload.user ? payload.user : null;
  state.business = payload && payload.business ? payload.business : null;
}

export function clearSession() {
  state.user = null;
  state.business = null;
  state.meta = null;
}

export async function loadMeta() {
  try {
    state.meta = await api.meta();
  } catch (error) {
    // Meta yuklanmasa ham interfeys fallback qiymatlar bilan ishlaydi.
    state.meta = state.meta || null;
  }
}

export function metaOptions(key) {
  const fromApi = state.meta ? state.meta[key] : null;
  if (Array.isArray(fromApi) && fromApi.length) return fromApi;
  return FALLBACK[key] || [];
}

const LABEL_MAPS = {
  debt_directions: DIRECTION_LABELS,
  debt_statuses: STATUS_LABELS,
  payment_methods: METHOD_LABELS,
  contact_types: CONTACT_TYPE_LABELS,
};

export function labelOf(key, value) {
  if (!value) return "—";
  const items = metaOptions(key);
  const found = items.find((item) => item.value === value);
  if (found) return found.label;
  const map = LABEL_MAPS[key];
  return (map && map[value]) || value;
}

export function userFullName() {
  if (!state.user) return "";
  return (
    state.user.full_name ||
    [state.user.first_name, state.user.last_name].filter(Boolean).join(" ") ||
    state.user.username ||
    ""
  );
}

export function initials(name) {
  const text = String(name || "").trim();
  if (!text) return "?";
  const parts = text.split(/\s+/).filter(Boolean);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function businessName() {
  return state.business ? state.business.name : "Biznes";
}
