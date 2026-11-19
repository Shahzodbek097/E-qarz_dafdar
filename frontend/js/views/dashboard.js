/**
 * Boshqaruv paneli.
 *
 * Barcha raqamlar backendda hisoblanadi (`/reports/dashboard/`).
 * Frontend faqat formatlaydi.
 */

import { api } from "../api.js";
import {
  directionBadge,
  emptyState,
  formatDate,
  formatMoney,
  isAlive,
  loadingBlock,
  methodLabel,
  pageHead,
  renderError,
  statCard,
  statusBadge,
  todayISO,
} from "../ui.js";

function topDebtorsCard(items) {
  if (!items || !items.length) {
    return emptyState({
      title: "Qarzdorlar yo'q",
      text: "Hozircha qoldig'i bor \"menga qarzdor\" yozuvi topilmadi.",
      icon: "✓",
    });
  }

  return `<div class="list">${items
    .map(
      (item, index) => `
        <div class="list-row">
          <span class="list-rank">${index + 1}</span>
          <div class="list-main">
            <strong>
              <a href="#/contacts/${item.contact_id}">${item.name}</a>
            </strong>
            <small>${item.phone ? item.phone : "Telefon kiritilmagan"}</small>
          </div>
          <span class="list-value">${formatMoney(item.remaining)}</span>
        </div>`
    )
    .join("")}</div>`;
}

function recentPaymentsCard(items) {
  if (!items || !items.length) {
    return emptyState({
      title: "To'lovlar yo'q",
      text: "Birinchi to'lovni qarz sahifasidan qo'shishingiz mumkin.",
      icon: "₽",
    });
  }

  return `<div class="list">${items
    .map(
      (payment) => `
        <div class="list-row">
          <div class="list-main">
            <strong>
              <a href="#/debts/${payment.debt}">${payment.debt_contact_name}</a>
            </strong>
            <small>${formatDate(payment.payment_date)} · ${methodLabel(
        payment.method
      )}</small>
          </div>
          <span class="list-value money-green">+${formatMoney(payment.amount)}</span>
        </div>`
    )
    .join("")}</div>`;
}

function recentDebtsTable(items) {
  if (!items || !items.length) {
    return emptyState({
      title: "Qarzlar yo'q",
      text: "Yangi qarz qo'shish uchun \"Qarzlar\" bo'limiga o'ting.",
      icon: "＋",
      action: '<a class="btn btn-primary btn-sm" href="#/debts">Qarzlar bo\'limi</a>',
    });
  }

  return `<div class="table-wrap">
    <table class="table">
      <thead>
        <tr>
          <th>Mijoz</th>
          <th>Yo'nalish</th>
          <th class="num">Summa</th>
          <th class="num">Qoldiq</th>
          <th>Holat</th>
          <th>Muddat</th>
        </tr>
      </thead>
      <tbody>
        ${items
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
            <td>${statusBadge(debt.display_status)}</td>
            <td class="nowrap">${formatDate(debt.due_date)}</td>
          </tr>`
          )
          .join("")}
      </tbody>
    </table>
  </div>`;
}

export async function renderDashboard(container) {
  container.innerHTML = `
    ${pageHead({
      title: "Boshqaruv paneli",
      subtitle: `Bugun ${formatDate(todayISO())}`,
      actions: `
        <a class="btn btn-ghost" href="#/reports/debts">Hisobotlar</a>
        <a class="btn btn-primary" href="#/debts">Qarzlar</a>`,
    })}
    <div id="dashboard-body">${loadingBlock("Ko'rsatkichlar yuklanmoqda…")}</div>`;

  const body = container.querySelector("#dashboard-body");

  try {
    const data = await api.reports.dashboard();
    if (!isAlive(container)) return;

    const totals = data.totals;

    body.innerHTML = `
      <div class="stat-grid">
        ${statCard({
          label: "Menga qarzdor",
          value: totals.receivable,
          sub: "Qaytarilishi kerak bo'lgan qoldiq",
          tone: "green",
        })}
        ${statCard({
          label: "Men qarzdorman",
          value: totals.payable,
          sub: "Boshqalarga to'lanishi kerak",
          tone: "violet",
        })}
        ${statCard({
          label: "Muddati o'tgan",
          value: totals.overdue_receivable,
          sub: `Men qarzdorman: ${formatMoney(totals.overdue_payable, {
            currency: true,
          })}`,
          tone: "red",
        })}
        ${statCard({
          label: "Jami to'langan",
          value: totals.paid_total,
          sub: `Faol qarzlar: ${totals.active_debts_count} ta · Muddati o'tgan: ${totals.overdue_count} ta`,
          tone: "amber",
        })}
      </div>

      <div class="grid-2" style="margin-bottom:18px">
        <section class="card">
          <div class="card-head">
            <div>
              <div class="card-title">Eng katta qarzdorlar</div>
              <div class="card-sub">Qoldiq bo'yicha top 5 mijoz</div>
            </div>
            <a class="btn btn-ghost btn-sm" href="#/contacts">Mijozlar</a>
          </div>
          <div class="card-body flush">${topDebtorsCard(data.top_debtors)}</div>
        </section>

        <section class="card">
          <div class="card-head">
            <div>
              <div class="card-title">So'nggi to'lovlar</div>
              <div class="card-sub">Bekor qilinmagan to'lovlar</div>
            </div>
            <a class="btn btn-ghost btn-sm" href="#/payments">Barchasi</a>
          </div>
          <div class="card-body flush">${recentPaymentsCard(data.recent_payments)}</div>
        </section>
      </div>

      <section class="card">
        <div class="card-head">
          <div>
            <div class="card-title">So'nggi qarzlar</div>
            <div class="card-sub">Oxirgi qo'shilgan 5 ta yozuv</div>
          </div>
          <a class="btn btn-ghost btn-sm" href="#/debts">Barcha qarzlar</a>
        </div>
        <div class="card-body flush">${recentDebtsTable(data.recent_debts)}</div>
      </section>`;
  } catch (error) {
    if (isAlive(container)) renderError(body, error);
  }
}
