"""
Firebase Admin SDK initialization.
Loads the service account credentials and initializes the SDK once.
"""

import firebase_admin
from firebase_admin import credentials

from app.core.config import settings
from app.core.logging import logger


_firebase_app = None


def initialize_firebase() -> None:
    """
    Initialize Firebase Admin SDK using service account credentials.

    The credentials file path is loaded from the FIREBASE_CREDENTIALS_PATH
    environment variable. This function is idempotent — calling it multiple
    times will not re-initialize the SDK.

    Security notes:
    - The service account JSON file should NEVER be committed to version control.
    - In production, use environment variables or a secret manager to inject
      the credentials path.
    - The .gitignore includes the credentials file by default.
    """
    global _firebase_app

    if _firebase_app is not None:
        logger.info("Firebase already initialized, skipping")
        return

    try:
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
        _firebase_app = firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized successfully")
    except FileNotFoundError:
        logger.warning(
            "Firebase credentials file not found at '%s'. "
            "FCM notifications will NOT work until the file is provided.",
            settings.FIREBASE_CREDENTIALS_PATH,
        )
    except Exception as e:
        logger.error("Failed to initialize Firebase: %s", str(e))
        raise
