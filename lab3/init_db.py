from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from jwt import Base, UserDB, ProductDB, CartDB, CartItemDB
from passlib.context import CryptContext

# Настройка PostgreSQL
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:archdb@db/ozon_db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Настройка паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Создание таблиц
Base.metadata.create_all(bind=engine)

def load_test_data():
    db = SessionLocal()

    # Проверка существования пользователя перед добавлением
    def add_user(username, first_name, last_name, hashed_password, email):
        user = db.query(UserDB).filter(UserDB.email == email).first()
        if not user:
            user = UserDB(
                username=username,
                first_name=first_name,
                last_name=last_name,
                hashed_password=hashed_password,
                email=email,
            )
            db.add(user)
            db.commit()  # Сохраняем пользователя сразу
            return user
        return user

    # Создание пользователей
    admin = add_user(
        username="admin",
        first_name="Admin",
        last_name="Admin",
        hashed_password=pwd_context.hash("admin123"),
        email="admin@ozon.com",
    )

    user1 = add_user(
        username="user1",
        first_name="Ivan",
        last_name="Ivanov",
        hashed_password=pwd_context.hash("user123"),
        email="ivan.ivanov@ozon.com",
    )

    user2 = add_user(
        username="user2",
        first_name="Kirill",
        last_name="Kotov",
        hashed_password=pwd_context.hash("user456"),
        email="kirill.kotov@ozon.com",
    )

    # Проверка существования продукта перед добавлением
    def add_product(name, price):
        product = db.query(ProductDB).filter(ProductDB.name == name).first()
        if not product:
            product = ProductDB(
                name=name,
                price=price,
            )
            db.add(product)
            db.commit()  # Сохраняем продукт сразу
            return product
        return product

    # Создание продуктов
    laptop = add_product("Laptop", 999.99)
    smartphone = add_product("Smartphone", 499.99)
    headphones = add_product("Headphones", 149.99)

    # Проверка существования корзины перед добавлением
    def add_cart(user_id):
        cart = db.query(CartDB).filter(CartDB.user_id == user_id).first()
        if not cart:
            cart = CartDB(user_id=user_id)
            db.add(cart)
            db.commit()  # Сохраняем корзину сразу
            return cart
        return cart

    # Создание корзин
    admin_cart = add_cart(admin.id)  # Корзина для admin
    user1_cart = add_cart(user1.id)  # Корзина для user1
    user2_cart = add_cart(user2.id)  # Корзина для user2

    # Проверка существования элемента корзины перед добавлением
    def add_cart_item(cart_id, product_id, quantity):
        cart_item = db.query(CartItemDB).filter(
            CartItemDB.cart_id == cart_id,
            CartItemDB.product_id == product_id
        ).first()
        if not cart_item:
            cart_item = CartItemDB(
                cart_id=cart_id,
                product_id=product_id,
                quantity=quantity,
            )
            db.add(cart_item)
            db.commit()  # Сохраняем элемент корзины сразу
            return cart_item
        return cart_item

    # Создание элементов корзины
    add_cart_item(admin_cart.id, laptop.id, 1)  # Laptop in admin's cart
    add_cart_item(user1_cart.id, smartphone.id, 2)  # Smartphone in user1's cart
    add_cart_item(user2_cart.id, headphones.id, 1)  # Headphones in user2's cart

    db.close()

if __name__ == "__main__":
    load_test_data()