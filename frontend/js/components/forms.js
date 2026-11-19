/**
 * Qayta ishlatiladigan formalar (modal oynalar).
 *
 * Har bir forma API'ga yuboradi va muvaffaqiyatli saqlangandan keyin
 * `onSaved` callback'ni chaqiradi. Xatolar maydon ostida ko'rsatiladi.
 */

import { api } from "../api.js";
import { metaOptions } from "../state.js";
import {
  clearFormErrors,
  esc,
  formatMoney,
  openModal,
  options,
  renderFieldErrors,
  serializeForm,
  setButtonLoading,
  todayISO,
  toast,
} from "../ui.js";

/* --------------------------------------------------------------------------
   Umumiy yordamchilar
   -------------------------------------------------------------------------- */

function ensureErrorBox(form) {
  let box = form.querySelector("[data-form-error]");
  if (!box) {
    box = document.createElement("div");
    box.className = "form-error";
    box.setAttribute("data-form-error", "");
    form.prepend(box);
  }
  return box;
}

function showFormError(form, error) {
  const fields = (error && error.fields) || {};
  renderFieldErrors(form, fields);

  const box = ensureErrorBox(form);
  const hasFieldMessage = Object.keys(fields).some(
    (key) => key !== "non_field_errors" && key !== "detail"
  );
  if (!hasFieldMessage) {
    box.hidden = false;
    box.textContent = (error && error.message) || "Saqlab bo'lmadi.";
  }
}

function bindSubmit(form, button, handler) {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearFormErrors(form);
    setButtonLoading(button, true);
    try {
      await handler();
    } catch (error) {
      showFormError(form, error);
    } finally {
      setButtonLoading(button, false);
    }
  });
}

function modalFooter(submitLabel, formId) {
  return `
    <button type="button" class="btn btn-ghost" data-modal-close>Bekor qilish</button>
    <button type="submit" form="${formId}" class="btn btn-primary" data-submit>${esc(
    submitLabel
  )}</button>`;
}

/* --------------------------------------------------------------------------
   Mijoz formasi
   -------------------------------------------------------------------------- */

export function openContactForm({ contact = null, onSaved = null } = {}) {
  const isEdit = Boolean(contact);
  const title = isEdit ? "Mijozni tahrirlash" : "Yangi mijoz";
  const contactTypes = metaOptions("contact_types");

  const body = `
    <form id="contact-form" novalidate>
      <div class="form-error" data-form-error hidden></div>
      <div class="field">
        <label for="contact-name">Nomi <span class="req">*</span></label>
        <input id="contact-name" name="name" maxlength="150" required
          value="${esc(contact ? contact.name : "")}" placeholder="Masalan: Ali Valiyev">
      </div>
      <div class="form-grid">
        <div class="field">
          <label for="contact-phone">Telefon</label>
          <input id="contact-phone" name="phone" maxlength="30"
            value="${esc(contact ? contact.phone : "")}" placeholder="+998 90 123 45 67">
        </div>
        <div class="field">
          <label for="contact-type">Turi</label>
          <select id="contact-type" name="type">
            ${options(contactTypes, contact ? contact.type : "customer")}
          </select>
        </div>
        <div class="field span-2">
          <label for="contact-address">Manzil</label>
          <input id="contact-address" name="address" maxlength="255"
            value="${esc(contact ? contact.address : "")}" placeholder="Shahar, tuman, ko'cha">
        </div>
        <div class="field span-2">
          <label for="contact-note">Izoh</label>
          <textarea id="contact-note" name="note" placeholder="Qo'shimcha ma'lumot">${esc(
            contact ? contact.note : ""
          )}</textarea>
        </div>
      </div>
    </form>`;

  const modal = openModal({
    title,
    body,
    footer: modalFooter(isEdit ? "Saqlash" : "Qo'shish", "contact-form"),
  });

  const form = modal.root.querySelector("#contact-form");
  const button = modal.footer.querySelector("[data-submit]");

  bindSubmit(form, button, async () => {
    const data = serializeForm(form);
    if (!data.name) {
      showFormError(form, {
        message: "Mijoz nomi majburiy.",
        fields: { name: ["Mijoz nomi majburiy."] },
      });
      return;
    }

    const payload = {
      name: data.name,
      phone: data.phone,
      address: data.address,
      type: data.type,
      note: data.note,
    };

    const saved = isEdit
      ? await api.contacts.update(contact.id, payload)
      : await api.contacts.create(payload);

    toast(isEdit ? "Mijoz yangilandi." : "Mijoz qo'shildi.");
    modal.close();
    if (onSaved) onSaved(saved);
  });
}

/* --------------------------------------------------------------------------
   Qarz formasi
   -------------------------------------------------------------------------- */

async function fetchContactsForSelect() {
  const response = await api.contacts.list({
    page_size: 100,
    ordering: "name",
  });
  return response.results || [];
}

export async function openDebtForm({
  debt = null,
  contactId = null,
  onSaved = null,
} = {}) {
  const isEdit = Boolean(debt);
  const locked = Boolean(debt && debt.has_payments);

  let contacts = [];
  try {
    contacts = await fetchContactsForSelect();
  } catch (error) {
    toast(error.message || "Mijozlar ro'yxatini yuklab bo'lmadi.", "error");
    return;
  }

  if (!contacts.length) {
    toast("Avval kamida bitta mijoz qo'shing.", "error");
    return;
  }

  const selectedContact = debt
    ? debt.contact
    : contactId || contacts[0].id;

  const contactOptions = contacts
    .map(
      (item) =>
        `<option value="${item.id}"${
          String(item.id) === String(selectedContact) ? " selected" : ""
        }>${esc(item.name)}</option>`
    )
    .join("");

  const issueDate = debt ? debt.issue_date : todayISO();
  const dueDate = debt && debt.due_date ? debt.due_date : "";

  const body = `
    <form id="debt-form" novalidate>
      <div class="form-error" data-form-error hidden></div>
      ${
        locked
          ? `<div class="alert alert-warning" style="margin-bottom:16px">
               Bu qarzda to'lovlar mavjud. Summa, yo'nalish va mijozni
               o'zgartirib bo'lmaydi. Muddat, sabab va izohni tahrirlash mumkin.
             </div>`
          : ""
      }
      <div class="form-grid">
        <div class="field span-2">
          <label for="debt-contact">Mijoz <span class="req">*</span></label>
          <select id="debt-contact" name="contact" ${locked ? "disabled" : ""}>
            ${contactOptions}
          </select>
        </div>
        <div class="field">
          <label for="debt-direction">Yo'nalish <span class="req">*</span></label>
          <select id="debt-direction" name="direction" ${locked ? "disabled" : ""}>
            ${options(
              metaOptions("debt_directions"),
              debt ? debt.direction : "receivable"
            )}
          </select>
        </div>
        <div class="field">
          <label for="debt-amount">Summa (so'm) <span class="req">*</span></label>
          <input id="debt-amount" name="amount" inputmode="decimal"
            value="${esc(debt ? debt.amount : "")}" placeholder="1000000.00"
            ${locked ? "disabled" : ""} required>
          <span class="hint">2 xonagacha: 1000000 yoki 1000000.50</span>
        </div>
        <div class="field">
          <label for="debt-issue-date">Qarz sanasi <span class="req">*</span></label>
          <input id="debt-issue-date" name="issue_date" type="date"
            value="${esc(issueDate)}" required>
        </div>
        <div class="field">
          <label for="debt-due-date">Qaytarish muddati</label>
          <input id="debt-due-date" name="due_date" type="date"
            value="${esc(dueDate)}">
          <span class="hint">Bo'sh qoldirilsa, muddat belgilanmaydi.</span>
        </div>
        <div class="field span-2">
          <label for="debt-reason">Sabab</label>
          <input id="debt-reason" name="reason" maxlength="255"
            value="${esc(debt ? debt.reason : "")}"
            placeholder="Masalan: tovar uchun qarz">
        </div>
        <div class="field span-2">
          <label for="debt-note">Izoh</label>
          <textarea id="debt-note" name="note">${esc(
            debt ? debt.note : ""
          )}</textarea>
        </div>
      </div>
    </form>`;

  const modal = openModal({
    title: isEdit ? "Qarzni tahrirlash" : "Yangi qarz",
    body,
    footer: modalFooter(isEdit ? "Saqlash" : "Qo'shish", "debt-form"),
    wide: true,
  });

  const form = modal.root.querySelector("#debt-form");
  const button = modal.footer.querySelector("[data-submit]");

  bindSubmit(form, button, async () => {
    const data = serializeForm(form);
    const amount = String(data.amount || "").trim();

    if (!/^\d+(\.\d{1,2})?$/.test(amount) || /^0+(\.0{1,2})?$/.test(amount)) {
      showFormError(form, {
        message: "Summa noldan katta son bo'lishi kerak (2 xonagacha).",
        fields: { amount: ["Summani to'g'ri kiriting."] },
      });
      return;
    }

    if (!data.issue_date) {
      showFormError(form, {
        message: "Qarz sanasini kiriting.",
        fields: { issue_date: ["Qarz sanasi majburiy."] },
      });
      return;
    }

    if (data.due_date && data.due_date < data.issue_date) {
      showFormError(form, {
        message: "Qaytarish muddati qarz sanasidan oldin bo'lishi mumkin emas.",
        fields: { due_date: ["Muddat qarz sanasidan oldin bo'lmasin."] },
      });
      return;
    }

    // Mijoz select'dan o'qiladi: foydalanuvchi ro'yxatdan boshqa mijozni
    // tanlashi mumkin. Locked holatda select disabled bo'ladi va
    // `serializeForm` uni tashlab ketadi — shuning uchun boshlang'ich
    // qiymatga qaytamiz.
    const contactValue = data.contact || String(selectedContact);

    const payload = {
      contact: Number(contactValue),
      issue_date: data.issue_date,
      due_date: data.due_date || null,
      reason: data.reason,
      note: data.note,
    };

    if (!locked) {
      payload.direction = data.direction;
      payload.amount = amount;
    }

    const saved = isEdit
      ? await api.debts.update(debt.id, payload)
      : await api.debts.create(payload);

    toast(isEdit ? "Qarz yangilandi." : "Qarz qo'shildi.");
    modal.close();
    if (onSaved) onSaved(saved);
  });
}

/* --------------------------------------------------------------------------
   To'lov formasi
   -------------------------------------------------------------------------- */

export function openPaymentForm({ debt, onSaved = null } = {}) {
  const body = `
    <form id="payment-form" novalidate>
      <div class="form-error" data-form-error hidden></div>
      <div class="alert alert-info" style="margin-bottom:16px">
        <strong>${esc(debt.contact_name)}</strong> · qoldiq:
        <strong>${formatMoney(debt.remaining, { currency: true })}</strong>
      </div>
      <div class="form-grid">
        <div class="field">
          <label for="payment-amount">Summa (so'm) <span class="req">*</span></label>
          <input id="payment-amount" name="amount" inputmode="decimal"
            placeholder="100000.00" required>
          <span class="hint">Qoldiqdan oshirib bo'lmaydi.</span>
        </div>
        <div class="field">
          <label for="payment-date">To'lov sanasi</label>
          <input id="payment-date" name="payment_date" type="date"
            value="${todayISO()}">
        </div>
        <div class="field">
          <label for="payment-method">To'lov turi</label>
          <select id="payment-method" name="method">
            ${options(metaOptions("payment_methods"), "cash")}
          </select>
        </div>
        <div class="field">
          <label for="payment-note">Izoh</label>
          <input id="payment-note" name="note" maxlength="255"
            placeholder="Masalan: naqd qabul qilindi">
        </div>
      </div>
    </form>`;

  const modal = openModal({
    title: "To'lov qo'shish",
    body,
    footer: modalFooter("To'lovni saqlash", "payment-form"),
  });

  const form = modal.root.querySelector("#payment-form");
  const button = modal.footer.querySelector("[data-submit]");

  bindSubmit(form, button, async () => {
    const data = serializeForm(form);
    const amount = String(data.amount || "").trim();

    if (!/^\d+(\.\d{1,2})?$/.test(amount) || /^0+(\.0{1,2})?$/.test(amount)) {
      showFormError(form, {
        message: "To'lov summasi noldan katta bo'lishi kerak.",
        fields: { amount: ["Summani to'g'ri kiriting."] },
      });
      return;
    }

    const payload = {
      amount,
      method: data.method,
      note: data.note,
    };
    if (data.payment_date) payload.payment_date = data.payment_date;

    const saved = await api.debts.addPayment(debt.id, payload);
    toast("To'lov qo'shildi.");
    modal.close();
    if (onSaved) onSaved(saved);
  });
}

/* --------------------------------------------------------------------------
   To'lovni bekor qilish
   -------------------------------------------------------------------------- */

export function openReverseForm({ payment, onSaved = null } = {}) {
  const body = `
    <form id="reverse-form" novalidate>
      <div class="form-error" data-form-error hidden></div>
      <div class="alert alert-warning" style="margin-bottom:16px">
        <strong>${formatMoney(payment.amount, { currency: true })}</strong>
        to'lovi bekor qilinadi. Yozuv o'chirilmaydi — tarixda sabab bilan
        saqlanadi va qarz qoldig'i qayta hisoblanadi.
      </div>
      <div class="field">
        <label for="reverse-reason">Bekor qilish sababi <span class="req">*</span></label>
        <textarea id="reverse-reason" name="reason" required
          placeholder="Masalan: xato summa kiritilgan"></textarea>
      </div>
    </form>`;

  const modal = openModal({
    title: "To'lovni bekor qilish",
    body,
    footer: `
      <button type="button" class="btn btn-ghost" data-modal-close>Yopish</button>
      <button type="submit" form="reverse-form" class="btn btn-danger" data-submit>
        Bekor qilish
      </button>`,
  });

  const form = modal.root.querySelector("#reverse-form");
  const button = modal.footer.querySelector("[data-submit]");

  bindSubmit(form, button, async () => {
    const data = serializeForm(form);
    if (!data.reason) {
      showFormError(form, {
        message: "Bekor qilish sababini kiritish majburiy.",
        fields: { reason: ["Sababni kiriting."] },
      });
      return;
    }

    const saved = await api.payments.reverse(payment.id, {
      reason: data.reason,
    });
    toast("To'lov bekor qilindi.");
    modal.close();
    if (onSaved) onSaved(saved);
  });
}
