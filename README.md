# OnionShare Pi

**Versiya:** 2.6.3
**Platforma:** Raspberry Pi (Linux ARM) · Python 3.10–3.12
**Litsenziya:** GPLv3+

OnionShare Pi — bu [OnionShare](https://onionshare.org/) loyihasining Raspberry Pi uchun moslashtirilgan CLI versiyasi. Dastur fayllarni xavfsiz va anonim ravishda Tor tarmog'i orqali ulashish, qabul qilish, veb-sayt nashr etish va shifrlangan chat o'tkazish imkonini beradi. Hech qanday uchinchi tomon serveri yoki bulut xizmati talab qilinmaydi.

---

## Imkoniyatlar

- **Ulashish** — fayllar va papkalarni Tor onion manzil orqali yuborish
- **Qabul qilish** — boshqalardan fayl va xabar qabul qilish (anonim pochta qutisi)
- **Veb-sayt** — statik veb-saytni onion xizmat sifatida nashr etish
- **Chat** — serverga asoslangan, jurnalsiz, shifrlangan matn chati
- **QR kod** — onion manzilni terminalda QR kod sifatida ko'rsatish
- **Doimiy sessiya** — onion manzilni saqlab qayta ishlatish
- **Ko'prik qo'llab-quvvatlash** — obfs4, snowflake, meek-azure orqali tsenzurani chetlab o'tish

---

## Talablar

| Talab | Versiya |
|---|---|
| Python | 3.10 – 3.12 |
| Tor | 0.3.5.7+ (ephemeral onion uchun 0.2.7.1+) |
| Poetry | 1.4+ (o'rnatish uchun) |
| OS | Linux (ARM / x86), Raspberry Pi OS |

---

## O'rnatish

### 1. Reponi klonlash

```bash
git clone https://github.com/VIPOS-testuser/onionshare-pi.git
cd onionshare-pi/cli
```

### 2. Tor o'rnatish

```bash
sudo apt update
sudo apt install tor -y
```

### 3. Poetry orqali o'rnatish

```bash
pip install poetry --break-system-packages
poetry install
```

### 4. To'g'ridan-to'g'ri pip orqali o'rnatish (muqobil)

```bash
pip install . --break-system-packages
```

---

## Ishlatish

### Asosiy buyruq formati

```bash
onionshare-cli [opsiyalar] [fayl ...]
```

---

### Rejimlar

#### Fayl ulashish (standart)

```bash
onionshare-cli fayl.pdf
onionshare-cli rasm.jpg hujjat.docx
onionshare-cli ~/papka/
```

Yuklab olingandan keyin server avtomatik to'xtatiladi. Davom ettirish uchun:

```bash
onionshare-cli --no-autostop-sharing fayl.zip
```

#### Fayl qabul qilish

```bash
onionshare-cli --receive
onionshare-cli --receive --data-dir /home/pi/qabul/
onionshare-cli --receive --disable-text
onionshare-cli --receive --disable-files
```

#### Veb-sayt nashr etish

```bash
onionshare-cli --website ~/sayt/
onionshare-cli --website --disable_csp ~/sayt/
onionshare-cli --website --custom_csp "default-src 'self'" ~/sayt/
```

#### Chat

```bash
onionshare-cli --chat
```

---

### Barcha opsiyalar

| Opsiya | Tavsif |
|---|---|
| `--receive` | Fayl qabul qilish rejimi |
| `--website` | Veb-sayt nashr etish rejimi |
| `--chat` | Chat serveri rejimi |
| `--public` | Shaxsiy kalit ishlatilmaydi (ochiq kirish) |
| `--title SARLAVHA` | Sahifa sarlavhasini belgilash |
| `--persistent FAYL` | Doimiy sessiya fayli (onion manzilni saqlash) |
| `--config FAYL` | Maxsus sozlamalar fayli |
| `--qr` | Onion manzilni QR kod sifatida ko'rsatish |
| `--no-autostop-sharing` | Yuklab olingandan keyin ham ishlashni davom ettirish |
| `--log-filenames` | Fayl yuklash faoliyatini stdout ga chiqarish |
| `--auto-start-timer SONIYA` | Xizmatni N soniyadan keyin ishga tushirish |
| `--auto-stop-timer SONIYA` | Xizmatni N soniyadan keyin to'xtatish |
| `--connect-timeout SONIYA` | Torga ulanish kutish vaqti (standart: 120) |
| `--data-dir PAPKA` | Qabul qilingan fayllarni saqlash joyi |
| `--webhook-url URL` | Yuklash bildirishnomalari uchun webhook URL |
| `--disable-text` | Matn xabarlarini qabul qilishni o'chirish |
| `--disable-files` | Fayllarni qabul qilishni o'chirish |
| `--disable_csp` | Content Security Policy sarlavhasini o'chirish |
| `--custom_csp CSP` | Maxsus Content Security Policy belgilash |
| `-v`, `--verbose` | Batafsil xato chiqishi |
| `--local-only` | Tor ishlatilmaydi (faqat ishlab chiqish uchun) |

---

### Amaliy misollar

**Fayl ulashish va QR kod ko'rsatish:**
```bash
onionshare-cli --qr hisobot.pdf
```

**Doimiy onion manzil bilan veb-sayt:**
```bash
onionshare-cli --website --persistent ~/sessiya.json ~/sayt/
```

**30 daqiqadan keyin avtomatik to'xtatish:**
```bash
onionshare-cli --auto-stop-timer 1800 --receive
```

**60 soniyadan keyin boshlanadigan ulashish:**
```bash
onionshare-cli --auto-start-timer 60 fayl.zip
```

**Webhook bilan fayl qabul qilish:**
```bash
onionshare-cli --receive --webhook-url https://example.com/hook
```

---

## Loyiha tuzilishi

```
onionshare-pi/
├── cli/
│   ├── pyproject.toml
│   └── onionshare_cli/
│       ├── __init__.py          ← CLI kirish nuqtasi
│       ├── common.py            ← Umumiy yordamchi funksiyalar
│       ├── onion.py             ← Tor ulanish va onion xizmat boshqaruvi
│       ├── onionshare.py        ← Asosiy dastur klassi
│       ├── mode_settings.py     ← Sessiya sozlamalari
│       ├── settings.py          ← Global sozlamalar
│       ├── censorship.py        ← Ko'prik va tsenzura chetlab o'tish
│       ├── meek.py              ← Meek transport yordamchisi
│       ├── web/
│       │   ├── web.py           ← Flask veb-server
│       │   ├── share_mode.py    ← Ulashish rejimi
│       │   ├── receive_mode.py  ← Qabul qilish rejimi
│       │   ├── website_mode.py  ← Veb-sayt rejimi
│       │   ├── chat_mode.py     ← Chat rejimi
│       │   └── send_base_mode.py
│       └── resources/
│           ├── templates/       ← HTML sahifalar (o'zbek tilida)
│           ├── static/
│           │   ├── css/         ← Uslublar
│           │   ├── img/         ← Rasmlar
│           │   └── js/          ← JavaScript fayllar
│           ├── torrc_template*  ← Tor konfiguratsiya shablonlari
│           └── version.txt
```

---

## Xavfsizlik eslatmalari

- Onion manzil faqat Tor Browser yoki `torsocks` orqali ochiladi
- Standart holda **shaxsiy kalit** (stealth auth) yoqilgan — manzilni faqat siz bergan odamlar kira oladi
- `--public` bayrog'i shaxsiy kalitni o'chiradi — hamma kira oladi
- Qabul qilish rejimida yuklangan fayllar **ishonchsiz** bo'lishi mumkin
- Server to'xtatilgandan keyin onion manzil yana ishlamaydi (doimiy sessiya ishlatilmasa)

---

## Litsenziya

GNU General Public License v3 yoki undan yuqori versiyasi.
Mualliflar: Micah Lee va boshqalar — https://onionshare.org/

Ushbu dastur erkin dasturiy ta'minot: uni GNU GPL shartlarida qayta tarqatishingiz va/yoki o'zgartirishingiz mumkin.
