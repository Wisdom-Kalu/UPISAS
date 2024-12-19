import signal
import sys
import time
from threading import Thread
from UPISAS.exemplar import Exemplar
from UPISAS.exemplars.ramses import RAMSES
from UPISAS.strategies.ramses_reactive_strategy import ReactiveAdaptationManager
# from failure_injection import FailureInjector

if __name__ == '__main__':
    exemplar = RAMSES(auto_start=True)
    monitor_url = "http://127.0.0.1:50000/monitor"
    execute_url = "http://127.0.0.1:50000/execute"


    #failure_injector = FailureInjector()
    #failure_injector_thread = Thread(target=failure_injector.inject_failures)
    #failure_injector_thread.start()

    time.sleep(20)  # Allow some time for the container to start
    exemplar.start_run()
    time.sleep(10)  # Allow some time for the API endpoints to initialize

    try:
        strategy = ReactiveAdaptationManager(exemplar, monitor_url, execute_url)

        while True:
            strategy.run()
            
    except (Exception, KeyboardInterrupt) as e:
        print(str(e))
        input("Something went wrong. Press Enter to exit.")
        exemplar.stop_container()
        sys.exit(0)



'''
import signal
import sys
import time
from UPISAS.exemplar import Exemplar
from UPISAS.exemplars.ramses import RAMSES
from UPISAS.strategies.ramses_reactive_strategy import ReactiveAdaptationManager




if __name__ == '__main__':
    exemplar = RAMSES(auto_start=True)
    # URLs for the monitor and execute endpoints
    monitor_url = "http://127.0.0.1:50000/monitor"
    execute_url = "http://127.0.0.1:50000/execute"

    time.sleep(20)  # Allow some time for the container to start
    exemplar.start_run()
    time.sleep(10)  # Allow some time for the API endpoints to initialize

    try:
        strategy = ReactiveAdaptationManager(exemplar, monitor_url, execute_url)

        #strategy.get_monitor_schema()
        #strategy.get_adaptation_options_schema()
        #strategy.get_execute_schema()

        while True:
            #input("Try to adapt? (yes/no): ")
            strategy.run()
            #if strategy.analyze():
                #if strategy.plan():
                    #strategy.execute()
            
    except (Exception, KeyboardInterrupt) as e:
        print(str(e))
        input("something went wrong")
        exemplar.stop_container()
        sys.exit(0)


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