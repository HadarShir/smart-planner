
---

# 🗓 Smart Planner

A personal productivity app for students built with Python, Streamlit, and SQLite.  
Plan your week, track tasks, schedule workouts, and get weather-aware daily recommendations — all in one place.

---

## ✨ Features

### 📅 Weekly View
- 7-column grid showing the full week at a glance
- Color-coded event types: study blocks, workouts, task sessions, free windows
- Overloaded-day detection with warnings
- Live weather strip above each day (temperature, condition, clothing tip)
- Toggle individual layers: free windows, workouts, task sessions, commute times, recommendations

> *Screenshot: weekly grid with weather strip and commute blocks*
> 
> <img width="1882" height="841" alt="image" src="https://github.com/user-attachments/assets/1a8602c4-f104-4a4c-835f-399c46d26ae2" />


---

### 📆 Daily View
- Navigate between days with ← Prev / Today / Next → buttons
- Large weather display for the selected day
- **👗 Outfit Recommendation** button — suggests clothing, shoes, and accessories based on temperature, rain, and sun conditions
- Bigger event cards for easy reading

> *Screenshot: daily view with outfit recommendation open*
> 
> <img width="1365" height="777" alt="image" src="https://github.com/user-attachments/assets/d23bc2d9-5c8f-4519-a3cf-f3227b81353b" />


---

### 🚗 Commute Time
- Add location and commute duration (minutes) to any study block or workout
- Visual commute blocks appear before and after each event in the schedule
- Toggle commute display on/off from the weekly view controls

> *Screenshot: weekly view with commute blocks visible*
> 
> <img width="1652" height="650" alt="image" src="https://github.com/user-attachments/assets/d5f7a9fe-3856-45c4-ae75-fc17a60bb36f" />


---

### ✅ Tasks
- Add tasks with title, description, due date, priority (high / medium / low), and estimated hours
- Smart slot suggestions: the scheduler finds free windows before the deadline
- Accept a suggested slot → it locks into the weekly grid
- Deadline warning if there isn't enough free time before the due date
- Mark tasks as done, edit, or delete

---

### 🏃 Workouts
- Schedule workouts with location and commute time
- Weekly completion progress bar
- Smart recommendations based on preferred time of day and free windows in your schedule
- Reschedule missed workouts with one click

---

### ☀️ Daily Check-in
- Rate your energy level and mood each morning
- Personalized tip based on your check-in and what's on your plate (heavy day, high-priority tasks, etc.)

---

### 📊 Weekly Insights
- At-a-glance metrics: total study hours, free time, workouts completed, tasks done
- Overloaded day alerts

---

### 🌤 Weather Forecasts
- 7-day forecast powered by [Open-Meteo](https://open-meteo.com/) (free, no API key required)
- Supports city names in Hebrew and English
- Clothing tips per day: umbrella, sunglasses, sunscreen, jacket, gloves, etc.

---

### ⚙️ Preferences
- Set workouts per week, duration, preferred time of day, and buffer between events
- Home city for weather forecasts

---

## 🗂 Project Structure

```
smart_planner/
├── app_streamlit.py       # Main Streamlit app
├── db/
│   ├── schema.py          # Table creation & migrations
│   └── database.py        # All database read/write functions
├── logic/
│   ├── scheduler.py       # Recommendation engine & free-slot logic
│   └── weather.py         # Open-Meteo API integration
└── update_locations.py    # One-time migration script for existing records
```

---

## 🚀 Getting Started

```bash
# Install dependencies
pip install streamlit requests

# Run the app
streamlit run app_streamlit.py
```

The database (`smart_planner.db`) is created automatically on first run.

---

## 🛠 Tech Stack

- **Python 3.10+**
- **Streamlit** — UI framework
- **SQLite** — local database
- **Open-Meteo API** — free weather forecasts (no key needed)
