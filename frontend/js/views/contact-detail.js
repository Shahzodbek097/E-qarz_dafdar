/**
 * Bitta mijoz sahifasi: profil, jamlanma va qarzlar tarixi.
 */

import { api } from "../api.js";
import { openContactForm, openDebtForm } from "../components/forms.js";
import {
  archivedBadge,
  contactTypeLabel,
  confirmDialog,
  directionBadge,
  emptyState,
  formatDate,
  formatMoney,
  isAlive,
  loadingBlock,
  renderError,
  statCard,
  statusBadge,
  toast,
} from "../ui.js";
import { navigate } from "../router.js";

function debtsTable(debts) {
  if (!debts.length) {
    return emptyState({
      title: "Qarzlar yo'q",
      text: "Bu mijoz uchun hali qarz kiritilmagan.",
      icon: "📄",
    });
  }

  return `<div class="table-wrap">
    <table class="table">
      <thead>
        <tr>
          <th>Yo'nalish</th>
          <th class="num">Summa</th>
          <th class="num">To'langan</th>
          <th class="num">Qolgan</th>
          <th>Holat</th>
          <th>Sana</th>
          <th>Muddat</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        ${debts
          .map(
            (debt) => `
          <tr>
            <td>
              ${directionBadge(debt.direction, debt.direction_display)}
              ${archivedBadge(debt)}
              ${debt.reason ? `<span class="sub">${debt.reason}</span>` : ""}
            </td>
            <td class="num">${formatMoney(debt.amount)}</td>
            <td class="num">${formatMoney(debt.paid_total)}</td>
            <td class="num strong">${formatMoney(debt.remaining)}</td>
            <td>${statusBadge(debt.display_status)}</td>
            <td class="nowrap">${formatDate(debt.issue_date)}</td>
            <td class="nowrap">${formatDate(debt.due_date)}</td>
            <td class="table-actions">
              <a class="btn btn-ghost btn-sm" href="#/debts/${debt.id}">Ochish</a>
            </td>
          </tr>`
          )
          .join("")}
      </tbody>
    </table>
  </div>`;
}

export async function renderContactDetail(container, params) {
  const contactId = params.id;
  let showArchived = false;

  container.innerHTML = `
    <a class="back-link" href="#/contacts">← Mijozlar ro'yxati</a>
    <div id="contact-detail">${loadingBlock()}</div>`;

  const body = container.querySelector("#contact-detail");

  async function load() {
    body.innerHTML = loadingBlock();
    try {
      const [contact, summary, debts] = await Promise.all([
        api.contacts.get(contactId),
        api.contacts.summary(contactId),
        api.debts.list({
          contact: contactId,
          archived: showArchived ? "all" : "false",
          page_size: 100,
          ordering: "-issue_date",
        }),
      ]);
      if (!isAlive(container)) return;

      const receivable = summary.receivable;
      const payable = summary.payable;

      body.innerHTML = `
        <div class="detail-head">
          <div>
            <div class="detail-title">
              <h1>${contact.name}</h1>
              <span class="badge badge-muted">${contactTypeLabel(contact.type)}</span>
            </div>
            <div class="badge-row">
              ${contact.phone ? `<span class="muted">${contact.phone}</span>` : ""}
              ${contact.address ? `<span class="muted">· ${contact.address}</span>` : ""}
            </div>
          </div>
          <div class="detail-actions">
            <button type="button" class="btn btn-ghost" id="edit-contact">Tahrirlash</button>
            <button type="button" class="btn btn-danger-soft" id="delete-contact">O'chirish</button>
            <button type="button" class="btn btn-primary" id="add-debt">+ Qarz qo'shish</button>
          </div>
        </div>

        <div class="stat-grid" style="grid-template-columns:repeat(2,minmax(0,1fr))">
          ${statCard({
            label: "Menga qarzdor",
            value: receivable.remaining,
            sub: `${receivable.count} ta qarz · jami ${formatMoney(
              receivable.total_amount,
              { currency: true }
            )}`,
            tone: "green",
          })}
          ${statCard({
            label: "Men qarzdorman",
            value: payable.remaining,
            sub: `${payable.count} ta qarz · jami ${formatMoney(
              payable.total_amount,
              { currency: true }
            )}`,
            tone: "violet",
          })}
        </div>

        <section class="card" style="margin-bottom:18px">
          <div class="card-head">
            <div>
              <div class="card-title">Qarzlar</div>
              <div class="card-sub">${debts.count} ta yozuv</div>
            </div>
            <label class="chip" style="cursor:pointer">
              <input type="checkbox" id="show-archived" ${
                showArchived ? "checked" : ""
              }>
              Arxivlanganlar
            </label>
          </div>
          <div class="card-body flush">${debtsTable(debts.results || [])}</div>
        </section>

        ${
          contact.note
            ? `<section class="card">
                 <div class="card-head"><div class="card-title">Izoh</div></div>
                 <div class="card-body"><div class="note-box">${contact.note}</div></div>
               </section>`
            : ""
        }`;

      body.querySelector("#edit-contact").addEventListener("click", () => {
        openContactForm({ contact, onSaved: load });
      });

      body.querySelector("#add-debt").addEventListener("click", () => {
        openDebtForm({ contactId: contact.id, onSaved: load });
      });

      body.querySelector("#delete-contact").addEventListener("click", async () => {
        const confirmed = await confirmDialog({
          title: "Mijozni o'chirish",
          message: `"${contact.name}" mijozini o'chirmoqchimisiz? Qarzlari bo'lsa, o'chirish mumkin emas.`,
          confirmText: "O'chirish",
          danger: true,
        });
        if (!confirmed) return;

        try {
          await api.contacts.remove(contact.id);
          toast("Mijoz o'chirildi.");
          navigate("/contacts");
        } catch (error) {
          toast(error.message || "Mijozni o'chirib bo'lmadi.", "error");
        }
      });

      body.querySelector("#show-archived").addEventListener("change", (event) => {
        showArchived = event.target.checked;
        load();
      });
    } catch (error) {
      if (isAlive(container)) renderError(body, error);
    }
  }

  await load();
}
