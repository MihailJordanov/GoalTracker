from flask import Blueprint, render_template
from database.db import get_db_connection

# Смени import-а ако helper функциите са в друг файл
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
        cursor.execute("""
            SELECT id, name
            FROM teams
            WHERE id = %s
        """, (team_id,))
        team_row = cursor.fetchone()

        if not team_row:
            return "Team not found.", 404

        team_name = team_row[1]

        cursor.execute("""
            SELECT
                date
            FROM matches
            WHERE team_id = %s
              AND date IS NOT NULL
              AND home_team_result IS NOT NULL
              AND away_team_result IS NOT NULL
            ORDER BY date ASC
        """, (team_id,))

        rows = cursor.fetchall()

        month_labels = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]

        yearly_data = {}
        years_set = set()

        timeline_map = {}

        for row in rows:
            match_date = row[0]
            if not match_date:
                continue

            year = match_date.year
            month = match_date.month
            month_index = month - 1

            years_set.add(year)

            if year not in yearly_data:
                yearly_data[year] = [0] * 12
            yearly_data[year][month_index] += 1

            key = f"{year}-{month:02d}"
            timeline_map[key] = timeline_map.get(key, 0) + 1

        years = sorted(list(years_set))

        # Пълна месечна линия от първата до последната дата
        all_time_labels = []
        all_time_counts = []

        if rows:
            first_date = rows[0][0]
            last_date = rows[-1][0]

            current_year = first_date.year
            current_month = first_date.month

            end_year = last_date.year
            end_month = last_date.month

            while (current_year < end_year) or (current_year == end_year and current_month <= end_month):
                key = f"{current_year}-{current_month:02d}"
                all_time_labels.append(key)
                all_time_counts.append(timeline_map.get(key, 0))

                current_month += 1
                if current_month > 12:
                    current_month = 1
                    current_year += 1

        return render_template(
            "play_time.html",
            team_id=team_id,
            team_name=team_name,
            month_labels=month_labels,
            years=years,
            yearly_data=yearly_data,
            all_time_labels=all_time_labels,
            all_time_counts=all_time_counts
        )

    finally:
        cursor.close()
        conn.close()