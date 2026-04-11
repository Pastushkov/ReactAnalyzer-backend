from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Smart React Analyzer API")

# Налаштування CORS, щоб твій React-фронтенд міг робити запити сюди
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # У продакшені тут буде URL твого фронтенду (напр. "http://localhost:3000")
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Smart React Analyzer Backend is running!"}

# Тестовий ендпоінт для перевірки
@app.get("/health")
def health_check():
    return {"status": "ok"}