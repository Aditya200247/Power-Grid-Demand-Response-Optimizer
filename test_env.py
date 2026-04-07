import sys
import os
import unittest

# Ensure we can import from the parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import TaskDifficulty, LoadZone, PowerGridAction
from phase2.environment import PowerGridEnv

class TestPowerGridEnv(unittest.TestCase):
    def setUp(self):
        self.env = PowerGridEnv()
        
    def test_reset_easy(self):
        obs = self.env.reset(TaskDifficulty.EASY)
        self.assertAlmostEqual(self.env.current_frequency, 50.0)
        self.assertEqual(len(obs.forecast_demand_kw), 5)
        # Easy starts with 50% battery
        self.assertAlmostEqual(obs.battery_charge_level, 0.5)

    def test_step_battery_discharge(self):
        obs = self.env.reset(TaskDifficulty.EASY)
        action = PowerGridAction(
            battery_flow=-1.0,  # Full discharge
            diesel_activation=0.0,
            grid_trade=0.0,
            shed_load_zone=LoadZone.NONE
        )
        response = self.env.step(action)
        # Battery should have dropped
        self.assertLess(self.env.battery_current_energy, self.env.battery_max_capacity_kwh * 0.5)
        self.assertTrue(0.0 <= response.reward <= 1.0)
        self.assertFalse(response.done)

    def test_grid_collapse_if_no_action(self):
        obs = self.env.reset(TaskDifficulty.HARD)
        # Storm, no solar, high demand. If we do nothing, grid should collapse soon.
        action = PowerGridAction(
            battery_flow=0.0,
            diesel_activation=0.0,
            grid_trade=0.0,
            shed_load_zone=LoadZone.NONE
        )
        # Step a few times to let the frequency drop below 49.0
        done = False
        for _ in range(5):
            response = self.env.step(action)
            if response.done:
                done = True
                break
        
        self.assertTrue(done)
        self.assertEqual(response.reward, 0.0)

    def test_grid_trade_saving_grid(self):
        self.env.reset(TaskDifficulty.HARD)
        # Use everything to offset the storm
        action = PowerGridAction(
            battery_flow=-1.0, # Discharge max battery (200kW)
            diesel_activation=1.0, # Run diesel max (1000kW)
            grid_trade=1.0, # Buy max from grid (1000kW)
            shed_load_zone=LoadZone.ZONE_A # Shed load 
        )
        response = self.env.step(action)
        self.assertFalse(response.done)
        self.assertGreater(self.env.current_frequency, 49.0)

if __name__ == '__main__':
    unittest.main()
