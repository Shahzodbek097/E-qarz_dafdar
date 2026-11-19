/**
 * UI yordamchilari: formatlash, modal, toast, sahifalash, forma xatolari.
 *
 * Bu modul hech qanday biznes mantiqni bilmaydi — faqat ko'rinish bilan
 * ishlaydi. Shu tufayli uni barcha view'lar bemalol ishlatadi.
 */

import {
  CONTACT_TYPE_LABELS,
  DIRECTION_LABELS,
  METHOD_LABELS,
  STATUS_LABELS,
} from "./constants.js";

const MONTHS = [
  "Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
  "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr",
];

/* --------------------------------------------------------------------------
   Asosiy yordamchilar
   -------------------------------------------------------------------------- */

export function esc(value) {
  return String(value === null || value === undefined ? "" : value).replace(
    /[&<>"']/g,
    (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    })[char]
  );
}

export function qs(selector, root = document) {
  return root.querySelector(selector);
}

export function qsa(selector, root = document) {
  return Array.from(root.querySelectorAll(selector));
}

export function isAlive(node) {
  return Boolean(node && node.isConnected);
}

export function debounce(fn, delay = 300) {
  let timer = null;
  return (...args) => {
    window.clearTimeout(timer);
    timer = window.setTimeout(() => fn(...args), delay);
  };
}

/* --------------------------------------------------------------------------
   Pul va sana
   -------------------------------------------------------------------------- */

/**
 * Pulni guruhlab ko'rsatadi: "1000000.00" -> "1 000 000.00".
 * Hech qanday arifmetika bajarilmaydi — qiymat string sifatida qayta ishlanadi.
 */
export function formatMoney(value, { currency = false, decimals = 2 } = {}) {
  const raw = value === null || value === undefined ? "0" : String(value);
  const negative = raw.startsWith("-");
  const clean = negative ? raw.slice(1) : raw;
  const [integerPart, fractionPart = ""] = clean.split(".");

  const grouped = (integerPart || "0").replace(
    /\B(?=(\d{3})+(?!\d))/g,
    " "
  );

  let result = grouped;
  if (decimals > 0) {
    const fraction = (fractionPart + "0".repeat(decimals)).slice(0, decimals);
    result += `.${fraction}`;
  }
  if (currency) result += " so'm";
  return (negative ? "-" : "") + result;
}

export function formatDate(value) {
  if (!value) return "—";
  const text = String(value).slice(0, 10);
  const parts = text.split("-");
  if (parts.length !== 3) return text;
  return `${parts[2]}.${parts[1]}.${parts[0]}`;
}

export function formatDateTime(value) {
  if (!value) return "—";
  const text = String(value);
  const datePart = text.slice(0, 10);
  const timePart = text.slice(11, 16);
  return timePart ? `${formatDate(datePart)} ${timePart}` : formatDate(datePart);
}

export function formatPeriod(value, groupBy = "day") {
  if (!value) return "—";
  if (groupBy === "month") {
    const parts = String(value).slice(0, 10).split("-");
    const month = MONTHS[Number(parts[1]) - 1] || parts[1];
    return `${month} ${parts[0]}`;
  }
  return formatDate(value);
}

export function todayISO() {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

export function addDaysISO(days, from = null) {
  const base = from ? new Date(`${from}T12:00:00`) : new Date();
  base.setDate(base.getDate() + days);
  const month = String(base.getMonth() + 1).padStart(2, "0");
  const day = String(base.getDate()).padStart(2, "0");
  return `${base.getFullYear()}-${month}-${day}`;
}

export function monthStartISO() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
}

/* --------------------------------------------------------------------------
   Badge'lar
   -------------------------------------------------------------------------- */

export function statusBadge(status, label = null) {
  const text = label || STATUS_LABELS[status] || status || "—";
  return `<span class="badge badge-${esc(status || "muted")}">${esc(text)}</span>`;
}

export function directionBadge(direction, label = null) {
  const text = label || DIRECTION_LABELS[direction] || direction || "—";
  return `<span class="badge badge-${esc(direction || "muted")}">${esc(text)}</span>`;
}

export function methodLabel(method) {
  return METHOD_LABELS[method] || method || "—";
}

export function contactTypeLabel(type) {
  return CONTACT_TYPE_LABELS[type] || type || "—";
}

/* --------------------------------------------------------------------------
   Select / chiplar
   -------------------------------------------------------------------------- */

export function options(items, selected = "", { placeholder = null } = {}) {
  const head =
    placeholder === null
      ? ""
      : `<option value="">${esc(placeholder)}</option>`;
  const body = (items || [])
    .map((item) => {
      const value = String(item.value);
      const isSelected = String(selected ?? "") === value;
      return `<option value="${esc(value)}"${isSelected ? " selected" : ""}>${esc(
        item.label
      )}</option>`;
    })
    .join("");
  return head + body;
}

/* --------------------------------------------------------------------------
   Toast
   -------------------------------------------------------------------------- */

export function toast(message, type = "success") {
  const root = document.getElementById("toast-root");
  if (!root) return;
  const node = document.createElement("div");
  node.className = `toast toast-${type}`;
  node.textContent = message;
  root.appendChild(node);
  window.setTimeout(() => {
    node.classList.add("toast-out");
    window.setTimeout(() => node.remove(), 240);
  }, 3600);
}

/* --------------------------------------------------------------------------
   Modal
   -------------------------------------------------------------------------- */

let modalCounter = 0;

export function openModal({
  title,
  body = "",
  footer = "",
  wide = false,
  onClose = null,
}) {
  const root = document.getElementById("modal-root");
  const id = `modal-title-${++modalCounter}`;
  const overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.innerHTML = `
    <div class="modal${wide ? " modal-wide" : ""}" role="dialog" aria-modal="true" aria-labelledby="${id}">
      <div class="modal-head">
        <h2 id="${id}">${esc(title)}</h2>
        <button type="button" class="icon-btn" data-modal-close aria-label="Yopish">✕</button>
      </div>
      <div class="modal-body">${body}</div>
      ${footer ? `<div class="modal-foot">${footer}</div>` : ""}
    </div>`;
  root.appendChild(overlay);
  document.body.classList.add("modal-open");

  const close = () => {
    if (!overlay.isConnected) return;
    overlay.remove();
    document.body.classList.remove("modal-open");
    document.removeEventListener("keydown", onKey);
    if (onClose) onClose();
  };

  const onKey = (event) => {
    if (event.key === "Escape") close();
  };

  document.addEventListener("keydown", onKey);
  overlay.addEventListener("click", (event) => {
    if (event.target === overlay || event.target.closest("[data-modal-close]")) {
      close();
    }
  });

  window.setTimeout(() => {
    const focusable = overlay.querySelector(
      "input:not([disabled]), select:not([disabled]), textarea:not([disabled]), button"
    );
    if (focusable) focusable.focus();
  }, 40);

  return {
    root: overlay,
    body: overlay.querySelector(".modal-body"),
    footer: overlay.querySelector(".modal-foot"),
    close,
  };
}

export function confirmDialog({
  title = "Tasdiqlaysizmi?",
  message,
  confirmText = "Tasdiqlash",
  cancelText = "Bekor qilish",
  danger = false,
}) {
  return new Promise((resolve) => {
    let settled = false;
    const finish = (value) => {
      if (settled) return;
      settled = true;
      modal.close();
      resolve(value);
    };

    const modal = openModal({
      title,
      body: `<p class="confirm-text">${esc(message)}</p>`,
      footer: `
        <button type="button" class="btn btn-ghost" data-cancel>${esc(cancelText)}</button>
        <button type="button" class="btn ${danger ? "btn-danger" : "btn-primary"}" data-ok>${esc(confirmText)}</button>`,
      onClose: () => {
        if (!settled) {
          settled = true;
          resolve(false);
        }
      },
    });

    modal.footer.querySelector("[data-cancel]").addEventListener("click", () => finish(false));
    modal.footer.querySelector("[data-ok]").addEventListener("click", () => finish(true));
  });
}

/* --------------------------------------------------------------------------
   Formalar
   -------------------------------------------------------------------------- */

export function clearFormErrors(form) {
  form.querySelectorAll(".field-error").forEach((node) => node.remove());
  form.querySelectorAll("[aria-invalid]").forEach((node) => node.removeAttribute("aria-invalid"));
  const box = form.querySelector("[data-form-error]");
  if (box) {
    box.hidden = true;
    box.textContent = "";
  }
}

export function renderFieldErrors(form, fields = {}) {
  clearFormErrors(form);
  const leftovers = [];

  for (const [name, value] of Object.entries(fields || {})) {
    const message = Array.isArray(value) ? value[0] : String(value);
    if (!message) continue;

    if (name === "non_field_errors" || name === "detail") {
      leftovers.push(message);
      continue;
    }

    const input = form.querySelector(`[name="${name}"]`);
    if (!input) {
      leftovers.push(`${name}: ${message}`);
      continue;
    }

    input.setAttribute("aria-invalid", "true");
    const field = input.closest(".field");
    if (field) {
      const node = document.createElement("div");
      node.className = "field-error";
      node.textContent = message;
      field.appendChild(node);
    }
  }

  if (leftovers.length) {
    let box = form.querySelector("[data-form-error]");
    if (!box) {
      box = document.createElement("div");
      box.className = "form-error";
      box.setAttribute("data-form-error", "");
      form.prepend(box);
    }
    box.hidden = false;
    box.textContent = leftovers[0];
  }
}

export function serializeForm(form) {
  const data = {};
  form.querySelectorAll("input[name], select[name], textarea[name]").forEach((input) => {
    if (input.disabled) return;
    if (input.type === "checkbox") {
      data[input.name] = input.checked;
    } else {
      data[input.name] = typeof input.value === "string" ? input.value.trim() : input.value;
    }
  });
  return data;
}

export function setButtonLoading(button, loading, text = "Saqlanmoqda…") {
  if (!button) return;
  if (loading) {
    button.dataset.originalText = button.textContent;
    button.disabled = true;
    button.textContent = text;
  } else {
    button.disabled = false;
    if (button.dataset.originalText) {
      button.textContent = button.dataset.originalText;
      delete button.dataset.originalText;
    }
  }
}

/* --------------------------------------------------------------------------
   Sahifa qismlari
   -------------------------------------------------------------------------- */

export function pageHead({ title, subtitle = "", actions = "" }) {
  return `
    <div class="page-head">
      <div>
        <h1 class="page-title">${esc(title)}</h1>
        ${subtitle ? `<p class="page-sub">${esc(subtitle)}</p>` : ""}
      </div>
      ${actions ? `<div class="page-actions">${actions}</div>` : ""}
    </div>`;
}

export function statCard({
  label,
  value,
  sub = "",
  tone = "",
  currency = true,
  raw = false,
}) {
  const display = raw ? value : formatMoney(value, { currency });
  return `
    <div class="stat${tone ? ` tone-${tone}` : ""}">
      <div class="stat-label">${esc(label)}</div>
      <div class="stat-value">${display}</div>
      ${sub ? `<div class="stat-sub">${esc(sub)}</div>` : ""}
    </div>`;
}

export function loadingBlock(text = "Yuklanmoqda…") {
  return `<div class="loading-block"><div class="spinner"></div><span>${esc(text)}</span></div>`;
}

export function renderError(container, error) {
  const message =
    error && error.message ? error.message : "Kutilmagan xatolik yuz berdi.";
  container.innerHTML = `<div class="alert alert-error"><strong>Xatolik.</strong> ${esc(
    message
  )}</div>`;
}

export function emptyState({ title, text = "", icon = "∅", action = "" }) {
  return `
    <div class="empty">
      <div class="empty-icon">${icon}</div>
      <div class="empty-title">${esc(title)}</div>
      ${text ? `<div class="empty-text">${esc(text)}</div>` : ""}
      ${action}
    </div>`;
}

export function renderPager(container, { count, page, pageSize, onPage }) {
  if (!container) return;
  const totalPages = Math.max(1, Math.ceil(count / pageSize));
  if (count === 0) {
    container.innerHTML = "";
    return;
  }
  container.innerHTML = `
    <div class="pager">
      <span class="pager-info">${count} ta yozuv · ${page}/${totalPages} sahifa</span>
      <div class="pager-actions">
        <button type="button" class="btn btn-ghost btn-sm" data-page="${page - 1}" ${
    page <= 1 ? "disabled" : ""
  }>‹ Oldingi</button>
        <button type="button" class="btn btn-ghost btn-sm" data-page="${page + 1}" ${
    page >= totalPages ? "disabled" : ""
  }>Keyingi ›</button>
      </div>
    </div>`;

  container.querySelectorAll("[data-page]").forEach((button) => {
    button.addEventListener("click", () => {
      const next = Number(button.dataset.page);
      if (next >= 1 && next <= totalPages && next !== page) onPage(next);
    });
  });
}

/* --------------------------------------------------------------------------
   Kichik tafsilotlar
   -------------------------------------------------------------------------- */

export function debtStatusInfo(debt) {
  const status = debt.display_status || debt.status;
  const label = STATUS_LABELS[status] || status;
  return { status, label, html: statusBadge(status, label) };
}

export function archivedBadge(debt) {
  return debt.is_archived
    ? '<span class="badge badge-archived">Arxivlangan</span>'
    : "";
}

export function reverseBadge(payment) {
  return payment.is_reversed
    ? '<span class="badge badge-reversed">Bekor qilingan</span>'
    : '<span class="badge badge-active">Faol</span>';
}

export function truncate(value, length = 60) {
  const text = String(value || "");
  return text.length > length ? `${text.slice(0, length)}…` : text;
}
