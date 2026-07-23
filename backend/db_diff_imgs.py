import os
import argparse
from app.database import SessionLocal
from app.config import UPLOAD_DIR
from app.models import Product

parser = argparse.ArgumentParser()
parser.add_argument("--delete", action="store_true", help="Delete orphan images on disk not found in DB")
args = parser.parse_args()

db = SessionLocal()
referenced = set()
missing_files = []
products = db.query(Product).filter(Product.image_url.isnot(None)).all()
for p in products:
    filename = p.image_url.replace("/uploads/", "")
    referenced.add(filename)
    filepath = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(filepath):
        missing_files.append(filename)

on_disk = {f for f in os.listdir(UPLOAD_DIR) if f != ".gitkeep"}

print(f"Checking DB... Images in table products image_url not found on disk ({len(missing_files)}):")
if missing_files:
    for f in sorted(missing_files):
        print(f"  {f}")
else:
    print("  None found.")

print()

orphans = on_disk - referenced
print(f"Checking uploads/... Images on disk not found in DB products.image_url ({len(orphans)}):")
if orphans:
    for f in sorted(orphans):
        print(f"  {f}")

    if args.delete:
        print()
        for f in sorted(orphans):
            path = os.path.join(UPLOAD_DIR, f)
            os.remove(path)
            print(f"Deleted: {f}")
        print(f"Deleted {len(orphans)} orphan images.")
else:
    print("  None found.")

db.close()

# run script in docker
# docker compose exec backend python db_diff_imgs.py
