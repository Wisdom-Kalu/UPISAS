from UPISAS.strategy_ramses import Strategy
import requests
import time
import json


#This is a port of the ReactiveAdaptationManager originally published alongside SWIM.
class ReactiveAdaptationManager(Strategy):
   
    def analyze(self):

        """
        Analyzes the monitored data from Knowledge to identify failed instances.
        Updates analysis results in Knowledge.
        """
        monitored_data = self.knowledge.monitored_data
        failed_instances = []

        for service_id, service_data in monitored_data.items():
            for snapshot in service_data.get("snapshot", []):
                instance_id = snapshot.get("instanceId")
                if snapshot["failed"] or snapshot["unreachable"]:
                    failed_instances.append(instance_id)

        # Update analysis results in Knowledge
        self.knowledge.analysis_data = {
            "failed_instances": failed_instances
        }
    

    
    def plan(self):

        """
        Plans actions based on the analysis data in Knowledge and updates the plan in Knowledge.
        """
        analysis_data = self.knowledge.analysis_data
        failed_instances = analysis_data.get("failed_instances", [])
        actions = []

        if failed_instances:
            actions.append({
                "operation": "addInstances",
                "serviceImplementationName": "ordering-service",
                "numberOfInstances": len(failed_instances) 
            })
        
        # Update planned actions in Knowledge
        self.knowledge.plan_data = actions
    
    def run(self):
        """
        Executes the MAPE-K loop.
        """
        input("Try to adapt? (yes/no): ")

        while True:

            print("Running MAPE-K loop...")
            
            # Monitor phase
            self.monitor(verbose=True)
            
            # Analyze phase
            self.analyze()
            
            # Plan phase
            actions = self.plan()
            print(f"Planned actions: {actions}")
            
            # Execute phase
            self.execute(actions)
            
            # Sleep before next loop iteration
            time.sleep(10)

    
    '''
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
'''