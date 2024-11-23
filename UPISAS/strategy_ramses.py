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
        self.knowledge = Knowledge(dict(), dict(), dict(), dict())  

    def monitor(self, verbose=False):
        """
        Fetches monitoring data from the API and updates the knowledge base.
        """
        try:
            response = requests.get(self.monitor_url)
            response.raise_for_status()
            data = response.json()
            self.knowledge.monitored_data = data
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

