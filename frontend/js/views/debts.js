/**
 * Qarzlar ro'yxati: qidiruv, yo'nalish, holat va arxiv filtrlari.
 */

import { api } from "../api.js";
import { metaOptions } from "../state.js";
import { openDebtForm } from "../components/forms.js";
import {
  archivedBadge,
  debounce,
  directionBadge,
  emptyState,
  formatDate,
  formatMoney,
  isAlive,
  loadingBlock,
  options,
  pageHead,
  renderError,
  renderPager,
  statusBadge,
} from "../ui.js";

const PAGE_SIZE = 20;

export function renderDebts(container) {
  let page = 1;
  let search = "";
  let direction = "";
  let status = "";
  let archived = "false";
  let ordering = "-created_at";

  container.innerHTML = `
    ${pageHead({
      title: "Qarzlar",
      subtitle: "Barcha qarzlar va ularning joriy holati",
      actions: `<button type="button" class="btn btn-primary" id="new-debt">+ Yangi qarz</button>`,
    })}

    <section class="card">
      <div class="toolbar">
        <div class="search">
          <input id="debt-search" type="search" placeholder="Mijoz, sabab yoki izoh bo'yicha qidirish" autocomplete="off">
        </div>
        <div class="toolbar-group">
          <select class="filter-select" id="debt-direction" aria-label="Yo'nalish">
            ${options(metaOptions("debt_directions"), "", { placeholder: "Barcha yo'nalishlar" })}
          </select>
          <select class="filter-select" id="debt-status" aria-label="Holat">
            ${options(metaOptions("debt_statuses"), "", { placeholder: "Barcha holatlar" })}
          </select>
          <select class="filter-select" id="debt-archived" aria-label="Arxiv">
            <option value="false" selected>Faol</option>
            <option value="true">Arxivlangan</option>
            <option value="all">Barchasi</option>
          </select>
          <select class="filter-select" id="debt-ordering" aria-label="Tartiblash">
            <option value="-created_at">Eng yangi</option>
            <option value="created_at">Eng eski</option>
            <option value="due_date">Muddat (yaqin)</option>
            <option value="-due_date">Muddat (uzoq)</option>
            <option value="-amount">Summa (katta)</option>
            <option value="amount">Summa (kichik)</option>
          </select>
        </div>
      </div>
      <div id="debts-table">${loadingBlock()}</div>
      <div id="debts-pager"></div>
    </section>`;

  const tableWrap = container.querySelector("#debts-table");
  const pagerWrap = container.querySelector("#debts-pager");
  const searchInput = container.querySelector("#debt-search");

  async function load(targetPage = 1) {
    page = targetPage;
    tableWrap.innerHTML = loadingBlock();
    try {
      const data = await api.debts.list({
        page,
        page_size: PAGE_SIZE,
        search,
        direction,
        status,
        archived,
        ordering,
      });
      if (!isAlive(container)) return;

      const results = data.results || [];
      if (!results.length) {
        tableWrap.innerHTML = emptyState({
          title: "Qarzlar topilmadi",
          text:
            search || direction || status
              ? "Filtrlarni o'zgartirib ko'ring."
              : "Birinchi qarzni qo'shishdan boshlang.",
          icon: "📄",
          action: `<button type="button" class="btn btn-primary btn-sm" id="empty-add-debt">+ Qarz qo'shish</button>`,
        });
        const emptyButton = tableWrap.querySelector("#empty-add-debt");
        if (emptyButton) {
          emptyButton.addEventListener("click", () =>
            openDebtForm({ onSaved: () => load(1) })
          );
        }
      } else {
        tableWrap.innerHTML = `
          <div class="table-wrap">
            <table class="table">
              <thead>
                <tr>
                  <th>Mijoz</th>
                  <th>Yo'nalish</th>
                  <th class="num">Summa</th>
                  <th class="num">To'langan</th>
                  <th class="num">Qolgan</th>
                  <th>Holat</th>
                  <th>Muddat</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                ${results
                  .map(
                    (debt) => `
                  <tr>
                    <td>
                      <a class="row-link" href="#/debts/${debt.id}">${debt.contact_name}</a>
                      ${debt.reason ? `<span class="sub">${debt.reason}</span>` : ""}
                    </td>
                    <td>${directionBadge(debt.direction, debt.direction_display)}</td>
                    <td class="num">${formatMoney(debt.amount)}</td>
                    <td class="num">${formatMoney(debt.paid_total)}</td>
                    <td class="num strong">${formatMoney(debt.remaining)}</td>
                    <td>
                      ${statusBadge(debt.display_status)}
                      ${archivedBadge(debt)}
                    </td>
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

  container.querySelector("#new-debt").addEventListener("click", () => {
    openDebtForm({ onSaved: () => load(1) });
  });

  searchInput.addEventListener(
    "input",
    debounce(() => {
      search = searchInput.value.trim();
      load(1);
    }, 350)
  );

  container.querySelector("#debt-direction").addEventListener("change", (event) => {
    direction = event.target.value;
    load(1);
  });

  container.querySelector("#debt-status").addEventListener("change", (event) => {
    status = event.target.value;
    load(1);
  });

  container.querySelector("#debt-archived").addEventListener("change", (event) => {
    archived = event.target.value;
    load(1);
  });

  container.querySelector("#debt-ordering").addEventListener("change", (event) => {
    ordering = event.target.value;
    load(1);
  });

  load(1);
}
