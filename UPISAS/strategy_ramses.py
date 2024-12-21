from abc import ABC, abstractmethod
import requests
import pprint
import time
import json


from UPISAS.exceptions import EndpointNotReachable, ServerNotReachable
from UPISAS.knowledge_ramses import Knowledge
from UPISAS import validate_schema, get_response_for_get_request
import logging

pp = pprint.PrettyPrinter(indent=4)


class Strategy(ABC):
    
    def __init__(self, exemplar, monitor_url, execute_url, lb_url):
        self.monitor_url = monitor_url
        self.execute_url = execute_url
        self.exemplar = exemplar
        self.lb_url = lb_url
        self.knowledge = Knowledge(dict(), dict(), dict(), dict())  #Initializing the knowledge class to hold information from monitor(), analyze(), plan() and execute() functions

    def monitor(self, verbose=False):
        """
        Fetches monitoring data from the API, ensures consistency for httpMetrics and CircuitBreakerMetrics,
        and tracks historical metrics for trend analysis.
        """
        try:
            response = requests.get(self.monitor_url)
            response.raise_for_status()
            data = response.json()

            # Populate missing metrics with defaults and track historical data
            for service_id, service_data in data.items():
                for snapshot in service_data.get("snapshot", []):
                    instance_id = snapshot.get("instanceId", "unknown")

                    # Initialize historical data for the instance
                    if instance_id not in self.knowledge.monitored_data:
                        self.knowledge.monitored_data[instance_id] = {
                            "history": {
                                "cpuUsage": [],
                                "responseTime": [],
                                "bootingStatus": [],
                                "requestLatency": []
                            }
                        }

                    # Track CPU usage
                    cpu_usage = snapshot.get("cpuUsage", 0)
                    self.knowledge.monitored_data[instance_id]["history"]["cpuUsage"].append(cpu_usage)
                    if len(self.knowledge.monitored_data[instance_id]["history"]["cpuUsage"]) > 5:
                        self.knowledge.monitored_data[instance_id]["history"]["cpuUsage"].pop(0)

                    # Track average response time
                    avg_response_time = snapshot.get("httpMetrics", {}).get("avgResponseTime", 0)
                    self.knowledge.monitored_data[instance_id]["history"]["responseTime"].append(avg_response_time)
                    if len(self.knowledge.monitored_data[instance_id]["history"]["responseTime"]) > 5:
                        self.knowledge.monitored_data[instance_id]["history"]["responseTime"].pop(0)

                    # Track booting status
                    booting_status = snapshot.get("booting", False)
                    self.knowledge.monitored_data[instance_id]["history"]["bootingStatus"].append(booting_status)
                    if len(self.knowledge.monitored_data[instance_id]["history"]["bootingStatus"]) > 5:
                        self.knowledge.monitored_data[instance_id]["history"]["bootingStatus"].pop(0)

                    # Track request latency
                    request_latency = snapshot.get("httpMetrics", {}).get("avgLatency", 0)
                    self.knowledge.monitored_data[instance_id]["history"]["requestLatency"].append(request_latency)
                    if len(self.knowledge.monitored_data[instance_id]["history"]["requestLatency"]) > 5:
                        self.knowledge.monitored_data[instance_id]["history"]["requestLatency"].pop(0)

            # Store the monitoring data in Knowledge
            self.knowledge.monitored_data.update(data)
            # self.knowledge.monitored_data = data

            if verbose:
                print("Monitoring data updated.")

        except requests.RequestException as e:
            print(f"Monitoring failed: {e}")



    def execute(self):
        """
        Executes planned actions via the execute API. Handles both 'addInstances' and 'changeLBWeights' operations.
        """
        plan_data = self.knowledge.plan_data
        load_balancer_adjustments = self.knowledge.adaptation_options
        results = []

        # Check if there are planned actions
        if not plan_data and not load_balancer_adjustments:
            print("No planned actions. No adaptation required at this time.")
            return

        print("Checking planned actions for execution...")

        # Execute addInstances actions
        for action in plan_data:
            if action.get("operation") == "addInstances":
                print(f"Executing addInstances action: {action}")
                try:
                    response = requests.post(self.execute_url, json=action)
                    response.raise_for_status()
                    result = response.json()
                    results.append(result)
                    print(f"Instance added successfully: {result}")

                    # Update standby pool if a new instance is added
                    #if action.get("operation") == "addInstances":
                    service_id = action.get("serviceImplementationName")
                    new_instance_id = result.get("newInstance", {}).get("instanceId")
                    if service_id and new_instance_id:
                        self.knowledge.standby_pool[service_id] = new_instance_id
                        print(f"Updated standby pool for {service_id} with new instance ID: {new_instance_id}")
                except requests.RequestException as e:
                    error_message = f"Failed to execute addInstances action {action}: {e}"
                    results.append({"action": action, "error": error_message})
                    print(error_message)


        # Execute changeLBWeights actions
        time.sleep(20) #wait for instance to power up fully
        for adjustment in load_balancer_adjustments:
            if adjustment.get("operation") == "changeLBWeights":
                print(f"Executing changeLBWeights action: {adjustment}")
                try:
                    # Construct the request body as per the specified API
                    service_id = adjustment.get("serviceID")
                    updated_instances = self.get_instances_for_service(service_id)

                    print(f"[Execute]\tUpdated instances: {updated_instances}")

                    new_weights = 1 / len(updated_instances)
                    updated_weights = {instance: new_weights for instance in updated_instances}
                    adjustment["newWeights"] = updated_weights
                    
                    headers = {'Content-Type': 'application/json'}
                    lb_request_body = {
                        "serviceID": adjustment.get("serviceID"),
                        "newWeights": new_weights,
                        "instancesToRemoveWeightOf": adjustment.get("instancesToRemoveWeightOf", [])
                    }
                    response = requests.post(self.lb_url, headers=headers, json=lb_request_body)
                    print(f"  Request body: {json.dumps(lb_request_body, indent=2)}")
                    response.raise_for_status()
                    result = response.json()
                    results.append(result)
                    print(f"Load balancer weights updated successfully: {result}")
                except requests.RequestException as e:
                    error_message = f"Failed to execute changeLBWeights action {adjustment}: {e}"
                    results.append({"adjustment": adjustment, "error": error_message})
                    print(error_message)

        # Store execution results in the Knowledge base
        self.knowledge.adaptation_options = results

    
    def manage_standby_pool(self, critical_services=None):
        """
        Dynamically adjusts the size of the standby pool for critical services based on traffic or failure trends.
        Returns actions to add missing standby instances.
        """
        if critical_services is None:
            critical_services = {"ordering-service": 1, "payment-proxy-1-service": 1}

        actions = []

        for service_id, size in critical_services.items():
            current_pool = self.knowledge.standby_pool.get(service_id, [])
            pool_deficit = size - len(current_pool)

            # Add instances to fill the pool
            if pool_deficit > 0:
                print(f"Adding {pool_deficit} standby instances for {service_id}.")
                for _ in range(pool_deficit):
                    new_instance = f"{service_id}-standby-{len(current_pool) + _}"
                    actions.append({
                        "operation": "addInstances",
                        "serviceImplementationName": service_id,
                        "numberOfInstances": 1
                    })
                    self.knowledge.standby_pool[service_id] = self.knowledge.standby_pool.get(service_id, []) + [new_instance]

            # Remove unused instances
            while len(current_pool) > size:
                removed_instance = current_pool.pop()
                print(f"Removing excess standby instance {removed_instance} for {service_id}.")

        return actions



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

        # Calculate average response time and availability
        availability = (successful_requests_window / total_requests_count) * 100 if total_requests_count > 0 else None


        return avg_response_time, availability
    
    
    def _perform_get_request(self, endpoint_suffix: "API Endpoint"):
        url = '/'.join([self.exemplar.base_endpoint, endpoint_suffix])
        response = get_response_for_get_request(url)
        if response.status_code == 404:
            logging.error("Please check that the endpoint you are trying to reach actually exists.")
            raise EndpointNotReachable
        return response.json()
    
    
    def get_instances_for_service(self, service_id):
        fresh_data = self._perform_get_request("monitor")
        self.knowledge.monitored_data.update(fresh_data)
        service_data = self.knowledge.monitored_data.get(service_id)
        if not service_data:
            print(f"[get_instances_for_service]\tService '{service_id}' not found in monitored data.")
            return []
        instances = service_data.get('instances', [])
        if not instances:
            print(f"[get_instances_for_service]\tNo instances found for service '{service_id}'.")
        return instances

    @abstractmethod
    def analyze(self):
        """ ... """
        pass

    @abstractmethod
    def plan(self):
        """ ... """
        pass

    @abstractmethod
    def run(self):
        """ ... """
        pass


    