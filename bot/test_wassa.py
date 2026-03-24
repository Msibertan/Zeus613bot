import httpx
import asyncio

BLURIT_CLIENT_ID = "U2FsdGVkX1+jkGZppOj4nURTD0cL2jWqZJvxMNb+TWtvri1Ss5Ss1iN2mZVXS825yX9rr97yH3X7JvDf62GTQZfKIYIx2jpWScsw87ZTz5GfRTQ27kUMs2rx2S9C9R0+LTMufmc4R3L2Epbj0QoB2dOJJte6axV0V4ar8FBiJtHITrqYv9DTS8J2j10gKOi0RUDrDB+9P8ArgvjTOqB4904PG/lzrh13+eSu+b+FRFDIJudxs0cLyP1FjiQ7V3SxNjMNpASsayn56TspAS+hFLNkZGx0G7ipNQXsf7t91pi5mPnVMkROn0/ZDW9I0bb0IX3k6pzUYFu+eCZ7gAH1Nf/OGwJ5ZHXqLQ4AwrYC7LGLMZv4AT9cMnypRvbpDoeRyUzpx9gI6zE4AfpTkwGUsr4VcZjMsBjpe+XKDnx/VvU="
BLURIT_SECRET_ID = "U2FsdGVkX189rJtNXa4CZug+7PsBwBMRZ8KEinF6QGaKRhuAawA1jFiDjRGYOw/vYxFw9vvh+MvcM4FIbvMSqA9lNqJ7uO+6jMERYIjKoWAkFEHw4zzRhL6eJZg92J+8ZQkfzrGjQJALUklOjOXxqg5C1O9mfvTUgqIz8SNVzBJ0cEd3zt8KPXsTdWwoANVxU+m3s8rLxEi0sPFog2fW/g=="
login_url = "https://api.services.wassa.io/login"

async def main():
    async with httpx.AsyncClient() as client:
        print("Testing JSON:")
        try:
            r1 = await client.post(login_url, json={"clientId": BLURIT_CLIENT_ID, "secretId": BLURIT_SECRET_ID})
            print(r1.status_code, r1.text)
        except Exception as e: print("Error:", e)

        print("\nTesting form-urlencoded:")
        try:
            r2 = await client.post(login_url, data={"clientId": BLURIT_CLIENT_ID, "secretId": BLURIT_SECRET_ID})
            print(r2.status_code, r2.text)
        except Exception as e: print("Error:", e)

asyncio.run(main())
