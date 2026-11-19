/**
 * Kirish va ro'yxatdan o'tish sahifalari.
 *
 * Ro'yxatdan o'tish avtomatik login qilmaydi: backend ham shunday ishlaydi.
 * Foydalanuvchi paroli bilan qayta kiradi.
 */

import { api, resetCsrf } from "../api.js";
import { loadMeta, metaOptions, setSession } from "../state.js";
import {
  options,
  renderFieldErrors,
  setButtonLoading,
  toast,
} from "../ui.js";
import { navigate } from "../router.js";

function showFormError(form, error) {
  renderFieldErrors(form, (error && error.fields) || {});
  const box = form.querySelector("[data-form-error]");
  if (box && box.hidden) {
    box.hidden = false;
    box.textContent = (error && error.message) || "Amalni bajarib bo'lmadi.";
  }
}

function authShell({ active, card }) {
  return `
    <div class="auth-page">
      <section class="auth-brand">
        <a class="brand brand-lg" href="#/login">
          <span class="brand-mark">EQ</span>
          <span class="brand-text">
            <strong>E-QarzDaftar</strong>
            <small>qarz va to'lovlar daftari</small>
          </span>
        </a>

        <div>
          <h1>Qarzlar hisobini tartibga soling.</h1>
          <p class="lead" style="margin-top:14px">
            Mijozlar, qarzlar va to'lovlarni bitta joyda yuriting.
            Qoldiq va holat har doim to'lovlar tarixidan avtomatik hisoblanadi.
          </p>
        </div>

        <ul class="auth-points">
          <li>Har bir mijoz bo'yicha "menga qarzdor" va "men qarzdorman" alohida ko'rinadi.</li>
          <li>To'lovlar atomar saqlanadi — ortiqcha to'lov qabul qilinmaydi.</li>
          <li>Bekor qilingan to'lov o'chmaydi: sabab bilan tarixda qoladi.</li>
          <li>Ma'lumotlaringiz faqat sizning biznesingizga tegishli.</li>
        </ul>

        <div class="auth-note">
          Moliyaviy tarix hech qachon o'chirilmaydi. Xato to'lov "bekor qilish"
          orqali tuzatiladi — bu audit uchun ishonchli iz qoldiradi.
        </div>
      </section>

      <section class="auth-panel">
        <div class="auth-card">
          <div class="auth-tabs">
            <a class="auth-tab${active === "login" ? " active" : ""}" href="#/login">Kirish</a>
            <a class="auth-tab${active === "register" ? " active" : ""}" href="#/register">Ro'yxatdan o'tish</a>
          </div>
          ${card}
        </div>
      </section>
    </div>`;
}

export function renderLogin(container) {
  container.innerHTML = authShell({
    active: "login",
    card: `
      <h2>Xush kelibsiz</h2>
      <p class="muted">Hisobingizga kirib ishlashni davom ettiring.</p>
      <form id="login-form" novalidate>
        <div class="form-error" data-form-error hidden></div>
        <div class="field">
          <label for="login-username">Login</label>
          <input id="login-username" name="username" autocomplete="username"
            placeholder="username" required>
        </div>
        <div class="field">
          <label for="login-password">Parol</label>
          <input id="login-password" name="password" type="password"
            autocomplete="current-password" placeholder="••••••••" required>
        </div>
        <button class="btn btn-primary btn-block" type="submit" data-submit>
          Kirish
        </button>
      </form>
      <p class="auth-foot">
        Hisobingiz yo'qmi? <a href="#/register">Ro'yxatdan o'ting</a>
      </p>`,
  });

  const form = container.querySelector("#login-form");
  const button = form.querySelector("[data-submit]");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const username = form.username.value.trim();
    const password = form.password.value;

    if (!username || !password) {
      showFormError(form, {
        message: "Login va parolni kiriting.",
        fields: { non_field_errors: ["Login va parolni kiriting."] },
      });
      return;
    }

    setButtonLoading(button, true, "Kirilmoqda…");
    try {
      const data = await api.auth.login({ username, password });
      setSession(data);
      // Django login'dan keyin CSRF tokenini almashtiradi.
      resetCsrf();
      await loadMeta();
      toast(`Xush kelibsiz, ${data.user.full_name || data.user.username}!`);
      navigate("/dashboard");
    } catch (error) {
      showFormError(form, error);
    } finally {
      setButtonLoading(button, false);
    }
  });
}

export function renderRegister(container) {
  container.innerHTML = authShell({
    active: "register",
    card: `
      <h2>Ro'yxatdan o'tish</h2>
      <p class="muted">Biznesingiz uchun shaxsiy daftar yarating.</p>
      <form id="register-form" novalidate>
        <div class="form-error" data-form-error hidden></div>
        <div class="form-grid">
          <div class="field">
            <label for="reg-first">Ism</label>
            <input id="reg-first" name="first_name" maxlength="150" required>
          </div>
          <div class="field">
            <label for="reg-last">Familiya</label>
            <input id="reg-last" name="last_name" maxlength="150" required>
          </div>
          <div class="field">
            <label for="reg-username">Login</label>
            <input id="reg-username" name="username" maxlength="150"
              autocomplete="username" required>
          </div>
          <div class="field">
            <label for="reg-phone">Telefon</label>
            <input id="reg-phone" name="phone" maxlength="20"
              placeholder="+998901234567" required>
          </div>
          <div class="field span-2">
            <label for="reg-email">Elektron pochta</label>
            <input id="reg-email" name="email" type="email"
              autocomplete="email" required>
          </div>
          <div class="field">
            <label for="reg-business">Biznes nomi</label>
            <input id="reg-business" name="business_name" maxlength="150" required>
          </div>
          <div class="field">
            <label for="reg-industry">Faoliyat sohasi</label>
            <select id="reg-industry" name="industry">
              ${options(metaOptions("industries"), "retail")}
            </select>
          </div>
          <div class="field">
            <label for="reg-password">Parol</label>
            <input id="reg-password" name="password" type="password"
              minlength="8" autocomplete="new-password" required>
            <span class="hint">Kamida 8 belgi.</span>
          </div>
          <div class="field">
            <label for="reg-password2">Parolni tasdiqlang</label>
            <input id="reg-password2" name="password_confirm" type="password"
              minlength="8" autocomplete="new-password" required>
          </div>
        </div>
        <button class="btn btn-primary btn-block" type="submit" data-submit>
          Ro'yxatdan o'tish
        </button>
      </form>
      <p class="auth-foot">
        Hisobingiz bormi? <a href="#/login">Kirish</a>
      </p>`,
  });

  const form = container.querySelector("#register-form");
  const button = form.querySelector("[data-submit]");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = {};
    form.querySelectorAll("input[name], select[name]").forEach((input) => {
      data[input.name] = input.value.trim();
    });

    if (data.password !== data.password_confirm) {
      showFormError(form, {
        message: "Parollar mos kelmadi.",
        fields: { password_confirm: ["Parollar mos kelmadi."] },
      });
      return;
    }

    setButtonLoading(button, true, "Yaratilmoqda…");
    try {
      await api.auth.register(data);
      toast("Ro'yxatdan o'tdingiz. Endi login va parol bilan kiring.");
      navigate("/login");
    } catch (error) {
      showFormError(form, error);
    } finally {
      setButtonLoading(button, false);
    }
  });
}
