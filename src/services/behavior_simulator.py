"""Behavior Simulation Scheduler Service

This service runs in the background and periodically simulates user behavior
(fetching feed, viewing posts, liking) for tokens to make them appear more active.
"""
import asyncio
import random
import time
from datetime import datetime
from typing import Dict, Set, Optional, List
from dataclasses import dataclass, field


@dataclass
class TokenSimulationState:
    """Track simulation state for a single token"""
    token_id: int
    last_simulation_time: float = 0.0
    simulation_count: int = 0
    last_error: Optional[str] = None
    is_simulating: bool = False


@dataclass
class BehaviorSimulatorConfig:
    """Configuration for the behavior simulator"""
    enabled: bool = True
    # Interval between simulation rounds (in seconds)
    min_interval: int = 300  # 5 minutes minimum
    max_interval: int = 900  # 15 minutes maximum
    # How many tokens to simulate per round
    tokens_per_round: int = 3
    # Prioritize tokens that haven't been simulated recently
    prioritize_unsimulated: bool = True
    # Skip tokens that had errors recently (cooldown in seconds)
    error_cooldown: int = 600  # 10 minutes


class BehaviorSimulator:
    """Background service that simulates user behavior for tokens"""
    
    def __init__(self):
        self._config = BehaviorSimulatorConfig()
        self._token_states: Dict[int, TokenSimulationState] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._db = None
        self._sora_client = None
        self._lock = asyncio.Lock()
    
    def configure(
        self,
        enabled: bool = None,
        min_interval: int = None,
        max_interval: int = None,
        tokens_per_round: int = None,
        prioritize_unsimulated: bool = None,
        error_cooldown: int = None
    ):
        """Update simulator configuration"""
        if enabled is not None:
            self._config.enabled = enabled
        if min_interval is not None:
            self._config.min_interval = max(60, min_interval)  # At least 1 minute
        if max_interval is not None:
            self._config.max_interval = max(self._config.min_interval, max_interval)
        if tokens_per_round is not None:
            self._config.tokens_per_round = max(1, min(10, tokens_per_round))
        if prioritize_unsimulated is not None:
            self._config.prioritize_unsimulated = prioritize_unsimulated
        if error_cooldown is not None:
            self._config.error_cooldown = max(60, error_cooldown)
        
        print(f"🤖 [BehaviorSimulator] Config updated: enabled={self._config.enabled}, "
              f"interval={self._config.min_interval}-{self._config.max_interval}s, "
              f"tokens_per_round={self._config.tokens_per_round}")
    
    def get_config(self) -> dict:
        """Get current configuration"""
        return {
            "enabled": self._config.enabled,
            "min_interval": self._config.min_interval,
            "max_interval": self._config.max_interval,
            "tokens_per_round": self._config.tokens_per_round,
            "prioritize_unsimulated": self._config.prioritize_unsimulated,
            "error_cooldown": self._config.error_cooldown,
            "running": self._running
        }
    
    def get_stats(self) -> dict:
        """Get simulation statistics"""
        total_simulations = sum(s.simulation_count for s in self._token_states.values())
        tokens_with_errors = sum(1 for s in self._token_states.values() if s.last_error)
        tokens_simulated = sum(1 for s in self._token_states.values() if s.simulation_count > 0)
        
        return {
            "running": self._running,
            "total_tokens_tracked": len(self._token_states),
            "tokens_simulated": tokens_simulated,
            "tokens_with_errors": tokens_with_errors,
            "total_simulations": total_simulations,
            "token_details": [
                {
                    "token_id": state.token_id,
                    "simulation_count": state.simulation_count,
                    "last_simulation": datetime.fromtimestamp(state.last_simulation_time).isoformat() if state.last_simulation_time > 0 else None,
                    "last_error": state.last_error,
                    "is_simulating": state.is_simulating
                }
                for state in sorted(self._token_states.values(), key=lambda x: x.simulation_count, reverse=True)
            ]
        }
    
    async def start(self, db, sora_client):
        """Start the background simulation task"""
        if self._running:
            print("🤖 [BehaviorSimulator] Already running")
            return
        
        self._db = db
        self._sora_client = sora_client
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        print(f"🤖 [BehaviorSimulator] Started background simulation task")
    
    async def stop(self):
        """Stop the background simulation task"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        print(f"🤖 [BehaviorSimulator] Stopped")
    
    async def _run_loop(self):
        """Main simulation loop"""
        # Initial delay to let the system fully start
        await asyncio.sleep(30)
        
        while self._running:
            try:
                if self._config.enabled:
                    await self._run_simulation_round()
                
                # Random interval between rounds
                interval = random.randint(self._config.min_interval, self._config.max_interval)
                print(f"🤖 [BehaviorSimulator] Next round in {interval}s")
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"🤖 [BehaviorSimulator] ❌ Loop error: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _run_simulation_round(self):
        """Run one round of simulation"""
        if not self._db or not self._sora_client:
            return
        
        print(f"🤖 [BehaviorSimulator] Starting simulation round...")
        
        # Get all active tokens
        all_tokens = await self._db.get_all_tokens()
        active_tokens = [t for t in all_tokens if t.is_active]
        
        if not active_tokens:
            print(f"🤖 [BehaviorSimulator] No active tokens available")
            return
        
        # Initialize states for new tokens
        for token in active_tokens:
            if token.id not in self._token_states:
                self._token_states[token.id] = TokenSimulationState(token_id=token.id)
        
        # Select tokens to simulate
        tokens_to_simulate = await self._select_tokens(active_tokens)
        
        print(f"🤖 [BehaviorSimulator] Selected {len(tokens_to_simulate)} tokens for simulation")
        
        # Simulate each selected token
        for token in tokens_to_simulate:
            if not self._running:
                break
            
            await self._simulate_token(token)
            
            # Small delay between tokens
            await asyncio.sleep(random.uniform(2, 5))
    
    async def _select_tokens(self, active_tokens: List) -> List:
        """Select which tokens to simulate this round"""
        current_time = time.time()
        
        # Filter out tokens currently being simulated or in error cooldown
        eligible_tokens = []
        for token in active_tokens:
            state = self._token_states.get(token.id)
            if not state:
                eligible_tokens.append(token)
                continue
            
            # Skip if currently simulating
            if state.is_simulating:
                continue
            
            # Skip if in error cooldown
            if state.last_error and (current_time - state.last_simulation_time) < self._config.error_cooldown:
                continue
            
            eligible_tokens.append(token)
        
        if not eligible_tokens:
            return []
        
        # Sort by priority
        if self._config.prioritize_unsimulated:
            # Prioritize tokens that haven't been simulated or were simulated longest ago
            eligible_tokens.sort(
                key=lambda t: self._token_states.get(t.id, TokenSimulationState(token_id=t.id)).last_simulation_time
            )
        else:
            # Random selection
            random.shuffle(eligible_tokens)
        
        # Take the configured number of tokens
        return eligible_tokens[:self._config.tokens_per_round]
    
    async def _simulate_token(self, token):
        """Simulate behavior for a single token"""
        state = self._token_states.get(token.id)
        if not state:
            state = TokenSimulationState(token_id=token.id)
            self._token_states[token.id] = state
        
        state.is_simulating = True
        
        try:
            # Get token's access token
            access_token = token.token
            if not access_token:
                state.last_error = "No access token"
                return
            
            print(f"🤖 [BehaviorSimulator] Simulating token #{token.id} ({token.name or 'unnamed'})...")
            
            # Run the behavior simulation
            result = await self._sora_client.simulate_user_behavior(access_token)
            
            # Update state
            state.last_simulation_time = time.time()
            state.simulation_count += 1
            
            if result.get("errors"):
                state.last_error = result["errors"][0]
                print(f"🤖 [BehaviorSimulator] Token #{token.id} completed with errors: {result['errors']}")
            else:
                state.last_error = None
                print(f"🤖 [BehaviorSimulator] ✅ Token #{token.id} simulated: "
                      f"views={result.get('views_submitted', 0)}, likes={result.get('posts_liked', 0)}")
            
        except Exception as e:
            state.last_error = str(e)
            state.last_simulation_time = time.time()
            print(f"🤖 [BehaviorSimulator] ❌ Token #{token.id} failed: {e}")
        finally:
            state.is_simulating = False
    
    async def simulate_token_now(self, token_id: int) -> dict:
        """Manually trigger simulation for a specific token"""
        if not self._db or not self._sora_client:
            return {"success": False, "error": "Simulator not initialized"}
        
        token = await self._db.get_token_by_id(token_id)
        if not token:
            return {"success": False, "error": "Token not found"}
        
        if not token.is_active:
            return {"success": False, "error": "Token is not active"}
        
        state = self._token_states.get(token_id)
        if state and state.is_simulating:
            return {"success": False, "error": "Token is already being simulated"}
        
        await self._simulate_token(token)
        
        state = self._token_states.get(token_id)
        return {
            "success": state.last_error is None if state else False,
            "simulation_count": state.simulation_count if state else 0,
            "last_error": state.last_error if state else None
        }


# Global singleton instance
behavior_simulator = BehaviorSimulator()
