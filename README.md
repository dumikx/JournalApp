# Jurnal personal

Aplicație web de jurnal personal, single-user: Flask + PostgreSQL (Railway) +
Cloudflare R2 pentru poze (upload direct din browser prin presigned PUT URLs).

## Funcționalități

- O intrare pe zi (constrângere UNIQUE pe dată), scriere retroactivă cu date picker.
- Timeline cronologic grupat pe lună + an, cu infinite scroll și arhivă an → lună.
- Poze per intrare: redimensionare client-side (max 2560px), upload direct în R2
  (originalul + versiunea display), galerie cu lightbox, descărcare original.
- Căutare full-text (PostgreSQL FTS + `unaccent` — găsește text scris cu sau fără diacritice).
- Export PDF pe interval de date (WeasyPrint).
- Interfață în română, mobile-first, dark mode automat.

## Dezvoltare locală

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows; pe Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # completează valorile
# local, fără HTTPS:
#   COOKIE_SECURE=0

# generează hash-ul parolei și pune-l în .env ca JOURNAL_PASSWORD_HASH
flask --app app create-password-hash parola-ta

# rulează migrațiile (necesită un PostgreSQL accesibil prin DATABASE_URL)
flask --app app db upgrade

flask --app app run --debug
```

> **Notă:** aplicația folosește funcționalități specifice PostgreSQL
> (`tsvector`, `unaccent`, coloană generată) — SQLite nu e suportat.
> **WeasyPrint** (exportul PDF) are nevoie de biblioteci de sistem (Pango etc.);
> restul aplicației funcționează și fără ele — importul se face abia la export.

## Deploy pe Railway

1. **Creează proiectul** din repo (GitHub) sau `railway up`.
2. **Adaugă addon-ul PostgreSQL** — Railway setează `DATABASE_URL` automat
   (schema `postgres://` e normalizată de aplicație).
3. **Setează variabilele de environment** pe serviciul web:

   | Variabilă | Valoare |
   |---|---|
   | `SECRET_KEY` | șir lung aleator (`python -c "import secrets; print(secrets.token_hex(32))"`) |
   | `JOURNAL_USER` | numele tău de utilizator |
   | `JOURNAL_PASSWORD_HASH` | rezultatul `flask create-password-hash <parola>` |
   | `R2_ACCOUNT_ID` | ID-ul contului Cloudflare |
   | `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` | token API R2 (permisiuni Object Read & Write pe bucket) |
   | `R2_BUCKET` | numele bucket-ului |
   | `R2_ENDPOINT` | `https://<account_id>.r2.cloudflarestorage.com` (opțional, se derivă din account id) |

4. **Migrații:** setează în Railway *Pre-deploy command*:
   `flask --app app db upgrade`
   (alternativ, schimbă comanda de start în `flask --app app db upgrade && gunicorn app:app`).
5. **WeasyPrint:** pachetele de sistem (pango, harfbuzz, fonturi) sunt declarate
   în `railpack.json` (builderul implicit Railpack) și în `nixpacks.toml`
   (builderul Nixpacks) — oricare ar fi activ, se instalează. Cu Dockerfile:
   `libpango-1.0-0 libpangocairo-1.0-0 libpangoft2-1.0-0 fonts-dejavu-core`.
6. Start command: din `Procfile` — `web: gunicorn app:app`.

## Setup Cloudflare R2

1. Creează un **bucket privat** (fără acces public — pozele se servesc prin
   presigned GET URLs cu expirare 1h).
2. Creează un **API token** cu permisiunea *Object Read & Write* limitată la bucket.
3. Setează **politica CORS** a bucket-ului (necesară pentru PUT direct din browser;
   GET prin presigned URL în `<img>` nu are nevoie de CORS):

   ```json
   [
     {
       "AllowedOrigins": ["https://aplicatia-ta.up.railway.app"],
       "AllowedMethods": ["PUT"],
       "AllowedHeaders": ["Content-Type"],
       "MaxAgeSeconds": 3600
     }
   ]
   ```

   Pentru dezvoltare locală adaugă și `http://localhost:5000` la `AllowedOrigins`.

## Cum funcționează upload-ul de poze

1. Browserul redimensionează poza (canvas, max 2560px latura lungă, JPEG q0.85)
   → versiunea „display"; originalul rămâne neatins.
2. `POST /api/entries/<id>/photos/presign` → două presigned PUT URLs
   (chei `journal/<entry_id>/<uuid>_orig.<ext>` și `..._display.jpg`).
3. Browserul face PUT direct în R2 (nu trece prin gunicorn — fără timeout-uri
   la fișiere mari), cu progress bar și retry.
4. `POST /api/entries/<id>/photos/confirm` verifică obiectele în R2 (HEAD) și
   creează rândurile în tabela `photos`.
5. Ștergerea unei poze/intrări șterge și obiectele din R2.

## Căutarea și diacriticele

Textul poate fi scris mixt (cu și fără ăâîșț). Indexarea folosește dicționarul
`simple` + `unaccent` pe ambele părți (index și query), printr-un wrapper
IMMUTABLE `f_unaccent()` necesar coloanei generate `search_vector`
(tsvector, index GIN). Totul e creat de migrația inițială — inclusiv
`CREATE EXTENSION unaccent`.

## Structura proiectului

```
app.py                  # entrypoint gunicorn (app:app)
config.py
journal/
  __init__.py           # app factory + CLI (create-password-hash)
  auth.py               # login single-user (env vars), rate limit 10/15min
  entries.py            # timeline, CRUD intrări, arhivă, prev/next
  photos_api.py         # presign / confirm / delete / reorder
  search.py             # FTS cu unaccent + ts_headline
  export.py             # PDF cu WeasyPrint
  r2.py                 # client boto3 + presigning
  dates_ro.py           # formatare date în română
migrations/             # Alembic (flask db upgrade)
templates/  static/
```

## Backup

Backup-ul bazei de date NU face parte din aplicație — rulează extern
(`pg_dump` de pe alt server, folosind connection string-ul Railway).
