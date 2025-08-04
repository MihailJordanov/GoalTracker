import os
import psycopg2
import cloudinary
import cloudinary.uploader
from PIL import Image

# === Настрой Cloudinary ===
cloudinary.config(
    cloud_name="diael5zdg",
    api_key="856348268889796",
    api_secret="79r4BETBHkb4UigPjbmGNvaPj9o"
)

# === Настрой връзка към Render база ===
conn = psycopg2.connect("postgresql://goaltracker_db_eu_user:kPPHMGnWrx5wHsYwXKvY3lnmPTOCLs9D@dpg-d25lph7diees73c20q00-a.frankfurt-postgres.render.com/goaltracker_db_eu?sslmode=require")
cur = conn.cursor()

# === Извлечи enemy teams ===
cur.execute("SELECT id, image FROM enemy_teams")
rows = cur.fetchall()

for row in rows:
    id_, image = row
    local_path = os.path.join("static", "uploads", "enemy_teams", image)
    if not os.path.exists(local_path):
        print(f"❌ File not found: {local_path}")
        continue

    file_ext = os.path.splitext(image)[1].lower()
    if file_ext in [".jpg", ".jpeg"]:
        # Конвертирай в PNG временно
        try:
            with Image.open(local_path) as im:
                png_path = os.path.splitext(local_path)[0] + ".png"
                im.save(png_path, "PNG")
                local_path = png_path
        except Exception as e:
            print(f"⚠️ Failed to convert {image} to PNG: {e}")
            continue

    print(f"📤 Uploading {local_path}...")

    try:
        result = cloudinary.uploader.upload(local_path)
        cloud_url = result['secure_url']
        cur.execute("UPDATE enemy_teams SET image = %s WHERE id = %s", (cloud_url, id_))
        print(f"✅ Updated ID {id_} with {cloud_url}")
    except Exception as e:
        print(f"❌ Failed to upload {local_path}: {e}")

# === Запази промените ===
conn.commit()
cur.close()
conn.close()

print("✅ Migration complete.")
