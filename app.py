"""
Rock-Paper-Scissors Tournament Leaderboard
CSCI 210 Final Project

A Flask-based web application that manages a persistent, multi-player
Rock-Paper-Scissors tournament using Dictionary and List data structures.

Features:
- Global LEADERBOARD dictionary for O(1) player lookups by unique ID
- Unique player IDs allow same username for different players
- List conversion with sorting for dual leaderboard views
- Strategic AI with player choice memory and pattern recognition
- Secure file-based persistence with SHA-256 checksums
"""

from flask import Flask, jsonify, request, render_template
import random
import json
import hashlib
import os
import uuid
from datetime import datetime

app = Flask(__name__)

# =============================================================================
# DATA FILE CONFIGURATION
# =============================================================================
DATA_FILE = "leaderboard_data.json"
BACKUP_FILE = "leaderboard_data.backup.json"

# =============================================================================
# CENTRAL DATA STORE: Dictionary (LEADERBOARD)
# =============================================================================
# Structure: Global Python Dictionary serving as single source of truth
# Key: Unique player ID (UUID string)
# Value: Nested dictionary with player name and cumulative statistics
# Purpose: O(1) average time complexity for searching and updating
# 
# Structure with unique IDs and AI pattern tracking:
# {
#     "uuid-string-here": {
#         "id": "uuid-string-here",
#         "name": "PlayerName",           # Display name (can be duplicated)
#         "score": int,
#         "games_won": int,
#         "games_played": int,
#         "is_cpu": bool,
#         "created_at": "ISO timestamp",
#         "choice_history": {             # Frequency counts for AI
#             "rock": int,
#             "paper": int,
#             "scissors": int
#         },
#         "move_sequence": [],            # Last N moves for pattern detection
#         "pattern_history": {            # What move follows each 2-move pattern
#             "('rock','rock')": {"rock": 0, "paper": 0, "scissors": 0},
#             ...
#         }
#     }
# }
# =============================================================================
LEADERBOARD = {}

# CPU's fixed ID (singleton - only one CPU player)
CPU_ID = "cpu-00000000-0000-0000-0000-000000000000"

# =============================================================================
# GAME STATE: Dictionary to track current game session
# =============================================================================
GAME_STATE = {
    "player1_id": None,
    "player2_id": None,
    "player1_name": None,
    "player2_name": None,
    "player1_round_wins": 0,
    "player2_round_wins": 0,
    "current_round": 0,
    "game_active": False,
    "previous_winner_id": None,
    "previous_winner_name": None,
    "game_history": []
}

# Rock-Paper-Scissors game rules
RPS_RULES = {
    "rock": {"beats": "scissors", "loses_to": "paper"},
    "paper": {"beats": "rock", "loses_to": "scissors"},
    "scissors": {"beats": "paper", "loses_to": "rock"}
}

# Counter moves - what beats each choice
COUNTER_MOVES = {
    "rock": "paper",
    "paper": "scissors",
    "scissors": "rock"
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def generate_player_id():
    """Generate a unique player ID."""
    return str(uuid.uuid4())


def get_player_by_id(player_id):
    """Get player data by their unique ID. O(1) lookup."""
    return LEADERBOARD.get(player_id)


def get_player_name(player_id):
    """Get player's display name by ID."""
    player = LEADERBOARD.get(player_id)
    return player["name"] if player else None


# =============================================================================
# DATA PERSISTENCE FUNCTIONS
# =============================================================================
def calculate_checksum(data):
    """Calculate SHA-256 checksum for data integrity verification."""
    json_str = json.dumps(data, sort_keys=True)
    return hashlib.sha256(json_str.encode()).hexdigest()


def save_leaderboard():
    """Save LEADERBOARD to JSON file with checksum and backup."""
    global LEADERBOARD
    
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                backup_data = f.read()
            with open(BACKUP_FILE, 'w') as f:
                f.write(backup_data)
        except Exception as e:
            print(f"Backup failed: {e}")
    
    save_data = {
        "version": "2.0",
        "last_updated": datetime.now().isoformat(),
        "leaderboard": LEADERBOARD,
        "checksum": calculate_checksum(LEADERBOARD)
    }
    
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(save_data, f, indent=2)
        return True
    except Exception as e:
        print(f"Save failed: {e}")
        return False


def load_leaderboard():
    """Load LEADERBOARD from JSON file with integrity check."""
    global LEADERBOARD
    
    if not os.path.exists(DATA_FILE):
        print("No data file found. Starting fresh.")
        LEADERBOARD = {}
        init_cpu_player()
        return
    
    try:
        with open(DATA_FILE, 'r') as f:
            save_data = json.load(f)
        
        loaded_data = save_data.get("leaderboard", {})
        
        # Verify checksum if present
        if "checksum" in save_data:
            expected = save_data["checksum"]
            actual = calculate_checksum(loaded_data)
            if expected != actual:
                print("WARNING: Checksum mismatch! Loading from backup...")
                return load_from_backup()
        
        LEADERBOARD = loaded_data
        print(f"Leaderboard loaded successfully ({len(LEADERBOARD)} players)")
        
        # Ensure CPU player exists
        init_cpu_player()
        
    except Exception as e:
        print(f"Load failed: {e}")
        load_from_backup()


def load_from_backup():
    """Load from backup file if main file is corrupted."""
    global LEADERBOARD
    
    if not os.path.exists(BACKUP_FILE):
        print("No backup file. Starting fresh.")
        LEADERBOARD = {}
        init_cpu_player()
        return
    
    try:
        with open(BACKUP_FILE, 'r') as f:
            save_data = json.load(f)
        LEADERBOARD = save_data.get("leaderboard", {})
        print(f"Loaded from backup ({len(LEADERBOARD)} players)")
        init_cpu_player()
    except Exception as e:
        print(f"Backup load failed: {e}")
        LEADERBOARD = {}
        init_cpu_player()


def init_cpu_player():
    """Initialize the CPU player if not exists."""
    global LEADERBOARD
    if CPU_ID not in LEADERBOARD:
        LEADERBOARD[CPU_ID] = {
            "id": CPU_ID,
            "name": "CPU",
            "score": 0,
            "games_won": 0,
            "games_played": 0,
            "is_cpu": True,
            "created_at": datetime.now().isoformat(),
            "choice_history": {"rock": 0, "paper": 0, "scissors": 0}
        }


# Load data on startup
load_leaderboard()


# =============================================================================
# AI STRATEGY FUNCTIONS
# =============================================================================
def get_strategic_cpu_choice(opponent_id):
    """
    AI Strategy: Analyze opponent's HISTORICAL play patterns and make strategic counter-pick.
    
    FAIR PLAY: This function ONLY accesses data from COMPLETED rounds:
    - choice_history: Frequency counts from past rounds only
    - move_sequence: Last N moves from past rounds only  
    - pattern_history: Patterns detected from past rounds only
    
    The current round's choice is NOT available to this function because:
    1. Player's choice is stored in frontend memory only
    2. record_player_choice() is called AFTER this function returns
    3. No current-round data exists in LEADERBOARD when this runs
    
    Strategy Priority:
    1. Pattern Recognition - If we've seen the last 2 moves before, predict next move
    2. Frequency Analysis - Counter opponent's most common choice
    3. Weighted Random - Slight bias toward countering common moves
    4. Pure Random - Fallback when insufficient data
    """
    choices = ["rock", "paper", "scissors"]
    MIN_HISTORY_THRESHOLD = 5
    MIN_PATTERN_THRESHOLD = 3
    
    # Get player data by their unique ID
    player_data = get_player_by_id(opponent_id)
    
    if not player_data:
        return {
            "choice": random.choice(choices),
            "strategy_used": "random",
            "confidence": 0,
            "analysis": "Unknown player ID"
        }
    
    player_name = player_data.get("name", "Unknown")
    history = player_data.get("choice_history", {"rock": 0, "paper": 0, "scissors": 0})
    total_choices = sum(history.values())
    
    if total_choices < MIN_HISTORY_THRESHOLD:
        return {
            "choice": random.choice(choices),
            "strategy_used": "learning",
            "confidence": total_choices,
            "analysis": f"Learning {player_name}'s patterns ({total_choices}/{MIN_HISTORY_THRESHOLD} moves)",
            "player_id": opponent_id,
            "player_name": player_name
        }
    
    # Strategy 1: Pattern Recognition
    move_sequence = player_data.get("move_sequence", [])
    pattern_history = player_data.get("pattern_history", {})
    
    if len(move_sequence) >= 2:
        last_pattern = str(tuple(move_sequence[-2:]))
        if last_pattern in pattern_history:
            pattern_data = pattern_history[last_pattern]
            pattern_total = sum(pattern_data.values())
            
            if pattern_total >= MIN_PATTERN_THRESHOLD:
                predicted_move = max(pattern_data, key=pattern_data.get)
                pattern_confidence = pattern_data[predicted_move] / pattern_total
                
                if pattern_confidence > 0.5:
                    counter = COUNTER_MOVES[predicted_move]
                    return {
                        "choice": counter,
                        "strategy_used": "pattern",
                        "confidence": round(pattern_confidence * 100),
                        "analysis": f"Detected {player_name}'s pattern: after {last_pattern}, picks {predicted_move}",
                        "predicted_opponent_move": predicted_move,
                        "pattern_occurrences": pattern_total,
                        "player_id": opponent_id,
                        "player_name": player_name
                    }
    
    # Strategy 2: Frequency Analysis
    probabilities = {
        "rock": history["rock"] / total_choices,
        "paper": history["paper"] / total_choices,
        "scissors": history["scissors"] / total_choices
    }
    
    predicted_choice = max(probabilities, key=probabilities.get)
    prediction_confidence = probabilities[predicted_choice]
    
    if prediction_confidence > 0.4:
        optimal_counter = COUNTER_MOVES[predicted_choice]
        
        RANDOMNESS_FACTOR = 0.15
        
        if random.random() < RANDOMNESS_FACTOR:
            final_choice = random.choice(choices)
            strategy = "random_variation"
        else:
            final_choice = optimal_counter
            strategy = "frequency"
        
        return {
            "choice": final_choice,
            "strategy_used": strategy,
            "confidence": round(prediction_confidence * 100),
            "analysis": f"{player_name} favors {predicted_choice} ({prediction_confidence*100:.1f}%)",
            "player_tendencies": {
                "rock": f"{probabilities['rock']*100:.1f}%",
                "paper": f"{probabilities['paper']*100:.1f}%",
                "scissors": f"{probabilities['scissors']*100:.1f}%"
            },
            "total_choices_analyzed": total_choices,
            "player_id": opponent_id,
            "player_name": player_name
        }
    
    # Strategy 3: Weighted Random
    weights = []
    for choice in choices:
        beats = RPS_RULES[choice]["beats"]
        weight = 1 + (history.get(beats, 0) / max(total_choices, 1))
        weights.append(weight)
    
    total_weight = sum(weights)
    weights = [w / total_weight for w in weights]
    final_choice = random.choices(choices, weights=weights, k=1)[0]
    
    return {
        "choice": final_choice,
        "strategy_used": "weighted",
        "confidence": round(max(weights) * 100),
        "analysis": f"No strong pattern for {player_name}, using weighted random",
        "player_tendencies": {
            "rock": f"{probabilities['rock']*100:.1f}%",
            "paper": f"{probabilities['paper']*100:.1f}%",
            "scissors": f"{probabilities['scissors']*100:.1f}%"
        },
        "player_id": opponent_id,
        "player_name": player_name
    }


def record_player_choice(player_id, choice):
    """
    Record a player's choice for AI learning using their unique ID.
    
    IMPORTANT: This function is ONLY called AFTER a round is complete.
    The CPU makes its strategic choice BEFORE this is called, ensuring
    the CPU cannot see the current round's choice - only historical data.
    
    Tracks:
    1. Frequency counts (choice_history)
    2. Move sequence (last N moves)
    3. Pattern history (what move follows each 2-move sequence)
    
    Flow:
    1. Player 1 picks -> Frontend stores locally (NOT sent to server yet)
    2. CPU calls /api/cpu/strategic_choice -> Uses ONLY historical data
    3. Both choices sent to /api/game/play_round -> THIS function records them
    """
    player_data = get_player_by_id(player_id)
    
    if not player_data or choice not in ["rock", "paper", "scissors"]:
        return
    
    # Skip tracking for CPU
    if player_data.get("is_cpu", False):
        return
    
    # Initialize tracking structures if needed
    if "choice_history" not in player_data:
        player_data["choice_history"] = {"rock": 0, "paper": 0, "scissors": 0}
    if "move_sequence" not in player_data:
        player_data["move_sequence"] = []
    if "pattern_history" not in player_data:
        player_data["pattern_history"] = {}
    
    # Update frequency count
    player_data["choice_history"][choice] += 1
    
    # Record pattern: what move follows the last 2 moves
    move_seq = player_data["move_sequence"]
    if len(move_seq) >= 2:
        pattern_key = str(tuple(move_seq[-2:]))
        if pattern_key not in player_data["pattern_history"]:
            player_data["pattern_history"][pattern_key] = {"rock": 0, "paper": 0, "scissors": 0}
        player_data["pattern_history"][pattern_key][choice] += 1
    
    # Update move sequence (keep last 10 moves)
    move_seq.append(choice)
    if len(move_seq) > 10:
        move_seq.pop(0)


def determine_round_winner(choice1, choice2):
    """Determine the winner of a single round."""
    if choice1 == choice2:
        return "tie"
    elif RPS_RULES[choice1]["beats"] == choice2:
        return "player1"
    else:
        return "player2"


# =============================================================================
# API ROUTES
# =============================================================================
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/player/register', methods=['POST'])
def register_player():
    """
    Register a new player with a unique ID.
    Always creates a new player entry, even if name already exists.
    This allows multiple players to have the same display name.
    """
    data = request.get_json()
    player_name = data.get('name', '').strip()
    is_cpu = data.get('is_cpu', False)
    
    if not player_name:
        return jsonify({"error": "Player name is required"}), 400
    
    # Handle CPU specially - use fixed ID
    if is_cpu or player_name.upper() == "CPU":
        return jsonify({
            "message": "CPU player ready",
            "player": {
                "id": CPU_ID,
                "name": "CPU",
                "stats": LEADERBOARD[CPU_ID]
            }
        }), 200
    
    # Generate unique ID for new player
    player_id = generate_player_id()
    
    LEADERBOARD[player_id] = {
        "id": player_id,
        "name": player_name,
        "score": 0,
        "games_won": 0,
        "games_played": 0,
        "is_cpu": False,
        "created_at": datetime.now().isoformat(),
        "choice_history": {"rock": 0, "paper": 0, "scissors": 0},
        "move_sequence": [],
        "pattern_history": {}
    }
    
    save_leaderboard()
    
    return jsonify({
        "message": f"Player '{player_name}' registered successfully",
        "player": {
            "id": player_id,
            "name": player_name,
            "stats": LEADERBOARD[player_id]
        }
    }), 201


@app.route('/api/player/<player_id>/stats', methods=['GET'])
def get_player_stats(player_id):
    """Get detailed statistics for a specific player by their unique ID."""
    player = get_player_by_id(player_id)
    
    if not player:
        return jsonify({"error": "Player not found"}), 404
    
    history = player.get("choice_history", {"rock": 0, "paper": 0, "scissors": 0})
    total = sum(history.values())
    
    stats = {
        "id": player_id,
        "name": player["name"],
        "score": player["score"],
        "games_won": player["games_won"],
        "games_played": player["games_played"],
        "total_choices": total,
        "choice_percentages": {
            "rock": round(history["rock"] / total * 100, 1) if total > 0 else 0,
            "paper": round(history["paper"] / total * 100, 1) if total > 0 else 0,
            "scissors": round(history["scissors"] / total * 100, 1) if total > 0 else 0
        }
    }
    
    return jsonify(stats), 200


@app.route('/api/game/start', methods=['POST'])
def start_game():
    """Start a new game between two players using their unique IDs."""
    global GAME_STATE
    data = request.get_json()
    
    player1_id = data.get('player1_id', '').strip()
    player2_id = data.get('player2_id', '').strip()
    
    if not player1_id or not player2_id:
        return jsonify({"error": "Both player IDs are required"}), 400
    
    player1 = get_player_by_id(player1_id)
    player2 = get_player_by_id(player2_id)
    
    if not player1 or not player2:
        return jsonify({"error": "Both players must be registered first"}), 400
    
    GAME_STATE = {
        "player1_id": player1_id,
        "player2_id": player2_id,
        "player1_name": player1["name"],
        "player2_name": player2["name"],
        "player1_round_wins": 0,
        "player2_round_wins": 0,
        "current_round": 0,
        "game_active": True,
        "previous_winner_id": GAME_STATE.get("previous_winner_id"),
        "previous_winner_name": GAME_STATE.get("previous_winner_name"),
        "game_history": []
    }
    
    save_leaderboard()
    
    return jsonify({
        "message": "Game started",
        "game_state": {
            "player1": {"id": player1_id, "name": player1["name"]},
            "player2": {"id": player2_id, "name": player2["name"]},
            "current_round": 0,
            "game_active": True
        }
    }), 200


@app.route('/api/game/play_round', methods=['POST'])
def play_round():
    """
    Play a round of the game.
    
    IMPORTANT - Data Flow for Fair Play:
    1. Player picks choice -> stored in frontend only
    2. CPU calls /api/cpu/strategic_choice -> analyzes PAST data only
    3. CPU returns choice -> stored in frontend
    4. Frontend calls THIS endpoint with BOTH choices
    5. THIS function records choices -> NOW they become historical data
    
    This ensures CPU only ever sees completed round data, never current round.
    """
    global GAME_STATE
    
    if not GAME_STATE["game_active"]:
        return jsonify({"error": "No active game"}), 400
    
    if GAME_STATE["current_round"] >= 10:
        return jsonify({"error": "Game is over"}), 400
    
    data = request.get_json()
    choice1 = data.get('player1_choice', '').lower()
    choice2 = data.get('player2_choice', '').lower()
    
    valid_choices = ['rock', 'paper', 'scissors']
    if choice1 not in valid_choices or choice2 not in valid_choices:
        return jsonify({"error": "Invalid choice"}), 400
    
    player1_id = GAME_STATE["player1_id"]
    player2_id = GAME_STATE["player2_id"]
    
    # Record choices for AI learning AFTER both players have committed
    # This is when choices become "historical" data for future CPU analysis
    record_player_choice(player1_id, choice1)
    record_player_choice(player2_id, choice2)
    
    GAME_STATE["current_round"] += 1
    
    round_result = determine_round_winner(choice1, choice2)
    
    round_data = {
        "round": GAME_STATE["current_round"],
        "player1_choice": choice1,
        "player2_choice": choice2,
        "result": round_result
    }
    
    if round_result == "player1":
        GAME_STATE["player1_round_wins"] += 1
        LEADERBOARD[player1_id]["score"] += 1
    elif round_result == "player2":
        GAME_STATE["player2_round_wins"] += 1
        LEADERBOARD[player2_id]["score"] += 1
    
    GAME_STATE["game_history"].append(round_data)
    
    game_over = GAME_STATE["current_round"] >= 10
    game_winner_id = None
    game_winner_name = None
    
    if game_over:
        GAME_STATE["game_active"] = False
        
        if GAME_STATE["player1_round_wins"] > GAME_STATE["player2_round_wins"]:
            game_winner_id = player1_id
            game_winner_name = GAME_STATE["player1_name"]
            LEADERBOARD[player1_id]["games_won"] += 1
        elif GAME_STATE["player2_round_wins"] > GAME_STATE["player1_round_wins"]:
            game_winner_id = player2_id
            game_winner_name = GAME_STATE["player2_name"]
            LEADERBOARD[player2_id]["games_won"] += 1
        
        LEADERBOARD[player1_id]["games_played"] += 1
        LEADERBOARD[player2_id]["games_played"] += 1
        
        # Store winner for retention (skip CPU)
        if game_winner_id and game_winner_id != CPU_ID:
            GAME_STATE["previous_winner_id"] = game_winner_id
            GAME_STATE["previous_winner_name"] = game_winner_name
        else:
            GAME_STATE["previous_winner_id"] = None
            GAME_STATE["previous_winner_name"] = None
    
    save_leaderboard()
    
    return jsonify({
        "round": round_data,
        "game_state": {
            "current_round": GAME_STATE["current_round"],
            "player1_round_wins": GAME_STATE["player1_round_wins"],
            "player2_round_wins": GAME_STATE["player2_round_wins"],
            "game_active": GAME_STATE["game_active"]
        },
        "game_over": game_over,
        "game_winner": {
            "id": game_winner_id,
            "name": game_winner_name
        } if game_winner_id else None
    }), 200


@app.route('/api/game/state', methods=['GET'])
def get_game_state():
    """Get current game state."""
    return jsonify({
        "game_active": GAME_STATE["game_active"],
        "player1": {
            "id": GAME_STATE["player1_id"],
            "name": GAME_STATE["player1_name"]
        },
        "player2": {
            "id": GAME_STATE["player2_id"],
            "name": GAME_STATE["player2_name"]
        },
        "current_round": GAME_STATE["current_round"],
        "player1_round_wins": GAME_STATE["player1_round_wins"],
        "player2_round_wins": GAME_STATE["player2_round_wins"],
        "previous_winner": {
            "id": GAME_STATE["previous_winner_id"],
            "name": GAME_STATE["previous_winner_name"]
        } if GAME_STATE["previous_winner_id"] else None,
        "game_history": GAME_STATE["game_history"]
    }), 200


@app.route('/api/cpu/strategic_choice', methods=['POST'])
def cpu_strategic_choice():
    """
    Get a strategic choice from the CPU based on opponent's HISTORICAL data only.
    
    FAIR PLAY GUARANTEE:
    - CPU can ONLY see data from COMPLETED rounds (choice_history, pattern_history)
    - CPU CANNOT see the current round's choice (it hasn't been recorded yet)
    - Player's current choice is stored in frontend only until round is submitted
    - Data is only recorded via play_round() AFTER CPU has already chosen
    
    This ensures the CPU never "cheats" by seeing what the player picked this round.
    """
    data = request.get_json()
    opponent_id = data.get('opponent_id', '').strip()
    
    if not opponent_id:
        return jsonify({"error": "Opponent ID is required"}), 400
    
    result = get_strategic_cpu_choice(opponent_id)
    
    return jsonify(result), 200


@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    """
    Retrieves the complete leaderboard with two sorted views.
    Includes unique IDs for each player.
    """
    # Convert Dictionary to List of Dictionaries
    players_list = [
        {
            "id": player_id,
            "name": stats["name"],
            "score": stats["score"],
            "games_won": stats["games_won"],
            "games_played": stats["games_played"],
            "is_cpu": stats.get("is_cpu", False),
            "total_rounds": sum(stats.get("choice_history", {}).values())
        }
        for player_id, stats in LEADERBOARD.items()
    ]
    
    # Sorting Algorithm 1: Alphabetically by name (case-insensitive)
    sorted_by_name = sorted(players_list, key=lambda x: x["name"].lower())
    
    # Sorting Algorithm 2: Numerically by score (descending)
    sorted_by_score = sorted(players_list, key=lambda x: (-x["score"], x["name"].lower()))
    
    return jsonify({
        "total_players": len(players_list),
        "sorted_by_name": sorted_by_name,
        "sorted_by_score": sorted_by_score
    }), 200


@app.route('/api/reset', methods=['POST'])
def reset_tournament():
    """Reset all tournament data."""
    global LEADERBOARD, GAME_STATE
    
    LEADERBOARD = {}
    init_cpu_player()
    
    GAME_STATE = {
        "player1_id": None,
        "player2_id": None,
        "player1_name": None,
        "player2_name": None,
        "player1_round_wins": 0,
        "player2_round_wins": 0,
        "current_round": 0,
        "game_active": False,
        "previous_winner_id": None,
        "previous_winner_name": None,
        "game_history": []
    }
    
    save_leaderboard()
    
    return jsonify({"message": "Tournament reset successfully"}), 200


# =============================================================================
# Run the Flask application
# =============================================================================
if __name__ == '__main__':
    app.run(debug=True, port=5000)