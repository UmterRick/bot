#!/usr/bin/env python
"""Create a new admin user able to view the /reports endpoint."""
from getpass import getpass
import sys

from flask import current_app
from app import app, db, UserLogin
from werkzeug.security import generate_password_hash


def main():
    """Main entry point for script."""
    with app.app_context():
        db.metadata.create_all(db.engine)
        if UserLogin.query.all():
            print('A user already exists! Create another? (y/n):', )
            create = input()
            if create == 'n':
                return

        print('Enter name: ', )
        name = input()
        password = getpass()
        assert password == getpass('Password (again):')

        user = UserLogin(
            login=name,
            password=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        print('User added.')


if __name__ == '__main__':
    sys.exit(main())
