from flask import Blueprint, redirect, url_for, flash
import os
import shutil

utility_bp = Blueprint('utility_bp', __name__)

@utility_bp.route('/move-images', methods=['POST'])
def move_images():
    source_dir = 'static/images'
    target_dir = 'static/uploads'

    os.makedirs(target_dir, exist_ok=True)

    moved = 0
    for filename in os.listdir(source_dir):
        source_path = os.path.join(source_dir, filename)
        target_path = os.path.join(target_dir, filename)

        if os.path.isfile(source_path):
            shutil.move(source_path, target_path)
            moved += 1

    flash(f'Moved {moved} images to uploads folder.', 'success')
    return redirect(url_for('auth.index'))  # или 'home_bp.home' или друга начална страница
