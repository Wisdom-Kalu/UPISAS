from abc import ABC, abstractmethod
import requests
import pprint
import time
import json


from UPISAS.exceptions import EndpointNotReachable, ServerNotReachable
from UPISAS.knowledge import Knowledge
from UPISAS import validate_schema, get_response_for_get_request
import logging

pp = pprint.PrettyPrinter(indent=4)


class Strategy(ABC):
    
    def __init__(self, exemplar, monitor_url, execute_url):
        self.monitor_url = monitor_url
        self.execute_url = execute_url
        self.exemplar = exemplar

    def monitor(self, verbose=False):
        """
        Fetches monitoring data from the API.
        """
        try:
            response = requests.get(self.monitor_url)
            response.raise_for_status()
            data = response.json()
            return data
        except requests.RequestException as e:
            print(f"Monitoring failed: {e}")
            return {}


    def execute(self, actions):
        """
        Executes planned actions via the execute API.
        """
        for action in actions:
            try:
                response = requests.post(self.execute_url, json=action)
                response.raise_for_status()
                result = response.json()
                print(f"Action executed successfully: {result}")
            except requests.RequestException as e:
                print(f"Failed to execute action {action}: {e}")

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

