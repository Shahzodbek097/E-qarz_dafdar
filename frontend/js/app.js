/**
 * Ilovaning kirish nuqtasi: sessiyani tiklash, layout, router va sahifalar.
 *
 * Frontend same-origin ishlaydi (`/` va `/assets/...`), API esa `/api/v1/`.
 * Shu sababli cookie va CSRF oddiy ishlaydi, CORS kerak emas.
 */

import { api, resetCsrf, setUnauthorizedHandler } from "./api.js";
import {
  businessName,
  clearSession,
  initials,
  loadMeta,
  setSession,
  state,
  userFullName,
} from "./state.js";
import {
  defineRoute,
  matchRoute,
  navigate,
  startRouter,
} from "./router.js";
import { esc, toast } from "./ui.js";

import { renderLogin, renderRegister } from "./views/auth.js";
import { renderDashboard } from "./views/dashboard.js";
import { renderContacts } from "./views/contacts.js";
import { renderContactDetail } from "./views/contact-detail.js";
import { renderDebts } from "./views/debts.js";
import { renderDebtDetail } from "./views/debt-detail.js";
import { renderPayments } from "./views/payments.js";
import {
  renderDebtsReport,
  renderOverdueReport,
  renderPaymentsReport,
} from "./views/reports.js";
import { renderSettings } from "./views/settings.js";

const app = document.getElementById("app");

/* --------------------------------------------------------------------------
   Ikonkalar
   -------------------------------------------------------------------------- */

const ICONS = {
  dashboard:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>',
  users:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
  file:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M8 13h8"/><path d="M8 17h5"/></svg>',
  wallet:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="5" width="20" height="14" rx="2.5"/><path d="M2 10h20"/><circle cx="16.5" cy="15" r="1"/></svg>',
  chart:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><rect x="7" y="12" width="3" height="6" rx="1"/><rect x="12" y="8" width="3" height="10" rx="1"/><rect x="17" y="5" width="3" height="13" rx="1"/></svg>',
  gear:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
  menu:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 6h16"/><path d="M4 12h16"/><path d="M4 18h16"/></svg>',
};

const NAV_ITEMS = [
  { href: "/dashboard", label: "Boshqaruv", icon: "dashboard" },
  { href: "/contacts", label: "Mijozlar", icon: "users" },
  { href: "/debts", label: "Qarzlar", icon: "file" },
  { href: "/payments", label: "To'lovlar", icon: "wallet" },
  { href: "/reports/debts", label: "Hisobotlar", icon: "chart" },
  { href: "/settings", label: "Sozlamalar", icon: "gear" },
];

/* --------------------------------------------------------------------------
   Layout
   -------------------------------------------------------------------------- */

let layout = null;

function navLinksHtml() {
  return NAV_ITEMS.map(
    (item) => `
      <a class="nav-link" href="#${item.href}" data-nav="${item.href}">
        <span class="nav-icon">${ICONS[item.icon]}</span>
        <span>${item.label}</span>
      </a>`
  ).join("");
}

function shellHtml() {
  const name = userFullName();
  const user = state.user || {};
  const business = state.business || {};

  return `
    <div class="layout">
      <aside class="sidebar" id="sidebar">
        <a class="brand" href="#/dashboard">
          <span class="brand-mark">EQ</span>
          <span class="brand-text">
            <strong>E-QarzDaftar</strong>
            <small>qarzlar daftari</small>
          </span>
        </a>

        <nav class="nav">${navLinksHtml()}</nav>

        <div class="sidebar-foot">
          <div class="sidebar-user">
            <div class="avatar" data-avatar>${esc(initials(name))}</div>
            <div>
              <strong id="sidebar-user-name">${esc(name)}</strong>
              <small id="sidebar-user-login">@${esc(user.username || "")}</small>
            </div>
          </div>
          <button type="button" class="btn btn-ghost btn-sm btn-block" id="logout-btn">
            Chiqish
          </button>
        </div>
      </aside>

      <div class="sidebar-backdrop" id="sidebar-backdrop"></div>

      <div class="main">
        <header class="topbar">
          <button type="button" class="icon-btn menu-btn" id="menu-btn" aria-label="Menyu">
            ${ICONS.menu}
          </button>
          <div class="topbar-title">
            <strong id="topbar-business">${esc(business.name || "Biznes")}</strong>
            <span id="topbar-industry">${esc(business.industry_display || "")}</span>
          </div>
          <div class="topbar-user">
            <div class="avatar avatar-lg" data-avatar>${esc(initials(name))}</div>
            <span id="topbar-user-name">${esc(name)}</span>
          </div>
        </header>
        <main id="view" class="view"></main>
      </div>
    </div>`;
}

function closeSidebar() {
  const sidebar = document.getElementById("sidebar");
  const backdrop = document.getElementById("sidebar-backdrop");
  if (sidebar) sidebar.classList.remove("open");
  if (backdrop) backdrop.classList.remove("open");
}

function bindShell() {
  const menuButton = document.getElementById("menu-btn");
  const sidebar = document.getElementById("sidebar");
  const backdrop = document.getElementById("sidebar-backdrop");
  const logoutButton = document.getElementById("logout-btn");

  if (menuButton && sidebar && backdrop) {
    menuButton.addEventListener("click", () => {
      sidebar.classList.toggle("open");
      backdrop.classList.toggle("open");
    });
    backdrop.addEventListener("click", closeSidebar);
  }

  document.querySelectorAll("[data-nav]").forEach((link) => {
    link.addEventListener("click", closeSidebar);
  });

  if (logoutButton) {
    logoutButton.addEventListener("click", logout);
  }
}

function ensureShell() {
  if (layout !== "shell") {
    app.innerHTML = shellHtml();
    layout = "shell";
    bindShell();
  }
  return document.getElementById("view");
}

function ensureAuth() {
  if (layout !== "auth") {
    app.innerHTML = "";
    layout = "auth";
  }
  return app;
}

function updateNav(path) {
  document.querySelectorAll("[data-nav]").forEach((link) => {
    const target = link.dataset.nav;
    const active =
      path === target ||
      (target !== "/dashboard" && path.startsWith(`${target}/`)) ||
      (target === "/reports/debts" && path.startsWith("/reports"));
    link.classList.toggle("active", active);
  });
}

function refreshShellUser() {
  if (layout !== "shell") return;
  const name = userFullName();
  const business = state.business || {};
  const user = state.user || {};

  const setName = (id, value) => {
    const node = document.getElementById(id);
    if (node) node.textContent = value;
  };

  setName("sidebar-user-name", name);
  setName("sidebar-user-login", `@${user.username || ""}`);
  setName("topbar-user-name", name);
  setName("topbar-business", business.name || "Biznes");
  setName("topbar-industry", business.industry_display || "");

  document.querySelectorAll("[data-avatar]").forEach((node) => {
    node.textContent = initials(name);
  });
}

/* --------------------------------------------------------------------------
   Sessiya
   -------------------------------------------------------------------------- */

async function logout() {
  try {
    await api.auth.logout();
  } catch (error) {
    // Sessiya allaqachon tugagan bo'lsa ham davom etamiz.
  }
  resetCsrf();
  clearSession();
  layout = null;
  toast("Tizimdan chiqdingiz.", "info");
  navigate("/login");
}

function handleUnauthorized() {
  if (!state.user) return;
  clearSession();
  layout = null;
  toast("Sessiya tugadi. Qayta kiring.", "info");
  navigate("/login");
}

/* --------------------------------------------------------------------------
   Router
   -------------------------------------------------------------------------- */

defineRoute("/login", renderLogin, { public: true });
defineRoute("/register", renderRegister, { public: true });
defineRoute("/dashboard", renderDashboard);
defineRoute("/contacts", renderContacts);
defineRoute("/contacts/:id", renderContactDetail);
defineRoute("/debts", renderDebts);
defineRoute("/debts/:id", renderDebtDetail);
defineRoute("/payments", renderPayments);
defineRoute("/reports", renderDebtsReport);
defineRoute("/reports/debts", renderDebtsReport);
defineRoute("/reports/payments", renderPaymentsReport);
defineRoute("/reports/overdue", renderOverdueReport);
defineRoute("/settings", renderSettings);

async function handleRoute({ path }) {
  if (!path || path === "/") {
    navigate(state.user ? "/dashboard" : "/login", { replace: true });
    return;
  }

  const found = matchRoute(path);
  if (!found) {
    navigate(state.user ? "/dashboard" : "/login", { replace: true });
    return;
  }

  const isPublic = found.route.public;

  if (!isPublic && !state.user) {
    navigate("/login", { replace: true });
    return;
  }

  if (isPublic && state.user) {
    navigate("/dashboard", { replace: true });
    return;
  }

  const container = isPublic ? ensureAuth() : ensureShell();
  updateNav(path);
  closeSidebar();
  window.scrollTo(0, 0);

  try {
    await found.route.handler(container, found.params);
  } catch (error) {
    console.error(error);
    toast(error.message || "Sahifani yuklab bo'lmadi.", "error");
  }
}

/* --------------------------------------------------------------------------
   Boot
   -------------------------------------------------------------------------- */

async function boot() {
  setUnauthorizedHandler(handleUnauthorized);

  try {
    const session = await api.auth.me();
    setSession(session);
  } catch (error) {
    clearSession();
  }

  if (state.user) {
    await loadMeta();
  }

  document.addEventListener("session-updated", refreshShellUser);

  startRouter(handleRoute);
}

boot();
