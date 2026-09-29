# Finora v11 — Render Unified

Finora è una personal finance app privata. In questa versione GitHub è usato esclusivamente come repository privato e Render è l’unico punto di pubblicazione: frontend, FastAPI e OAuth vivono sullo stesso origin.

## Architettura
- GitHub private repository → sorgente/deploy
- Render Web Service → frontend + API + Google OAuth
- MongoDB Atlas → dati persistenti
- Nessun GitHub Pages
- Nessun Client ID/Secret Google nel frontend

## Render
Root Directory: `.`
Build Command: `pip install -r backend/requirements.txt`
Start Command: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
Health Check: `/health`

## Environment Variables

```env
MONGODB_URI=...
MONGODB_DB=finora
GOOGLE_CLIENT_ID=...apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=https://finora-nekg.onrender.com/api/auth/google/callback
JWT_SECRET=...
DATA_ENCRYPTION_KEY=...
USER_INDEX_SECRET=...
COOKIE_SECURE=true
COOKIE_SAMESITE=lax
ACCESS_TOKEN_MINUTES=10080
```

`GOOGLE_CLIENT_SECRET` resta esclusivamente su Render. Il browser avvia OAuth tramite `/api/auth/google/start`; Google torna su `/api/auth/google/callback`.

## Google Cloud
Authorized JavaScript origins:
`https://finora-nekg.onrender.com`

Authorized redirect URI:
`https://finora-nekg.onrender.com/api/auth/google/callback`

## UI/UX v11
- Design fintech pastel aggiornato
- Dark mode
- Responsive desktop/mobile
- Navigazione con Lucide Icons
- Nuova schermata OAuth server-side
- Favicon + PWA icons
- Transazioni, conti, budget, obiettivi, ricorrenti e pianificazione
- Analisi a 12 mesi con entrate/uscite/risparmio
- Tasso di risparmio corrente e media risparmio
- Confronto con il mese precedente
- Previsione fine mese
- Smart Finance con proiezioni 30/90 giorni
- Aggiornamento PWA v11

## Sviluppo locale

```bash
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

Il frontend viene servito direttamente da FastAPI su `/`.
