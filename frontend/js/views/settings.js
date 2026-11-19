/**
 * Sozlamalar: foydalanuvchi profili, biznes profili va sessiya.
 */

import { api, resetCsrf } from "../api.js";
import {
  clearSession,
  metaOptions,
  setSession,
  state,
} from "../state.js";
import {
  formatDateTime,
  options,
  pageHead,
  renderFieldErrors,
  serializeForm,
  setButtonLoading,
  toast,
} from "../ui.js";
import { navigate } from "../router.js";

function showFormError(form, error) {
  renderFieldErrors(form, (error && error.fields) || {});
  const box = form.querySelector("[data-form-error]");
  if (box && box.hidden) {
    box.hidden = false;
    box.textContent = (error && error.message) || "Saqlab bo'lmadi.";
  }
}

function notifySessionUpdate() {
  document.dispatchEvent(new CustomEvent("session-updated"));
}

export function renderSettings(container) {
  const user = state.user || {};
  const business = state.business || {};

  container.innerHTML = `
    ${pageHead({
      title: "Sozlamalar",
      subtitle: "Profil va biznes ma'lumotlarini boshqaring",
    })}

    <div class="grid-2" style="margin-bottom:18px">
      <section class="card">
        <div class="card-head">
          <div>
            <div class="card-title">Foydalanuvchi profili</div>
            <div class="card-sub">Login o'zgartirilmaydi</div>
          </div>
        </div>
        <div class="card-body">
          <form id="profile-form" novalidate>
            <div class="form-error" data-form-error hidden></div>
            <div class="field">
              <label for="profile-username">Login</label>
              <input id="profile-username" value="${user.username || ""}" disabled>
            </div>
            <div class="form-grid">
              <div class="field">
                <label for="profile-first">Ism</label>
                <input id="profile-first" name="first_name" maxlength="150"
                  value="${user.first_name || ""}" required>
              </div>
              <div class="field">
                <label for="profile-last">Familiya</label>
                <input id="profile-last" name="last_name" maxlength="150"
                  value="${user.last_name || ""}" required>
              </div>
              <div class="field span-2">
                <label for="profile-email">Elektron pochta</label>
                <input id="profile-email" name="email" type="email"
                  value="${user.email || ""}" required>
              </div>
              <div class="field span-2">
                <label for="profile-phone">Telefon</label>
                <input id="profile-phone" name="phone" maxlength="20"
                  value="${user.phone || ""}" placeholder="+998901234567" required>
              </div>
            </div>
            <div class="form-actions">
              <button type="submit" class="btn btn-primary" data-submit>Saqlash</button>
            </div>
          </form>
        </div>
      </section>

      <section class="card">
        <div class="card-head">
          <div>
            <div class="card-title">Biznes profili</div>
            <div class="card-sub">Hisobot va sarlavhalarda ko'rinadi</div>
          </div>
        </div>
        <div class="card-body">
          <form id="business-form" novalidate>
            <div class="form-error" data-form-error hidden></div>
            <div class="field">
              <label for="business-name">Biznes nomi</label>
              <input id="business-name" name="name" maxlength="150"
                value="${business.name || ""}" required>
            </div>
            <div class="field">
              <label for="business-industry">Faoliyat sohasi</label>
              <select id="business-industry" name="industry">
                ${options(metaOptions("industries"), business.industry || "other")}
              </select>
            </div>
            <div class="field">
              <label for="business-phone">Telefon</label>
              <input id="business-phone" name="phone" maxlength="20"
                value="${business.phone || ""}" placeholder="+998901234567" required>
            </div>
            <div class="form-actions">
              <button type="submit" class="btn btn-primary" data-submit>Saqlash</button>
            </div>
          </form>
        </div>
      </section>
    </div>

    <section class="card">
      <div class="card-head">
        <div>
          <div class="card-title">Sessiya</div>
          <div class="card-sub">Joriy hisob ma'lumotlari</div>
        </div>
      </div>
      <div class="card-body">
        <dl class="info-grid">
          <div class="info-item">
            <dt>Foydalanuvchi</dt>
            <dd>${user.full_name || user.username || "—"}</dd>
          </div>
          <div class="info-item">
            <dt>Login</dt>
            <dd>${user.username || "—"}</dd>
          </div>
          <div class="info-item">
            <dt>Ro'yxatdan o'tgan</dt>
            <dd>${formatDateTime(user.date_joined)}</dd>
          </div>
          <div class="info-item">
            <dt>Biznes</dt>
            <dd>${business.name || "—"}</dd>
          </div>
        </dl>
        <div class="divider"></div>
        <button type="button" class="btn btn-danger-soft" id="settings-logout">
          Tizimdan chiqish
        </button>
      </div>
    </section>`;

  const profileForm = container.querySelector("#profile-form");
  const businessForm = container.querySelector("#business-form");

  profileForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = profileForm.querySelector("[data-submit]");
    setButtonLoading(button, true);
    try {
      const data = serializeForm(profileForm);
      const payload = await api.auth.updateMe({
        first_name: data.first_name,
        last_name: data.last_name,
        email: data.email,
        phone: data.phone,
      });
      setSession(payload);
      notifySessionUpdate();
      toast("Profil saqlandi.");
    } catch (error) {
      showFormError(profileForm, error);
    } finally {
      setButtonLoading(button, false);
    }
  });

  businessForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = businessForm.querySelector("[data-submit]");
    setButtonLoading(button, true);
    try {
      const data = serializeForm(businessForm);
      const updated = await api.business.update({
        name: data.name,
        industry: data.industry,
        phone: data.phone,
      });
      state.business = updated;
      notifySessionUpdate();
      toast("Biznes profili saqlandi.");
    } catch (error) {
      showFormError(businessForm, error);
    } finally {
      setButtonLoading(button, false);
    }
  });

  container.querySelector("#settings-logout").addEventListener("click", async () => {
    try {
      await api.auth.logout();
    } catch (error) {
      // Sessiya allaqachon tugagan bo'lsa ham davom etamiz.
    }
    resetCsrf();
    clearSession();
    toast("Tizimdan chiqdingiz.", "info");
    navigate("/login");
  });
}
