import sqlite3
import requests
import time

DB_NAME = "NHL_Analytics_Hub.db"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_all_tables():
    conn = get_connection()
    cursor = conn.cursor()

    # Table 1: teams
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            team_id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_abbrev VARCHAR(10) UNIQUE NOT NULL,
            team_name VARCHAR(100) NOT NULL,
            conference_name VARCHAR(50),
            division_name VARCHAR(50),
            logo_url TEXT
        );
    """)

    # Table 2: standings
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS standings (
            standing_id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            season VARCHAR(20),
            games_played INT,
            wins INT,
            losses INT,
            ot_losses INT,
            points INT,
            goals_for INT,
            goals_against INT,
            home_wins INT,
            away_wins INT,
            streak_type VARCHAR(20),
            streak_count INT,
            FOREIGN KEY (team_id) REFERENCES teams(team_id) ON DELETE CASCADE
        );
    """)

    # Table 3: players
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            player_id BIGINT PRIMARY KEY,
            team_id INTEGER NOT NULL,
            first_name VARCHAR(100),
            last_name VARCHAR(100),
            position VARCHAR(10),
            jersey_number INT,
            birth_date DATE,
            birth_country VARCHAR(10),
            height_cm REAL,
            weight_kg REAL,
            shoots_catches VARCHAR(5),
            headshot_url TEXT,
            FOREIGN KEY (team_id) REFERENCES teams(team_id) ON DELETE CASCADE
        );
    """)

    # Table 4: schedules
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            game_id BIGINT PRIMARY KEY,
            team_id INTEGER NOT NULL,
            game_date DATE,
            opponent_abbrev VARCHAR(10),
            home_away VARCHAR(10),
            team_score INT,
            opponent_score INT,
            game_outcome VARCHAR(10),
            FOREIGN KEY (team_id) REFERENCES teams(team_id) ON DELETE CASCADE
        );
    """)

    # Table 5: skater_stats
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS skater_stats (
            stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id BIGINT NOT NULL,
            team_id INTEGER NOT NULL,
            season VARCHAR(20),
            games_played INT,
            goals INT,
            assists INT,
            points INT,
            plus_minus INT,
            penalty_minutes INT,
            FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE,
            FOREIGN KEY (team_id) REFERENCES teams(team_id) ON DELETE CASCADE
        );
    """)

    # Table 6: goalie_stats
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS goalie_stats (
            stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id BIGINT NOT NULL,
            team_id INTEGER NOT NULL,
            season VARCHAR(20),
            games_played INT,
            wins INT,
            losses INT,
            save_percentage REAL,
            goals_against_avg REAL,
            shutouts INT,
            FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE,
            FOREIGN KEY (team_id) REFERENCES teams(team_id) ON DELETE CASCADE
        );
    """)

    # Table 7: team_season_stats
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS team_season_stats (
            summary_id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            season VARCHAR(20),
            wins INT,
            losses INT,
            ot_losses INT,
            points INT,
            point_pctg REAL,
            goals_per_game REAL,
            goals_against_per_game REAL,
            FOREIGN KEY (team_id) REFERENCES teams(team_id) ON DELETE CASCADE
        );
    """)

    conn.commit()
    conn.close()
    print("✅ All 7 Tables Initialized.")

def populate_teams_and_standings():
    url = "https://api-web.nhle.com/v1/standings/now"
    res = requests.get(url, headers=HEADERS).json().get("standings", [])
    
    conn = get_connection()
    cursor = conn.cursor()

    for item in res:
        team_abbrev = item.get("teamAbbrev", {}).get("default") if isinstance(item.get("teamAbbrev"), dict) else item.get("teamAbbrev")
        team_name = item.get("teamName", {}).get("default") if isinstance(item.get("teamName"), dict) else item.get("teamName")
        
        cursor.execute("""
            INSERT INTO teams (team_abbrev, team_name, conference_name, division_name, logo_url)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(team_abbrev) DO UPDATE SET
                team_name=excluded.team_name, conference_name=excluded.conference_name,
                division_name=excluded.division_name, logo_url=excluded.logo_url;
        """, (team_abbrev, team_name, item.get("conferenceName"), item.get("divisionName"), item.get("teamLogo")))

        cursor.execute("SELECT team_id FROM teams WHERE team_abbrev = ?", (team_abbrev,))
        team_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO standings (
                team_id, season, games_played, wins, losses, ot_losses, points,
                goals_for, goals_against, home_wins, away_wins, streak_type, streak_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            team_id, str(item.get("seasonId")), item.get("gamesPlayed"), item.get("wins"),
            item.get("losses"), item.get("otLosses"), item.get("points"), item.get("goalFor"),
            item.get("goalAgainst"), item.get("homeWins"), item.get("roadWins"),
            item.get("streakCode"), item.get("streakCount")
        ))

    conn.commit()
    conn.close()

def populate_team_roster_and_stats():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT team_id, team_abbrev FROM teams;")
    teams = cursor.fetchall()

    for team_id, team_abbrev in teams:
        roster_url = f"https://api-web.nhle.com/v1/roster/{team_abbrev}/current"
        try:
            r_data = requests.get(roster_url, headers=HEADERS).json()
            for cat in ["forwards", "defensemen", "goalies"]:
                for p in r_data.get(cat, []):
                    p_id = p.get("id")
                    f_name = p.get("firstName", {}).get("default") if isinstance(p.get("firstName"), dict) else p.get("firstName")
                    l_name = p.get("lastName", {}).get("default") if isinstance(p.get("lastName"), dict) else p.get("lastName")
                    cursor.execute("""
                        INSERT INTO players (
                            player_id, team_id, first_name, last_name, position,
                            jersey_number, birth_date, birth_country, height_cm,
                            weight_kg, shoots_catches, headshot_url
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(player_id) DO UPDATE SET team_id=excluded.team_id;
                    """, (
                        p_id, team_id, f_name, l_name, p.get("positionCode"),
                        p.get("sweaterNumber"), p.get("birthDate"), p.get("birthCountry"),
                        p.get("heightInCentimeters"), p.get("weightInKilograms"),
                        p.get("shootsCatches"), p.get("headshot")
                    ))
        except Exception:
            pass

        stats_url = f"https://api-web.nhle.com/v1/club-stats/{team_abbrev}/now"
        try:
            s_data = requests.get(stats_url, headers=HEADERS).json()
            season = str(s_data.get("season", "20232024"))
            
            for s in s_data.get("skaters", []):
                p_id = s.get("playerId")
                cursor.execute("""
                    INSERT INTO skater_stats (player_id, team_id, season, games_played, goals, assists, points, plus_minus, penalty_minutes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (p_id, team_id, season, s.get("gamesPlayed"), s.get("goals"), s.get("assists"), s.get("points"), s.get("plusMinus"), s.get("penaltyMinutes")))

            for g in s_data.get("goalies", []):
                p_id = g.get("playerId")
                cursor.execute("""
                    INSERT INTO goalie_stats (player_id, team_id, season, games_played, wins, losses, save_percentage, goals_against_avg, shutouts)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (p_id, team_id, season, g.get("gamesPlayed"), g.get("wins"), g.get("losses"), g.get("savePercentage"), g.get("goalsAgainstAverage"), g.get("shutouts")))
        except Exception:
            pass

        season_stats_url = f"https://api-web.nhle.com/v1/club-stats-season/{team_abbrev}"
        try:
            tss_data = requests.get(season_stats_url, headers=HEADERS).json()
            for row in tss_data if isinstance(tss_data, list) else []:
                cursor.execute("""
                    INSERT INTO team_season_stats (team_id, season, wins, losses, ot_losses, points, point_pctg, goals_per_game, goals_against_per_game)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (team_id, str(row.get("season")), row.get("wins"), row.get("losses"), row.get("otLosses"), row.get("points"), row.get("pointPctg"), row.get("goalsPerGame"), row.get("goalsAgainstPerGame")))
        except Exception:
            pass

        time.sleep(0.1)

    conn.commit()
    conn.close()

def populate_schedules():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT team_id, team_abbrev FROM teams;")
    teams = cursor.fetchall()

    for team_id, team_abbrev in teams:
        url = f"https://api-web.nhle.com/v1/club-schedule-season/{team_abbrev}/now"
        try:
            games = requests.get(url, headers=HEADERS).json().get("games", [])
            for g in games[:20]:
                game_id = g.get("id")
                home_team = g.get("homeTeam", {}).get("abbrev")
                away_team = g.get("awayTeam", {}).get("abbrev")
                home_away = "HOME" if home_team == team_abbrev else "AWAY"
                opp_abbrev = away_team if home_away == "HOME" else home_team
                team_score = g.get("homeTeam", {}).get("score", 0) if home_away == "HOME" else g.get("awayTeam", {}).get("score", 0)
                opp_score = g.get("awayTeam", {}).get("score", 0) if home_away == "HOME" else g.get("homeTeam", {}).get("score", 0)
                outcome = "WIN" if team_score > opp_score else "LOSS"

                cursor.execute("""
                    INSERT INTO schedules (game_id, team_id, game_date, opponent_abbrev, home_away, team_score, opponent_score, game_outcome)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(game_id) DO NOTHING;
                """, (game_id, team_id, g.get("gameDate"), opp_abbrev, home_away, team_score, opp_score, outcome))
        except Exception:
            pass

    conn.commit()
    conn.close()

if __name__ == "__main__":
    print("🚀 Starting NHL Analytics Hub ETL Process...")
    init_all_tables()
    populate_teams_and_standings()
    populate_team_roster_and_stats()
    populate_schedules()
    print("🎉 ETL Completed Successfully! Database 'NHL_Analytics_Hub.db' is ready.")
