import sys
import os
import random

# Ensure we can import from the parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import TaskDifficulty, LoadZone, PowerGridObservation, PowerGridAction, StepResponse

class PowerGridEnv:
    def __init__(self):
        self.max_steps = 24  # 1 step = 1 hour, standard 24 hour episode
        
        # Grid capabilities
        self.battery_max_capacity_kwh = 500.0
        self.battery_max_flow_kw = 200.0
        self.diesel_max_output_kw = 1000.0
        self.grid_trade_max_kw = 1000.0
        
        # Episode state
        self.current_step = 0
        self.task_id = None
        
        # Dynamic variables
        self.battery_current_energy = 0.0
        self.current_frequency = 50.0
        self.current_spot_price = 0.15 # $/kWh
        
    def reset(self, task_id: TaskDifficulty) -> PowerGridObservation:
        """
        Initializes the episode based on the task difficulty.
        """
        self.task_id = task_id
        self.current_step = 0
        self.current_frequency = 50.0
        
        # Initialize conditions based on difficulty
        if task_id == TaskDifficulty.EASY:
            self.battery_current_energy = self.battery_max_capacity_kwh * 0.5
            self.current_spot_price = 0.10
        elif task_id == TaskDifficulty.MEDIUM:
            self.battery_current_energy = self.battery_max_capacity_kwh * 0.5
            self.current_spot_price = 0.15
        elif task_id == TaskDifficulty.HARD:
            # Low battery at the start of a storm
            self.battery_current_energy = self.battery_max_capacity_kwh * 0.2
            self.current_spot_price = 0.40
            
        return self._get_obs()

    def _get_obs(self) -> PowerGridObservation:
        """
        Generates the current observation, including forecasts.
        """
        forecast_solar = []
        forecast_wind = []
        forecast_demand = []
        
        # Look ahead 5 steps
        for i in range(5):
            hour = (self.current_step + i) % 24
            
            # Simple baseline curves
            demand = 2000.0 if hour > 17 else 1000.0
            solar = 1500.0 if 8 <= hour <= 18 else 0.0
            wind = 500.0
            
            # Adjust based on difficulty
            if self.task_id == TaskDifficulty.HARD:
                solar = 0.0  # Storm: No solar
                wind = 0.0   # Storm: High winds but turbines locked for safety
                demand += 1000.0  # Demand surge
            elif self.task_id == TaskDifficulty.MEDIUM:
                solar *= (0.4 + 0.6 * random.random())  # Cloud cover
                demand *= (0.8 + 0.4 * random.random()) # Unpredictable demand
                
            forecast_solar.append(solar)
            forecast_wind.append(wind)
            forecast_demand.append(demand)
            
        obs = PowerGridObservation(
            current_demand_kw=forecast_demand[0],
            grid_frequency_hz=self.current_frequency,
            spot_price_dollars=self.current_spot_price,
            battery_charge_level=self.battery_current_energy / self.battery_max_capacity_kwh,
            forecast_solar_kw=forecast_solar,
            forecast_wind_kw=forecast_wind,
            forecast_demand_kw=forecast_demand
        )
        return obs

    def step(self, action: PowerGridAction) -> StepResponse:
        """
        The physics engine. Applies the agent's action and advances the simulation.
        """
        obs = self._get_obs()
        
        # 1. Calculate Supply
        solar_supply = obs.forecast_solar_kw[0]
        wind_supply = obs.forecast_wind_kw[0]
        diesel_supply = action.diesel_activation * self.diesel_max_output_kw
        
        # Battery Physics: 
        # battery_flow > 0 means charging (consumes power)
        # battery_flow < 0 means discharging (supplies power)
        requested_battery_kw = action.battery_flow * self.battery_max_flow_kw
        
        actual_battery_kw = 0.0
        if requested_battery_kw > 0.0: # Agent wants to charge
            space_left = self.battery_max_capacity_kwh - self.battery_current_energy
            actual_battery_kw = min(requested_battery_kw, space_left)
            self.battery_current_energy += actual_battery_kw
        elif requested_battery_kw < 0.0: # Agent wants to discharge
            energy_available = self.battery_current_energy
            actual_battery_kw = max(requested_battery_kw, -energy_available)
            self.battery_current_energy += actual_battery_kw
            
        # If battery flow is negative, it's adding to supply
        battery_supply_kw = -actual_battery_kw

        # Grid trade: > 0 buying (supply), < 0 selling (demand)
        grid_trade_kw = action.grid_trade * self.grid_trade_max_kw
        
        total_supply = solar_supply + wind_supply + diesel_supply + battery_supply_kw + grid_trade_kw
        
        # 2. Calculate Demand
        demand = obs.current_demand_kw
        if action.shed_load_zone == LoadZone.ZONE_A:
            demand *= 0.8
        elif action.shed_load_zone == LoadZone.ZONE_B:
            demand *= 0.6

        # 3. Frequency Physics
        net_power = total_supply - demand
        frequency_delta = (net_power / 2000.0) * 0.5  # Mapping delta kW to delta Hz
        self.current_frequency += frequency_delta
        
        # Grid natural inertia slowly pulls frequency towards 50.0 if not out of bounds
        self.current_frequency += (50.0 - self.current_frequency) * 0.1
        
        # 4. Step Rewards
        # Simple dense reward for Phase 2: heavily penalize straying from 50.0Hz
        frequency_error = abs(self.current_frequency - 50.0)
        reward = 1.0 - (frequency_error / 1.0)
        reward = max(0.0, min(1.0, reward))
        
        # 5. Check Terminal Conditions
        self.current_step += 1
        done = False
        
        if self.current_step >= self.max_steps:
            done = True
        
        if self.current_frequency < 49.0 or self.current_frequency > 51.0:
            done = True
            reward = 0.0  # Blackout penalty!
            
        new_obs = self._get_obs()
        return StepResponse(observation=new_obs, reward=reward, done=done, info={"net_power_kw": net_power})

    def state(self) -> dict:
        """
        Returns environment metadata.
        """
        return {
            "current_step": self.current_step,
            "max_steps": self.max_steps,
            "task_id": self.task_id.value if self.task_id else None,
            "agent_alive": not (self.current_frequency < 49.0 or self.current_frequency > 51.0)
        }
