# The Learning Bistro — React Frontend

## Run
npm install
npm run dev

Open http://localhost:5173

Create `.env` from `.env.example` if needed:
VITE_API_BASE=http://127.0.0.1:8000

Expected backend endpoints:
- GET /api/health
- POST /api/ask
- POST /api/reservations
- POST /api/documents/upload

FastAPI CORS should allow http://localhost:5173 and http://127.0.0.1:5173.
