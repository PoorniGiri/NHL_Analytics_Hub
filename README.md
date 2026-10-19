# 🏒 NHL Analytics Hub

An end-to-end data engineering and analytics capstone project built with Python, SQLite, Streamlit, and Plotly.

## 📌 Project Overview
This project extracts real-time NHL data across **7 relational tables** from official NHL REST API endpoints, stores the data in an optimized SQLite relational database (`NHL_Analytics_Hub.db`), and presents an interactive data analytics web application using Streamlit.

## 🗄️ Relational Database Schema (7 Tables)
1. **`teams`**: Team profile, division, conference, logo URL.
2. **`standings`**: Wins, losses, points, streak, goals for/against.
3. **`players`**: Player bio, jersey number, position, height, weight.
4. **`schedules`**: Game dates, home/away status, scores, outcomes.
5. **`skater_stats`**: Goals, assists, points, penalty minutes.
6. **`goalie_stats`**: Save %, goals against average, wins, shutouts.
7. **`team_season_stats`**: Team historical season summary metrics.

## 🚀 How to Run Locally

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run ETL Pipeline
To extract live API data and populate the SQLite database:
```bash
python etl_pipeline.py
```

### 3. Launch Streamlit Dashboard
```bash
streamlit run app.py
```
