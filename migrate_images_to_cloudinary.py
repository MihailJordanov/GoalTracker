import os
import cloudinary
import cloudinary.uploader
from database.db import get_db_connection

# Cloudinary конфигурация
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET")
)

UPLOAD_PATH = os.path.join("static", "uploads", "enemy_teams")

def migrate_images():
    conn = get_db_connection()
    cur = conn.cursor()

    # Взимаме всички със стар локален път
    cur.execute("SELECT id, image FROM enemy_teams WHERE image LIKE 'enemy_teams/%'")
    rows = cur.fetchall()

    for enemy_id, image_path in rows:
        full_path = os.path.join(UPLOAD_PATH, os.path.basename(image_path))

        if not os.path.exists(full_path):
            print(f"❌ Image not found: {full_path}")
            continue

        print(f"📤 Uploading {full_path}...")
        result = cloudinary.uploader.upload(full_path)

        if 'secure_url' in result:
            cloud_url = result['secure_url']
            cur.execute("UPDATE enemy_teams SET image = %s WHERE id = %s", (cloud_url, enemy_id))
            print(f"✅ Updated ID {enemy_id} with {cloud_url}")
        else:
            print(f"⚠️ Upload failed for {image_path}")

    conn.commit()
    cur.close()
    conn.close()
    print("✅ Migration complete.")

if __name__ == "__main__":
    migrate_images()
