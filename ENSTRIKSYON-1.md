# Enstriksyon pou Bot Diamond Squad la

## Kijan Bot la Fonksyone
1. Client voye `/start` → chwazi pak dyaman
2. Bot mande ID Free Fire client la
3. Bot mande metòd peman (NatCash/MonCash) → montre nimewo pou peye
4. Client voye referans tranzaksyon an
5. **Ou resevwa yon mesaj dirèk** avèk tout enfo kòmand la + 2 bouton:
   - ✅ Konplete (lè ou fin verifye peman ak livre dyaman yo)
   - ❌ Anile (si peman an pa valid)
6. Client resevwa yon mesaj otomatik selon sa ou chwazi a

Pa gen sit web ki nesesè — tout bagay fèt sou Telegram.

## Etap pou Enstale

### 1. Kreye Bot la sou Telegram
- Al pale ak **@BotFather** sou Telegram
- Voye `/newbot`, swiv enstriksyon yo
- Li ap ba ou yon **TOKEN** (sanble ak `123456:ABC-DEF...`)
- Kole token sa a nan `bot.py`, ranplase `REPLACE_WITH_YOUR_BOT_TOKEN`

### 2. Jwenn ID Chat pa ou (pou resevwa notifikasyon yo)
- Al pale ak **@userinfobot** sou Telegram
- Li ap voye ou yon nimewo (egzanp: `987654321`) — se sa ki ID chat ou
- Kole nimewo sa a nan `bot.py`, ranplase `123456789` bò kote `ADMIN_CHAT_ID`

### 3. Mete Pri ak Nimewo Peman Reyèl Yo
Nan `bot.py`, chanje:
- `NATCASH_NUMBER` ak `MONCASH_NUMBER` — mete vrè nimewo ou yo
- `PACKAGES` — ajiste pak dyaman ak pri yo selon sa ou vann

### 4. Teste Lokalman (opsyonèl)
```bash
pip install -r requirements.txt
python bot.py
```

### 5. Deplwaye sou Render.com (gratis, ap kouri 24/24)
1. Kreye yon kont sou render.com
2. Kreye yon **"Background Worker"** (pa "Web Service")
3. Konekte repo GitHub kote ou mete kòd sa a
4. Build Command: `pip install -r requirements.txt`
5. Start Command: `python bot.py`
6. Deploye — bot la ap kouri san rete

⚠️ **Enpòtan**: SQLite (`orders.db`) ap efase chak fwa Render "redeploy" sèvè a
(disk pa pèsistan sou plan gratis la). Pou kòmand ou yo pa pèdi, ou ka:
- Egzòte yo regilyèman ak `/pending`, oswa
- Pita, pase sou yon baz dòne ki pèsistan (Postgres gratis sou Render)

## Kòmand Itil pou Ou (Admin)
- `/pending` — wè tout kòmand ki poko trete

## Pwochen Etap Posib
- Ajoute bouton "Kontakte Sipò" pou client ki gen kesyon
- Ajoute mesaj otomatik apre X minit si admin pa reponn (pou pa pèdi client)
