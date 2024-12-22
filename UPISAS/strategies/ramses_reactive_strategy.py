from UPISAS.strategy_ramses import Strategy
import requests
import time
import json


#This is a port of the ReactiveAdaptationManager originally published alongside SWIM.
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
        predicted_failures = {}
        self.processed_predicted_instances = set()
        #MAX_FAILURE_TIME = 100

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
            snapshots = service_data.get("snapshot", [])
            #print(f"Service: {service_id}, Snapshots: {snapshots}")

            if not snapshots:
                print(f"{service_id} Service {service_id} has no snapshots available yet. Will retry in the next iteration.")
                continue

            for snapshot in snapshots:
                instance_id = snapshot.get("instanceId", None)

                if not instance_id:
                    #print(f"Skipping snapshot for service {service_id}: Missing instanceId.")
                    continue

                # Skip already processed predicted instances
                if instance_id in self.processed_predicted_instances:
                    continue

                # Mark instance as processed
                self.processed_predicted_instances.add(instance_id)

                history = monitored_data.get(instance_id, {}).get("history", {})

                # Skip instances that have already been acted upon
                if instance_id in self.processed_failed_instances:
                    continue

                # Check for failed, unreachable, or inactive instances
                if not snapshot.get("active", True) or snapshot.get("failed") or snapshot.get("unreachable"):
                    print(f"  Instance {instance_id} is failed or unreachable.")
                    failed_instances[service_id] = failed_instances.get(service_id, [])
                    failed_instances[service_id].append(instance_id)
                    continue

                # Check if a new instance has replaced a failed one
                if snapshot.get("active", True) and snapshot.get("status") == "ACTIVE":
                    #print(f"New active instance detected: {instance_id}")
                    self.processed_failed_instances.discard(instance_id)

                # Prolonged booting detection
                booting_trend = history.get("bootingStatus", [])[-5:]
                if len(booting_trend) == 5 and all(booting_trend):
                    print(f"Instance {instance_id} stuck in booting state.")
                    failed_instances[service_id] = failed_instances.get(service_id, [])
                    failed_instances[service_id].append(instance_id)
                    continue

                # Predictive failure detection for critical services
                if service_id in ["ordering-service", "payment-proxy-1-service"]:
                    cpu_trend = history.get("cpuUsage", [])[-5:]
                    response_trend = history.get("responseTime", [])[-5:]
                    latency_trend = history.get("requestLatency", [])[-5:]

                    if (
                        all(cpu > trend_thresholds["cpuUsage"] for cpu in cpu_trend) or
                        all(rt > trend_thresholds["responseTime"] for rt in response_trend) or
                        all(latency > trend_thresholds["requestLatency"] for latency in latency_trend)
                    ):
                        predicted_failures[service_id] = predicted_failures.get(service_id, [])
                        predicted_failures[service_id].append(instance_id)

                # Compare current snapshot with the oldest snapshot for incremental metrics
                oldest_snapshot = self.oldest_snapshot.get(instance_id, {})
                avg_response_time, availability = self.compute_metrics_window(snapshot, oldest_snapshot)



                # Aggregate metrics
                if avg_response_time > 0:
                    total_avg_response_time += avg_response_time
                    active_service_count_response_time += 1

                if availability is not None:
                    total_availability += availability
                    active_service_count_availability += 1

                    # Update oldest_snapshot if availability is non-zero
                    if availability > 0:
                        self.oldest_snapshot[instance_id] = snapshot
                    else:
                        print(f"Availability is zero for instance {instance_id}, not updating oldest snapshot.")


        # Calculate final average metrics
        avg_response_time = total_avg_response_time / active_service_count_response_time if active_service_count_response_time > 0 else 0
        availability = total_availability / active_service_count_availability if active_service_count_availability > 0 else None

        # Update analysis results in Knowledge
        self.knowledge.analysis_data = {
            "failed_instances": failed_instances,
            "avg_response_time": avg_response_time,
            "availability": availability,
            "predicted_failures": predicted_failures,
        
        }

        # if time.time() - self.failed_timestamps[instance_id] > MAX_FAILURE_TIME:
        #     print(f"Instance {instance_id} exceeded failure timeout. Marking for removal.")
        #     failed_instances[service_id] = failed_instances.get(service_id, [])
        #     failed_instances[service_id].append(instance_id)

        # Debugging results
        print("Analysis complete.")
        #print(f"  Failed Instances: {json.dumps(failed_instances, indent=2)}")
        print(f"  Average Response Time: {avg_response_time}")
        print(f"  Availability: {availability}")


        # Print thresholds and warnings
        if avg_response_time > response_time_threshold:
            print(f"Warning: Average Response Time exceeds threshold ({response_time_threshold} ms).")
        if availability is not None and availability < availability_threshold:
            print(f"Warning: Availability below threshold ({availability_threshold}%).")


    def plan(self):
        
        analysis_data = self.knowledge.analysis_data
        print(f"Analysis data: {analysis_data}")
        failed_instances = analysis_data.get("failed_instances", {})
        predicted_failures = analysis_data.get("predicted_failures", {})
        actions = []
        load_balancer_adjustments = []

        # Dynamically manage standby pool for critical services
        standby_actions = self.manage_standby_pool()
        actions.extend(standby_actions)

        # Maintain standby instances for critical services
        #critical_services = ["ordering-service", "payment-proxy-1-service"]
        #standby_pool = self.knowledge.standby_pool
        #print(f"Standby Pool Before Planning: {json.dumps(self.knowledge.standby_pool, indent=2)}")

        #for service_id in critical_services:
            #if service_id not in standby_pool or not standby_pool[service_id]:
                #print(f"No standby instance for {service_id}. Adding one.")
                #actions.append({
                    #"operation": "addInstances",
                    #"serviceImplementationName": service_id,
                    #"numberOfInstances": 1
                #})
                #standby_pool[service_id] = f"{service_id}-standby"

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
                standby_instance = self.knowledge.standby_pool.get(service_id)

                if service_implementation_name and standby_instance:
                    print(f"Activating standby instance {standby_instance} for predicted failure in {service_id}.")
                    load_balancer_adjustments.append({
                        "operation": "changeLBWeights",
                        "serviceID": service_id,
                        "newWeights": {standby_instance: 1.0},
                        "instancesToRemoveWeightOf": instances
                    })

                    # If recovery attempts fail, remove the failed instance and replace it
                    for instance_id in instances:
                        print(f"Removing predicted failed instance {instance_id} for {service_id}.")
                        actions.append({
                            "operation": "removeInstance",
                            "serviceImplementationName": service_id,
                            "address": instance_id.split("@")[1].split(":")[0],
                            "port": int(instance_id.split(":")[1])
                        })

                    # Add a new standby instance to replace the failed one
                    new_standby = f"{service_id}-standby-new"
                    print(f"Adding new standby instance {new_standby} for {service_id}.")
                    actions.append({
                        "operation": "addInstances",
                        "serviceImplementationName": service_id,
                        "numberOfInstances": 1
                    })
                    self.knowledge.standby_pool[service_id] = new_standby
                    load_balancer_adjustments.append({
                        "operation": "changeLBWeights",
                        "serviceID": service_id,
                        "newWeights": {new_standby: 0.0}
                    })

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