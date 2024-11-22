import signal
import sys
import time
from UPISAS.exemplar import Exemplar
from UPISAS.exemplars.ramses import RAMSES



if __name__ == '__main__':
    exemplar = RAMSES(auto_start=True)
    time.sleep(30)  # Allow some time for the container to start
    exemplar.start_run()
    time.sleep(3)  # Allow some time for the API endpoints to initialize

'''
class ReactiveAdaptationManager:
    """
    Placeholders for the reactive adaptation manager.
    TODO: Replace with actual implementation.
    """
    def __init__(self, exemplar):
        self.exemplar = exemplar

    def get_monitor_schema(self):
        print("Fetching monitor schema...")

    def get_adaptation_options_schema(self):
        print("Fetching adaptation options schema...")

    def get_execute_schema(self):
        print("Fetching execute schema...")

    def monitor(self, verbose=False):
        if verbose:
            print("Monitoring system...")

    def analyze(self):
        print("Analyzing system...")
        # TODO: Simulate analysis result
        return True

    def plan(self):
        print("Planning adaptations...")
        # TODO: Simulate planning result
        return True

    def execute(self):
        print("Executing adaptation...")



    try:
        strategy = ReactiveAdaptationManager(exemplar)

        strategy.get_monitor_schema()
        strategy.get_adaptation_options_schema()
        strategy.get_execute_schema()

        while True:
            user_input = input("Try to adapt? (yes/no): ").strip().lower()
            
            if user_input == "no":
                print("Exiting adaptation process...")
                break
            elif user_input == "yes":
                strategy.monitor(verbose=True)
                if strategy.analyze():
                    if strategy.plan():
                        strategy.execute()
            else:
                print("Invalid input. Please type 'yes' to adapt or 'no' to exit.")


    except (Exception, KeyboardInterrupt) as e:
        print(f"Error or interruption: {str(e)}")
        exemplar.stop_container()
        sys.exit(0)
'''