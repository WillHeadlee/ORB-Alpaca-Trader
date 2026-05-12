#!/usr/bin/env python3

import sys
import os
import getpass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal
from backend.models import User
from backend.auth import get_password_hash

def create_user():
    print("Create Dashboard User")
    print("=" * 40)

    username = input("Username: ")
    password = getpass.getpass("Password: ")
    password_confirm = getpass.getpass("Confirm Password: ")

    if password != password_confirm:
        print("Passwords don't match!")
        sys.exit(1)

    if len(password) < 8:
        print("Password must be at least 8 characters!")
        sys.exit(1)

    db = SessionLocal()

    existing = db.query(User).filter(User.username == username).first()
    if existing:
        print(f"User '{username}' already exists!")
        db.close()
        sys.exit(1)

    new_user = User(username=username, password_hash=get_password_hash(password))
    db.add(new_user)
    db.commit()
    print(f"User '{username}' created successfully!")
    db.close()

if __name__ == '__main__':
    create_user()
