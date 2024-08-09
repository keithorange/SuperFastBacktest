import json
import os
import numpy as np
import pandas as pd

class ResultPrinter:
    def __init__(self, results):
        self.results = results

    def print_strategy_summary(self, strategy, performance):
        print(f"\n{strategy} Strategy Summary:")
        for interval, interval_performance in performance.items():
            if interval != 'overall_mean':
                print(f"  Interval: {interval}")
                for stat_type in ['Mean', 'Min', 'Max']:
                    print(f"    {stat_type}:")
                    for key, value in interval_performance[stat_type].items():
                        print(f"      {key.replace('_', ' ').title()}: {value:.2f}")
        print(f"  Overall Mean: {performance['overall_mean']:.2f}")

    def print_detailed_summary(self):
        print("\nDetailed Strategy Performance Summary:")
        for strategy, strategy_results in self.results.items():
            self.print_strategy_summary(strategy, strategy_results)

    def print_summary(self, sorted_strategies):
        print("\nStrategy Performance Summary:")
        for strategy, performance in sorted_strategies:
            print(f"\n{strategy}:")
            print(f"  Overall Mean: {performance['overall_mean']:.2f}")
            for interval, interval_performance in performance.items():
                if interval != 'overall_mean':
                    print(f"  {interval}:")
                    print(f"    Mean Total Return: {interval_performance['Mean']['total_return']:.2f}%")

    def print_concise_summary(self, aggregated_performance):
        print("\nConcise Strategy Performance Summary:")
        
        headers = ['Strategy', 'Overall Mean']
        intervals = [interval for interval in next(iter(aggregated_performance.values())).keys() if interval != 'overall_mean']
        headers.extend([f'{interval} Return (%)' for interval in intervals])
        print(f"{headers[0]:<20} {headers[1]:<20}", end=' ')
        for header in headers[2:]:
            print(f"{header:<20}", end=' ')
        print()

        sorted_strategies = sorted(
            aggregated_performance.items(),
            key=lambda x: x[1]['overall_mean'],
            reverse=True
        )

        for strategy, metrics in sorted_strategies:
            overall_mean = metrics['overall_mean']
            print(f"{strategy:<20} {overall_mean:<20.2f}", end=' ')
            for interval in intervals:
                returns = metrics[interval]['Mean']['total_return'] if interval in metrics else 'N/A'
                print(f"{returns:<20.2f}", end=' ')
            print()

    def save_to_file(self, strategy_name, output_dir='backtesting_results'):
        os.makedirs(output_dir, exist_ok=True)
        filename = f"{strategy_name}_results.json"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(self.results[strategy_name], f, indent=2)
        
        print(f"Results for {strategy_name} saved to {filepath}")
