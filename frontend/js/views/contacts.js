/**
 * Mijozlar ro'yxati.
 *
 * Qidiruv, tur bo'yicha filtr va sahifalash. Har bir yozuv o'z tafsilot
 * sahifasiga olib boradi.
 */

import { api } from "../api.js";
import { metaOptions } from "../state.js";
import { openContactForm } from "../components/forms.js";
import {
  contactTypeLabel,
  debounce,
  emptyState,
  formatDate,
  isAlive,
  loadingBlock,
  options,
  pageHead,
  renderError,
  renderPager,
} from "../ui.js";

const PAGE_SIZE = 20;

export function renderContacts(container) {
  let page = 1;
  let search = "";
  let type = "";
  let ordering = "name";

  container.innerHTML = `
    ${pageHead({
      title: "Mijozlar",
      subtitle: "Qarzdorlar, mijozlar va ta'minotchilar ro'yxati",
      actions: `<button type="button" class="btn btn-primary" id="new-contact">+ Yangi mijoz</button>`,
    })}

    <section class="card">
      <div class="toolbar">
        <div class="search">
          <input id="contact-search" type="search" placeholder="Nomi yoki telefon bo'yicha qidirish" autocomplete="off">
        </div>
        <div class="toolbar-group">
          <select class="filter-select" id="contact-type" aria-label="Mijoz turi">
            ${options(metaOptions("contact_types"), "", { placeholder: "Barcha turlar" })}
          </select>
          <select class="filter-select" id="contact-ordering" aria-label="Tartiblash">
            <option value="name">Nomi (A–Z)</option>
            <option value="-name">Nomi (Z–A)</option>
            <option value="-created_at">Eng yangi</option>
            <option value="created_at">Eng eski</option>
          </select>
        </div>
      </div>
      <div id="contacts-table">${loadingBlock()}</div>
      <div id="contacts-pager"></div>
    </section>`;

  const tableWrap = container.querySelector("#contacts-table");
  const pagerWrap = container.querySelector("#contacts-pager");
  const searchInput = container.querySelector("#contact-search");
  const typeSelect = container.querySelector("#contact-type");
  const orderingSelect = container.querySelector("#contact-ordering");

  async function load(targetPage = 1) {
    page = targetPage;
    tableWrap.innerHTML = loadingBlock();
    try {
      const data = await api.contacts.list({
        page,
        page_size: PAGE_SIZE,
        search,
        type,
        ordering,
      });
      if (!isAlive(container)) return;

      const results = data.results || [];
      if (!results.length) {
        tableWrap.innerHTML = emptyState({
          title: search || type ? "Hech narsa topilmadi" : "Mijozlar yo'q",
          text:
            search || type
              ? "Qidiruv yoki filtrni o'zgartirib ko'ring."
              : "Birinchi mijozni qo'shishdan boshlang.",
          icon: "👥",
          action: `<button type="button" class="btn btn-primary btn-sm" id="empty-add-contact">+ Mijoz qo'shish</button>`,
        });
        const emptyButton = tableWrap.querySelector("#empty-add-contact");
        if (emptyButton) {
          emptyButton.addEventListener("click", () =>
            openContactForm({ onSaved: () => load(1) })
          );
        }
      } else {
        tableWrap.innerHTML = `
          <div class="table-wrap">
            <table class="table">
              <thead>
                <tr>
                  <th>Nomi</th>
                  <th>Telefon</th>
                  <th>Turi</th>
                  <th>Manzil</th>
                  <th>Qo'shilgan</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                ${results
                  .map(
                    (contact) => `
                  <tr>
                    <td>
                      <a class="row-link" href="#/contacts/${contact.id}">${contact.name}</a>
                      ${contact.note ? `<span class="sub">${contact.note}</span>` : ""}
                    </td>
                    <td class="nowrap">${contact.phone || "—"}</td>
                    <td><span class="badge badge-muted">${contactTypeLabel(
                      contact.type
                    )}</span></td>
                    <td>${contact.address || "—"}</td>
                    <td class="nowrap">${formatDate(contact.created_at)}</td>
                    <td class="table-actions">
                      <a class="btn btn-ghost btn-sm" href="#/contacts/${contact.id}">Ochish</a>
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

  container.querySelector("#new-contact").addEventListener("click", () => {
    openContactForm({ onSaved: () => load(1) });
  });

  searchInput.addEventListener(
    "input",
    debounce(() => {
      search = searchInput.value.trim();
      load(1);
    }, 350)
  );

  typeSelect.addEventListener("change", () => {
    type = typeSelect.value;
    load(1);
  });

  orderingSelect.addEventListener("change", () => {
    ordering = orderingSelect.value;
    load(1);
  });

  load(1);
}
