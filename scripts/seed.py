import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app
from app.extensions import db
from app.services.seed_service import seed_data_if_empty


def seed():
    app = create_app()
    with app.app_context():
        db.create_all()
        created = seed_data_if_empty()
        print("Seed complete!" if created else "Database already has data — nothing seeded.")


if __name__ == '__main__':
    seed()