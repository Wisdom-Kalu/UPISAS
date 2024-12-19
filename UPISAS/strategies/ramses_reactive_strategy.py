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
        print(f"ReactiveAdaptationManager Initialized: {self.knowledge}")


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
        predicted_failures = {}
        #recyclable_instances = {}

        # Define thresholds
        availability_threshold = 95.0  # Minimum acceptable availability
        response_time_threshold = 1000  # Maximum acceptable average response time in ms

        # Thresholds for trend analysis
        trend_thresholds = {
            "cpuUsage": 0.85,  # Sustained high CPU usage
            "responseTime": 1000,  # High response time
            "requestLatency": 200,  # High latency
            "bootingDuration": 5  # Booting persists across 5 iterations
        }

        for service_id, service_data in monitored_data.items():
            for snapshot in service_data.get("snapshot", []):
                instance_id = snapshot.get("instanceId", None)
                if not instance_id:  # Changed: Check if instance_id is missing
                    print(f"Skipping snapshot for service {service_id}: Missing instanceId.") 
                    continue
                history = monitored_data.get(instance_id, {}).get("history", {})

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

                # Prolonged booting detection
                booting_trend = history.get("bootingStatus", [])[-5:]
                if len(booting_trend) == 5 and all(booting_trend):  # This one checks if boooting persists across 5 iterations
                    print(f"Instance {instance_id} stuck in booting state.")
                    failed_instances[service_id] = failed_instances.get(service_id, [])
                    failed_instances[service_id].append(instance_id)
                    continue

                # Detect recovered instances for recycling
                #if snapshot.get("active", True) and instance_id in self.processed_failed_instances:
                    #print(f"Instance {instance_id} has recovered and is now eligible for recycling.")
                    #recyclable_instances[service_id] = recyclable_instances.get(service_id, [])
                    #recyclable_instances[service_id].append(instance_id)

                # Predictive failure detection for the critical services in our restaurant system
                if service_id in ["ordering-service", "payment-service"]:
                    for snapshot in service_data.get("snapshot", []):
                        instance_id = snapshot.get("instanceId")
                        if not instance_id:
                            print(f"Skipping snapshot: Missing instanceId for service {service_id}.")
                            continue  # Skip this snapshot if instance_id is missing
                        print(f"Instance ID for {service_id}: {instance_id}")
                    # Calculate trends
                    cpu_trend = history["cpuUsage"][-5:] if len(history["cpuUsage"]) >= 5 else []
                    response_trend = history["responseTime"][-5:] if len(history["responseTime"]) >= 5 else []
                    latency_trend = history["requestLatency"][-5:] if len(history["requestLatency"]) >= 5 else []

                    # Detect trends
                    if (
                        all(cpu > trend_thresholds["cpuUsage"] for cpu in cpu_trend) or
                        all(rt > trend_thresholds["responseTime"] for rt in response_trend) or
                        all(latency > trend_thresholds["requestLatency"] for latency in latency_trend)
                    ):
                        predicted_failures[service_id] = predicted_failures.get(service_id, [])
                        predicted_failures[service_id].append(instance_id)

            # Compare current snapshot with oldest snapshot for incremental metrics
            oldest_snapshot = self.oldest_snapshot.get(instance_id, {})
            avg_response_time, availability = self.compute_metrics_window(snapshot, oldest_snapshot)

            # Print intermediate results (for debugging only)
            #print(f"  Avg Response Time (Instance): {avg_response_time}")
            #print(f"  Availability (Instance): {availability}")

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


        # Update analysis results in Knowledge
        self.knowledge.analysis_data = {
            "failed_instances": failed_instances,
            "avg_response_time": avg_response_time,
            "availability": availability,
            "predicted_failures": predicted_failures
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
        if predicted_failures:
            print(f"Predicted failures detected: {json.dumps(predicted_failures, indent=2)}")


    def plan(self):
        
        
        analysis_data = self.knowledge.analysis_data
        print(f"Analysis data: {analysis_data}")
        failed_instances = analysis_data.get("failed_instances", {})
        predicted_failures = analysis_data.get("predicted_failures", {})
        actions = []
        load_balancer_adjustments = []

        # Maintain standby instances for critical services
        critical_services = ["ordering-service", "payment-service"]
        standby_pool = self.knowledge.standby_pool
        print(f"Standby Pool Before Planning: {json.dumps(self.knowledge.standby_pool, indent=2)}")

        for service_id in critical_services:
            if service_id not in standby_pool or not standby_pool[service_id]:
                print(f"No standby instance for {service_id}. Adding one.")
                actions.append({
                    "operation": "addInstances",
                    "serviceImplementationName": service_id,
                    "numberOfInstances": 1
                })
                standby_pool[service_id] = f"{service_id}-standby"

        # Handle failed instances
        if failed_instances:
            for service_id, instances in failed_instances.items():
                service_implementation_name = self.knowledge.monitored_data.get(service_id, {}).get("currentImplementationId", None)
                sibling_instances = self.knowledge.monitored_data.get(service_id, {}).get("instances", [])

                if service_implementation_name:
                    for instance_id in instances:
                        print(f"Removing failed instance {instance_id} for {service_id}.")
                        actions.append({
                            "operation": "removeInstance",
                            "serviceImplementationName": service_id,
                            "address": instance_id.split("@")[1].split(":")[0],
                            "port": int(instance_id.split(":")[1])
                        })

                    if len(sibling_instances) == len(instances):
                        print(f"All instances of {service_id} failed. Adding a new instance.")
                        actions.append({
                            "operation": "addInstances",
                            "serviceImplementationName": service_implementation_name,
                            "numberOfInstances": 1
                        })
                    else:
                        print(f"Some instances of {service_id} are still alive. Reconfiguring load balancer.")
                        alive_instances = [inst for inst in sibling_instances if inst not in instances]
                        load_balancer_adjustments.append({
                            "operation": "changeLBWeights",
                            "serviceID": service_id,
                            "newWeights": {instance: 1.0 / len(alive_instances) if alive_instances else 0 for instance in alive_instances},
                            "instancesToRemoveWeightOf": instances
                        })

        # Handle predicted failures
        if predicted_failures:
            for service_id, instances in predicted_failures.items():
                service_implementation_name = self.knowledge.monitored_data.get(service_id, {}).get("currentImplementationId", None)
                standby_instance = standby_pool.get(service_id)

                if service_implementation_name and standby_instance:
                    print(f"Activating standby instance {standby_instance} for predicted failure in {service_id}.")
                    load_balancer_adjustments.append({
                        "operation": "changeLBWeights",
                        "serviceID": service_id,
                        "newWeights": {standby_instance: 1.0},
                        "instancesToRemoveWeightOf": instances
                    })

                    for instance_id in instances:
                        print(f"Removing predicted failed instance {instance_id} for {service_id}.")
                        actions.append({
                            "operation": "removeInstance",
                            "serviceImplementationName": service_id,
                            "address": instance_id.split("@")[1].split(":")[0],
                            "port": int(instance_id.split(":")[1])
                        })

                    # Add a new standby instance
                    new_standby = f"{service_id}-standby-new"
                    print(f"Adding new standby instance {new_standby} for {service_id}.")
                    actions.append({
                        "operation": "addInstances",
                        "serviceImplementationName": service_id,
                        "numberOfInstances": 1
                    })
                    standby_pool[service_id] = new_standby
                    load_balancer_adjustments.append({
                        "operation": "changeLBWeights",
                        "serviceID": service_id,
                        "newWeights": {new_standby: 0.0}
                    })

        # Update planned actions and load balancer adjustments in Knowledge
        self.knowledge.plan_data = actions
        self.knowledge.adaptation_options = load_balancer_adjustments


        """
        if predicted_failures:

            # Handle proactive predictions for critical services
            for service_id, instances in predicted_failures.items():
                service_implementation_name = self.knowledge.monitored_data.get(service_id, {}).get("currentImplementationId", None)
                standby_instance = standby_pool.get(service_id)

                
                if service_implementation_name and standby_instance:
                    print(f"Proactively adding new instances for {service_id} due to predicted failures.")
                    actions.append({
                        "operation": "addInstances",
                        "serviceImplementationName": service_implementation_name,
                        "numberOfInstances": len(instances)  # Add one instance per predicted failure
                    })

                    # Redirect requests from predicted instances to the new ones
                    sibling_instances = self.knowledge.monitored_data.get(service_id, {}).get("instances", [])
                    alive_instances = [inst for inst in sibling_instances if inst not in instances]
                    new_instances = [f"{service_id}-new-{i}" for i in range(len(instances))]
                    load_balancer_adjustments.append({
                        "operation": "changeLBWeights",
                        "serviceID": service_id,
                        "newWeights": {instance: 1.0 / len(alive_instances + new_instances) for instance in (alive_instances + new_instances)},
                        "instancesToRemoveWeightOf": instances
                    })  
        """

        # Update planned actions and load balancer adjustments in Knowledge
        self.knowledge.plan_data = actions
        self.knowledge.adaptation_options = load_balancer_adjustments

    
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