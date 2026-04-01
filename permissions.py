import json
import os
from config import OWNER_ID

PERMIT_FILE = "permitted_users.json"


def load_permitted():
    if not os.path.exists(PERMIT_FILE):
        return set()
    with open(PERMIT_FILE, "r") as f:
        data = json.load(f)
    return set(data.get("users", []))


def save_permitted(users: set):
    with open(PERMIT_FILE, "w") as f:
        json.dump({"users": list(users)}, f)


def is_permitted(user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    return user_id in load_permitted()


def permit_user(user_id: int) -> bool:
    users = load_permitted()
    if user_id in users:
        return False  # already permitted
    users.add(user_id)
    save_permitted(users)
    return True


def revoke_user(user_id: int) -> bool:
    users = load_permitted()
    if user_id not in users:
        return False
    users.discard(user_id)
    save_permitted(users)
    return True


def list_permitted() -> list:
    return list(load_permitted())
