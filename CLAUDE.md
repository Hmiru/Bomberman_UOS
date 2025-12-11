# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Running the Game
```bash
# Play a match with 4 agents
python main.py play --agents shrimp shrimp rule_based_agent rule_based_agent

# Play with your agent against 3 rule-based agents
python main.py play --my-agent <your_agent_name>

# Play without GUI for faster execution
python main.py play --no-gui --n-rounds 10

# Play with a specific scenario
python main.py play --scenario classic  # Options: empty, coin-heaven, loot-crate, classic

# Train an agent (set first agent to training mode)
python main.py play --agents <your_agent> rule_based_agent rule_based_agent rule_based_agent --train 1

# Replay a saved game
python main.py replay <path_to_replay_file>
```

### Testing
```bash
# Run the basic test suite
python test.py

# Run unittest tests
python -m unittest
```

## Architecture Overview

### Core Components

**Game Engine**: The game loop is managed by `main.py` which coordinates:
- `environment.py`: Contains `BombeRLeWorld` class that manages game state, arena building, and game rules
- `agents.py`: Agent management system with `Agent` class and backend implementations
- `items.py`: Game objects (Coin, Bomb, Explosion) 
- `events.py`: Event definitions used for rewards and game logic
- `settings.py`: Game configuration including scenarios, timeouts, and rewards

**Agent System**: Each agent lives in `agent_code/<agent_name>/` and must implement:
- `callbacks.py`: Required functions `setup()` and `act()` for agent behavior
- `train.py` (optional): Training functions for learning agents

The game provides state information to agents as a dictionary containing:
- `round`: Current round number
- `step`: Current step in the round
- `field`: 2D arena array
- `bombs`: List of bomb positions and timers
- `explosion_map`: Current explosion positions
- `coins`: List of coin positions
- `self`: Agent's own state (position, bombs left, score)
- `others`: List of other agents' states

### Available Agents

- `rule_based_agent`: Hand-coded logic for competent play
- `shrimp`: Another rule-based implementation
- `random_agent`: Selects random valid actions
- `user_agent`: Human-controlled via keyboard
- `peaceful_agent`: Avoids combat
- `coin_collector_agent`: Focuses on collecting coins
- `tpl_agent`: Template for creating new RL agents with training structure
- `totoro`: Custom agent implementation

### Game Scenarios

Defined in `settings.py`:
- **empty**: No crates or coins (for testing movement)
- **coin-heaven**: No crates, 50 coins (for reward shaping)
- **loot-crate**: 75% crate density, 50 coins (practice destroying crates)
- **classic**: Tournament mode - 75% crates, 9 coins

### Key Game Parameters

- Arena size: 17x17 tiles
- Max agents: 4
- Bomb power: 3 tiles
- Bomb timer: 4 steps
- Agent timeout: 0.5 seconds (infinite during training)
- Max steps per round: 400

### Reward System

Standard rewards (defined in `settings.py`):
- Kill opponent: 5 points
- Collect coin: 1 point
- Custom events can be added in agent's `train.py`

### State Features

Agents receive game state and should extract relevant features. The `state_to_features()` function in agent callbacks converts raw state to feature vectors for learning algorithms.

## Development Notes

- Agents must return actions within the timeout or a fallback action is chosen
- Training mode disables timeout restrictions
- Game logs are written to `logs/` directory
- Replays are saved as `.pt` files when using `--save-replay`
- The `--silence-errors` flag suppresses agent exceptions during play