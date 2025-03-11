import time
from pymongo import MongoClient

# Настройка MongoDB
MONGO_URI = "mongodb://root:pass@mongo:27017/"
mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client["ozon"]
mongo_products_collection = mongo_db["products"]

# Загрузка тестовых данных
def load_test_data():
    print("Loading test data...")
    def add_product(id, name, price):
        product = mongo_products_collection.find_one({"id": id})  # Проверяем по id
        if not product:
            print(f"Adding product: {name}")
            product = {
                "id": id,
                "name": name,
                "price": price,
            }
            mongo_products_collection.insert_one(product)
        else:
            print(f"Product with id {id} already exists: {product}")

    add_product(1, "Laptop", 999.99)
    add_product(2, "Smartphone", 499.99)
    add_product(3, "Headphones", 149.99)

def wait_for_db(retries=20, delay=10):  # Увеличиваем количество попыток и задержку
    for _ in range(retries):
        try:
            mongo_client.admin.command('ismaster')
            print("MongoDB is ready!")
            return
        except Exception as e:
            print(f"MongoDB not ready yet: {e}")
            time.sleep(delay)
    raise Exception("Could not connect to MongoDB")

if __name__ == "__main__":
    wait_for_db()
    load_test_data()