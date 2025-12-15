# Rock-Paper-Scissors Tournament Leaderboard

**CSCI 210 Final Project**  
**Student:** Aric Hurkman  
**Professor:** Gheni Abla

## Project Description

A Flask-based web application that manages a persistent, multi-player Rock-Paper-Scissors tournament. The application demonstrates proficiency in Python's fundamental **Data Structures** (Dictionary, List) and associated algorithms (Sorting, Searching).

---

## User Manual: How to Run the Project

### Prerequisites

- Python 3.7 or higher installed
- pip (Python package manager)

### Step-by-Step Instructions

1. **Navigate to the project folder:**

   ```bash
   cd rps_tournament
   ```

2. **Install Flask (if not already installed):**

   ```bash
   pip install flask
   ```

3. **Run the application:**

   ```bash
   python app.py
   ```

4. **Open your web browser and go to:**

   ```
   http://localhost:5000
   ```

5. **Play the game!**

---

## How to Play

### Starting Your First Game

1. Enter **Player 1's name** in the first input field
2. Enter **Player 2's name** in the second input field
3. Click the **"Start Game"** button

### Playing a Round

1. **Player 1** clicks their choice (🪨 Rock, 📄 Paper, or ✂️ Scissors)
2. **Player 2** clicks their choice
3. Click **"Play Round"** to see who wins
4. Repeat for all 10 rounds

### Winner Retention System

- After a 10-round game ends, the **winner is automatically retained** as Player 1
- The winner's name is locked and cannot be edited
- Enter a new opponent's name to continue the tournament
- This ensures at least **5 unique players** participate over time

### Viewing the Leaderboard

The right panel shows two leaderboard views:

1. **By Name (A-Z):** Players sorted alphabetically
2. **By Score (High-Low):** Players ranked by total rounds won

### Resetting the Tournament

Click the **"Reset Tournament"** button to clear all player data and start fresh.

---

## Project Structure

```
rps_tournament/
├── app.py                 # Flask backend with all API endpoints
├── templates/
│   └── index.html         # Frontend HTML/CSS/JavaScript
└── README.md              # This file
```

---

## Required Data Structures & Algorithms

### 1. Central Data Store: Dictionary (LEADERBOARD)

```python
LEADERBOARD = {
    "PlayerName": {
        "score": 0,           # Total rounds won
        "games_won": 0,       # Total games won
        "games_played": 0,    # Total games participated
        "rounds_played": 0    # Total rounds played
    }
}
```

- **Purpose:** O(1) average time complexity for searching and updating player stats

### 2. Leaderboard Presentation: Lists & Sorting

```python
# Convert Dictionary to List of Dictionaries
players_list = [{"name": name, **stats} for name, stats in LEADERBOARD.items()]

# Sort alphabetically by name
sorted_by_name = sorted(players_list, key=lambda x: x["name"].lower())

# Sort by score (descending)
sorted_by_score = sorted(players_list, key=lambda x: x["score"], reverse=True)
```

---

## RESTful API Endpoints

| HTTP Method | Endpoint | Description |
|-------------|----------|-------------|
| **POST** | `/api/player/register` | Creates a new player if they don't exist |
| **POST** | `/api/game/start` | Initializes a new 10-round game |
| **POST** | `/api/game/play_round` | Executes one round of RPS |
| **GET** | `/api/leaderboard` | Retrieves the complete leaderboard |
| **GET** | `/api/game/state` | Gets current game status |
| **POST** | `/api/reset` | Resets the entire tournament |

---

## Game Rules

- **Rock** 🪨 beats **Scissors** ✂️
- **Scissors** ✂️ beats **Paper** 📄
- **Paper** 📄 beats **Rock** 🪨
- Same choice = **Tie** (no points awarded)

---

## Features

✅ 10-round games  
✅ Winner retention between games  
✅ Persistent leaderboard tracking  
✅ Two sorted leaderboard views (by name, by score)  
✅ Real-time score updates  
✅ Round-by-round history  
✅ Clean, responsive UI  
✅ RESTful API design  

---

## Testing the API

You can test the API endpoints using curl or Postman:

```bash
# Register a player
curl -X POST http://localhost:5000/api/player/register \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice"}'

# Start a game
curl -X POST http://localhost:5000/api/game/start \
  -H "Content-Type: application/json" \
  -d '{"player1": "Alice", "player2": "Bob"}'

# Play a round
curl -X POST http://localhost:5000/api/game/play_round \
  -H "Content-Type: application/json" \
  -d '{"player1_choice": "rock", "player2_choice": "scissors"}'

# Get leaderboard
curl http://localhost:5000/api/leaderboard
```

---

## License

This project was created for educational purposes as part of CSCI 210.
