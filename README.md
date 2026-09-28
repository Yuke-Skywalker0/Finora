# Finora UX MAX v7

## Nuovo blocco: Pianificazione finanziaria
- Calendario mensile con entrate/uscite previste.
- Prossimi 30 giorni aggregati da ricorrenti e transazioni future.
- Saldo attuale e saldo stimato a 30 giorni.
- Proiezione visuale e warning quando il saldo previsto scende sotto zero.
- Nuova sezione Pianificazione integrata nella navigazione desktop/mobile.

## Avvio
Frontend: apri `frontend/index.html` oppure pubblicalo su GitHub Pages.
Backend: `cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload`


## Finora 10.0.0
- GitHub Pages project-path safe frontend.
- Production Render API URL configured.
- Robust startup: missing optional DOM elements no longer blank the app.
- Service Worker cache bumped to v10.
- GitHub Pages workflow verifies index.html, version.json, JS and CSS before deployment.
