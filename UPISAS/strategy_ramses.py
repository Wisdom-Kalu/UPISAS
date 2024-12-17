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
        and updates the knowledge base with realistic fallback values.
        Prints the contents of httpMetrics and circuitBreakerMetrics for debugging.
        """
        try:
            response = requests.get(self.monitor_url)
            response.raise_for_status()
            data = response.json()

            # Populate missing httpMetrics and circuitBreakerMetrics with more realistic fallback values
            for service_id, service_data in data.items():
                for snapshot in service_data.get("snapshot", []):
                    instance_id = snapshot.get("instanceId", "unknown")

                    # Print the contents of httpMetrics
                    #print(f"Instance {instance_id} httpMetrics:")
                    #print(json.dumps(snapshot["httpMetrics"], indent=2))
                    
                    # Print the contents of circuitBreakerMetrics
                    #print(f"Instance {instance_id} circuitBreakerMetrics:")
                    #print(json.dumps(snapshot["circuitBreakerMetrics"], indent=2))

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
        Checks first if adaptation is needed and whether the operation is 'addInstances'.
        """
        plan_data = self.knowledge.plan_data
        results = []

        # Check if there are planned actions
        if not plan_data:
            print("No planned actions. Adaptation is not needed.")
            return

        print("Checking planned actions for execution...")

        # Iterate through each action and filter only 'addInstances' operations
        for action in plan_data:
            if action.get("operation") != "addInstances":
                continue

            print(f"Executing action: {action}")

            # Execute the addInstances action
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

