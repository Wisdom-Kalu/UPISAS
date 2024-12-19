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
    
    def __init__(self, exemplar, monitor_url, execute_url):
        self.monitor_url = monitor_url
        self.execute_url = execute_url
        self.exemplar = exemplar
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
        for adjustment in load_balancer_adjustments:
            if adjustment.get("operation") == "changeLBWeights":
                print(f"Executing changeLBWeights action: {adjustment}")
                try:
                    # Construct the request body as per the specified API
                    lb_request_body = {
                        "serviceID": adjustment.get("serviceID"),
                        "newWeights": adjustment.get("newWeights"),
                        "instancesToRemoveWeightOf": adjustment.get("instancesToRemoveWeightOf", [])
                    }
                    response = requests.post(self.execute_url, json=lb_request_body)
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

