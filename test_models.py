from server.models import PowerGridAction, LoadZone, TaskDifficulty

try:
  
    bad_action = PowerGridAction(
        battery_flow=5.0, 
        diesel_activation=0.5,
        grid_trade=0.0,
        shed_load_zone=0
    )
except ValueError as e:
    print(f"Caught bad agent action successfully:\n{e}")
