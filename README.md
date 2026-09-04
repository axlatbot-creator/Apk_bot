# APK Kod Bot — o'rnatish qo'llanmasi (Pydroid 3)

## 1. O'rnatish
Pydroid 3 ichidagi terminalda:
```
pip install pyTelegramBotAPI
```

## 2. Sozlash
`bot.py` faylini oching, faylning tepasidagi konfiguratsiya qismini o'zgartiring:
```python
BOT_TOKEN = "SIZNING_BOT_TOKEN"      # @BotFather dan olingan token
MAIN_ADMIN_ID = 123456789            # sizning Telegram ID'ingiz (@userinfobot orqali bilib oling)
```

## 3. Ishga tushirish
Pydroid 3'da `bot.py` faylini ochib, ▶️ (Run) tugmasini bosing.
Terminalda "Bot ishga tushdi..." degan yozuv chiqsa — hammasi tayyor.

Bot **long-polling** orqali ishlaydi — hech qanday hosting, domen yoki SSL
sertifikat shart emas. Telefon internetga ulangan va dastur ochiq turgan
vaqtda bot ishlaydi.

## 4. Birinchi qadamlar
1. Telegram'da botingizga `/admin` deb yozing — admin panel ochiladi
2. "📢 Majburiy obuna" → "➕ Kanal qo'shish" orqali kanal(lar)ingizni qo'shing
   (botni albatta kanalga **admin** qilib qo'ying, aks holda obuna tekshiruvi ishlamaydi)
3. "➕ O'yin qo'shish" orqali birinchi o'yiningizni qo'shing — bot sizdan
   nom, kod, tavsif, versiya, hajm, kategoriya, rasm va APK faylni ketma-ket so'raydi
4. Kodni Instagram videongizda ko'rsating — foydalanuvchi botga shu kodni
   yuborsa, bot avtomatik o'yin ma'lumoti va yuklab olish tugmasini beradi

## 5. Muhim eslatmalar
- Bot doim ishlashi uchun telefon ekranini o'chirmaslik yoki Pydroid 3'ni
  fon rejimida ishlashga ruxsat berish kerak (Android battery optimization'ni
  bot uchun o'chiring)
- Baza fayli `bot_database.db` — bot.py bilan bir papkada avtomatik yaratiladi
- "💾 Backup" tugmasi orqali istalgan vaqtda baza faylini o'zingizga yuborib,
  nusxa saqlab qo'yishingiz mumkin
- Faqat o'zingiz tarqatishga huquqingiz bo'lgan yoki o'zingiz yaratgan APK
  fayllarni yuklang

## 6. Admin panel bo'limlari
- **➕ O'yin qo'shish** — yangi o'yin va uning kodini qo'shish
- **📋 O'yinlar** — barcha o'yinlar ro'yxati, har birida tahrirlash/o'chirish/
  statistika/APK almashtirish
- **🔑 Kodlar** — barcha kod → o'yin nomi ro'yxati
- **📢 Majburiy obuna** — kanallarni boshqarish
- **👥 Foydalanuvchilar** — umumiy son va qidiruv
- **📊 Statistika** — umumiy va kunlik ko'rsatkichlar, top o'yinlar
- **📣 Xabar yuborish** — barcha foydalanuvchilarga ommaviy xabar
- **⚙️ Sozlamalar** — botni yoqish/o'chirish, xabar matnlarini o'zgartirish
- **👑 Adminlar** — qo'shimcha adminlar qo'shish/o'chirish (faqat asosiy admin)
- **📝 Loglar** — kim, qachon, nima qilgani
- **💾 Backup** — baza faylini yuklab olish
