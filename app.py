"""
Rock-Paper-Scissors Tournament Leaderboard
CSCI 210 Final Project

A Flask-based web application that manages a persistent, multi-player
Rock-Paper-Scissors tournament using Dictionary and List data structures.

Features:
- Global LEADERBOARD dictionary for O(1) player lookups
- List conversion with sorting for dual leaderboard views
- Strategic AI with player choice memory and pattern recognition
- Secure file-based persistence with SHA-256 checksums
"""

from flask import Flask, jsonify, request, render_template
import random
import json
import hashlib
import os
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
# Key: Unique player name (String)
# Value: Nested dictionary with cumulative statistics
# Purpose: O(1) average time complexity for searching and updating
# 
# Enhanced with choice_history and pattern tracking for AI:
# {
#     "PlayerName": {
#         "score": int,
#         "games_won": int,
#         "games_played": int,
#         "is_cpu": bool,
#         "choice_history": {           # Frequency counts
#             "rock": int,
#             "paper": int,
#             "scissors": int
#         },
#         "move_sequence": [],           # Last N moves for pattern detection
#         "pattern_history": {           # What move follows each 2-move pattern
#             "(rock,rock)": {"rock": 0, "paper": 0, "scissors": 0},
#             "(rock,paper)": {...}, ...
#         }
#     }
# }
# =============================================================================
LEADERBOARD = {}

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
    "previous_winner": None,
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
            print(f"Warning: Could not create backup: {e}")
    
    save_data = {
        "leaderboard": LEADERBOARD,
        "checksum": calculate_checksum(LEADERBOARD),
        "saved_at": datetime.now().isoformat()
    }
    
    with open(DATA_FILE, 'w') as f:
        json.dump(save_data, f, indent=2)


def load_leaderboard():
    """Load LEADERBOARD from JSON file with integrity verification."""
    global LEADERBOARD
    
    if not os.path.exists(DATA_FILE):
        LEADERBOARD = {}
        return
    
    try:
        with open(DATA_FILE, 'r') as f:
            save_data = json.load(f)
        
        stored_checksum = save_data.get("checksum", "")
        loaded_data = save_data.get("leaderboard", {})
        calculated_checksum = calculate_checksum(loaded_data)
        
        if stored_checksum == calculated_checksum:
            for player_name, stats in loaded_data.items():
                if "choice_history" not in stats:
                    stats["choice_history"] = {"rock": 0, "paper": 0, "scissors": 0}
            LEADERBOARD = loaded_data
            print(f"Leaderboard loaded successfully ({len(LEADERBOARD)} players)")
        else:
            print("Warning: Checksum mismatch, attempting backup restore...")
            load_from_backup()
            
    except Exception as e:
        print(f"Error loading leaderboard: {e}")
        load_from_backup()


def load_from_backup():
    """Attempt to restore from backup file."""
    global LEADERBOARD
    
    if os.path.exists(BACKUP_FILE):
        try:
            with open(BACKUP_FILE, 'r') as f:
                backup_data = json.load(f)
            loaded_data = backup_data.get("leaderboard", {})
            for player_name, stats in loaded_data.items():
                if "choice_history" not in stats:
                    stats["choice_history"] = {"rock": 0, "paper": 0, "scissors": 0}
            LEADERBOARD = loaded_data
            print("Restored from backup successfully")
        except Exception as e:
            print(f"Backup restore failed: {e}")
            LEADERBOARD = {}
    else:
        LEADERBOARD = {}


load_leaderboard()


# =============================================================================
# AI STRATEGY FUNCTIONS
# =============================================================================
def get_strategic_cpu_choice(opponent_name):
    """
    AI Strategy: Analyze opponent's play patterns and make strategic counter-pick.
    
    Strategy Priority:
    1. Pattern Recognition - If we've seen the last 2 moves before, predict next move
    2. Frequency Analysis - Counter opponent's most common choice
    3. Weighted Random - Slight bias toward countering common moves
    4. Pure Random - Fallback when insufficient data
    """
    choices = ["rock", "paper", "scissors"]
    MIN_HISTORY_THRESHOLD = 5
    MIN_PATTERN_THRESHOLD = 3
    
    if opponent_name not in LEADERBOARD:
        return {
            "choice": random.choice(choices),
            "strategy_used": "random",
            "confidence": 0,
            "analysis": "Unknown opponent"
        }
    
    player_data = LEADERBOARD[opponent_name]
    history = player_data.get("choice_history", {"rock": 0, "paper": 0, "scissors": 0})
    total_choices = sum(history.values())
    
    if total_choices < MIN_HISTORY_THRESHOLD:
        return {
            "choice": random.choice(choices),
            "strategy_used": "learning",
            "confidence": total_choices,
            "analysis": f"Still learning ({total_choices}/{MIN_HISTORY_THRESHOLD} moves)"
        }
    
    # Strategy 1: Pattern Recognition
    # Check if we can predict based on the last 2 moves
    move_sequence = player_data.get("move_sequence", [])
    pattern_history = player_data.get("pattern_history", {})
    
    if len(move_sequence) >= 2:
        last_pattern = str(tuple(move_sequence[-2:]))
        if last_pattern in pattern_history:
            pattern_data = pattern_history[last_pattern]
            pattern_total = sum(pattern_data.values())
            
            if pattern_total >= MIN_PATTERN_THRESHOLD:
                # Find the most likely next move
                predicted_move = max(pattern_data, key=pattern_data.get)
                pattern_confidence = pattern_data[predicted_move] / pattern_total
                
                # If confidence > 50%, counter the predicted move
                if pattern_confidence > 0.5:
                    counter = COUNTER_MOVES[predicted_move]
                    return {
                        "choice": counter,
                        "strategy_used": "pattern",
                        "confidence": round(pattern_confidence * 100),
                        "analysis": f"Detected pattern: after {last_pattern}, player picks {predicted_move}",
                        "predicted_opponent_move": predicted_move,
                        "pattern_occurrences": pattern_total
                    }
    
    # Strategy 2: Frequency Analysis
    probabilities = {
        "rock": history["rock"] / total_choices,
        "paper": history["paper"] / total_choices,
        "scissors": history["scissors"] / total_choices
    }
    
    predicted_choice = max(probabilities, key=probabilities.get)
    prediction_confidence = probabilities[predicted_choice]
    
    # If there's a clear preference (> 40%), counter it
    if prediction_confidence > 0.4:
        optimal_counter = COUNTER_MOVES[predicted_choice]
        
        # Add some randomness (15%) to stay unpredictable
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
            "analysis": f"Player favors {predicted_choice} ({prediction_confidence*100:.1f}%)",
            "player_tendencies": {
                "rock": f"{probabilities['rock']*100:.1f}%",
                "paper": f"{probabilities['paper']*100:.1f}%",
                "scissors": f"{probabilities['scissors']*100:.1f}%"
            },
            "total_choices_analyzed": total_choices
        }
    
    # Strategy 3: Weighted Random
    # No clear pattern, but bias toward countering common moves
    weights = []
    for choice in choices:
        # What does this choice beat?
        beats = RPS_RULES[choice]["beats"]
        # Weight by how often opponent plays what this beats
        weight = 1 + (history.get(beats, 0) / max(total_choices, 1))
        weights.append(weight)
    
    # Normalize and pick
    total_weight = sum(weights)
    weights = [w / total_weight for w in weights]
    final_choice = random.choices(choices, weights=weights, k=1)[0]
    
    return {
        "choice": final_choice,
        "strategy_used": "weighted",
        "confidence": round(max(weights) * 100),
        "analysis": "No strong pattern detected, using weighted random",
        "player_tendencies": {
            "rock": f"{probabilities['rock']*100:.1f}%",
            "paper": f"{probabilities['paper']*100:.1f}%",
            "scissors": f"{probabilities['scissors']*100:.1f}%"
        }
    }


def record_player_choice(player_name, choice):
    """
    Record a player's choice for AI learning.
    
    Tracks:
    1. Frequency counts (choice_history)
    2. Move sequence (last N moves)
    3. Pattern history (what move follows each 2-move sequence)
    """
    if player_name not in LEADERBOARD or choice not in ["rock", "paper", "scissors"]:
        return
    
    player_data = LEADERBOARD[player_name]
    
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


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/player/register', methods=['POST'])
def register_player():
    data = request.get_json()
    player_name = data.get('name', '').strip()
    is_cpu = data.get('is_cpu', False)
    
    if not player_name:
        return jsonify({"error": "Player name is required"}), 400
    
    if player_name not in LEADERBOARD:
        LEADERBOARD[player_name] = {
            "score": 0,
            "games_won": 0,
            "games_played": 0,
            "is_cpu": is_cpu,
            "choice_history": {"rock": 0, "paper": 0, "scissors": 0}
        }
        save_leaderboard()
        return jsonify({
            "message": f"Player '{player_name}' registered successfully",
            "player": {"name": player_name, "stats": LEADERBOARD[player_name]}
        }), 201
    else:
        return jsonify({
            "message": f"Player '{player_name}' already exists",
            "player": {"name": player_name, "stats": LEADERBOARD[player_name]}
        }), 200


@app.route('/api/game/start', methods=['POST'])
def start_game():
    global GAME_STATE
    data = request.get_json()
    
    player1 = data.get('player1', '').strip()
    player2 = data.get('player2', '').strip()
    
    if not player1 or not player2:
        return jsonify({"error": "Both player names are required"}), 400
    
    if player1 not in LEADERBOARD or player2 not in LEADERBOARD:
        return jsonify({"error": "Both players must be registered first"}), 400
    
    GAME_STATE = {
        "player1": player1,
        "player2": player2,
        "player1_round_wins": 0,
        "player2_round_wins": 0,
        "current_round": 0,
        "game_active": True,
        "previous_winner": GAME_STATE.get("previous_winner"),
        "game_history": []
    }
    
    save_leaderboard()
    
    return jsonify({"message": "Game started", "game_state": GAME_STATE}), 200


@app.route('/api/game/play_round', methods=['POST'])
def play_round():
    global GAME_STATE
    
    if not GAME_STATE["game_active"]:
        return jsonify({"error": "No active game. Start a game first."}), 400
    
    data = request.get_json()
    choice1 = data.get('player1_choice', '').lower()
    choice2 = data.get('player2_choice', '').lower()
    
    valid_choices = ["rock", "paper", "scissors"]
    if choice1 not in valid_choices or choice2 not in valid_choices:
        return jsonify({"error": "Invalid choice. Use rock, paper, or scissors."}), 400
    
    player1_name = GAME_STATE["player1"]
    player2_name = GAME_STATE["player2"]
    
    if not LEADERBOARD.get(player1_name, {}).get("is_cpu", False):
        record_player_choice(player1_name, choice1)
    if not LEADERBOARD.get(player2_name, {}).get("is_cpu", False):
        record_player_choice(player2_name, choice2)
    
    round_result = determine_round_winner(choice1, choice2)
    
    GAME_STATE["current_round"] += 1
    
    round_data = {
        "round": GAME_STATE["current_round"],
        "player1_choice": choice1,
        "player2_choice": choice2,
        "result": round_result
    }
    
    if round_result == "player1":
        GAME_STATE["player1_round_wins"] += 1
        LEADERBOARD[player1_name]["score"] += 1
    elif round_result == "player2":
        GAME_STATE["player2_round_wins"] += 1
        LEADERBOARD[player2_name]["score"] += 1
    
    GAME_STATE["game_history"].append(round_data)
    
    game_over = GAME_STATE["current_round"] >= 10
    game_winner = None
    
    if game_over:
        GAME_STATE["game_active"] = False
        
        if GAME_STATE["player1_round_wins"] > GAME_STATE["player2_round_wins"]:
            game_winner = player1_name
            LEADERBOARD[player1_name]["games_won"] += 1
        elif GAME_STATE["player2_round_wins"] > GAME_STATE["player1_round_wins"]:
            game_winner = player2_name
            LEADERBOARD[player2_name]["games_won"] += 1
        
        LEADERBOARD[player1_name]["games_played"] += 1
        LEADERBOARD[player2_name]["games_played"] += 1
        
        if game_winner and not LEADERBOARD.get(game_winner, {}).get("is_cpu", False):
            GAME_STATE["previous_winner"] = game_winner
        else:
            GAME_STATE["previous_winner"] = None
    
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
        "game_winner": game_winner
    }), 200


@app.route('/api/cpu/strategic_choice', methods=['POST'])
def cpu_strategic_choice():
    """Get a strategic choice from the CPU based on opponent's history."""
    data = request.get_json()
    opponent_name = data.get('opponent_name', '').strip()
    
    if not opponent_name:
        return jsonify({"error": "Opponent name is required"}), 400
    
    result = get_strategic_cpu_choice(opponent_name)
    
    return jsonify(result), 200


@app.route('/api/player/<name>/stats', methods=['GET'])
def get_player_stats(name):
    """Get detailed statistics for a specific player."""
    if name not in LEADERBOARD:
        return jsonify({"error": "Player not found"}), 404
    
    stats = LEADERBOARD[name].copy()
    history = stats.get("choice_history", {"rock": 0, "paper": 0, "scissors": 0})
    total = history["rock"] + history["paper"] + history["scissors"]
    
    if total > 0:
        stats["choice_percentages"] = {
            "rock": round(history["rock"] / total * 100, 1),
            "paper": round(history["paper"] / total * 100, 1),
            "scissors": round(history["scissors"] / total * 100, 1)
        }
    else:
        stats["choice_percentages"] = {"rock": 0, "paper": 0, "scissors": 0}
    
    stats["total_choices"] = total
    
    return jsonify({"name": name, "stats": stats}), 200


@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    """Retrieves the complete leaderboard with two sorted views."""
    players_list = [
        {
            "name": name,
            "score": stats["score"],
            "games_won": stats["games_won"],
            "games_played": stats["games_played"],
            "is_cpu": stats.get("is_cpu", False),
            "choice_history": stats.get("choice_history", {"rock": 0, "paper": 0, "scissors": 0})
        }
        for name, stats in LEADERBOARD.items()
    ]
    
    sorted_by_name = sorted(players_list, key=lambda x: x["name"].lower())
    sorted_by_score = sorted(players_list, key=lambda x: (-x["score"], x["name"].lower()))
    
    return jsonify({
        "by_name": sorted_by_name,
        "by_score": sorted_by_score,
        "total_players": len(players_list)
    }), 200


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
    save_leaderboard()
    return jsonify({"message": "Tournament reset successfully"}), 200


if __name__ == '__main__':
    app.run(debug=True, port=5000)