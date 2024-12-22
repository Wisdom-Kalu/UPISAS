#from UPISAS.ramses_baseline_strategy import Strategy
from UPISAS.strategy_ramses import Strategy
import requests
import time
import json


class ReactiveAdaptationManager(Strategy):
    def __init__(self, exemplar, monitor_url, execute_url, lb_url):
        super().__init__(exemplar, monitor_url, execute_url, lb_url)
        self.processed_failed_instances = set()  # Track already processed failed instances
        self.oldest_snapshot = {}  # Store the oldest active metrics snapshot for incremental comparison

    def analyze(self):
        """
        Analyzes the monitored data from Knowledge to calculate metrics and identify failures.
        Updates analysis results in Knowledge and avoids re-processing failed instances.
        """
        monitored_data = self.knowledge.monitored_data
        failed_instances = {}
        total_avg_response_time = 0
        total_availability = 0
        active_service_count_response_time = 0
        active_service_count_availability = 0

        for service_id, service_data in monitored_data.items():
            snapshots = service_data.get("snapshot", [])

            if not snapshots:
                print(f"{service_id} has no snapshots available.")
                continue

            for snapshot in snapshots:
                instance_id = snapshot.get("instanceId")

                # Check for failed, unreachable, or inactive instances
                if not snapshot.get("active", True) or snapshot.get("failed") or snapshot.get("unreachable"):
                    print(f"Instance {instance_id} of service {service_id} is failed or unreachable.")
                    failed_instances[service_id] = failed_instances.get(service_id, [])
                    failed_instances[service_id].append(instance_id)
                    continue

                # Compare current snapshot with the oldest snapshot for incremental metrics
                oldest_snapshot = self.oldest_snapshot.get(instance_id, {})
                avg_response_time, availability = self.compute_metrics_window(snapshot, oldest_snapshot)

                # Aggregate metrics
                if avg_response_time > 0:
                    total_avg_response_time += avg_response_time
                    active_service_count_response_time += 1

                if availability > 0:
                    total_availability += availability
                    active_service_count_availability += 1
                    # Update oldest snapshot only if availability > 0
                    self.oldest_snapshot[instance_id] = snapshot

        # Calculate final average metrics
        avg_response_time = total_avg_response_time / active_service_count_response_time if active_service_count_response_time > 0 else 0
        availability = total_availability / active_service_count_availability if active_service_count_availability > 0 else 0

        # Update analysis results in Knowledge
        self.knowledge.analysis_data = {
            "failed_instances": failed_instances,
            "avg_response_time": avg_response_time,
            "availability": availability
        }

        print("Analysis complete.")
        print(f"Average Response Time: {avg_response_time}")
        print(f"Availability: {availability}")


    def plan(self):
        """
        Plans actions to add instances for failed services and reconfigure load balancer weights.
        """
        analysis_data = self.knowledge.analysis_data
        failed_instances = analysis_data.get("failed_instances", {})
        actions = []
        load_balancer_adjustments = []

        if failed_instances:
            for service_id, instances in failed_instances.items():
                service_implementation_name = self.knowledge.monitored_data.get(service_id, {}).get("currentImplementationId", None)

                if service_implementation_name:
                    print(f"Adding a new instance for service {service_id}.")
                    actions.append({
                        "operation": "addInstances",
                        "serviceImplementationName": service_implementation_name,
                        "numberOfInstances": 1
                    })

                    # Assign 100% weight to the new instance
                    load_balancer_adjustments.append({
                        "operation": "changeLBWeights",
                        "serviceID": service_id,
                        "newWeights": 1.0,  # 100% weight to the new instance
                        "instancesToRemoveWeightOf": instances
                    })

        # Update planned actions and load balancer adjustments in Knowledge
        self.knowledge.plan_data = actions
        self.knowledge.adaptation_options = load_balancer_adjustments

        print("Planning complete.")
        print(f"Planned Actions: {json.dumps(actions, indent=2)}")
        print(f"Load Balancer Adjustments: {json.dumps(load_balancer_adjustments, indent=2)}")


    def run(self):
        """
        Executes the MAPE-K loop.
        """
        #input("Try to adapt? (yes/no): ")

        while True:

            print("Running MAPE-K loop...")
            input("try to adapt?")
            
            # Monitor phase
            self.monitor(verbose=True)
            self.analyze()
            self.plan()
            self.execute()
            
            # Analyze phase
            #if self.analyze():
            
                # Plan phase
                #if self.plan():
            
                    # Execute phase
                    #self.execute()
            
            # Sleep before next loop iteration
            time.sleep(10)