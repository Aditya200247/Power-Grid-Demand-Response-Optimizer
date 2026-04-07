import sys
import os
import unittest
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import TaskDifficulty, LoadZone, PowerGridAction
from phase3.environment import PowerGridEnv

class TestPhase3Env(unittest.TestCase):
    def setUp(self):
        self.env = PowerGridEnv()
        
    def test_scenario_generation(self):
        obs = self.env.reset(TaskDifficulty.HARD)
        # Solar array should be all 0s
        self.assertTrue(np.all(self.env.solar_arr == 0.0))
        # Initial battery should be 20%
        self.assertAlmostEqual(obs.battery_charge_level, 0.2)
        
    def test_score_normalization_on_collapse(self):
        self.env.reset(TaskDifficulty.HARD)
        action = PowerGridAction(
            battery_flow=0.0,
            diesel_activation=0.0,
            grid_trade=0.0,
            shed_load_zone=LoadZone.NONE
        )
        
        # Run until episode ends
        done = False
        final_info = {}
        for _ in range(self.env.max_steps):
            response = self.env.step(action)
            if response.done:
                done = True
                final_info = response.info
                break
                
        self.assertTrue(done)
        self.assertIn("final_score", final_info)
        # Assuming it collapses fast, score should be very low
        self.assertLess(final_info["final_score"], 0.2)
        self.assertGreaterEqual(final_info["final_score"], 0.0)

if __name__ == '__main__':
    unittest.main()
