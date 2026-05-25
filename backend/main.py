from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel

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
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["*"]  
)

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

# --- ДОПОЛНИТЕЛЬНЫЕ ЭНДПОИНТЫ ДЛЯ ТЕСТА СБОРКИ ---

@app.get("/health", tags=["System"])
def health_check():
    """Эндпоинт для проверки того, что контейнер успешно поднялся и работает"""
    return {"status": "healthy", "message": "FastAPI pipeline works perfectly!"}

# --- CRUD ЗАПРОСЫ ---

# POST
@app.post("/items", response_model=ItemResponse, status_code=201, tags=["Items"])
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    db_item = DBItem(title=item.title, description=item.description)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

# GET ALL (С поиском)
@app.get("/items", response_model=list[ItemResponse], tags=["Items"])
def read_items(search: str | None = None, db: Session = Depends(get_db)):
    """Получает все элементы. Можно отфильтровать: /items?search=название"""
    query = db.query(DBItem)
    if search:
        query = query.filter(DBItem.title.contains(search))
    return query.all()

# GET BY ID (Новый метод)
@app.get("/items/{item_id}", response_model=ItemResponse, tags=["Items"])
def read_item_by_id(item_id: int, db: Session = Depends(get_db)):
    """Получение одного конкретного элемента по его ID"""
    db_item = db.query(DBItem).filter(DBItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail=f"Item with id {item_id} not found")
    return db_item

# PUT
@app.put("/items/{item_id}", response_model=ItemResponse, tags=["Items"])
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
@app.delete("/items/{item_id}", status_code=204, tags=["Items"])
def delete_item(item_id: int, db: Session = Depends(get_db)):
    db_item = db.query(DBItem).filter(DBItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(db_item)
    db.commit()
    return None