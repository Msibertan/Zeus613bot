import os

# Твой токен
BOT_TOKEN = os.getenv("BOT_TOKEN", "8592007803:AAHDfWgpUrzvzM360xIRr7Z6xIGpKP6SgzI")

NANO_BANANA_API_KEY = os.getenv("NANO_BANANA_API_KEY", "3961c6a6fe56aa412d504ac422176f83")
BLURIT_CLIENT_ID = os.getenv("BLURIT_CLIENT_ID", "U2FsdGVkX1+jkGZppOj4nURTD0cL2jWqZJvxMNb+TWtvri1Ss5Ss1iN2mZVXS825yX9rr97yH3X7JvDf62GTQZfKIYIx2jpWScsw87ZTz5GfRTQ27kUMs2rx2S9C9R0+LTMufmc4R3L2Epbj0QoB2dOJJte6axV0V4ar8FBiJtHITrqYv9DTS8J2j10gKOi0RUDrDB+9P8ArgvjTOqB4904PG/lzrh13+eSu+b+FRFDIJudxs0cLyP1FjiQ7V3SxNjMNpASsayn56TspAS+hFLNkZGx0G7ipNQXsf7t91pi5mPnVMkROn0/ZDW9I0bb0IX3k6pzUYFu+eCZ7gAH1Nf/OGwJ5ZHXqLQ4AwrYC7LGLMZv4AT9cMnypRvbpDoeRyUzpx9gI6zE4AfpTkwGUsr4VcZjMsBjpe+XKDnx/VvU=")
BLURIT_SECRET_ID = os.getenv("BLURIT_SECRET_ID", "U2FsdGVkX189rJtNXa4CZug+7PsBwBMRZ8KEinF6QGaKRhuAawA1jFiDjRGYOw/vYxFw9vvh+MvcM4FIbvMSqA9lNqJ7uO+6jMERYIjKoWAkFEHw4zzRhL6eJZg92J+8ZQkfzrGjQJALUklOjOXxqg5C1O9mfvTUgqIz8SNVzBJ0cEd3zt8KPXsTdWwoANVxU+m3s8rLxEi0sPFog2fW/g==")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "sk_c90dd8514179da338e3ac34acdc695291ee8a9a43f32b8fa")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://nonnephritic-minda-logarithmically.ngrok-free.dev")

# Админы (полный доступ)
ADMIN_IDS = [7291312605]

# Белый список
WHITELIST_ENABLED = True
WHITELIST_IDS = [8523013758
    # Сюда можно добавлять ID сотрудников через запятую, если нужно
]

# ID ГРУППЫ для логов (Обязательно с минусом!)
# Сюда будут приходить отчеты о созданных договорах
LOG_CHAT_ID = -1003594991783
NETLIFY_TOKEN = "nfp_MBVJEhcrHqcx6ovXt4qzQhtt3BY9sQjd6ea5"
NETLIFY_SITE_ID = "595e38c4-0a21-4f1a-9901-df6c72eac2d4"