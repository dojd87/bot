# -*- coding: utf-8 -*-
"""
ALLO Consultation Assistant — Telegram-бот для консультантів АЛЛО.
Логіка: Allo onepager + стандарти обслуговування та сервісної діагностики (10.2026).

Запуск:
    pip install python-telegram-bot python-dotenv
    python bot.py

Налаштування (.env):
    TELEGRAM_BOT_TOKEN=ваш_токен_сюди
"""

import os
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
from telegram.request import HTTPXRequest

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
log = logging.getLogger("allo_bot")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CA_BUNDLE = os.getenv("CA_BUNDLE")
IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")

HOME = ("🏠 Головне меню", "menu")


def kb(rows):
    """rows: список рядків; кожен рядок — список кортежів (текст, callback)."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(t, callback_data=c) for t, c in row] for row in rows]
    )


# ─────────────────────────────────────────────────────────────
# ЕКРАНИ
# ─────────────────────────────────────────────────────────────
S = {}

# ── 1. GCP (ГОЛОВНЕ МЕНЮ) ────────────────────────────────────
S["menu"] = (
    "🛡️ <b>КРОК 1 — GCP</b>\n\n"
    "Привітайтеся <b>українською</b> та запитайте:\n\n"
    "💬 <i>«Підкажіть, будь ласка, Ви є повнолітнім споживачем нікотинової продукції?»</i>\n\n"
    "⚠️ Якщо відвідувач виглядає молодо — попросіть документ для підтвердження віку.",
    [
        [("✅ Так", "current"), ("❌ Ні", "gcp_no")],
        [("🔄 Інформація про Апгрейд", "upgrade")],
        [("🛠️ Сервісне обслуговування", "service")],
    ],
)
S["gcp"] = S["menu"]

S["gcp_no"] = (
    "⛔ <b>Презентацію НЕ проводимо</b>\n\n"
    "• Якщо повнолітній, але не курець і купує на подарунок — <b>тільки продаж</b>, без презентації.\n"
    "• Якщо неповнолітній — <b>припиняємо комунікацію</b>.",
    [[HOME]],
)

# ── 2. ПОТОЧНИЙ ДОСВІД ───────────────────────────────────────
S["current"] = (
    "🎯 <b>КРОК 2 — ПОТОЧНИЙ ДОСВІД</b>\n\n"
    "💬 <i>«Підкажіть, які нікотинові продукты Ви споживаєте зараз?»</i>\n\n"
    "Поставте 1–2 відкритих питання про потребу:\n"
    "• <i>«Що для вас важливо в процесі паління/використання?»</i>\n"
    "• <i>«Чули щось раніше про IQOS?»</i>\n\n"
    "Оберіть категорію клієнта:",
    [
        [("🟦 Користувач паучів", "cat_pouch")],
        [("🚬 Курець сигарет / 🔥 Систем конкурентів", "cat_cig_comp")],
        [("💨 Користувач вейпів", "cat_vape")],
        [("📱 Користувач нашими пристроями", "cat_our")],
        [("⬅️ Назад", "menu"), HOME],
    ],
)

# ── ПИТАННЯ МІКСИНГУ ДЛЯ СИГАРЕТ / КОНКУРЕНТІВ ───────────────
S["mix_pouch_q"] = (
    "🔄 <b>МІКСИНГ — ПАУЧІ</b>\n\n"
    "💬 <i>«Чи Ви міксуєте з нікотиновими паучами?»</i>",
    [
        [("✅ Так", "mix_p_yes"), ("❌ Ні", "mix_p_no")],
        [("⬅️ Назад", "current"), HOME],
    ],
)

S["mix_vape_q"] = (
    "🔄 <b>МІКСИНГ — ВЕЙПИ</b>\n\n"
    "💬 <i>«Чи Ви міксуєте з вейпами?»</i>",
    [
        [("✅ Так", "mix_v_yes"), ("❌ Ні", "mix_v_no")],
        [("⬅️ Назад", "mix_pouch_q"), HOME],
    ],
)

# ── ПИТАННЯ МІКСИНГУ ДЛЯ НАШИХ ПРИСТРОЇВ ─────────────────────
S["our_mix_q"] = (
    "🔄 <b>МІКСИНГ З ВЕЙПОМ</b>\n\n"
    "💬 <i>«Чи міксує клієнт з вейпом?»</i>",
    [
        [("✅ Так (міксує з вейпом)", "our_v_yes")],
        [("❌ Ні (не міксує з вейпом)", "our_v_no")],
        [("⬅️ Назад", "current"), HOME],
    ],
)

S["our_need_vape"] = (
    "🎯 <b>КРОК 1 — ЗАКРИВАЄМО ПОТРЕБУ СПОЖИВАЧА + LEVIA</b>\n\n"
    "• Закрийте поточну потребу споживача (сервіс, девайс, аксесуари).\n"
    "• <b>Оскільки міксує з вейпом — обов'язково пропонуємо LEVIA</b> (без тютюну).",
    [
        [("🟦 КРОК 2: Презентація категорії ZYN", "zyn")],
        [("🍃 Детальніше про LEVIA", "levia")],
        [HOME],
    ],
)

S["our_need_no_vape"] = (
    "🎯 <b>КРОК 1 — ЗАКРИВАЄМО ПОТРЕБУ СПОЖИВАЧА</b>\n\n"
    "• Закрийте поточну потребу споживача (підбір стіків, сервісне обслуговування, новий девайс).",
    [
        [("🟦 КРОК 2: Презентація категорії ZYN", "zyn")],
        [HOME],
    ],
)

# ── ZYN ───────────────────────────────────────────────────────
S["zyn"] = (
    "🟦 <b>ПРЕЗЕНТАЦІЯ КАТЕГОРІЇ ZYN</b>\n\n"
    "<b>Презентація категорії:</b>\n"
    "• ZYN у двох форматах:\n"
    "   — <b>Slim</b> — вологі та більш інтенсивні\n"
    "   — <b>Mini Dry</b> — сухі та більш м'які\n"
    "• Розміщуються під губою, нікотин без диму і запаху — можна використовувати всюди\n\n"
    "<b>Рекомендації використання:</b>\n"
    "• Пауч під верхню губу на ясна, можливе пощипування — так виділяється нікотин\n"
    "• Тримати за відчуттями, але <b>не більше 30 хвилин</b>\n"
    "• Не жувати, не смоктати, не ковтати | Тільки <b>одна</b> подушечка за раз",
    [
        [("💪 Підібрати міцність ZYN", "zyn_str")],
        [("🔥 Перейти до систем нагрівання (ILUMA/Bonds)", "heat_cat")],
        [("✅ Завершити (тільки ZYN)", "finish")],
        [HOME],
    ],
)

S["zyn_str"] = (
    "💪 <b>Підбір міцності ZYN</b>\n\n"
    "💬 <i>«Якої міцності паучі Ви вживали? Пам'ятаєте міцність, яка Вам підходила?»</i>",
    [
        [("Не пам'ятає / не користувався", "zyn_3")],
        [("Нижче 6 мг були ок", "zyn_3")],
        [("6 мг були ок", "zyn_6")],
        [("Більше 6 мг були ок", "zyn_slim")],
        [("⬅️ Назад", "zyn"), HOME],
    ],
)

_zyn_next = [
    [("🔥 Перейти до систем нагрівання (ILUMA/Bonds)", "heat_cat")],
    [("✅ Завершити (тільки ZYN)", "finish")],
    [("⬅️ Назад", "zyn_str"), HOME],
]
S["zyn_3"] = ("✅ Рекомендуйте: <b>ZYN Mini 3 мг</b> (Cool Mint, Spearmint, Black Cherry).", _zyn_next)
S["zyn_6"] = ("✅ Рекомендуйте: <b>ZYN Mini 6 мг</b> (Cool Mint, Spearmint, Black Cherry).", _zyn_next)
S["zyn_slim"] = ("✅ Підберіть <b>ZYN Slim</b> (9 мг, 11 мг, 13.5 мг або 16.5 мг).", _zyn_next)

# ── КАТЕГОРІЯ НАГРІВАННЯ (ПЕРЕВАГА) ───────────────────────────
S["heat_cat"] = (
    "🔥 <b>КАТЕГОРІЯ НАГРІВАННЯ ТЮТЮНУ — ПЕРЕВАГА</b>\n\n"
    "Обов'язково наголосіть клієнту на <b>головній перевазі</b> систем IQOS ILUMA та BONDS 2:\n\n"
    "✅ <b>НЕМАЄ ЗАПАХУ, ДИМУ ТА ПОПЕЛУ</b>\n\n"
    "💬 <i>«На відміну від сигарет, ці системи <b>нагрівають тютюн, а не спалюють його</b>. "
    "Тому вони не виділяють диму, немає попелу та залишають значно менше стійкого запаху "
    "на руках, волоссі й одязі.»</i>\n\n"
    "📌 Використовуйте поточний досвід клієнта як аргумент.",
    [[("➡️ Далі (Характеристики ILUMA i)", "iluma")], [("⬅️ Назад", "zyn"), HOME]],
)

# ── IQOS ILUMA i ──────────────────────────────────────────────
S["iluma"] = (
    "📱 <b>ПРЕЗЕНТАЦІЯ IQOS ILUMA i</b>\n\n"
    "<b>Технологія:</b> індукційне нагрівання — без вбудованого леза та <b>без потреби у чистці</b>.\n\n"
    "<b>Ключові характеристики:</b>\n"
    "• до <b>20 стіків</b> на повному заряді | до <b>4 додаткових затяжок</b> | режим паузи\n"
    "• гарантія — <b>12 місяців</b>\n\n"
    "<b>Моделі:</b> ILUMA i One, ILUMA i, ILUMA i Prime\n\n"
    "⚠️ Сумісний <b>ТІЛЬКИ</b> зі стіками <b>TEREA, DELIA, LEVIA</b>.",
    [
        [("🍃 Озвучити про LEVIA (стіки без тютюну)", "levia")],
        [("🌈 Підібрати стіки", "fl_i")],
        [("🟦 КРОК 2: Презентація категорії ZYN", "zyn")],
        [("💰 Для клієнта дорого → BONDS 2", "bonds")],
        [("⬅️ Назад до переваг", "heat_cat"), HOME],
    ],
)

S["iluma_levia_first"] = (
    "📱 <b>КРОК 1 — ПРЕЗЕНТАЦІЯ ILUMA з LEVIA</b>\n\n"
    "🔥 <b>Наголосіть на перевазі:</b> <i>«Система нагріває, а не спалює, тому немає диму, попелу та стійкого запаху.»</i>\n\n"
    "• Для користувачів вейпів / міксуючих з вейпом розкажіть про <b>IQOS ILUMA i</b> у поєднанні зі стіками <b>LEVIA</b> (без тютюну).\n"
    "• LEVIA має 5 насичених ягідних/фруктових смаків із капсулою без тютюнового післясмаку.\n"
    "🎁 Перевірте, чи доступна клієнту <b>безкоштовна пачка LEVIA</b>.",
    [
        [("🌈 Підібрати смаки LEVIA / TEREA", "fl_i")],
        [("🟦 КРОК 2: Презентація категорії ZYN", "zyn")],
        [("⬅️ Назад", "current"), HOME],
    ],
)

S["levia"] = (
    "🍃 <b>LEVIA — стіки без тютюну</b>\n\n"
    "• <b>5 смаків</b> з капсулою: Амарело Пьорпл, Зінг Рубі, Блаш Корал, Зінг Азур, Пьорпл Рубі\n"
    "🎁 Запропонуйте безкоштовну випробувальну пачку LEVIA, якщо доступно в системі.",
    [[("🌈 Підібрати стіки", "fl_i")], [("⬅️ Назад", "iluma"), HOME]],
)

S["bonds"] = (
    "📱 <b>Альтернатива: BONDS 2 by IQOS</b>\n\n"
    "🔥 <b>Наголосіть:</b> <i>«Нагріває тютюн замість спалювання — без диму, запаху і попелу.»</i>\n\n"
    "• Нагрівання Round Heat (ззовні), без чистки | до 28 стіків | гарантія 24 місяці\n"
    "⚠️ Сумісний <b>ТІЛЬКИ</b> зі стіками <b>BLENDS</b>.",
    [[("✅ Підходить — до стіків", "fl_b")], [("⬅️ До IQOS ILUMA i", "iluma"), HOME]],
)

# ── ПІДБІР СТІКІВ ─────────────────────────────────────────────
_FL_Q = (
    "💬 <i>«У нас є чотири лінійки стіків — класична, тютюново-ягідна, "
    "ментолізована та капсульна. Яким смакам Ви надаєте перевагу?»</i>"
)
S["fl_i"] = (
    "🌈 <b>ПІДБІР СТІКІВ для IQOS ILUMA i</b>\nTEREA / DELIA / LEVIA\n\n" + _FL_Q,
    [
        [("🟤 Тютюнові", "fi_tob"), ("🟢 Ментолові", "fi_men")],
        [("🟣 Фруктові", "fi_fruit"), ("🔵 Капсульні", "fi_caps")],
        [("🍃 Без тютюну (LEVIA)", "fi_levia")],
        [("➡️ Рекомендації перед завершенням", "recs")],
        [HOME],
    ],
)
_TO_RECS_I = [[("➡️ Рекомендації перед завершенням", "recs")], [("⬅️ Інший смак", "fl_i"), HOME]]

S["fi_tob"] = ("🟤 <b>Тютюнові:</b> TEREA Silver/Amber/Sienna, DELIA Classic Gold/Red", _TO_RECS_I)
S["fi_men"] = ("🟢 <b>Ментолові:</b> TEREA Turquoise/Blue, DELIA Classic Green", _TO_RECS_I)
S["fi_fruit"] = ("🟣 <b>Фруктові:</b> TEREA Purple Wave/Summer Wave, DELIA Purple", _TO_RECS_I)
S["fi_caps"] = ("🔵 <b>Капсульні:</b> TEREA Sun Pearl/Twilight Pearl/Oasis Pearl", _TO_RECS_I)
S["fi_levia"] = ("🍃 <b>LEVIA (без тютюну):</b> Amarelo, Zing Ruby, Blush Coral, Zing Azure, Purple Ruby", _TO_RECS_I)

S["fl_b"] = (
    "🌈 <b>ПІДБІР СТІКІВ для BONDS 2 (BLENDS)</b>\n\n" + _FL_Q,
    [
        [("🟤 Тютюнові", "fb_tob"), ("🟢 Ментолові", "fb_men")],
        [("🟣 Фруктові", "fb_fruit"), ("🔵 Капсульні", "fb_caps")],
        [("➡️ Рекомендації перед завершенням", "recs")],
        [HOME],
    ],
)
_TO_RECS_B = [[("➡️ Рекомендації перед завершенням", "recs")], [("⬅️ Інший смак", "fl_b"), HOME]]
S["fb_tob"] = ("🟤 <b>Тютюнові BLENDS:</b> Red / Gold / Silver Classics", _TO_RECS_B)
S["fb_men"] = ("🟢 <b>Ментолові BLENDS:</b> Green Classics", _TO_RECS_B)
S["fb_fruit"] = ("🟣 <b>Фруктові BLENDS:</b> Purple / Exotic", _TO_RECS_B)
S["fb_caps"] = ("🔵 <b>Капсульні BLENDS:</b> Purple Caps / Summer Caps / Cerise Caps", _TO_RECS_B)

# ── ЗАВЕРШЕННЯ ТА РЕКОМЕНДАЦІЇ ────────────────────────────────
def recs_screen(device: str):
    if device == "bonds":
        dev_name, warranty, sticks, back = "BONDS 2 by IQOS", "<b>24 місяці (2 роки)</b>", "BLENDS", "fl_b"
    else:
        dev_name, warranty, sticks, back = "IQOS ILUMA i", "<b>12 місяців (1 рік)</b>", "TEREA / DELIA / LEVIA", "fl_i"

    text = (
        f"✅ <b>КРОК 8 — ОБОВ'ЯЗКОВІ РЕКОМЕНДАЦІЇ</b>\n"
        f"Обраний пристрій: <b>{dev_name}</b>\n\n"
        "1️⃣ Для комфортного переходу <b>не використовувати сигарети/вейпи 7 днів</b>\n"
        "2️⃣ Робити <b>паузи між затяжками</b>\n"
        "3️⃣ <b>Смак стіків відрізняється</b> — тютюн нагрівається, а не спалюється\n"
        f"4️⃣ 🛡️ <b>ГАРАНТІЯ:</b> на {dev_name} — {warranty}\n"
        f"5️⃣ Працює <b>тільки зі стіками {sticks}</b>\n"
        "6️⃣ Сервіс та гаряча лінія <b>4767</b>"
    )
    buttons = [[("✅ Все озвучено → завершення", "finish")], [("⬅️ Назад", back), HOME]]
    return text, buttons


S["finish"] = (
    "📲 <b>ЗАВЕРШЕННЯ КОНСУЛЬТАЦІЇ</b>\n\n"
    "☐ Попросіть номер телефону клієнта\n"
    "☐ Внесіть дані у планшет під час консультації\n"
    "☐ Перевірте вікно NBA\n"
    "☐ Зареєструйте споживача та продаж\n\n"
    "Дякуємо за консультацію! 🙌",
    [[("🔄 Нова консультація", "menu")], [HOME]],
)

# ── АПГРЕЙД ──────────────────────────────────────────────────
S["upgrade"] = (
    "🔄 <b>IQOS АПГРЕЙД</b>\n\n"
    "💬 <b>Запитайте клієнта:</b>\n"
    "<i>«Підкажіть, будь ласка, чи є Вам 18 років, чи споживаєте Ви нікотиновмісну продукцію та чи це Ваш особистий пристрій?»</i>\n\n"
    "<b>Умови участі в програмі:</b>\n"
    "• Повнолітній споживач нікотиновмісної продукції\n"
    "• Зареєстрований профіль на сайті iqos.com.ua\n"
    "• Девайс прив’язаний до облікового запису\n"
    "• Девайсу більше 3-х місяців\n"
    "• Девайс не втрачений / заблокований\n"
    "• Девайс не є російським\n"
    "• Девайс не є прокатним\n"
    "• Не більше 5 апгрейдів протягом останніх 3 місяців",
    [
        [("📱 Які пристрої можна апгрейднути", "upg_dev")],
        [("❓ FAQ Апгрейд", "upg_faq")],
        [HOME],
    ],
)

S["upg_dev"] = (
    "📱 <b>ЯКІ ПРИСТРОЇ МОЖНА АПГРЕЙДНУТИ</b>\n\n"
    "<b>Можна здати:</b>\n"
    "ILUMA Prime/MID/One • IQOS 3 DUO/Refreshed • IQOS Or. DUO/ONE • "
    "LIL SOLID 2.0/HYBRID/ES • IQOS VEEV • BONDS 1.0/1.5/1.6 • IQOS 2.4+ • "
    "IQOS MULTI • LIL 1.0 • IQOS 3.0\n\n"
    "➡️ <b>На нові пристрої:</b>\n"
    "IQOS ILUMA / ILUMA PRIME / ILUMA ONE або IQOS ILUMA i / ILUMA i PRIME / ILUMA i ONE",
    [[("⬅️ Назад", "upgrade")], [HOME]],
)

S["upg_faq"] = (
    "❓ <b>FAQ Апгрейд</b>\n\n"
    "<b>Ціна?</b> Залежить від моделі, віку пристрою та системних алгоритмів.\n\n"
    "<b>Чи повертати старий девайс?</b> Так, тільки за умови повернення старого пристрою.\n\n"
    "<b>Що повертати?</b> Холдер та чарджер. Коробку та зарядку — необов'язково.",
    [[("⬅️ Назад", "upgrade")], [HOME]],
)

# ── СЕРВІС ───────────────────────────────────────────────────
_SRV_BACK = [[("⬅️ Сервісне меню", "service")], [HOME]]

S["service"] = (
    "🛠️ <b>СЕРВІСНЕ ОБСЛУГОВУВАННЯ</b>\n(для сервісних точок)\n\n"
    "💬 <b>Запитайте клієнта:</b>\n"
    "<i>«Підкажіть, будь ласка, чи є Вам 18 років, чи споживаєте Ви нікотинові продукти та чи це Ваш особистий пристрій?»</i>\n\n"
    "Оберіть розділ сервісу:",
    [
        [("1️⃣ Кроки діагностики", "srv_steps")],
        [("👁️ Фізичні пошкодження", "srv_phys")],
        [("💻 Checking App / USU", "srv_app")],
        [("🌳 Дерево IQOS/BONDS", "srv_tree_iqos"), ("🌳 Дерево lil SOLID", "srv_tree_lil")],
        [("🔢 Коди BONDS", "srv_codes_bonds"), ("🔢 Коди lil SOLID", "srv_codes_lil")],
        [("🛡️ Гарантія та гудвіл", "srv_warranty"), ("📦 Заміна в 1С", "srv_1c")],
        [HOME],
    ],
)

S["srv_steps"] = (
    "1️⃣ <b>КРОКИ ДІАГНОСТИКИ</b>\n\n"
    "1. <b>Привітання та з'ясування проблеми:</b>\n"
    "💬 Запитайте клієнта: <i>«Підкажіть, чим можу вам допомогти? Які саме у вас складнощі з пристроєм? Давайте продіагностую ваш пристрій та спробую вам допомогти та вирішити проблему.»</i>\n\n"
    "2. <b>Визначення пристрою:</b>\n"
    "Визначаємо, з яким саме пристроєм звернувся клієнт (IQOS, BONDS чи lil SOLID).\n\n"
    "3. <b>Візуальний огляд:</b>\n"
    "Проводимо візуальний огляд пристрою на предмет фізичних пошкоджень.\n\n"
    "4. <b>Діагностика та оновлення:</b>\n"
    "• <b>Якщо IQOS / BONDS:</b>\n"
    "  1. Підключаємо пристрій IQOS до додатку діагностики <b>Checking App</b>.\n"
    "  2. Для оновлення ПЗ підключаємо до додатку <b>USU (IQOS/BONDS)</b>.\n"
    "• <b>Якщо lil SOLID:</b>\n"
    "  1. Перевіряємо пристрій за допомогою ручної діагностики згідно з <b>деревом діагностики</b>.\n\n"
    "5. <b>Дерево діагностики:</b>\n"
    "Застосовуємо Дерево діагностики IQOS/BONDS або Дерево діагностики lil SOLID.\n\n"
    "6. <b>Завершення:</b>\n"
    "Перевірка гарантії та гудвілу ➡️ Оформлення заміни в 1С.",
    _SRV_BACK,
)

S["srv_phys"] = (
    "👁️ <b>Огляд на фізичні пошкодження</b>\n\n"
    "• Корпус тримача, ковпачок, нагрівальна камера + лезо\n"
    "• Потрапляння рідини/бруду, сколи, тріщини корпуса\n"
    "• Контакти тримача та КЗП — окислення\n\n"
    "Є пошкодження → заміна, <b>якщо доступний гудвіл</b>.",
    _SRV_BACK,
)
S["srv_app"] = (
    "💻 <b>Checking App / USU</b>\n\n"
    "<b>Checking App:</b> підключіть пристрій USB-кабелем → «Розпочати перевірку». "
    "Для lil SOLID — «Перевірка гарантії».\n"
    "<b>USU:</b> підключіть до Web USU → «Оновити пристрій». Заряд — не менше 20%.",
    _SRV_BACK,
)
S["srv_tree_iqos"] = (
    "🌳 <b>Дерево діагностики IQOS/BONDS</b>\n\n"
    "1. Фіз. пошкодження? Так → гудвіл (заміна / апгрейд)\n"
    "2. Вмикається? Ні → перевірка гарантії → заміна / апгрейд\n"
    "3. LED мигає червоним / білим → гарантія → заміна\n"
    "4. Все ок → <b>A101</b> + рекомендації з користування.",
    _SRV_BACK,
)
S["srv_tree_lil"] = (
    "🌳 <b>Дерево діагностики lil SOLID 2.0 / ES</b>\n\n"
    "1. Фіз. пошкодження? C101 / C046 / C028 — заміна НЕ можлива → Апгрейд\n"
    "2. Не вмикається / проблеми з LED → коди B (гарантійна заміна)\n"
    "3. Все ок → <b>A101</b>.",
    _SRV_BACK,
)
S["srv_codes_bonds"] = (
    "🔢 <b>Коди помилок BONDS</b>\n\n"
    "C101 (фіз. пошкодження), C028 (нагрівається), C046 (рідина)\n"
    "B102, B103, B104, B004, B051, B032, B101 — гарантія\n"
    "A101 — справний",
    _SRV_BACK,
)
S["srv_codes_lil"] = (
    "🔢 <b>Коди помилок lil SOLID</b>\n\n"
    "C-коди — фізичні пошкодження (без заміни)\n"
    "B-коди — гарантійна заміна\n"
    "A101 — справний",
    _SRV_BACK,
)
S["srv_warranty"] = (
    "🛡️ <b>Перевірка гарантії та гудвілу</b>\n\n"
    "1. <b>Зареєстровані:</b> через Checking App або кодентіфай.\n"
    "2. <b>Незареєстровані:</b> за чеком (до 12 міс). Поза гарантією — контакт-центр <b>4767</b>.",
    _SRV_BACK,
)
S["srv_1c"] = (
    "📦 <b>Оформлення заміни в 1С</b>\n\n"
    "• Внесіть дані пристрою та клієнта в 1С\n"
    "• Оформіть замовлення на заміну\n"
    "⚠️ При заміні комплекту вилучіть обидві деталі (несправна — C/B код, справна — D001).",
    _SRV_BACK,
)


# ─────────────────────────────────────────────────────────────
# МАРШРУТИЗАЦІЯ
# ─────────────────────────────────────────────────────────────
def route(key: str, data: dict):
    if key in ("gcp", "menu"):
        data.clear()
        return S["menu"]

    # Категорії покупця
    if key == "cat_pouch":
        data["flow"] = "pouch"
        return S["zyn"]

    if key == "cat_cig_comp":
        return S["mix_pouch_q"]

    if key == "mix_p_yes":
        data["flow"] = "mix_pouch_yes"
        return S["zyn"]

    if key == "mix_p_no":
        return S["mix_vape_q"]

    if key == "mix_v_no":
        data["flow"] = "no_mix"
        return S["heat_cat"]

    if key == "mix_v_yes" or key == "cat_vape":
        data["flow"] = "vape"
        return S["iluma_levia_first"]

    if key == "cat_our":
        return S["our_mix_q"]

    if key == "our_v_yes":
        return S["our_need_vape"]

    if key == "our_v_no":
        return S["our_need_no_vape"]

    if key in ("iluma", "levia", "fl_i"):
        data["device"] = "iluma"
    if key in ("bonds", "fl_b"):
        data["device"] = "bonds"

    if key == "recs":
        return recs_screen(data.get("device", "iluma"))

    return S.get(key, S["menu"])


# ─────────────────────────────────────────────────────────────
# ОБРОБНИКИ TELEGRAM
# ─────────────────────────────────────────────────────────────
async def send_screen(chat, key, text, buttons):
    image = None
    for ext in (".jpg", ".jpeg", ".png"):
        path = os.path.join(IMAGES_DIR, key + ext)
        if os.path.exists(path):
            image = path
            break
    if image:
        with open(image, "rb") as f:
            await chat.send_photo(photo=f)
    await chat.send_message(text, parse_mode=ParseMode.HTML, reply_markup=kb(buttons))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    text, buttons = S["menu"]
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(buttons))


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    key = query.data
    text, buttons = route(key, context.user_data)

    has_image = any(os.path.exists(os.path.join(IMAGES_DIR, key + e)) for e in (".jpg", ".jpeg", ".png"))
    if has_image:
        await send_screen(query.message.chat, key, text, buttons)
    else:
        try:
            await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(buttons))
        except Exception:
            await query.message.chat.send_message(text, parse_mode=ParseMode.HTML, reply_markup=kb(buttons))


def build_request():
    if CA_BUNDLE and os.path.exists(CA_BUNDLE):
        log.info("Використовую сертифікат: %s", CA_BUNDLE)
        return HTTPXRequest(httpx_kwargs={"verify": CA_BUNDLE})
    return HTTPXRequest()


def main():
    if not TOKEN:
        raise RuntimeError("Помилка: TELEGRAM_BOT_TOKEN не знайдено у .env")

    app = (
        Application.builder()
        .token(TOKEN)
        .request(build_request())
        .get_updates_request(build_request())
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_button))

    log.info("ALLO Bot запущено!")
    app.run_polling()


if __name__ == "__main__":
    main()
