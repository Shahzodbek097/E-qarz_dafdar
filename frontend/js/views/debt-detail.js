/**
 * Bitta qarz sahifasi: hisob-kitob, ma'lumotlar va to'lovlar tarixi.
 *
 * To'lovni tahrirlash yo'q — faqat bekor qilish (reversal) mavjud.
 * Bu moliyaviy tarixning o'zgarmasligini ta'minlaydi.
 */

import { api } from "../api.js";
import {
  openDebtForm,
  openPaymentForm,
  openReverseForm,
} from "../components/forms.js";
import {
  archivedBadge,
  confirmDialog,
  directionBadge,
  emptyState,
  formatDate,
  formatDateTime,
  formatMoney,
  isAlive,
  loadingBlock,
  methodLabel,
  renderError,
  reverseBadge,
  statCard,
  statusBadge,
  toast,
} from "../ui.js";
import { navigate } from "../router.js";

function paymentsTable(payments) {
  if (!payments.length) {
    return emptyState({
      title: "To'lovlar yo'q",
      text: "Bu qarz bo'yicha hali to'lov kiritilmagan.",
      icon: "₽",
    });
  }

  return `<div class="table-wrap">
    <table class="table">
      <thead>
        <tr>
          <th>Sana</th>
          <th class="num">Summa</th>
          <th>Turi</th>
          <th>Izoh</th>
          <th>Holat</th>
          <th>Kim</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        ${payments
          .map(
            (payment) => `
          <tr>
            <td class="nowrap">${formatDate(payment.payment_date)}</td>
            <td class="num strong">${formatMoney(payment.amount)}</td>
            <td>${methodLabel(payment.method)}</td>
            <td>${payment.note || "—"}</td>
            <td>
              ${reverseBadge(payment)}
              ${
                payment.is_reversed && payment.reversal_reason
                  ? `<span class="sub">Sabab: ${payment.reversal_reason}</span>`
                  : ""
              }
            </td>
            <td class="nowrap">${payment.created_by || "—"}</td>
            <td class="table-actions">
              ${
                payment.is_reversed
                  ? ""
                  : `<button type="button" class="btn btn-danger-soft btn-sm" data-reverse="${payment.id}">Bekor qilish</button>`
              }
            </td>
          </tr>`
          )
          .join("")}
      </tbody>
    </table>
  </div>`;
}

export async function renderDebtDetail(container, params) {
  const debtId = params.id;

  container.innerHTML = `
    <a class="back-link" href="#/debts">← Qarzlar ro'yxati</a>
    <div id="debt-detail">${loadingBlock()}</div>`;

  const body = container.querySelector("#debt-detail");

  async function load() {
    body.innerHTML = loadingBlock();
    try {
      const [debt, payments] = await Promise.all([
        api.debts.get(debtId),
        api.debts.payments(debtId, { page_size: 100 }),
      ]);
      if (!isAlive(container)) return;

      const paymentList = payments.results || [];
      const canPay = debt.status !== "paid";

      body.innerHTML = `
        <div class="detail-head">
          <div>
            <div class="detail-title">
              <h1>
                <a href="#/contacts/${debt.contact}" style="color:inherit">${debt.contact_name}</a>
              </h1>
              ${statusBadge(debt.display_status)}
              ${archivedBadge(debt)}
            </div>
            <div class="badge-row">
              ${directionBadge(debt.direction, debt.direction_display)}
              <span class="muted">Qarz №${debt.id}</span>
            </div>
          </div>
          <div class="detail-actions">
            <button type="button" class="btn btn-ghost" id="edit-debt">Tahrirlash</button>
            ${
              canPay
                ? `<button type="button" class="btn btn-primary" id="add-payment">+ To'lov</button>`
                : ""
            }
            <button type="button" class="btn btn-ghost" id="archive-debt">
              ${debt.is_archived ? "Arxivdan qaytarish" : "Arxivlash"}
            </button>
            ${
              debt.has_payments
                ? ""
                : `<button type="button" class="btn btn-danger-soft" id="delete-debt">O'chirish</button>`
            }
          </div>
        </div>

        ${
          debt.is_overdue
            ? `<div class="alert alert-warning" style="margin-bottom:18px">
                 Muddat ${debt.days_overdue} kun oldin o'tgan. Qoldiq:
                 <strong>${formatMoney(debt.remaining, { currency: true })}</strong>.
               </div>`
            : ""
        }

        <div class="stat-grid" style="grid-template-columns:repeat(3,minmax(0,1fr))">
          ${statCard({
            label: "Qarz summasi",
            value: debt.amount,
            sub: `Qarz sanasi: ${formatDate(debt.issue_date)}`,
          })}
          ${statCard({
            label: "To'langan",
            value: debt.paid_total,
            sub: `${paymentList.filter((item) => !item.is_reversed).length} ta faol to'lov`,
            tone: "green",
          })}
          ${statCard({
            label: "Qoldiq",
            value: debt.remaining,
            sub: debt.due_date
              ? `Muddat: ${formatDate(debt.due_date)}`
              : "Muddat belgilanmagan",
            tone: debt.is_overdue ? "red" : "amber",
          })}
        </div>

        <div class="grid-2" style="margin-bottom:18px">
          <section class="card">
            <div class="card-head"><div class="card-title">Qarz ma'lumotlari</div></div>
            <div class="card-body">
              <dl class="info-grid">
                <div class="info-item">
                  <dt>Mijoz</dt>
                  <dd><a href="#/contacts/${debt.contact}">${debt.contact_name}</a></dd>
                </div>
                <div class="info-item">
                  <dt>Yo'nalish</dt>
                  <dd>${debt.direction_display}</dd>
                </div>
                <div class="info-item">
                  <dt>Qarz sanasi</dt>
                  <dd>${formatDate(debt.issue_date)}</dd>
                </div>
                <div class="info-item">
                  <dt>Qaytarish muddati</dt>
                  <dd>${formatDate(debt.due_date)}</dd>
                </div>
                <div class="info-item">
                  <dt>Sabab</dt>
                  <dd>${debt.reason || "—"}</dd>
                </div>
                <div class="info-item">
                  <dt>Yaratilgan</dt>
                  <dd>${formatDateTime(debt.created_at)}</dd>
                </div>
              </dl>
              ${
                debt.note
                  ? `<div class="divider"></div><div class="note-box">${debt.note}</div>`
                  : ""
              }
            </div>
          </section>

          <section class="card">
            <div class="card-head">
              <div class="card-title">Hisob-kitob</div>
            </div>
            <div class="card-body">
              <div class="list">
                <div class="list-row" style="padding-left:0;padding-right:0">
                  <div class="list-main"><strong>Qarz summasi</strong></div>
                  <span class="list-value">${formatMoney(debt.amount)}</span>
                </div>
                <div class="list-row" style="padding-left:0;padding-right:0">
                  <div class="list-main"><strong>To'langan</strong></div>
                  <span class="list-value money-green">− ${formatMoney(
                    debt.paid_total
                  )}</span>
                </div>
                <div class="list-row" style="padding-left:0;padding-right:0">
                  <div class="list-main"><strong>Qoldiq</strong></div>
                  <span class="list-value">${formatMoney(debt.remaining)}</span>
                </div>
              </div>
              <div class="divider"></div>
              <p class="muted" style="font-size:12.5px">
                Holat va qoldiq to'lovlar tarixidan avtomatik hisoblanadi.
                To'lovni o'chirish mumkin emas — faqat bekor qilish.
              </p>
            </div>
          </section>
        </div>

        <section class="card">
          <div class="card-head">
            <div>
              <div class="card-title">To'lovlar tarixi</div>
              <div class="card-sub">${payments.count} ta yozuv</div>
            </div>
            ${
              canPay
                ? `<button type="button" class="btn btn-ghost btn-sm" id="add-payment-2">+ To'lov</button>`
                : ""
            }
          </div>
          <div class="card-body flush">${paymentsTable(paymentList)}</div>
        </section>`;

      const openPayment = () => openPaymentForm({ debt, onSaved: load });

      body.querySelector("#edit-debt").addEventListener("click", () => {
        openDebtForm({ debt, onSaved: load });
      });

      const addPaymentButton = body.querySelector("#add-payment");
      if (addPaymentButton) addPaymentButton.addEventListener("click", openPayment);

      const addPaymentButton2 = body.querySelector("#add-payment-2");
      if (addPaymentButton2) addPaymentButton2.addEventListener("click", openPayment);

      body.querySelector("#archive-debt").addEventListener("click", async () => {
        const action = debt.is_archived ? "arxivdan qaytarmoqchimisiz" : "arxivlamoqchimisiz";
        const confirmed = await confirmDialog({
          title: debt.is_archived ? "Arxivdan qaytarish" : "Qarzni arxivlash",
          message: `Bu qarzni ${action}?`,
          confirmText: debt.is_archived ? "Qaytarish" : "Arxivlash",
          danger: false,
        });
        if (!confirmed) return;

        try {
          if (debt.is_archived) {
            await api.debts.unarchive(debt.id);
            toast("Qarz arxivdan qaytarildi.");
          } else {
            await api.debts.archive(debt.id);
            toast("Qarz arxivlandi.");
          }
          load();
        } catch (error) {
          toast(error.message || "Amalni bajarib bo'lmadi.", "error");
        }
      });

      const deleteButton = body.querySelector("#delete-debt");
      if (deleteButton) {
        deleteButton.addEventListener("click", async () => {
          const confirmed = await confirmDialog({
            title: "Qarzni o'chirish",
            message:
              "Bu qarz butunlay o'chiriladi. Bu amalni qaytarib bo'lmaydi. Davom etasizmi?",
            confirmText: "O'chirish",
            danger: true,
          });
          if (!confirmed) return;

          try {
            await api.debts.remove(debt.id);
            toast("Qarz o'chirildi.");
            navigate("/debts");
          } catch (error) {
            toast(error.message || "Qarzni o'chirib bo'lmadi.", "error");
          }
        });
      }

      body.querySelectorAll("[data-reverse]").forEach((button) => {
        button.addEventListener("click", () => {
          const payment = paymentList.find(
            (item) => String(item.id) === button.dataset.reverse
          );
          if (!payment) return;
          openReverseForm({ payment, onSaved: load });
        });
      });
    } catch (error) {
      if (isAlive(container)) renderError(body, error);
    }
  }

  await load();
}
