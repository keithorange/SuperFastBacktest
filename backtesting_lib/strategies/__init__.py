# strategies/__init__.py
import os
import importlib

# Get the directory of the current file
strategies_dir = os.path.dirname(__file__)

# List all Python files in the directory
strategy_files = [f for f in os.listdir(strategies_dir) if f.endswith('.py') and f != '__init__.py']

# Dynamically import all strategy modules and their param_grid
strategy_modules = {}
for file in strategy_files:
    module_name = file[:-3]  # Remove the '.py' extension
    module = importlib.import_module(f'.{module_name}', package='strategies')
    strategy_modules[module_name] = module

# Get all param_grid objects from the strategy modules
param_grids = {}
for name, module in strategy_modules.items():
    if hasattr(module, 'param_grid'):
        param_grids[name] = module.param_grid

__all__ = list(strategy_modules.keys())
