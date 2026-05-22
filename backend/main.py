from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel

#7777777777777777

# Настройки БД
DATABASE_URL = "sqlite:///./sql_app.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class DBItem(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, nullable=True)

Base.metadata.create_all(bind=engine)

class ItemBase(BaseModel):
    title: str
    description: str | None = None

class ItemCreate(ItemBase):
    pass

class ItemResponse(ItemBase):
    id: int
    class Config:
        from_attributes = True

# Инициализация FastAPI
app = FastAPI(title="FastAPI CRUD App (No Nginx)", docs_url="/docs")

# --- НАСТРОЙКА ВСТРОЕННОГО ПРОКСИ / МИДЛВАРЕ ---
# Защита от HTTP Host Header attacks (заменяет базовый функционал прокси)
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["*"]  # В продакшене замени на свой домен, например: ["yourdomain.com", "localhost"]
)

# CORS-проксирование (разрешаем запросы с фронтенда/других сервисов)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- CRUD ЗАПРОСЫ ---

# POST
@app.post("/items", response_model=ItemResponse, status_code=201)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    db_item = DBItem(title=item.title, description=item.description)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

# GET
@app.get("/items", response_model=list[ItemResponse])
def read_items(db: Session = Depends(get_db)):
    return db.query(DBItem).all()

# PUT
@app.put("/items/{item_id}", response_model=ItemResponse)
def update_item(item_id: int, updated_item: ItemCreate, db: Session = Depends(get_db)):
    db_item = db.query(DBItem).filter(DBItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    db_item.title = updated_item.title
    db_item.description = updated_item.description
    db.commit()
    db.refresh(db_item)
    return db_item

# DELETE
@app.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    db_item = db.query(DBItem).filter(DBItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(db_item)
    db.commit()
    return None