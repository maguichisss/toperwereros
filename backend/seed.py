"""Idempotent seed script for the store catalog database.

Seeds categories, colors, roles, and the default admin user.
Safe to run multiple times — skips existing records.
"""

import os

from app.database import SessionLocal
from app.models import Category, Color, Role, User
from app.auth import hash_password


def seed_categories(db) -> None:
    categories = ["Varios", "Tazon", "Botella", "Jarra", "Vaso", "Plato", "Termo", "Cubiertos"]
    for name in categories:
        if not db.query(Category).filter(Category.name == name).first():
            db.add(Category(name=name))
    db.commit()
    print("Categories seeded.")


def seed_colors(db) -> None:
    colors = [
        ("rojo", "#FF0000"), ("naranja", "#FF6600"), ("vino", "#722F37"),
        ("fucsia", "#FF00FF"), ("rosa mexicano", "#E4007C"), ("mamey", "#FF8C42"),
        ("melon", "#FEBAAD"), ("rosa", "#FFC0CB"), ("durazno", "#FFDAB9"),
        ("zanahoria", "#ED9121"), ("salmon", "#FA8072"), ("verde", "#00AA00"),
        ("verde limon", "#BFFF00"), ("verde bandera", "#006341"), ("verde militar", "#4B5320"),
        ("verde oliva", "#808000"), ("azul", "#0000FF"), ("azul marino", "#000080"),
        ("azul cielo", "#87CEEB"), ("azul rey", "#4169E1"), ("azul claro", "#ADD8E6"),
        ("morado", "#800080"), ("lila", "#C8A2C8"), ("violeta", "#8B00FF"),
        ("amarillo", "#FFFF00"), ("dorado", "#FFD700"), ("plateado", "#C0C0C0"),
        ("beige", "#F5F5DC"), ("hueso", "#E3DAC9"), ("gris", "#808080"),
        ("negro", "#000000"), ("blanco", "#FFFFFF"),
    ]
    for name, hex_code in colors:
        if not db.query(Color).filter(Color.name == name).first():
            db.add(Color(name=name, hex=hex_code))
    db.commit()
    print(f"{len(colors)} colors seeded.")


def seed_roles_and_admin(db) -> None:
    for name in ("admin", "employee", "viewer"):
        if not db.query(Role).filter(Role.name == name).first():
            db.add(Role(name=name))
    db.flush()

    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if not db.query(User).filter(User.username == "admin").first():
        default_pw = os.environ.get("DEFAULT_ADMIN_PASSWORD", "admin123")
        db.add(User(
            username="admin",
            hashed_password=hash_password(default_pw),
            role_id=admin_role.id,
            active=True,
        ))
    db.commit()
    print("Roles and admin user seeded.")


def run_all() -> None:
    db = SessionLocal()
    try:
        seed_categories(db)
        seed_colors(db)
        seed_roles_and_admin(db)
    finally:
        db.close()


if __name__ == "__main__":
    run_all()
