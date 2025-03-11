from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.ext.declarative import declarative_base
from pymongo import MongoClient
from redis import Redis

# Настройка SQLAlchemy (PostgreSQL)
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:archdb@db/ozon_db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Подключение к MongoDB
MONGO_URI = "mongodb://root:pass@mongo:27017/"
mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client["ozon"]
mongo_products_collection = mongo_db["products"]

# Подключение к Redis
REDIS_URL = "redis://redis:6379"
redis_client = Redis.from_url(REDIS_URL)

# Модель пользователя
class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    hashed_password = Column(String)
    email = Column(String, unique=True, index=True)

# Модель элемента корзины
class CartItemDB(Base):
    __tablename__ = "cart_items"
    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey("carts.id"))
    product_id = Column(Integer)
    quantity = Column(Integer)

# Модель корзины
class CartDB(Base):
    __tablename__ = "carts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    items = relationship("CartItemDB", backref="cart")

# Создание таблиц в базе данных
Base.metadata.create_all(bind=engine)

# Настройка FastAPI
app = FastAPI()

# Настройка паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Настройка OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Секретный ключ для подписи JWT
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Зависимость для получения сессии базы данных
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Модели Pydantic
class User(BaseModel):
    id: int
    username: str
    first_name: str
    last_name: str
    hashed_password: str
    email: str

    class Config:
        from_attributes = True

class Product(BaseModel):
    id: int
    name: str
    price: float

    class Config:
        from_attributes = True

class CartItem(BaseModel):
    product_id: int
    quantity: int

    class Config:
        from_attributes = True

class Cart(BaseModel):
    user_id: int
    items: List[CartItem]

    class Config:
        from_attributes = True

# Функции для работы с Redis
def get_user_from_cache(username: str) -> Optional[User]:
    cached_user = redis_client.get(f"user:{username}")
    if cached_user:
        return User.parse_raw(cached_user)
    return None

def cache_user(user: User):
    redis_client.set(f"user:{user.username}", user.json(), ex=3600)  # Кешируем на 1 час

def invalidate_user_cache(username: str):
    redis_client.delete(f"user:{username}")

# Зависимости для получения текущего пользователя
async def get_current_client(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        user = db.query(UserDB).filter(UserDB.username == username).first()
        if user is None:
            raise credentials_exception
        return user
    except JWTError:
        raise credentials_exception

# Создание и проверка JWT токенов
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Маршрут для получения токена
@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.username == form_data.username).first()
    if not user or not pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Создание нового пользователя
@app.post("/users", response_model=User)
def create_user(user: User, db: Session = Depends(get_db)):
    db_user = db.query(UserDB).filter(UserDB.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="User already exists")
    hashed_password = pwd_context.hash(user.hashed_password)
    db_user = UserDB(
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        hashed_password=hashed_password,
        email=user.email,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Инвалидируем кеш
    invalidate_user_cache(user.username)
    return db_user

# Поиск пользователя по логину
@app.get("/users/{username}", response_model=User)
def get_user_by_username(username: str, db: Session = Depends(get_db)):
    # Проверяем кеш
    cached_user = get_user_from_cache(username)
    if cached_user:
        return cached_user

    # Если нет в кеше, запрашиваем из PostgreSQL
    user = db.query(UserDB).filter(UserDB.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Сохраняем в кеш
    user_model = User.from_orm(user)
    cache_user(user_model)
    return user_model

# Поиск пользователя по маске имени и фамилии
@app.get("/users", response_model=List[User])
def search_users_by_name(
    first_name: str, last_name: str, db: Session = Depends(get_db)
):
    users = db.query(UserDB).filter(
        UserDB.first_name.ilike(f"%{first_name}%"),
        UserDB.last_name.ilike(f"%{last_name}%")
    ).all()

    # Кешируем каждого пользователя
    for user in users:
        user_model = User.from_orm(user)
        cache_user(user_model)

    return users

# Создание продукта
@app.post("/products", response_model=Product)
def create_product(product: Product):
    existing_product = mongo_products_collection.find_one({"id": product.id})
    if existing_product:
        raise HTTPException(status_code=400, detail="Product already exists")
    product_dict = product.dict()
    mongo_products_collection.insert_one(product_dict)
    return product

# Получение продукта по id
@app.get("/products/{product_id}", response_model=Product)
def get_product(product_id: int):
    product = mongo_products_collection.find_one({"id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

# Добавление товара в корзину
@app.post("/carts/{user_id}/items", response_model=Cart)
def add_to_cart(user_id: int, item: CartItem, db: Session = Depends(get_db)):
    # Проверяем, существует ли продукт в MongoDB
    product = mongo_products_collection.find_one({"id": item.product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Проверяем, существует ли корзина у пользователя
    cart = db.query(CartDB).filter(CartDB.user_id == user_id).first()
    if not cart:
        cart = CartDB(user_id=user_id)
        db.add(cart)
        db.commit()
        db.refresh(cart)

    # Добавляем товар в корзину
    cart_item = CartItemDB(cart_id=cart.id, product_id=item.product_id, quantity=item.quantity)
    db.add(cart_item)
    db.commit()
    db.refresh(cart_item)
    return cart

# Получение корзины для пользователя
@app.get("/carts/{user_id}", response_model=Cart)
def get_cart(user_id: int, db: Session = Depends(get_db)):
    cart = db.query(CartDB).filter(CartDB.user_id == user_id).first()
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")

    # Получаем товары из MongoDB
    cart_items = []
    for item in cart.items:
        product = mongo_products_collection.find_one({"id": item.product_id})
        if product:
            cart_items.append(CartItem(product_id=item.product_id, quantity=item.quantity))

    return Cart(user_id=cart.user_id, items=cart_items)

# Запуск сервера
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)