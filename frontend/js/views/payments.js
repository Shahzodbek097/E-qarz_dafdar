/**
 * To'lovlar ro'yxati.
 *
 * Bekor qilingan to'lovlar ham ko'rinadi — moliyaviy tarix o'chirilmaydi.
 */

import { api } from "../api.js";
import { metaOptions } from "../state.js";
import { openReverseForm } from "../components/forms.js";
import {
  emptyState,
  formatDate,
  formatMoney,
  isAlive,
  loadingBlock,
  methodLabel,
  options,
  pageHead,
  renderError,
  renderPager,
  reverseBadge,
} from "../ui.js";

const PAGE_SIZE = 20;

export function renderPayments(container) {
  let page = 1;
  let method = "";
  let isReversed = "";
  let dateFrom = "";
  let dateTo = "";
  let ordering = "-payment_date";

  container.innerHTML = `
    ${pageHead({
      title: "To'lovlar",
      subtitle: "Qabul qilingan va bekor qilingan to'lovlar tarixi",
    })}

    <section class="card">
      <div class="toolbar">
        <div class="toolbar-group">
          <select class="filter-select" id="payment-method" aria-label="To'lov turi">
            ${options(metaOptions("payment_methods"), "", { placeholder: "Barcha turlar" })}
          </select>
          <select class="filter-select" id="payment-status" aria-label="Holat">
            <option value="">Barchasi</option>
            <option value="false">Faol</option>
            <option value="true">Bekor qilingan</option>
          </select>
          <input class="filter-select" type="date" id="payment-from" aria-label="Boshlanish sanasi">
          <input class="filter-select" type="date" id="payment-to" aria-label="Tugash sanasi">
          <select class="filter-select" id="payment-ordering" aria-label="Tartiblash">
            <option value="-payment_date">Sana (yangi)</option>
            <option value="payment_date">Sana (eski)</option>
            <option value="-amount">Summa (katta)</option>
            <option value="amount">Summa (kichik)</option>
          </select>
        </div>
        <div class="spacer"></div>
        <button type="button" class="btn btn-ghost btn-sm" id="payment-reset">Tozalash</button>
      </div>
      <div id="payments-table">${loadingBlock()}</div>
      <div id="payments-pager"></div>
    </section>`;

  const tableWrap = container.querySelector("#payments-table");
  const pagerWrap = container.querySelector("#payments-pager");
  const methodSelect = container.querySelector("#payment-method");
  const statusSelect = container.querySelector("#payment-status");
  const fromInput = container.querySelector("#payment-from");
  const toInput = container.querySelector("#payment-to");
  const orderingSelect = container.querySelector("#payment-ordering");

  async function load(targetPage = 1) {
    page = targetPage;
    tableWrap.innerHTML = loadingBlock();
    try {
      const data = await api.payments.list({
        page,
        page_size: PAGE_SIZE,
        method,
        is_reversed: isReversed,
        date_from: dateFrom,
        date_to: dateTo,
        ordering,
      });
      if (!isAlive(container)) return;

      const results = data.results || [];
      if (!results.length) {
        tableWrap.innerHTML = emptyState({
          title: "To'lovlar topilmadi",
          text: "Filtr shartlariga mos to'lov yo'q.",
          icon: "₽",
        });
      } else {
        tableWrap.innerHTML = `
          <div class="table-wrap">
            <table class="table">
              <thead>
                <tr>
                  <th>Sana</th>
                  <th>Mijoz</th>
                  <th class="num">Summa</th>
                  <th>Turi</th>
                  <th>Holat</th>
                  <th>Izoh</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                ${results
                  .map(
                    (payment) => `
                  <tr>
                    <td class="nowrap">${formatDate(payment.payment_date)}</td>
                    <td>
                      <a class="row-link" href="#/debts/${payment.debt}">${payment.debt_contact_name}</a>
                    </td>
                    <td class="num strong">${formatMoney(payment.amount)}</td>
                    <td>${methodLabel(payment.method)}</td>
                    <td>
                      ${reverseBadge(payment)}
                      ${
                        payment.is_reversed && payment.reversal_reason
                          ? `<span class="sub">Sabab: ${payment.reversal_reason}</span>`
                          : ""
                      }
                    </td>
                    <td>${payment.note || "—"}</td>
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

        tableWrap.querySelectorAll("[data-reverse]").forEach((button) => {
          button.addEventListener("click", () => {
            const payment = results.find(
              (item) => String(item.id) === button.dataset.reverse
            );
            if (!payment) return;
            openReverseForm({ payment, onSaved: () => load(page) });
          });
        });
      }

      renderPager(pagerWrap, {
        count: data.count,
        page,
        pageSize: PAGE_SIZE,
        onPage: load,
      });
    } catch (error) {
      if (isAlive(container)) renderError(tableWrap, error);
    }
  }

  methodSelect.addEventListener("change", () => {
    method = methodSelect.value;
    load(1);
  });

  statusSelect.addEventListener("change", () => {
    isReversed = statusSelect.value;
    load(1);
  });

  fromInput.addEventListener("change", () => {
    dateFrom = fromInput.value;
    load(1);
  });

  toInput.addEventListener("change", () => {
    dateTo = toInput.value;
    load(1);
  });

  orderingSelect.addEventListener("change", () => {
    ordering = orderingSelect.value;
    load(1);
  });

  container.querySelector("#payment-reset").addEventListener("click", () => {
    method = "";
    isReversed = "";
    dateFrom = "";
    dateTo = "";
    ordering = "-payment_date";
    methodSelect.value = "";
    statusSelect.value = "";
    fromInput.value = "";
    toInput.value = "";
    orderingSelect.value = "-payment_date";
    load(1);
  });

  load(1);
}
