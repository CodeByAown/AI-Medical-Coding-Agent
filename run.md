
  You need to run two commands in two separate terminals.

  ---
  Terminal 1 — Backend (FastAPI)

  cd "C:\Ai Agents\ai medical coding agent\backend"
  .\venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000

  Wait until you see:
  INFO:     Application startup complete.

  ---
  Terminal 2 — Frontend (Next.js)

  cd "C:\Ai Agents\ai medical coding agent\frontend"
  npm run dev

  Wait until you see:
  ✓ Ready in ...ms

  ---
  Then open in browser

  ┌──────────┬─────────────────────────────┐
  │   What   │             URL             │
  ├──────────┼─────────────────────────────┤
  │ App      │ http://localhost:3000       │
  ├──────────┼─────────────────────────────┤
  │ Login    │ http://localhost:3000/login │
  ├──────────┼─────────────────────────────┤
  │ API Docs │ http://localhost:8000/docs  │
  └──────────┴─────────────────────────────┘

  Login credentials:
  Email:    admin@medcoder.local
  Password: ChangeMe123!

  ---
  Quick tip — run both in one VS Code session

  Open VS Code → press Ctrl+` to open terminal → click the + icon twice to get two terminals, run one command in each.

  That's it. The project has no database setup, no Docker, no migrations needed — it all starts automatically.

✻ Brewed for 13s

● How is Claude doing this session? (optional)
  1: Bad    2: Fine   3: Good   0: Dismiss

──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
❯  
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
  ? for shortcuts · ← for agents                                                                                                                       100% context used




cd backend

.\venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000

cd frontend

npm run dev

http://localhost:3000 