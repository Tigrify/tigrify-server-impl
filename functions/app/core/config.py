"""Application-wide constants, CORS origins, and OpenAPI metadata."""

from __future__ import annotations

DEFAULT_PROJECT_ID = "tigrify-515619"

VALID_ROLES = {"STUDENT", "PARENT", "OPERATOR", "ADMIN"}
VALID_DIFFICULTIES = {1, 2, 3}

ALLOWED_ORIGINS = [
    "https://tigrify-515619.web.app",
    "https://tigrify-515619.firebaseapp.com",
    "http://localhost:3000",
    "http://localhost:4200",
    "http://localhost:5000",
    "http://127.0.0.1:5000",
]

FIREBASE_INIT_URLS = (
    "https://tigrify-515619.web.app/__/firebase/init.json",
    "https://tigrify-515619.firebaseapp.com/__/firebase/init.json",
)

TAGS_METADATA = [
    {
        "name": "Authentication",
        "description": "Backend email/password registration, sign-in, token refresh, session inspection, and email verification handled via main.py.",
    },
    {
        "name": "Users",
        "description": "User CRUD management, role administration (STUDENT, PARENT, OPERATOR, ADMIN), profile synchronization, and student queries.",
    },
    {
        "name": "Lessons",
        "description": "Curriculum lesson CRUD management, transactional placement auto-incrementation, and example seeding.",
    },
    {
        "name": "Streams",
        "description": "Live and recorded interactive streams management and discovery.",
    },
    {
        "name": "Messages",
        "description": "Real-time stream chat messages and communications.",
    },
    {
        "name": "Interactions",
        "description": "Stream reactions, emoji cheers, likes, and engagement metrics.",
    },
    {
        "name": "System",
        "description": "Health checks, DB diagnostics, root info, and Swagger redirects.",
    },
]
