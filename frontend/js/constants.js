/**
 * Frontend konstantalari.
 *
 * Backend `GET /api/v1/meta/` orqali barcha tanlovlarni beradi. Bu yerdagi
 * qiymatlar faqat zaxira (fallback) uchun: meta yuklanmagan holatda ham
 * interfeys ishlashi kerak.
 */

export const DEFAULT_PAGE_SIZE = 20;
export const MAX_PAGE_SIZE = 100;

export const FALLBACK = {
  debt_directions: [
    { value: "receivable", label: "Menga qarzdor" },
    { value: "payable", label: "Men qarzdorman" },
  ],
  debt_statuses: [
    { value: "open", label: "Ochiq" },
    { value: "partial", label: "Qisman to'langan" },
    { value: "paid", label: "To'liq to'langan" },
    { value: "overdue", label: "Muddati o'tgan" },
  ],
  payment_methods: [
    { value: "cash", label: "Naqd" },
    { value: "bank", label: "Bank o'tkazmasi" },
    { value: "other", label: "Boshqa" },
  ],
  contact_types: [
    { value: "customer", label: "Mijoz" },
    { value: "supplier", label: "Ta'minotchi" },
    { value: "other", label: "Boshqa" },
  ],
  industries: [
    { value: "retail", label: "Chakana savdo" },
    { value: "clothing", label: "Kiyim-kechak" },
    { value: "food", label: "Oziq-ovqat" },
    { value: "services", label: "Xizmat ko'rsatish" },
    { value: "auto_service", label: "Avtoservis / ustaxona" },
    { value: "construction", label: "Qurilish materiallari" },
    { value: "education", label: "O'quv markazi" },
    { value: "other", label: "Boshqa" },
  ],
};

export const STATUS_LABELS = {
  open: "Ochiq",
  partial: "Qisman to'langan",
  paid: "To'liq to'langan",
  overdue: "Muddati o'tgan",
};

export const DIRECTION_LABELS = {
  receivable: "Menga qarzdor",
  payable: "Men qarzdorman",
};

export const METHOD_LABELS = {
  cash: "Naqd",
  bank: "Bank o'tkazmasi",
  other: "Boshqa",
};

export const CONTACT_TYPE_LABELS = {
  customer: "Mijoz",
  supplier: "Ta'minotchi",
  other: "Boshqa",
};

export const REPORT_TABS = [
  { href: "#/reports/debts", key: "debts", label: "Qarzlar" },
  { href: "#/reports/payments", key: "payments", label: "To'lovlar" },
  { href: "#/reports/overdue", key: "overdue", label: "Muddati o'tgan" },
];
