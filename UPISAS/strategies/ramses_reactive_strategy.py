from UPISAS.strategy_ramses import Strategy
import requests
import time
import json


#This is a port of the ReactiveAdaptationManager originally published alongside SWIM.
class ReactiveAdaptationManager(Strategy):
   
    def analyze(self, service_data):
        """
        Analyzes the data to check for failures.
        """
        failed_instances = []
        for snapshot in service_data.get("snapshot", []):
            if snapshot["failed"] or snapshot["unreachable"]:
                failed_instances.append(snapshot["instanceId"])
        return failed_instances
    

    
    def plan(self, failed_instances):
        """
        Plans actions to handle failed instances.
        """
        actions = []
        if failed_instances:
            actions.append({
                "operation": "addInstances",
                "serviceImplementationName": "ordering-service",
                "numberOfInstances": 1  # Add one instance for simplicity
            })
        return actions
    
    def run(self):
        """
        Executes the MAPE-K loop.
        """
        while True:
            print("Running MAPE-K loop...")
            
            # Monitor phase
            data = self.monitor(verbose=True)
            if not data:
                print("No data retrieved, skipping iteration.")
                time.sleep(5)
                continue
            
            # Focus on ORDERING-SERVICE
            ordering_service_data = data.get("ORDERING-SERVICE", {})
            
            # Analyze phase
            failed_instances = self.analyze(ordering_service_data)
            if not failed_instances:
                print("No failed instances detected.")
                time.sleep(5)
                continue
            
            print(f"Failed instances detected: {failed_instances}")
            
            # Plan phase
            actions = self.plan(failed_instances)
            print(f"Planned actions: {actions}")
            
            # Execute phase
            self.execute(actions)
            
            # Sleep before next loop iteration
            time.sleep(10)