import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import os

# Streamlit Page Config
st.set_page_config(page_title="NHL Analytics Hub", page_icon="🏒", layout="wide")

DB_NAME = "NHL_Analytics_Hub.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def get_data(query, params=None):
    conn = get_connection()
    if params:
        df = pd.read_sql_query(query, conn, params=params)
    else:
        df = pd.read_sql_query(query, conn)
    conn.close()
    return df

st.sidebar.title("Main Menu")
page = st.sidebar.radio("Navigation", ["Home", "Queries", "Settings"])

if page == "Home":
    st.title("🏒 NHL Analytics Hub")
    st.markdown("Welcome to the **NHL Analytics Hub** dashboard!")
    
    tab1, tab2, tab3, tab4 = st.tabs(["🏆 Standings & Overview", "👤 Team Rosters", "🥇 Player Leaderboard", "📅 Game Schedules"])

    with tab1:
        st.header("League Standings & Performance")
        try:
            divisions = get_data("SELECT DISTINCT division_name FROM teams")["division_name"].dropna().tolist()
            selected_div = st.multiselect("Filter by Division:", options=divisions, default=divisions)

            if selected_div:
                placeholders = ','.join(['?']*len(selected_div))
                query = f"""
                    SELECT 
                        t.team_abbrev, t.team_name, t.conference_name, t.division_name,
                        s.games_played, s.wins, s.losses, s.ot_losses, s.points,
                        s.goals_for, s.goals_against, s.streak_type, s.streak_count
                    FROM teams t
                    JOIN standings s ON t.team_id = s.team_id
                    WHERE t.division_name IN ({placeholders})
                    ORDER BY s.points DESC;
                """
                df_standings = get_data(query, params=selected_div)
            else:
                df_standings = pd.DataFrame()

            if not df_standings.empty:
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Top Team Points", int(df_standings["points"].iloc[0]), f"{df_standings['team_abbrev'].iloc[0]}")
                col2.metric("Total Teams", len(df_standings))
                col3.metric("Avg Goals For", round(df_standings["goals_for"].mean(), 1))
                col4.metric("Avg Goals Against", round(df_standings["goals_against"].mean(), 1))

                st.dataframe(df_standings, width="stretch")

                fig = px.bar(df_standings, x="team_abbrev", y="points", color="division_name",
                             title="Points by Team across Divisions", text="points")
                st.plotly_chart(fig, width="stretch")
        except Exception as e:
            st.info("Run `python etl_pipeline.py` to create and populate the database.")

    with tab2:
        st.header("Team Roster Explorer")
        try:
            teams_df = get_data("SELECT team_abbrev, team_name FROM teams")
            if not teams_df.empty:
                selected_team = st.selectbox("Select Team:", teams_df["team_abbrev"] + " - " + teams_df["team_name"])
                team_code = selected_team.split(" - ")[0]

                query = f"""
                    SELECT p.first_name, p.last_name, p.position, p.jersey_number,
                           p.birth_date, p.birth_country, p.height_cm, p.weight_kg, p.shoots_catches
                    FROM players p
                    JOIN teams t ON p.team_id = t.team_id
                    WHERE t.team_abbrev = '{team_code}'
                    ORDER BY p.jersey_number;
                """
                df_roster = get_data(query)
                st.dataframe(df_roster, width="stretch")

                if not df_roster.empty:
                    fig_pos = px.pie(df_roster, names="position", title=f"Position Breakdown for {selected_team}")
                    st.plotly_chart(fig_pos, width="stretch")
        except Exception:
            st.info("Database records pending ETL extraction.")

    with tab3:
        st.header("Skater Stats Leaderboard")
        try:
            stat_choice = st.radio("Order By Metric:", ["points", "goals", "assists", "penalty_minutes"], horizontal=True)

            query = f"""
                SELECT p.first_name || ' ' || p.last_name AS player_name,
                       t.team_abbrev, p.position, s.games_played,
                       s.goals, s.assists, s.points, s.plus_minus, s.penalty_minutes
                FROM skater_stats s
                JOIN players p ON s.player_id = p.player_id
                JOIN teams t ON s.team_id = t.team_id
                ORDER BY s.{stat_choice} DESC
                LIMIT 20;
            """
            df_skaters = get_data(query)
            st.dataframe(df_skaters, width="stretch")

            if not df_skaters.empty:
                fig_skater = px.bar(df_skaters, x="player_name", y=stat_choice, color="team_abbrev", title=f"Top Players by {stat_choice.title()}")
                st.plotly_chart(fig_skater, width="stretch")
        except Exception:
            st.info("Database records pending ETL extraction.")

    with tab4:
        st.header("Game Schedules & Match Outcomes")
        try:
            teams_list = get_data("SELECT team_abbrev FROM teams")["team_abbrev"].tolist()
            if teams_list:
                selected_sched_team = st.selectbox("Select Team Schedule:", teams_list)
                query = f"""
                    SELECT game_date, opponent_abbrev, home_away, team_score, opponent_score, game_outcome
                    FROM schedules s
                    JOIN teams t ON s.team_id = t.team_id
                    WHERE t.team_abbrev = '{selected_sched_team}'
                    ORDER BY game_date DESC;
                """
                df_sched = get_data(query)
                st.dataframe(df_sched, width="stretch")
        except Exception:
            st.info("Database records pending ETL extraction.")

elif page == "Queries":
    st.title("NHL Analytics Hub")
    st.write("This is the Queries page.")
    st.markdown("---")

    query_dict = {
        "1. Which team has scored the most total goals this season? (Aggregation + ORDER BY)": """
            SELECT 
                t.team_name, 
                t.team_abbrev, 
                t.division_name, 
                s.goals_for 
            FROM standings s 
            JOIN teams t ON s.team_id = t.team_id 
            ORDER BY s.goals_for DESC 
            LIMIT 10;
        """,

        "2. Who are the top 5 point scorers across the entire league? (JOIN + ORDER BY)": """
            SELECT 
                p.first_name || ' ' || p.last_name AS player_name, 
                t.team_name, 
                sk.goals, 
                sk.assists, 
                sk.points 
            FROM skater_stats sk 
            JOIN players p ON sk.player_id = p.player_id 
            JOIN teams t ON sk.team_id = t.team_id 
            ORDER BY sk.points DESC 
            LIMIT 5;
        """,

        "3. Which players have scored more than 20 goals and 30 assists? (WHERE with multiple conditions)": """
            SELECT 
                p.first_name || ' ' || p.last_name AS player_name, 
                t.team_abbrev, 
                p.position, 
                sk.goals, 
                sk.assists, 
                sk.points 
            FROM skater_stats sk 
            JOIN players p ON sk.player_id = p.player_id 
            JOIN teams t ON sk.team_id = t.team_id 
            WHERE sk.goals > 20 AND sk.assists > 30 
            ORDER BY sk.points DESC;
        """,

        "4. Which teams have a season points total above the league average? (Subquery)": """
            SELECT 
                t.team_name, 
                t.conference_name, 
                t.division_name, 
                s.points,
                ROUND((SELECT AVG(points) FROM standings), 1) AS league_avg_points
            FROM standings s 
            JOIN teams t ON s.team_id = t.team_id 
            WHERE s.points > (SELECT AVG(points) FROM standings) 
            ORDER BY s.points DESC;
        """,

        "5. Which divisions have an average team points total above 90? (GROUP BY + HAVING)": """
            SELECT 
                t.division_name, 
                COUNT(t.team_id) AS total_teams, 
                ROUND(AVG(s.points), 2) AS avg_division_points,
                SUM(s.goals_for) AS total_division_goals
            FROM standings s 
            JOIN teams t ON s.team_id = t.team_id 
            GROUP BY t.division_name 
            HAVING AVG(s.points) > 90 
            ORDER BY avg_division_points DESC;
        """,

        "6. What are the top goalies with the best save percentage? (JOIN + WHERE + ORDER BY)": """
            SELECT 
                p.first_name || ' ' || p.last_name AS goalie_name, 
                t.team_name, 
                g.games_played, 
                g.wins, 
                g.save_percentage, 
                g.goals_against_avg, 
                g.shutouts
            FROM goalie_stats g 
            JOIN players p ON g.player_id = p.player_id 
            JOIN teams t ON g.team_id = t.team_id 
            WHERE g.games_played >= 10 
            ORDER BY g.save_percentage DESC 
            LIMIT 5;
        """,

        "7. Who is the top point scorer for each team? (JOIN + Subquery)": """
            SELECT 
                t.team_name, 
                p.first_name || ' ' || p.last_name AS player_name, 
                sk.goals, 
                sk.assists, 
                sk.points 
            FROM skater_stats sk 
            JOIN players p ON sk.player_id = p.player_id 
            JOIN teams t ON sk.team_id = t.team_id 
            WHERE sk.points = (
                SELECT MAX(sk2.points) 
                FROM skater_stats sk2 
                WHERE sk2.team_id = sk.team_id
            ) 
            ORDER BY sk.points DESC;
        """,

        "8. Which teams have won more games at home than away? (WHERE + ORDER BY)": """
            SELECT 
                t.team_name, 
                s.home_wins, 
                s.away_wins, 
                s.wins AS total_wins,
                (s.home_wins - s.away_wins) AS home_advantage_margin
            FROM standings s 
            JOIN teams t ON s.team_id = t.team_id 
            WHERE s.home_wins > s.away_wins 
            ORDER BY home_advantage_margin DESC;
        """,

        "9. What is the average height and weight of players by position? (GROUP BY + AVG)": """
            SELECT 
                position, 
                COUNT(*) AS total_players, 
                ROUND(AVG(height_cm), 1) AS avg_height_cm, 
                ROUND(AVG(weight_kg), 1) AS avg_weight_kg 
            FROM players 
            WHERE position IS NOT NULL AND position != '' 
            GROUP BY position 
            ORDER BY avg_height_cm DESC;
        """,

        "10. Which teams currently have a winning streak? (WHERE + ORDER BY)": """
            SELECT 
                t.team_name, 
                s.streak_type, 
                s.streak_count, 
                s.wins, 
                s.points 
            FROM standings s 
            JOIN teams t ON s.team_id = t.team_id 
            WHERE s.streak_type = 'W' 
            ORDER BY s.streak_count DESC;
        """
    }

    selected_query_label = st.selectbox("Select a query to run", list(query_dict.keys()))

    if selected_query_label:
        sql_query = query_dict[selected_query_label]

        st.markdown("#### SQL Query Code:")
        st.code(sql_query, language="sql")

        st.markdown("#### Query Results:")
        try:
            df_result = get_data(sql_query)
            if not df_result.empty:
                st.dataframe(df_result, width="stretch")
                st.caption(f"Fetched {len(df_result)} row(s).")
            else:
                st.warning("No records found matching the query criteria.")
        except Exception as e:
            st.error(f"Database error or missing tables: {e}")

elif page == "Settings":
    st.title("⚙️ Settings")
    st.write("Configure dashboard options and database preferences.")
    
    st.subheader("Database Status")
    db_exists = os.path.exists(DB_NAME)
    if db_exists:
        st.success(f"Connected to local Database: `{DB_NAME}`")
    else:
        st.warning("Database not found locally. Please run `python etl_pipeline.py` first.")

    st.subheader("ETL Data Refresh")
    st.info("To re-run the ETL pipeline, run `python etl_pipeline.py` in your terminal.")
