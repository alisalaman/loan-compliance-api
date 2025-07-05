import os
import dotenv

dotenv.load_dotenv()


class Settings:
    COHERE_API_KEY = os.getenv("COHERE_API_KEY")
    COHERE_EMBEDDING_MODEL = os.getenv("COHERE_EMBEDDING_MODEL")
    QDRANT_HOST = os.getenv("QDRANT_HOST")
    QDRANT_PORT = os.getenv("QDRANT_PORT")
    REGULATIONS_DIR = os.getenv("REGULATIONS_DIR", "output")


settings = Settings()
