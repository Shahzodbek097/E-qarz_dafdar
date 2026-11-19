# E-QarzDaftar

Qog‘oz daftar orqali yuritiladigan qarz va hisob-kitoblarni elektron shaklga
o‘tkazuvchi web-ilova. Kichik bizneslar — do‘konlar, xizmat ko‘rsatish
markazlari, avtoservislar, o‘quv markazlari va boshqalar uchun universal
qarz/to‘lov tizimi.

> **Loyiha holati:** 1-bosqich (Django asosi va ma’lumotlar modeli) yakunlandi.
> REST API, testlar va frontend keyingi bosqichlarda qo‘shiladi.

---

## 1. Texnologiyalar

| Qism | Texnologiya |
|---|---|
| Backend | Python 3.11.9, Django 5.2 LTS |
| API | Django REST Framework 3.18 |
| Baza | SQLite (loyiha boshlanishida) |
| Autentifikatsiya | Django Session + CSRF (reja bo‘yicha) |
| Frontend | HTML, CSS, sof JavaScript (keyingi bosqich) |
| Test | Django `TestCase`, DRF `APITestCase` |

Qo‘shimcha uchinchi tomon paketlari ishlatilmaydi: React/Vue, Bootstrap,
PostgreSQL, Docker, Redis, Celery, JWT, `django-filter`, Swagger — yo‘q.

---

## 2. Tez boshlash (Windows PowerShell)

```powershell
cd D:\NewProject\E-qarz_dafdar

# 1) Virtual muhit (bir marta)
py -3 -m venv .venv

# 2) Kutubxonalar
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 3) Migratsiyalar
.\.venv\Scripts\python.exe manage.py migrate

# 4) Serverni ishga tushirish
.\.venv\Scripts\python.exe manage.py runserver
```

Virtual muhitni faollashtirish (ixtiyoriy):

```powershell
.\.venv\Scripts\Activate.ps1
```

Agar PowerShell script bajarishni taqiqlasa, yuqoridagi kabi to‘g‘ridan-to‘g‘ri
`.\.venv\Scripts\python.exe` dan foydalaning.

### Tekshirish

| Manzil | Natija |
|---|---|
| http://127.0.0.1:8000/health/ | `{"status": "ok", "service": "E-QarzDaftar"}` |
| http://127.0.0.1:8000/admin/ | Admin panel login sahifasi |

---

## 3. Admin panel (faqat local dev)

Boshlang‘ich tekshiruv uchun yaratilgan foydalanuvchi:

```text
login:    admin
parol:    Admin12345!
```

> Bu parol faqat local ishlab chiqish uchun. Production’ga chiqarishdan oldin
> albatta almashtiring:
>
> ```powershell
> .\.venv\Scripts\python.exe manage.py changepassword admin
> ```

Yangi admin yaratish:

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

---

## 4. Testlar

Hozircha testlar 4-bosqichda yoziladi. Buyruq allaqachon ishlaydi:

```powershell
.\.venv\Scripts\python.exe manage.py test
```

Kutilgan natija (hozir): `Ran 0 tests ... OK`.

---

## 5. Papka tuzilishi

```text
E-qarz_dafdar/
├── .venv/                     # Virtual muhit (git'ga kirmaydi)
├── .gitignore
├── LICENSE
├── README.md
├── manage.py
├── requirements.txt
├── db.sqlite3                 # Local baza (git'ga kirmaydi)
├── config/                    # Django loyiha sozlamalari
│   ├── settings.py
│   ├── urls.py
│   ├── views.py               # /health/
│   ├── wsgi.py
│   └── asgi.py
└── apps/
    ├── accounts/              # User modeli
    ├── businesses/            # Business profili, faoliyat sohalari
    ├── contacts/              # Mijozlar va hamkorlar
    ├── debts/                 # Debt, Payment va moliyaviy mantiq
    ├── reports/               # Dashboard/hisobot service'lari (keyingi bosqich)
    ├── api/                   # REST API qatlami (keyingi bosqich)
    └── web/                   # Frontend HTML'larini berish (keyingi bosqich)
```

`frontend/` papkasi 5-bosqichda alohida yaratiladi va faqat REST API orqali
ishlaydi.

---

## 6. Ma’lumotlar modeli

### `accounts.User`

Django’ning `AbstractUser` modelidan meros oladi. Qo‘shimcha:

- `phone` — unikal, `+998XXXXXXXXX` formatida;
- `email` — case-insensitive unikal;
- `first_name`, `last_name` — majburiy.

### `businesses.Business`

- `owner` — `User` bilan `OneToOne` (bitta foydalanuvchi — bitta biznes);
- `name`, `industry`, `phone`;
- faoliyat sohalari: chakana savdo, kiyim-kechak, oziq-ovqat, xizmatlar,
  avtoservis, qurilish materiallari, o‘quv markazi, boshqa.

### `contacts.Contact`

- `business` — qaysi biznesga tegishli;
- `name`, `phone`, `address`, `type` (`customer` / `supplier` / `other`), `note`;
- `(business, name)` va `(business, phone)` bo‘yicha indekslar.

### `debts.Debt`

- `business`, `contact`;
- `direction` — `receivable` (“Menga qarzdor”) yoki `payable` (“Men qarzdorman”);
- `amount` — `Decimal(14, 2)`, faqat `> 0`;
- `issue_date`, `due_date` (ixtiyoriy), `reason`, `note`;
- `is_archived` — to‘lovi bor qarzni o‘chirish o‘rniga arxivlash;
- `created_by` — audit uchun.

### `debts.Payment`

- `debt`, `amount` (`Decimal`, `> 0`), `payment_date`, `method`, `note`;
- `created_by`, `created_at`;
- bekor qilish: `is_reversed`, `reversed_at`, `reversal_reason`, `reversed_by`.

---

## 7. Muhim biznes qoidalari

1. **Qoldiq bazada saqlanmaydi.**
   `remaining = amount - SUM(active payments)`. Bu hisob keyingi bosqichda
   `apps/debts/services.py` da yagona joyda yoziladi.
2. **To‘lovlar hech qachon hard delete qilinmaydi.**
   Xato to‘lov `is_reversed=True` + sabab bilan bekor qilinadi.
3. **Moliyaviy tarix himoyalangan.**
   - qarzi bor mijozni o‘chirish — `PROTECT`;
   - to‘lovi bor qarzni o‘chirish — `PROTECT`.
4. **Pul faqat `Decimal`.**
   `float` ishlatilmaydi. API’da summalar string ko‘rinishida qaytadi.
5. **Har bir so‘rov biznes bo‘yicha cheklanadi.**
   API qatlamida `request.user.business` ishlatiladi; frontend yuborgan
   `business_id` ga ishonilmaydi.

---

## 8. Muhit o‘zgaruvchilari

| O‘zgaruvchi | Default | Vazifasi |
|---|---|---|
| `DJANGO_SECRET_KEY` | dev kalit | Production’da majburiy |
| `DJANGO_DEBUG` | `1` | `0` qilinsa debug o‘chadi |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Vergul bilan ajratiladi |

PowerShell misoli:

```powershell
$env:DJANGO_DEBUG = "0"
$env:DJANGO_SECRET_KEY = "uzun-va-tasodifiy-kalit"
$env:DJANGO_ALLOWED_HOSTS = "example.com,www.example.com"
```

---

## 9. Keyingi bosqichlar

- [x] **1-bosqich** — Django asosi, modellar, migratsiyalar, admin.
- [ ] **2-bosqich** — qarz qoldig‘i, holat, atomar to‘lov, dashboard/hisobot service’lari.
- [ ] **3-bosqich** — `/api/v1/` REST API, session auth, CSRF, filtrlash.
- [ ] **4-bosqich** — Django/DRF testlari (15 ta majburiy holat).
- [ ] **5-bosqich** — alohida `frontend/` papkasi (HTML/CSS/Vanilla JS).
- [ ] **6-bosqich** — integratsiya, responsive tekshiruv, to‘liq README.

---

## 10. Litsenziya

MIT License — `LICENSE` fayliga qarang.
