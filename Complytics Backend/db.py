from motor.motor_asyncio import AsyncIOMotorClient
from config import settings

class Database:
    client: AsyncIOMotorClient = None
    db = None

    async def connect(self):
        self.client = AsyncIOMotorClient(settings.MONGODB_URL)
        self.db = self.client[settings.MONGODB_NAME]
        print("Connected to MongoDB")

    async def disconnect(self):
        self.client.close()
        print("Disconnected from MongoDB")

database = Database()