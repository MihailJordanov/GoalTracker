from flask import Blueprint, render_template
from database.db import get_db_connection

# ⚠️ Смени import-а според това откъде ги ползваш в проекта.
# Идеята е да са същите helper-и, които вече ползваш в win_rate.
from routes.win_rate import (
    get_logged_in_user_id,
    require_login_redirect,
    user_has_rights,
    no_rights_redirect
)

play_time_bp = Blueprint("play_time", __name__)


@play_time_bp.route("/play_time/<int:team_id>")
def play_time_view(team_id: int):
    user_id = get_logged_in_user_id()
    if not user_id:
        return require_login_redirect()

    allowed_team_id = user_has_rights(team_id, user_id)
    if not allowed_team_id:
        return no_rights_redirect()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Взимаме името на отбора
        cursor.execute("""
            SELECT id, name
            FROM teams
            WHERE id = %s
        """, (team_id,))
        team_row = cursor.fetchone()

        if not team_row:
            return "Отборът не беше намерен.", 404

        team_name = team_row[1]

        # Взимаме всички ИЗИГРАНИ мачове за отбора.
        #
        # Приемаме, че изигран мач = има дата И има въведен резултат
        # (home_team_result и away_team_result не са NULL).
        #
        # Ако при теб логиката е различна, кажи и ще я напасна.
        cursor.execute("""
            SELECT
                EXTRACT(YEAR FROM date)::int AS year,
                EXTRACT(MONTH FROM date)::int AS month
            FROM matches
            WHERE team_id = %s
              AND date IS NOT NULL
              AND home_team_result IS NOT NULL
              AND away_team_result IS NOT NULL
            ORDER BY date ASC
        """, (team_id,))

        rows = cursor.fetchall()

        # Месеци за chart labels
        month_labels = [
            "Януари", "Февруари", "Март", "Април", "Май", "Юни",
            "Юли", "Август", "Септември", "Октомври", "Ноември", "Декември"
        ]

        # Общо за всички години
        all_time_counts = [0] * 12

        # По години
        yearly_data = {}
        years_set = set()

        for year, month in rows:
            if not year or not month:
                continue

            years_set.add(year)

            month_index = month - 1
            all_time_counts[month_index] += 1

            if year not in yearly_data:
                yearly_data[year] = [0] * 12

            yearly_data[year][month_index] += 1

        years = sorted(list(years_set))

        return render_template(
            "play_time.html",
            team_id=team_id,
            team_name=team_name,
            month_labels=month_labels,
            years=years,
            all_time_counts=all_time_counts,
            yearly_data=yearly_data
        )

    finally:
        cursor.close()
        conn.close()