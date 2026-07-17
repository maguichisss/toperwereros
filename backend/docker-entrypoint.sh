#!/bin/sh
set -e

echo "Waiting for database..."
for i in $(seq 1 30); do
  python -c "
from app.database import engine
try:
    conn = engine.connect()
    conn.close()
    print('Database available')
    exit(0)
except Exception as e:
    exit(1)
" 2>/dev/null && break
  echo "  attempt $i/30 — retrying in 2s..."
  sleep 2
done
echo "Database is ready."

echo "Creating database tables..."
python -c "
from app.database import engine, Base
from app.models import Color, Category, Product, Sale, SaleItem, Customer, Layaway, LayawayItem, LayawayPayment
Base.metadata.create_all(engine)
print('Tables created successfully.')
"

echo "Migrating to many-to-many categories..."
python -c "
from app.database import engine
from sqlalchemy import text, inspect

inspector = inspect(engine)
columns = [c['name'] for c in inspector.get_columns('products')]

if 'category_id' in columns:
    with engine.connect() as conn:
        conn.execute(text('''
            INSERT INTO product_categories (product_id, category_id)
            SELECT id, category_id FROM products WHERE category_id IS NOT NULL
            ON CONFLICT DO NOTHING
        '''))
        conn.execute(text('ALTER TABLE products DROP COLUMN category_id'))
        conn.commit()
    print('Migration completed: product_categories populated, category_id dropped.')
else:
    print('Migration already applied, skipping.')
"

echo "Seeding categories..."
python -c "
from app.database import SessionLocal
from app.models import Category

categories = ['Varios', 'Tazon', 'Botella', 'Jarra', 'Vaso', 'Plato', 'Termo', 'Cubiertos']
db = SessionLocal()
try:
    for name in categories:
        existing = db.query(Category).filter(Category.name == name).first()
        if not existing:
            db.add(Category(name=name))
    db.commit()
    print('Categories seeded successfully.')
finally:
    db.close()
"

echo "Seeding colors..."
python -c "
from app.database import SessionLocal
from app.models import Color

colors = [
    ('rojo', '#FF0000'), ('naranja', '#FF6600'), ('vino', '#722F37'),
    ('fucsia', '#FF00FF'), ('rosa mexicano', '#E4007C'), ('mamey', '#FF8C42'),
    ('melon', '#FEBAAD'), ('rosa', '#FFC0CB'), ('durazno', '#FFDAB9'),
    ('zanahoria', '#ED9121'), ('salmon', '#FA8072'), ('verde', '#00AA00'),
    ('verde limon', '#BFFF00'), ('verde bandera', '#006341'), ('verde militar', '#4B5320'),
    ('verde oliva', '#808000'), ('azul', '#0000FF'), ('azul marino', '#000080'),
    ('azul cielo', '#87CEEB'), ('azul rey', '#4169E1'), ('azul claro', '#ADD8E6'),
    ('morado', '#800080'), ('lila', '#C8A2C8'), ('violeta', '#8B00FF'),
    ('amarillo', '#FFFF00'), ('dorado', '#FFD700'), ('plateado', '#C0C0C0'),
    ('beige', '#F5F5DC'), ('hueso', '#E3DAC9'), ('gris', '#808080'),
    ('negro', '#000000'), ('blanco', '#FFFFFF'),
]

db = SessionLocal()
try:
    for name, hex in colors:
        existing = db.query(Color).filter(Color.name == name).first()
        if not existing:
            db.add(Color(name=name, hex=hex))
    db.commit()
    print(f'{len(colors)} colors seeded successfully.')
finally:
    db.close()
"

exec "$@"
