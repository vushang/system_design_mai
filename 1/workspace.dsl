workspace {
    name "Магазин Ozon"
    description "Система для управления пользователями, товарами и корзинами"

    !identifiers hierarchical

    model {
        user = person "Пользователь" {
            description "Пользователь магазина Ozon"
        }

        admin = person "Администратор" {
            description "Администратор магазина Ozon"
        }

        system = softwareSystem "Магазин Ozon" {
            description "Система для управления пользователями, товарами и корзинами"

            webApp = container "Web-приложение" {
                description "Позволяет пользователям взаимодействовать с магазином через браузер"
                technology "React, JavaScript"
            }

            apiGateway = container "API Gateway" {
                description "Обеспечивает доступ к бизнес-логике"
                technology "Node.js, Express"
            }

            userService = container "User Service" {
                description "Сервис управления пользователями"
                technology "Java Spring Boot"
            }

            productService = container "Product Service" {
                description "Сервис управления товарами"
                technology "Java Spring Boot"
            }

            cartService = container "Cart Service" {
                description "Сервис управления корзинами"
                technology "Java Spring Boot"
            }

            database = container "База данных" {
                description "Хранит информацию о пользователях, товарах и корзинах"
                technology "PostgreSQL"
            }

            // Взаимодействие пользователя с системой
            user -> webApp "Использует для взаимодействия"
            admin -> webApp "Использует для управления"
            webApp -> apiGateway "Запросы к API"
            apiGateway -> userService "Запросы на управление пользователями" "HTTPS"
            apiGateway -> productService "Запросы на управление товарами" "HTTPS"
            apiGateway -> cartService "Запросы на управление корзинами" "HTTPS"
            userService -> database "Чтение/Запись данных" "JDBC"
            productService -> database "Чтение/Запись данных" "JDBC"
            cartService -> database "Чтение/Запись данных" "JDBC"

            // Основные сценарии использования
            user -> webApp "Создание нового пользователя"
            webApp -> apiGateway "POST /users"
            apiGateway -> userService "POST /users"
            userService -> database "INSERT INTO users"

            user -> webApp "Поиск пользователя по логину"
            webApp -> apiGateway "GET /users?login={login}"
            apiGateway -> userService "GET /users?login={login}"
            userService -> database "SELECT * FROM users WHERE login={login}"

            user -> webApp "Поиск пользователя по маске имени и фамилии"
            webApp -> apiGateway "GET /users?name={name}&surname={surname}"
            apiGateway -> userService "GET /users?name={name}&surname={surname}"
            userService -> database "SELECT * FROM users WHERE name LIKE {name} AND surname LIKE {surname}"

            user -> webApp "Создание товара"
            webApp -> apiGateway "POST /products"
            apiGateway -> productService "POST /products"
            productService -> database "INSERT INTO products"

            user -> webApp "Получение списка товаров"
            webApp -> apiGateway "GET /products"
            apiGateway -> productService "GET /products"
            productService -> database "SELECT * FROM products"

            user -> webApp "Добавление товара в корзину"
            webApp -> apiGateway "POST /carts/{userId}/items"
            apiGateway -> cartService "POST /carts/{userId}/items"
            cartService -> database "INSERT INTO cart_items"

            user -> webApp "Получение корзины для пользователя"
            webApp -> apiGateway "GET /carts/{userId}"
            apiGateway -> cartService "GET /carts/{userId}"
            cartService -> database "SELECT * FROM cart_items WHERE userId={userId}"
        }
    }
    
    views {
        themes default

        systemContext system {
            include *
            autolayout lr
        }

        container system {
            include *
            autolayout lr
        }

        dynamic system "createUser" "Создание нового пользователя" {
            user -> system.webApp "Создаёт нового пользователя"
            system.webApp -> system.apiGateway "POST /users"
            system.apiGateway -> system.userService "POST /users"
            system.userService -> system.database "INSERT INTO users"
            autolayout lr
        }

        dynamic system "findUserByLogin" "Поиск пользователя по логину" {
            user -> system.webApp "Ищет пользователя по логину"
            system.webApp -> system.apiGateway "GET /users?login={login}"
            system.apiGateway -> system.userService "GET /users?login={login}"
            system.userService -> system.database "SELECT * FROM users WHERE login={login}"
            autolayout lr
        }

        dynamic system "findUserByName" "Поиск пользователя по маске имени и фамилии" {
            user -> system.webApp "Ищет пользователя по имени и фамилии"
            system.webApp -> system.apiGateway "GET /users?name={name}&surname={surname}"
            system.apiGateway -> system.userService "GET /users?name={name}&surname={surname}"
            system.userService -> system.database "SELECT * FROM users WHERE name LIKE {name} AND surname LIKE {surname}"
            autolayout lr
        }

        dynamic system "createProduct" "Создание товара" {
            user -> system.webApp "Создаёт товар"
            system.webApp -> system.apiGateway "POST /products"
            system.apiGateway -> system.productService "POST /products"
            system.productService -> system.database "INSERT INTO products"
            autolayout lr
        }

        dynamic system "getProducts" "Получение списка товаров" {
            user -> system.webApp "Запрашивает список товаров"
            system.webApp -> system.apiGateway "GET /products"
            system.apiGateway -> system.productService "GET /products"
            system.productService -> system.database "SELECT * FROM products"
            autolayout lr
        }

        dynamic system "addToCart" "Добавление товара в корзину" {
            user -> system.webApp "Добавляет товар в корзину"
            system.webApp -> system.apiGateway "POST /carts/{userId}/items"
            system.apiGateway -> system.cartService "POST /carts/{userId}/items"
            system.cartService -> system.database "INSERT INTO cart_items"
            autolayout lr
        }

        dynamic system "getCart" "Получение корзины для пользователя" {
            user -> system.webApp "Запрашивает корзину"
            system.webApp -> system.apiGateway "GET /carts/{userId}"
            system.apiGateway -> system.cartService "GET /carts/{userId}"
            system.cartService -> system.database "SELECT * FROM cart_items WHERE userId={userId}"
            autolayout lr
        }

        theme default
    }
}