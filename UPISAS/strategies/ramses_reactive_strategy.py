from UPISAS.strategy_ramses import Strategy
import requests
import time
import json


#This is a port of the ReactiveAdaptationManager originally published alongside SWIM.
class ReactiveAdaptationManager(Strategy):

    def __init__(self, exemplar, monitor_url, execute_url):
        super().__init__(exemplar, monitor_url, execute_url)
        self.processed_failed_instances = set()  # Track already processed failed instances
        self.oldest_snapshot = {}  # Store the oldest active metrics snapshot for incremental comparison

    def compute_metrics_window(self, latest_snapshot, oldest_snapshot):
        """
        Computes the average response time and availability within a time window
        by comparing the latest snapshot and the oldest snapshot.
        """
        successful_requests_duration = 0
        successful_requests_count = 0
        total_requests_count = 0
        successful_requests_window = 0

        # Compare httpMetrics between latest and oldest snapshots
        latest_http_metrics = latest_snapshot.get("httpMetrics", {})
        oldest_http_metrics = oldest_snapshot.get("httpMetrics", {})

        for endpoint, metrics in latest_http_metrics.items():
            latest_success = metrics.get("outcomeMetrics", {}).get("SUCCESS", {})
            oldest_success = oldest_http_metrics.get(endpoint, {}).get("outcomeMetrics", {}).get("SUCCESS", {})

            # Increment successful duration and count
            duration_diff = latest_success.get("totalDuration", 0) - oldest_success.get("totalDuration", 0)
            count_diff = latest_success.get("count", 0) - oldest_success.get("count", 0)

            #For debugging only
            #print(f"Endpoint: {endpoint}")
            #print(f"  Duration Diff: {duration_diff}")
            #print(f"  Count Diff: {count_diff}")

            successful_requests_duration += duration_diff
            successful_requests_count += count_diff

        # Compare circuitBreakerMetrics between latest and oldest snapshots
        latest_circuit_metrics = latest_snapshot.get("circuitBreakerMetrics", {})
        oldest_circuit_metrics = oldest_snapshot.get("circuitBreakerMetrics", {})

        for circuit, metrics in latest_circuit_metrics.items():
            latest_total = metrics.get("totalCallsCount", 0)
            oldest_total = oldest_circuit_metrics.get(circuit, {}).get("totalCallsCount", 0)
            latest_successful = metrics.get("callCount", {}).get("SUCCESSFUL", 0)
            oldest_successful = oldest_circuit_metrics.get(circuit, {}).get("callCount", {}).get("SUCCESSFUL", 0)

            total_requests_count += latest_total - oldest_total
            successful_requests_window += latest_successful - oldest_successful

            # Print statements for debugging
            #print(f"Circuit: {circuit}")
            #print(f"  Latest Total Calls: {latest_total}, Oldest Total Calls: {oldest_total}")
            #print(f"  Latest Successful Calls: {latest_successful}, Oldest Successful Calls: {oldest_successful}")

        # Calculate average response time and availability
        avg_response_time = successful_requests_duration / successful_requests_count if successful_requests_count > 0 else 0
        availability = (successful_requests_window / total_requests_count) * 100 if total_requests_count > 0 else None

        # Print statements for debugging
        #print(f"Final successful_requests_duration: {successful_requests_duration}")
        #print(f"Final successful_requests_count: {successful_requests_count}")
        #print(f"Final total_requests_count: {total_requests_count}")
        #print(f"Final successful_requests_window: {successful_requests_window}")
        #print(f"Computed avg_response_time: {avg_response_time}")
        #print(f"Computed availability: {availability}")

        return avg_response_time, availability


    

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

        # Define thresholds
        availability_threshold = 95.0  # Minimum acceptable availability
        response_time_threshold = 1000  # Maximum acceptable average response time in ms

        for service_id, service_data in monitored_data.items():
            for snapshot in service_data.get("snapshot", []):
                instance_id = snapshot.get("instanceId")

                # Skip instances that have already been acted upon
                if instance_id in self.processed_failed_instances:
                    continue

                # Check for failed, unreachable, or inactive instances
                if not snapshot.get("active", True) or snapshot.get("failed") or snapshot.get("unreachable"):
                    failed_instances[service_id] = failed_instances.get(service_id, [])
                    failed_instances[service_id].append(instance_id)
                    continue  # Move to next snapshot

                # Check if a new instance has replaced a failed one
                if snapshot.get("active", True) and snapshot.get("status") == "ACTIVE":
                    print(f"New active instance detected: {instance_id}")
                    self.processed_failed_instances.discard(instance_id)
                # Check if a new instance has replaced a failed one
                #if snapshot["active"] and snapshot["status"] == "ACTIVE":
                    #service_name = snapshot.get("serviceId", "")
                    #self.processed_failed_instances = {
                        #instance for instance in self.processed_failed_instances
                        #if service_name not in instance
                    #}

            # Compare current snapshot with oldest snapshot for incremental metrics
            oldest_snapshot = self.oldest_snapshot.get(instance_id, {})
            avg_response_time, availability = self.compute_metrics_window(snapshot, oldest_snapshot)

            # Print intermediate results (for debugging only)
            print(f"  Avg Response Time (Instance): {avg_response_time}")
            print(f"  Availability (Instance): {availability}")

            # Aggregate response time
            if avg_response_time > 0:
                total_avg_response_time += avg_response_time
                active_service_count_response_time += 1

            # Aggregate availability if it exists
            if availability is not None:
                total_availability += availability
                active_service_count_availability += 1

                # Update oldest_snapshot only if new availability data is non-zero
                if availability > 0:
                    self.oldest_snapshot[instance_id] = snapshot
                    #print(f"  Updated oldest snapshot for instance {instance_id}")

        # Calculate final average metrics
        avg_response_time = total_avg_response_time / active_service_count_response_time if active_service_count_response_time > 0 else 0
        availability = total_availability / active_service_count_availability if active_service_count_availability > 0 else None

        # For debugging only
        print("\nFinal Aggregated Metrics:")
        print(f"  Total Avg Response Time: {avg_response_time}")
        print(f"  Total Availability: {availability}")


        # Update analysis results in Knowledge
        self.knowledge.analysis_data = {
            "failed_instances": failed_instances,
            "avg_response_time": avg_response_time,
            "availability": availability
        }

        # Print metrics
        print(f"Average Response Time: {avg_response_time:.2f} ms")
        if availability is not None:
            print(f"Availability: {availability:.2f}%")
        else:
            print("Availability: N/A (No circuitBreakerMetrics)")

        # Threshold checks
        if avg_response_time > response_time_threshold:
            print(f"Warning: Average Response Time exceeds threshold ({response_time_threshold} ms).")
        if availability is not None and availability < availability_threshold:
            print(f"Warning: Availability below threshold ({availability_threshold}%).")

        # Print failed instances
        if failed_instances:
            print(f"New failed instances detected: {json.dumps(failed_instances, indent=2)}")


    def plan(self):
        """
        Plans actions based on the analysis data in Knowledge and updates the plan in Knowledge.
        Dynamically determines which service requires a new instance.
        """
        analysis_data = self.knowledge.analysis_data
        failed_instances = analysis_data.get("failed_instances", {})
        actions = []

        if failed_instances:
            print(f"Failed instances detected: {json.dumps(failed_instances, indent=2)}")
            for service_id, instances in failed_instances.items():
                # Get the service implementation name dynamically
                service_implementation_name = self.knowledge.monitored_data.get(service_id, {}).get("currentImplementationId", None)
                if service_implementation_name:
                    for instance in instances:
                        actions.append({
                            "operation": "addInstances",
                            "serviceImplementationName": service_implementation_name,
                            "numberOfInstances": 1
                        })
                        # Add to processed failed instances to avoid duplicate actions
                        self.processed_failed_instances.add(instance)
                else:
                    print(f"Warning: Could not determine serviceImplementationName for service {service_id}")

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
            #print(f"Planned actions: {self.knowledge.plan_data}")
            
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