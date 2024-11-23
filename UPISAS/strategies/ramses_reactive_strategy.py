from UPISAS.strategy_ramses import Strategy
import requests
import time
import json


#This is a port of the ReactiveAdaptationManager originally published alongside SWIM.
class ReactiveAdaptationManager(Strategy):

    def analyze(self):
        """
        Analyzes the monitored data from Knowledge to calculate average response time and availability.
        Updates analysis results in Knowledge.
        """
        monitored_data = self.knowledge.monitored_data
        failed_instances = []
        response_time_sum = 0
        response_time_count = 0
        total_requests = 0
        successful_requests = 0

        for service_id, service_data in monitored_data.items():
            for snapshot in service_data.get("snapshot", []):
                instance_id = snapshot.get("instanceId")

                # Identify failed or unreachable instances
                if snapshot["failed"] or snapshot["unreachable"]:
                    failed_instances.append(instance_id)

                # Calculate average response time from httpMetrics
                http_metrics = snapshot.get("httpMetrics", {})
                for endpoint, metrics in http_metrics.items():
                    success_metrics = metrics.get("outcomeMetrics", {}).get("SUCCESS", {})
                    response_time_sum += success_metrics.get("totalDuration", 0)
                    response_time_count += success_metrics.get("count", 0)

                # Calculate availability from circuitBreakerMetrics
                circuit_metrics = snapshot.get("circuitBreakerMetrics", {})
                for _, metrics in circuit_metrics.items():
                    total_requests += metrics.get("totalCallsCount", 0)
                    successful_requests += metrics.get("bufferedCallsCount", {}).get("SUCCESSFUL", 0)

        # Calculate final metrics
        avg_response_time = response_time_sum / response_time_count if response_time_count > 0 else 0
        availability = (successful_requests / total_requests) * 100 if total_requests > 0 else 0

        # Update analysis results in Knowledge
        self.knowledge.analysis_data = {
            "failed_instances": failed_instances,
            "avg_response_time": 1630.06,
            "availability": 100.0 
        }

        # Print metrics
        print(f"Average Response Time: {avg_response_time:.2f} ms")
        print(f"Availability: {availability:.2f}%")

        # Threshold checks
        response_time_threshold = 1000  # Example: 1000 ms
        availability_threshold = 95.0  # Example: 95%

        if avg_response_time > response_time_threshold:
            print(f"Warning: Average Response Time exceeds threshold ({response_time_threshold} ms).")
        if availability < availability_threshold:
            print(f"Warning: Availability below threshold ({availability_threshold}%).")


    def plan(self):
        """
        Plans actions based on the analysis data in Knowledge and updates the plan in Knowledge.
        """
        analysis_data = self.knowledge.analysis_data
        failed_instances = analysis_data.get("failed_instances", [])
        avg_response_time = analysis_data.get("avg_response_time", 0)
        availability = analysis_data.get("availability", 0)
        actions = []

        # Plan based on failed instances
        if failed_instances:
            print(f"Failed instances detected: {failed_instances}")
            actions.append({
                "operation": "addInstances",
                "serviceImplementationName": "ordering-service",
                "numberOfInstances": len(failed_instances)
            })

        # Plan based on thresholds
        #response_time_threshold = 1000  # Example threshold
        #availability_threshold = 95.0  # Example threshold

        #if avg_response_time > response_time_threshold:
            #print("Planning actions to improve response time...")
            # Add response-time-specific actions here

        #if availability < availability_threshold:
            #print("Planning actions to improve availability...")
            # Add availability-specific actions here

        # Update planned actions in Knowledge
        self.knowledge.plan_data = actions
      
        
    
    def run(self):
        """
        Executes the MAPE-K loop.
        """
        #input("Try to adapt? (yes/no): ")

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
            self.execute()
            
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