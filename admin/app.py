import os
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from database.connection import get_db
from database.repository import ReservationRepository

app = FastAPI()

# Add CORS middleware for Railway
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Modify for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="admin/templates")
app.mount("/static", StaticFiles(directory="admin/static"), name="static")

@app.get("/")
async def admin_panel(request: Request):
    db = next(get_db())
    repo = ReservationRepository(db)
    reservations = repo.get_all_reservations()
    return templates.TemplateResponse(
        "calendar.html", 
        {"request": request, "reservations": reservations}
    )

# Health check endpoint for Railway
@app.get("/health")
async def health_check():
    return {"status": "healthy"}