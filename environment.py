import sys
import os
import random
import numpy as np

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
        self.cumulative_reward = 0.0
        
        # Dynamic variables
        self.battery_current_energy = 0.0
        self.current_frequency = 50.0
        
        # Scenario arrays
        self.solar_arr = None
        self.demand_arr = None
        self.price_arr = None

    def _generate_scenario(self, task_id: TaskDifficulty):
        steps = self.max_steps
        
        # 1. Establish the Baselines
        solar = np.zeros(steps)
        demand = np.full(steps, 1000.0)      # Base demand of 1000 kW
        spot_price = np.full(steps, 0.10)   # Base price of $0.10 per kWh
        
        # Create a perfect sunny day curve using a sine wave (6 AM to 6 PM)
        # This peaks at 1500 kW of generation
        solar[6:18] = np.sin(np.linspace(0, np.pi, 12)) * 1500.0 
        
        # 2. Modify based on Task ID
        if task_id == TaskDifficulty.EASY:
            # Predictable evening spike at 5 PM - 8 PM
            demand[17:21] += 1000.0 
            start_battery = 0.5
            
        elif task_id == TaskDifficulty.MEDIUM:
            demand[17:21] += 1000.0
            # Simulate intermittent clouds: 30% chance to drop solar output to 40%
            cloud_mask = np.random.choice([0.4, 1.0], size=12, p=[0.3, 0.7])
            solar[6:18] *= cloud_mask
            
            # Introduce unpredictable spot price spikes
            spike_indices = np.random.randint(0, 24, size=3)
            spot_price[spike_indices] = 0.80 
            start_battery = 0.5
            
        elif task_id == TaskDifficulty.HARD:
            # The Storm Surge: Zero solar, massive sustained demand, expensive power
            solar[:] = 0.0
            demand[:] += 2000.0 
            spot_price[:] = 0.50
            start_battery = 0.2
            
        else:
            raise ValueError("Invalid task_id. Choose TaskDifficulty.EASY, MEDIUM, or HARD.")
            
        return solar, demand, spot_price, start_battery

    def reset(self, task_id: TaskDifficulty) -> PowerGridObservation:
        self.task_id = task_id
        self.current_step = 0
        self.current_frequency = 50.0
        self.cumulative_reward = 0.0
        
        # Load the arrays from the generator
        self.solar_arr, self.demand_arr, self.price_arr, battery_soc = self._generate_scenario(task_id)
        
        self.battery_current_energy = self.battery_max_capacity_kwh * battery_soc
            
        return self._get_obs()

    def _get_obs(self) -> PowerGridObservation:
        forecast_solar = []
        forecast_wind = []  # Assuming flat 500kW for Easy/Medium, 0 for Hard
        forecast_demand = []
        
        base_wind = 0.0 if self.task_id == TaskDifficulty.HARD else 500.0

        for i in range(5):
            idx = (self.current_step + i) % self.max_steps
            forecast_solar.append(float(self.solar_arr[idx]))
            forecast_wind.append(base_wind)
            forecast_demand.append(float(self.demand_arr[idx]))
            
        current_spot_price = float(self.price_arr[self.current_step % self.max_steps])
            
        obs = PowerGridObservation(
            current_demand_kw=forecast_demand[0],
            grid_frequency_hz=self.current_frequency,
            spot_price_dollars=current_spot_price,
            battery_charge_level=self.battery_current_energy / self.battery_max_capacity_kwh,
            forecast_solar_kw=forecast_solar,
            forecast_wind_kw=forecast_wind,
            forecast_demand_kw=forecast_demand
        )
        return obs

    def step(self, action: PowerGridAction) -> StepResponse:
        obs = self._get_obs()
        
        # 1. Calculate Supply
        solar_supply = obs.forecast_solar_kw[0]
        wind_supply = obs.forecast_wind_kw[0]
        diesel_supply = action.diesel_activation * self.diesel_max_output_kw
        
        requested_battery_kw = action.battery_flow * self.battery_max_flow_kw
        
        actual_battery_kw = 0.0
        if requested_battery_kw > 0.0:
            space_left = self.battery_max_capacity_kwh - self.battery_current_energy
            actual_battery_kw = min(requested_battery_kw, space_left)
            self.battery_current_energy += actual_battery_kw
        elif requested_battery_kw < 0.0:
            energy_available = self.battery_current_energy
            actual_battery_kw = max(requested_battery_kw, -energy_available)
            self.battery_current_energy += actual_battery_kw
            
        battery_supply_kw = -actual_battery_kw
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
        frequency_delta = (net_power / 2000.0) * 0.5 
        self.current_frequency += frequency_delta
        self.current_frequency += (50.0 - self.current_frequency) * 0.1
        
        # 4. Step Rewards
        frequency_error = abs(self.current_frequency - 50.0)
        reward = 1.0 - (frequency_error / 1.0)
        
        step_reward = reward
        self.cumulative_reward += step_reward
        
        # 5. Check Terminal Conditions
        self.current_step += 1
        done = False
        
        if self.current_step >= self.max_steps:
            done = True
        
        if self.current_frequency < 49.0 or self.current_frequency > 51.0:
            done = True
            
        new_obs = self._get_obs()
        
        final_info = {"net_power_kw": net_power}
        
        if done:
            final_info["final_score"] = self._calculate_final_score()
            
        return StepResponse(observation=new_obs, reward=step_reward, done=done, info=final_info)

    def _calculate_final_score(self):
        # Temporary bounds based on Phase 3 needs. Will refine in Phase 4
        r_max = float(self.max_steps) * 1.0 
        r_min = 0.0 
        
        raw_score = (self.cumulative_reward - r_min) / (r_max - r_min)
        final_score = max(0.0, min(1.0, float(raw_score))) # Ensure basic python float
        
        return final_score

    def state(self) -> dict:
        return {
            "current_step": self.current_step,
            "max_steps": self.max_steps,
            "task_id": self.task_id.value if self.task_id else None,
            "agent_alive": not (self.current_frequency < 49.0 or self.current_frequency > 51.0),
            "cumulative_reward": self.cumulative_reward
        }
