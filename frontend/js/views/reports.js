/**
 * Hisobotlar: qarzlar, to'lovlar va muddati o'tgan qarzlar.
 *
 * Barcha hisob-kitob backendda bajariladi. Frontend faqat filtr yuboradi
 * va natijalarni jadval ko'rinishida chiqaradi.
 */

import { api } from "../api.js";
import { metaOptions } from "../state.js";
import { REPORT_TABS, STATUS_LABELS } from "../constants.js";
import {
  addDaysISO,
  directionBadge,
  emptyState,
  formatDate,
  formatMoney,
  formatPeriod,
  isAlive,
  loadingBlock,
  methodLabel,
  options,
  pageHead,
  renderError,
  statCard,
  statusBadge,
  todayISO,
} from "../ui.js";

function reportTabs(active) {
  return `<div class="tabs">${REPORT_TABS.map(
    (tab) =>
      `<a class="tab${tab.key === active ? " active" : ""}" href="${tab.href}">${tab.label}</a>`
  ).join("")}</div>`;
}

/**
 * Forma maydoni qiymatini xavfsiz oladi.
 *
 * `form.method` kabi nomlar HTMLFormElement'ning o'z xossalari bilan
 * to'qnashadi, shuning uchun har doim `form.elements` orqali o'qiymiz.
 */
function valueOf(form, name) {
  const field = form.elements.namedItem(name);
  return field ? field.value : "";
}

function filterForm(inner) {
  return `
    <section class="card" style="margin-bottom:18px">
      <div class="toolbar">
        <form id="report-form" class="toolbar-group" style="flex:1">
          ${inner}
          <button type="submit" class="btn btn-primary btn-sm">Ko'rsatish</button>
        </form>
      </div>
    </section>`;
}

function seriesTable(rows, groupBy) {
  if (!rows || !rows.length) {
    return emptyState({
      title: "Ma'lumot yo'q",
      text: "Tanlangan davr uchun yozuv topilmadi.",
      icon: "📊",
    });
  }

  return `<div class="table-wrap">
    <table class="table">
      <thead>
        <tr>
          <th>Davr</th>
          <th class="num">Soni</th>
          <th class="num">Menga qarzdor</th>
          <th class="num">Men qarzdorman</th>
          <th class="num">To'langan</th>
          <th class="num">Qoldiq</th>
        </tr>
      </thead>
      <tbody>
        ${rows
          .map(
            (row) => `
          <tr>
            <td class="nowrap strong">${formatPeriod(row.period, groupBy)}</td>
            <td class="num">${row.count}</td>
            <td class="num">${formatMoney(row.receivable_amount)}</td>
            <td class="num">${formatMoney(row.payable_amount)}</td>
            <td class="num">${formatMoney(row.paid_total)}</td>
            <td class="num strong">${formatMoney(row.remaining_total)}</td>
          </tr>`
          )
          .join("")}
      </tbody>
    </table>
  </div>`;
}

/* --------------------------------------------------------------------------
   Qarzlar hisoboti
   -------------------------------------------------------------------------- */

export function renderDebtsReport(container) {
  const defaultFrom = addDaysISO(-30);

  container.innerHTML = `
    ${pageHead({
      title: "Hisobotlar",
      subtitle: "Davr bo'yicha qarzlar harakati",
    })}
    ${reportTabs("debts")}
    ${filterForm(`
      <input class="filter-select" type="date" name="date_from" value="${defaultFrom}" aria-label="Boshlanish sanasi">
      <input class="filter-select" type="date" name="date_to" value="${todayISO()}" aria-label="Tugash sanasi">
      <select class="filter-select" name="group_by" aria-label="Guruhlash">
        <option value="day">Kun bo'yicha</option>
        <option value="month">Oy bo'yicha</option>
      </select>
      <select class="filter-select" name="direction" aria-label="Yo'nalish">
        ${options(metaOptions("debt_directions"), "", { placeholder: "Barcha yo'nalishlar" })}
      </select>
    `)}
    <div id="report-body">${loadingBlock()}</div>`;

  const form = container.querySelector("#report-form");
  const body = container.querySelector("#report-body");

  async function load() {
    const params = {
      date_from: valueOf(form, "date_from"),
      date_to: valueOf(form, "date_to"),
      group_by: valueOf(form, "group_by"),
      direction: valueOf(form, "direction"),
    };
    body.innerHTML = loadingBlock();
    try {
      const data = await api.reports.debts(params);
      if (!isAlive(container)) return;

      const totals = data.totals;
      const byStatus = data.by_status;

      body.innerHTML = `
        <div class="stat-grid">
          ${statCard({
            label: "Menga qarzdor",
            value: totals.receivable_amount,
            sub: `Qoldiq: ${formatMoney(totals.receivable_remaining, {
              currency: true,
            })}`,
            tone: "green",
          })}
          ${statCard({
            label: "Men qarzdorman",
            value: totals.payable_amount,
            sub: `Qoldiq: ${formatMoney(totals.payable_remaining, {
              currency: true,
            })}`,
            tone: "violet",
          })}
          ${statCard({
            label: "To'langan",
            value: totals.paid_total,
            sub: "Tanlangan davr bo'yicha",
            tone: "amber",
          })}
          ${statCard({
            label: "Qarzlar soni",
            value: String(totals.count),
            raw: true,
            currency: false,
            sub: "Tanlangan davrda yaratilgan",
          })}
        </div>

        <section class="card" style="margin-bottom:18px">
          <div class="card-head"><div class="card-title">Holat bo'yicha</div></div>
          <div class="card-body">
            <div class="chips">
              ${["overdue", "open", "partial", "paid"]
                .map(
                  (key) => `
                <span class="chip">
                  ${statusBadge(key, STATUS_LABELS[key])}
                  <strong>${byStatus[key] ?? 0}</strong>
                </span>`
                )
                .join("")}
            </div>
          </div>
        </section>

        <section class="card">
          <div class="card-head">
            <div>
              <div class="card-title">Davr bo'yicha</div>
              <div class="card-sub">${formatDate(
                data.period.date_from
              )} — ${formatDate(data.period.date_to)}</div>
            </div>
          </div>
          <div class="card-body flush">
            ${seriesTable(data.series, data.filters.group_by)}
          </div>
        </section>`;
    } catch (error) {
      if (isAlive(container)) renderError(body, error);
    }
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    load();
  });

  load();
}

/* --------------------------------------------------------------------------
   To'lovlar hisoboti
   -------------------------------------------------------------------------- */

function paymentsSeriesTable(rows, groupBy) {
  if (!rows || !rows.length) {
    return emptyState({
      title: "To'lovlar yo'q",
      text: "Tanlangan davr uchun to'lov topilmadi.",
      icon: "₽",
    });
  }

  return `<div class="table-wrap">
    <table class="table">
      <thead>
        <tr>
          <th>Davr</th>
          <th class="num">Soni</th>
          <th class="num">Jami</th>
          <th class="num">Kirim</th>
          <th class="num">Chiqim</th>
        </tr>
      </thead>
      <tbody>
        ${rows
          .map(
            (row) => `
          <tr>
            <td class="nowrap strong">${formatPeriod(row.period, groupBy)}</td>
            <td class="num">${row.count}</td>
            <td class="num">${formatMoney(row.total)}</td>
            <td class="num money-green">${formatMoney(row.received)}</td>
            <td class="num money-red">${formatMoney(row.paid_out)}</td>
          </tr>`
          )
          .join("")}
      </tbody>
    </table>
  </div>`;
}

export function renderPaymentsReport(container) {
  const defaultFrom = addDaysISO(-30);

  container.innerHTML = `
    ${pageHead({
      title: "Hisobotlar",
      subtitle: "Davr bo'yicha to'lovlar harakati",
    })}
    ${reportTabs("payments")}
    ${filterForm(`
      <input class="filter-select" type="date" name="date_from" value="${defaultFrom}" aria-label="Boshlanish sanasi">
      <input class="filter-select" type="date" name="date_to" value="${todayISO()}" aria-label="Tugash sanasi">
      <select class="filter-select" name="group_by" aria-label="Guruhlash">
        <option value="day">Kun bo'yicha</option>
        <option value="month">Oy bo'yicha</option>
      </select>
      <select class="filter-select" name="method" aria-label="To'lov turi">
        ${options(metaOptions("payment_methods"), "", { placeholder: "Barcha turlar" })}
      </select>
    `)}
    <div id="report-body">${loadingBlock()}</div>`;

  const form = container.querySelector("#report-form");
  const body = container.querySelector("#report-body");

  async function load() {
    const params = {
      date_from: valueOf(form, "date_from"),
      date_to: valueOf(form, "date_to"),
      group_by: valueOf(form, "group_by"),
      method: valueOf(form, "method"),
    };
    body.innerHTML = loadingBlock();
    try {
      const data = await api.reports.payments(params);
      if (!isAlive(container)) return;

      const totals = data.totals;

      body.innerHTML = `
        <div class="stat-grid">
          ${statCard({
            label: "Jami to'lov",
            value: totals.total,
            sub: `${totals.count} ta to'lov`,
          })}
          ${statCard({
            label: "Kirim",
            value: totals.received,
            sub: "\"Menga qarzdor\" qarzlardan",
            tone: "green",
          })}
          ${statCard({
            label: "Chiqim",
            value: totals.paid_out,
            sub: "\"Men qarzdorman\" qarzlar bo'yicha",
            tone: "red",
          })}
          ${statCard({
            label: "To'lovlar soni",
            value: String(totals.count),
            raw: true,
            currency: false,
            sub: "Bekor qilinganlar hisobga kirmaydi",
          })}
        </div>

        <div class="grid-2" style="margin-bottom:18px">
          <section class="card">
            <div class="card-head"><div class="card-title">To'lov turlari bo'yicha</div></div>
            <div class="card-body flush">
              ${
                data.by_method.length
                  ? `<div class="table-wrap">
                       <table class="table">
                         <thead>
                           <tr><th>Turi</th><th class="num">Soni</th><th class="num">Summa</th></tr>
                         </thead>
                         <tbody>
                           ${data.by_method
                             .map(
                               (row) => `
                             <tr>
                               <td>${methodLabel(row.method)}</td>
                               <td class="num">${row.count}</td>
                               <td class="num strong">${formatMoney(row.total)}</td>
                             </tr>`
                             )
                             .join("")}
                         </tbody>
                       </table>
                     </div>`
                  : emptyState({ title: "Ma'lumot yo'q", icon: "₽" })
              }
            </div>
          </section>

          <section class="card">
            <div class="card-head"><div class="card-title">Davr bo'yicha</div></div>
            <div class="card-body flush">
              ${paymentsSeriesTable(data.series, data.filters.group_by)}
            </div>
          </section>
        </div>`;
    } catch (error) {
      if (isAlive(container)) renderError(body, error);
    }
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    load();
  });

  load();
}

/* --------------------------------------------------------------------------
   Muddati o'tgan qarzlar
   -------------------------------------------------------------------------- */

export function renderOverdueReport(container) {
  container.innerHTML = `
    ${pageHead({
      title: "Hisobotlar",
      subtitle: "Muddati o'tgan va qoldig'i bor qarzlar",
    })}
    ${reportTabs("overdue")}
    ${filterForm(`
      <input class="filter-select" type="date" name="as_of" value="${todayISO()}" aria-label="Sana holatiga">
      <select class="filter-select" name="direction" aria-label="Yo'nalish">
        ${options(metaOptions("debt_directions"), "", { placeholder: "Barcha yo'nalishlar" })}
      </select>
    `)}
    <div id="report-body">${loadingBlock()}</div>`;

  const form = container.querySelector("#report-form");
  const body = container.querySelector("#report-body");

  async function load() {
    const params = {
      as_of: valueOf(form, "as_of"),
      direction: valueOf(form, "direction"),
    };
    body.innerHTML = loadingBlock();
    try {
      const data = await api.reports.overdue(params);
      if (!isAlive(container)) return;

      const totals = data.totals;

      body.innerHTML = `
        <div class="stat-grid" style="grid-template-columns:repeat(3,minmax(0,1fr))">
          ${statCard({
            label: "Menga qarzdor",
            value: totals.receivable,
            sub: "Muddati o'tgan qoldiq",
            tone: "red",
          })}
          ${statCard({
            label: "Men qarzdorman",
            value: totals.payable,
            sub: "Muddati o'tgan qoldiq",
            tone: "violet",
          })}
          ${statCard({
            label: "Qarzlar soni",
            value: String(totals.count),
            raw: true,
            currency: false,
            sub: `${formatDate(data.as_of)} holatiga`,
          })}
        </div>

        <section class="card">
          <div class="card-head">
            <div>
              <div class="card-title">Muddati o'tgan qarzlar</div>
              <div class="card-sub">${formatDate(data.as_of)} holatiga</div>
            </div>
          </div>
          <div class="card-body flush">
            ${
              data.items.length
                ? `<div class="table-wrap">
                     <table class="table">
                       <thead>
                         <tr>
                           <th>Mijoz</th>
                           <th>Yo'nalish</th>
                           <th class="num">Summa</th>
                           <th class="num">Qoldiq</th>
                           <th>Muddat</th>
                           <th class="num">Kechikish</th>
                           <th></th>
                         </tr>
                       </thead>
                       <tbody>
                         ${data.items
                           .map(
                             (debt) => `
                           <tr>
                             <td>
                               <a class="row-link" href="#/debts/${debt.id}">${debt.contact_name}</a>
                               ${debt.reason ? `<span class="sub">${debt.reason}</span>` : ""}
                             </td>
                             <td>${directionBadge(debt.direction, debt.direction_display)}</td>
                             <td class="num">${formatMoney(debt.amount)}</td>
                             <td class="num strong">${formatMoney(debt.remaining)}</td>
                             <td class="nowrap">${formatDate(debt.due_date)}</td>
                             <td class="num money-red">${debt.days_overdue} kun</td>
                             <td class="table-actions">
                               <a class="btn btn-ghost btn-sm" href="#/debts/${debt.id}">Ochish</a>
                             </td>
                           </tr>`
                           )
                           .join("")}
                       </tbody>
                     </table>
                   </div>`
                : emptyState({
                    title: "Muddati o'tgan qarz yo'q",
                    text: "Barcha qarzlar muddati ichida.",
                    icon: "✓",
                  })
            }
          </div>
        </section>`;
    } catch (error) {
      if (isAlive(container)) renderError(body, error);
    }
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    load();
  });

  load();
}
