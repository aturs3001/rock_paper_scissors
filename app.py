"""
Rock-Paper-Scissors Tournament Leaderboard
CSCI 210 Final Project
Student: Aric Hurkman
Professor: Gheni Abla

A Flask-based web application that manages a persistent, multi-player
Rock-Paper-Scissors tournament using Dictionary and List data structures.
"""

from flask import Flask, jsonify, request, render_template
import json
import os
import hashlib
from datetime import datetime

app = Flask(__name__)

# =============================================================================
# DATA FILE CONFIGURATION
# =============================================================================
DATA_FILE = 'leaderboard_data.json'
BACKUP_FILE = 'leaderboard_data.backup.json'

# =============================================================================
# SECURE DATA PERSISTENCE FUNCTIONS
# =============================================================================

def calculate_checksum(data):
    """Calculate SHA-256 checksum for data integrity verification."""
    data_string = json.dumps(data, sort_keys=True)
    return hashlib.sha256(data_string.encode()).hexdigest()


def save_leaderboard():
    """
    Save the LEADERBOARD dictionary to a secure JSON file.
    Includes checksum for data integrity and timestamp for tracking.
    """
    try:
        # Create backup of existing file first
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r') as f:
                    backup_data = f.read()
                with open(BACKUP_FILE, 'w') as f:
                    f.write(backup_data)
            except:
                pass  # Backup failed, continue anyway
        
        # Prepare data with metadata
        save_data = {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "leaderboard": LEADERBOARD,
            "checksum": calculate_checksum(LEADERBOARD)
        }
        
        # Write to file with pretty formatting
        with open(DATA_FILE, 'w') as f:
            json.dump(save_data, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error saving leaderboard: {e}")
        return False


def load_leaderboard():
    """
    Load the LEADERBOARD dictionary from the secure JSON file.
    Verifies data integrity using checksum.
    """
    global LEADERBOARD
    
    if not os.path.exists(DATA_FILE):
        print("No existing leaderboard file found. Starting fresh.")
        LEADERBOARD = {}
        return
    
    try:
        with open(DATA_FILE, 'r') as f:
            save_data = json.load(f)
        
        # Verify data structure
        if not isinstance(save_data, dict) or 'leaderboard' not in save_data:
            raise ValueError("Invalid data structure")
        
        loaded_leaderboard = save_data['leaderboard']
        
        # Verify checksum if present
        if 'checksum' in save_data:
            expected_checksum = save_data['checksum']
            actual_checksum = calculate_checksum(loaded_leaderboard)
            
            if expected_checksum != actual_checksum:
                print("WARNING: Data integrity check failed! Loading from backup...")
                return load_from_backup()
        
        # Validate each player entry
        for player_name, stats in loaded_leaderboard.items():
            if not isinstance(stats, dict):
                raise ValueError(f"Invalid stats for player {player_name}")
            # Ensure all required fields exist
            required_fields = ['score', 'games_won', 'games_played', 'rounds_played']
            for field in required_fields:
                if field not in stats:
                    stats[field] = 0
        
        LEADERBOARD = loaded_leaderboard
        print(f"Leaderboard loaded successfully. {len(LEADERBOARD)} players found.")
        print(f"Last updated: {save_data.get('last_updated', 'Unknown')}")
        
    except json.JSONDecodeError as e:
        print(f"Error parsing leaderboard file: {e}")
        load_from_backup()
    except Exception as e:
        print(f"Error loading leaderboard: {e}")
        load_from_backup()


def load_from_backup():
    """Attempt to load from backup file if main file is corrupted."""
    global LEADERBOARD
    
    if not os.path.exists(BACKUP_FILE):
        print("No backup file found. Starting fresh.")
        LEADERBOARD = {}
        return
    
    try:
        with open(BACKUP_FILE, 'r') as f:
            save_data = json.load(f)
        
        if 'leaderboard' in save_data:
            LEADERBOARD = save_data['leaderboard']
            print(f"Loaded from backup. {len(LEADERBOARD)} players restored.")
            # Save to main file
            save_leaderboard()
        else:
            LEADERBOARD = {}
    except Exception as e:
        print(f"Backup load failed: {e}. Starting fresh.")
        LEADERBOARD = {}


# =============================================================================
# CENTRAL DATA STORE: Dictionary (LEADERBOARD)
# =============================================================================
# Structure: Global Python Dictionary serving as single source of truth
# Key: Unique player name (String)
# Value: Nested dictionary with cumulative statistics
# Purpose: O(1) average time complexity for searching and updating
# =============================================================================
LEADERBOARD = {}

# Load existing data on startup
load_leaderboard()

# =============================================================================
# GAME STATE: Dictionary to track current game session
# =============================================================================
GAME_STATE = {
    "player1": None,
    "player2": None,
    "player1_round_wins": 0,
    "player2_round_wins": 0,
    "current_round": 0,
    "game_active": False,
    "previous_winner": None,  # For winner retention feature
    "game_history": []  # Track round-by-round results
}

# Rock-Paper-Scissors game rules
RPS_RULES = {
    "rock": {"beats": "scissors", "loses_to": "paper"},
    "paper": {"beats": "rock", "loses_to": "scissors"},
    "scissors": {"beats": "paper", "loses_to": "rock"}
}


def determine_round_winner(choice1, choice2):
    """
    Determine the winner of a single round.
    Returns: 'player1', 'player2', or 'tie'
    """
    if choice1 == choice2:
        return "tie"
    elif RPS_RULES[choice1]["beats"] == choice2:
        return "player1"
    else:
        return "player2"


# =============================================================================
# ROUTE: Serve the main HTML page
# =============================================================================
@app.route('/')
def index():
    return render_template('index.html')


# =============================================================================
# API ENDPOINT: Register a new player
# POST /api/player/register
# Creates a new player resource if they don't exist
# =============================================================================
@app.route('/api/player/register', methods=['POST'])
def register_player():
    data = request.get_json()
    player_name = data.get('name', '').strip()
    
    if not player_name:
        return jsonify({"error": "Player name is required"}), 400
    
    # Check if player already exists in LEADERBOARD dictionary
    if player_name not in LEADERBOARD:
        # Add new player to the LEADERBOARD dictionary
        # Value is a nested dictionary containing cumulative statistics
        LEADERBOARD[player_name] = {
            "score": 0,           # Total rounds won across all games
            "games_won": 0,       # Total 10-round games won
            "games_played": 0,    # Total games participated in
            "rounds_played": 0    # Total individual rounds played
        }
        # Save to file after adding new player
        save_leaderboard()
        
        return jsonify({
            "message": f"Player '{player_name}' registered successfully",
            "player": player_name,
            "stats": LEADERBOARD[player_name],
            "is_new": True
        }), 201
    else:
        return jsonify({
            "message": f"Player '{player_name}' already exists",
            "player": player_name,
            "stats": LEADERBOARD[player_name],
            "is_new": False
        }), 200


# =============================================================================
# API ENDPOINT: Start a new game
# POST /api/game/start
# Initializes state for a new 10-round game between current players
# =============================================================================
@app.route('/api/game/start', methods=['POST'])
def start_game():
    data = request.get_json()
    player1 = data.get('player1', '').strip()
    player2 = data.get('player2', '').strip()
    
    # Validate both players are provided
    if not player1 or not player2:
        return jsonify({"error": "Both player names are required"}), 400
    
    # Validate players are different
    if player1.lower() == player2.lower():
        return jsonify({"error": "Players must have different names"}), 400
    
    # Register players if they don't exist (using Dictionary O(1) lookup)
    for player in [player1, player2]:
        if player not in LEADERBOARD:
            LEADERBOARD[player] = {
                "score": 0,
                "games_won": 0,
                "games_played": 0,
                "rounds_played": 0
            }
    
    # Initialize game state for new 10-round game
    GAME_STATE["player1"] = player1
    GAME_STATE["player2"] = player2
    GAME_STATE["player1_round_wins"] = 0
    GAME_STATE["player2_round_wins"] = 0
    GAME_STATE["current_round"] = 0
    GAME_STATE["game_active"] = True
    GAME_STATE["game_history"] = []
    
    # Increment games_played for both players
    LEADERBOARD[player1]["games_played"] += 1
    LEADERBOARD[player2]["games_played"] += 1
    
    # Save after starting game
    save_leaderboard()
    
    return jsonify({
        "message": "Game started!",
        "player1": player1,
        "player2": player2,
        "total_rounds": 10,
        "current_round": 0,
        "player1_stats": LEADERBOARD[player1],
        "player2_stats": LEADERBOARD[player2]
    }), 200


# =============================================================================
# API ENDPOINT: Play one round
# POST /api/game/play_round
# Executes one round of RPS, updates scores in Dictionary, returns result
# =============================================================================
@app.route('/api/game/play_round', methods=['POST'])
def play_round():
    if not GAME_STATE["game_active"]:
        return jsonify({"error": "No active game. Please start a new game."}), 400
    
    if GAME_STATE["current_round"] >= 10:
        return jsonify({"error": "Game is complete. Please start a new game."}), 400
    
    data = request.get_json()
    player1_choice = data.get('player1_choice', '').lower().strip()
    player2_choice = data.get('player2_choice', '').lower().strip()
    
    # Validate choices
    valid_choices = ['rock', 'paper', 'scissors']
    if player1_choice not in valid_choices or player2_choice not in valid_choices:
        return jsonify({"error": "Invalid choice. Must be rock, paper, or scissors"}), 400
    
    # Increment round counter
    GAME_STATE["current_round"] += 1
    
    # Determine round winner
    round_result = determine_round_winner(player1_choice, player2_choice)
    
    player1 = GAME_STATE["player1"]
    player2 = GAME_STATE["player2"]
    
    # Update rounds played for both players
    LEADERBOARD[player1]["rounds_played"] += 1
    LEADERBOARD[player2]["rounds_played"] += 1
    
    # Update scores based on round result
    round_winner_name = None
    if round_result == "player1":
        GAME_STATE["player1_round_wins"] += 1
        # Update cumulative score in LEADERBOARD dictionary
        LEADERBOARD[player1]["score"] += 1
        round_winner_name = player1
    elif round_result == "player2":
        GAME_STATE["player2_round_wins"] += 1
        # Update cumulative score in LEADERBOARD dictionary
        LEADERBOARD[player2]["score"] += 1
        round_winner_name = player2
    
    # Record round in history
    round_record = {
        "round": GAME_STATE["current_round"],
        "player1_choice": player1_choice,
        "player2_choice": player2_choice,
        "winner": round_winner_name if round_winner_name else "Tie"
    }
    GAME_STATE["game_history"].append(round_record)
    
    # Check if game is complete (10 rounds played)
    game_complete = GAME_STATE["current_round"] >= 10
    game_winner = None
    
    if game_complete:
        GAME_STATE["game_active"] = False
        
        # Determine game winner
        if GAME_STATE["player1_round_wins"] > GAME_STATE["player2_round_wins"]:
            game_winner = player1
            LEADERBOARD[player1]["games_won"] += 1
            GAME_STATE["previous_winner"] = player1
        elif GAME_STATE["player2_round_wins"] > GAME_STATE["player1_round_wins"]:
            game_winner = player2
            LEADERBOARD[player2]["games_won"] += 1
            GAME_STATE["previous_winner"] = player2
        else:
            # Tie game - no winner retention
            GAME_STATE["previous_winner"] = None
    
    # Save leaderboard after each round
    save_leaderboard()
    
    return jsonify({
        "round": GAME_STATE["current_round"],
        "player1": player1,
        "player2": player2,
        "player1_choice": player1_choice,
        "player2_choice": player2_choice,
        "round_winner": round_winner_name,
        "round_result": round_result,
        "player1_round_wins": GAME_STATE["player1_round_wins"],
        "player2_round_wins": GAME_STATE["player2_round_wins"],
        "game_complete": game_complete,
        "game_winner": game_winner,
        "previous_winner": GAME_STATE["previous_winner"],
        "player1_total_score": LEADERBOARD[player1]["score"],
        "player2_total_score": LEADERBOARD[player2]["score"]
    }), 200


# =============================================================================
# API ENDPOINT: Get Leaderboard
# GET /api/leaderboard
# Retrieves the complete leaderboard with two sorted views
# Demonstrates: Dictionary to List conversion and Sorting algorithms
# =============================================================================
@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    """
    LEADERBOARD PRESENTATION: Lists & Sorting
    
    Step 1: Convert Dictionary to List of Dictionaries
    Step 2: Apply sorting with lambda keys for two views
    """
    
    # Step 1: Convert LEADERBOARD Dictionary to List of Dictionaries
    # This transformation is required for sorting operations
    players_list = []
    for player_name, stats in LEADERBOARD.items():
        player_dict = {
            "name": player_name,
            "score": stats["score"],
            "games_won": stats["games_won"],
            "games_played": stats["games_played"],
            "rounds_played": stats["rounds_played"]
        }
        players_list.append(player_dict)
    
    # Step 2: Create two sorted views using Python's sorted() with lambda keys
    
    # View 1: Sorted Alphabetically by Player Name (case-insensitive)
    sorted_by_name = sorted(players_list, key=lambda x: x["name"].lower())
    
    # View 2: Sorted Numerically (Descending) by Accumulative Score
    sorted_by_score = sorted(players_list, key=lambda x: x["score"], reverse=True)
    
    return jsonify({
        "total_players": len(players_list),
        "sorted_by_name": sorted_by_name,
        "sorted_by_score": sorted_by_score,
        "game_state": {
            "active": GAME_STATE["game_active"],
            "current_round": GAME_STATE["current_round"],
            "player1": GAME_STATE["player1"],
            "player2": GAME_STATE["player2"],
            "player1_round_wins": GAME_STATE["player1_round_wins"],
            "player2_round_wins": GAME_STATE["player2_round_wins"],
            "previous_winner": GAME_STATE["previous_winner"]
        }
    }), 200


# =============================================================================
# API ENDPOINT: Get current game state
# GET /api/game/state
# Helper endpoint to retrieve current game status
# =============================================================================
@app.route('/api/game/state', methods=['GET'])
def get_game_state():
    return jsonify({
        "game_active": GAME_STATE["game_active"],
        "player1": GAME_STATE["player1"],
        "player2": GAME_STATE["player2"],
        "current_round": GAME_STATE["current_round"],
        "player1_round_wins": GAME_STATE["player1_round_wins"],
        "player2_round_wins": GAME_STATE["player2_round_wins"],
        "previous_winner": GAME_STATE["previous_winner"],
        "game_history": GAME_STATE["game_history"]
    }), 200


# =============================================================================
# API ENDPOINT: Reset tournament (for testing purposes)
# POST /api/reset
# =============================================================================
@app.route('/api/reset', methods=['POST'])
def reset_tournament():
    global LEADERBOARD, GAME_STATE
    LEADERBOARD = {}
    GAME_STATE = {
        "player1": None,
        "player2": None,
        "player1_round_wins": 0,
        "player2_round_wins": 0,
        "current_round": 0,
        "game_active": False,
        "previous_winner": None,
        "game_history": []
    }
    # Save empty leaderboard to file
    save_leaderboard()
    return jsonify({"message": "Tournament reset successfully"}), 200


# =============================================================================
# Run the Flask application
# =============================================================================
if __name__ == '__main__':
    app.run(debug=True, port=5000)