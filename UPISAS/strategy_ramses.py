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
        and updates the knowledge base.
        """
        try:
            response = requests.get(self.monitor_url)
            response.raise_for_status()
            data = response.json()

            # Populate missing httpMetrics and CircuitBreakerMetrics with default structure and static data obtained from running the project in the SEAMS_ARTIFACT
            # This is because the httpMetrics was returning an empty json object, making it impossible for us to calculate the response time and availabiliy
            for service_id, service_data in data.items():
                for snapshot in service_data.get("snapshot", []):
                    # Ensure httpMetrics exists
                    if "httpMetrics" not in snapshot or not snapshot["httpMetrics"]: 
                        snapshot["httpMetrics"] = {
                            "default-endpoint": {
                                "id": None,
                                "endpoint": "default",
                                "httpMethod": "GET",
                                "outcomeMetrics": {
                                    "SUCCESS": {
                                        "outcome": "SUCCESS",
                                        "status": 200,
                                        "count": 0,
                                        "totalDuration": 0.0,
                                        "maxDuration": 0.0
                                    }
                                }
                            }
                        }
                        #if verbose:
                            #print(f"Added default httpMetrics for {snapshot.get('instanceId', 'unknown')}")

                    # Ensure circuitBreakerMetrics exists
                    if "circuitBreakerMetrics" not in snapshot or not snapshot["circuitBreakerMetrics"]:
                        snapshot["circuitBreakerMetrics"] = {
                            "default-circuit": {
                                "id": None,
                                "name": "default",
                                "state": "CLOSED",
                                "bufferedCallsCount": {"FAILED": 0, "SUCCESSFUL": 0},
                                "callDuration": {"FAILED": 0.0, "IGNORED": 0.0, "SUCCESSFUL": 0.0},
                                "callMaxDuration": {"FAILED": 0.0, "IGNORED": 0.0, "SUCCESSFUL": 0.0},
                                "callCount": {"FAILED": 0, "IGNORED": 0, "SUCCESSFUL": 0},
                                "slowCallCount": {"FAILED": 0, "SUCCESSFUL": 0},
                                "notPermittedCallsCount": 0,
                                "failureRate": -1,
                                "slowCallRate": -1,
                                "totalCallsCount": 0
                            }
                        }
                        #if verbose:
                            #print(f"Added default circuitBreakerMetrics for {snapshot.get('instanceId', 'unknown')}")

            # Store the monitoring data in Knowledge
            self.knowledge.monitored_data = data

            if verbose:
                print("Monitoring data updated:")
                #print(json.dumps(data, indent=2))

        except requests.RequestException as e:
            print(f"Monitoring failed: {e}")



    def execute(self):
        """
        Executes planned actions via the execute API and updates adaptation options in Knowledge.
        """
        plan_data = self.knowledge.plan_data
        results = []

        for action in plan_data:
            try:
                response = requests.post(self.execute_url, json=action)
                response.raise_for_status()
                result = response.json()
                results.append(result)
                print(f"Action executed successfully: {result}")
            except requests.RequestException as e:
                error_message = f"Failed to execute action {action}: {e}"
                results.append({"action": action, "error": error_message})
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

