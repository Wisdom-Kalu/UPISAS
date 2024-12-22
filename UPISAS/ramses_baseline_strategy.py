import json
import time
from abc import ABC, abstractmethod

from flask import Response
import requests
import pprint

from UPISAS.exceptions import EndpointNotReachable, ServerNotReachable
#from UPISAS.knowledge import Knowledge
from UPISAS.knowledge_ramses import Knowledge
from UPISAS import validate_schema, get_response_for_get_request
import logging

pp = pprint.PrettyPrinter(indent=2)


class Strategy(ABC):

    def __init__(self, exemplar):
        self.exemplar = exemplar
        self.knowledge = Knowledge(dict(), dict(), dict(), dict(), dict(), dict(), dict())

    def ping(self):
        ping_res = self._perform_get_request(self.exemplar.base_endpoint)
        logging.info(f"ping result: {ping_res}")

    def monitor(self, endpoint_suffix="monitor", with_validation=True, verbose=False):
        fresh_data = self._perform_get_request(endpoint_suffix)
        if(verbose): print("[Monitor]\tgot fresh_data: " + str(fresh_data))
        if with_validation:
            if(not self.knowledge.monitor_schema): self.get_monitor_schema()
            validate_schema(fresh_data, self.knowledge.monitor_schema)
        data = self.knowledge.monitored_data
        for key in fresh_data.keys():
            data[key] = fresh_data[key]
            # print(key)
        if(verbose):
            print("[Knowledge]\tdata monitored so far: ")
            # print(json.dumps(self.knowledge.monitored_data, indent=4, ensure_ascii=False))
            pp.pprint(self.knowledge.monitored_data)
        return True

    def execute(self, adaptation=None, endpoint_suffix="execute", with_validation=True):
        if(not adaptation): adaptation= self.knowledge.plan_data
        print("adaptation plan: " + json.dumps(adaptation, indent=4))
        if with_validation:
            if(not self.knowledge.execute_schema): self.get_execute_schema()
            validate_schema(adaptation, self.knowledge.execute_schema)
        if not adaptation:
            print("[Execute]\tNo adaptation plan to execute.")
            return True
        url = '/'.join([self.exemplar.base_endpoint, endpoint_suffix])
        add_instance_plan = adaptation.get("add_instance_plan")
        if add_instance_plan:
            try:
                print(f"[Execute]\tAdding new instance for {add_instance_plan['serviceImplementationName']}.")
                url = "http://localhost:32840/rest/addInstances"
                headers = {
                    'Content-Type': 'application/json'
                }
                request_body = {
                    "serviceImplementationName": add_instance_plan.get("serviceImplementationName").lower(),
                    "numberOfInstances": add_instance_plan.get("numberOfInstances")
                }
                response = requests.post(url, headers=headers, data=json.dumps(request_body)).json()
                print(
                    f"[Execute]\tSuccessfully added instance for {add_instance_plan['serviceImplementationName']}.")
            except Exception as e:
                print(f"[Execute]\tException during execution: {str(e)}")
                return False
        # wait for the new instance to be up and running
        time.sleep(15)
        change_lb_weights_plan = adaptation.get("change_lb_weights_plan")
        if change_lb_weights_plan:
            try:
                print(f"[Execute]\tAdjusting LB weights for {change_lb_weights_plan['serviceID']}.")
                service_id = change_lb_weights_plan.get("serviceID")
                updated_instances = self.get_instances_for_service(service_id)
                print(f"[Execute]\tUpdated instances: {updated_instances}")

                new_weights = 1 / len(updated_instances)
                updated_weights = {instance: new_weights for instance in updated_instances}
                change_lb_weights_plan["newWeights"] = updated_weights

                url = "http://localhost:32840/rest/changeLBWeights"
                headers = {'Content-Type': 'application/json'}
                request_body = {
                    "weightsId": change_lb_weights_plan.get("serviceID"),
                    "weights": updated_weights,
                    "instancesToRemoveWeightOf": change_lb_weights_plan.get("instancesToRemoveWeightOf", [])
                }
                  # Debugging
                print(f"DEBUG: Request body sent to load balancer: {json.dumps(request_body, indent=2)}")
                response = requests.post(url, headers=headers, data=json.dumps(request_body)).json()
                print(f"[Execute]\tSuccessfully adjusted LB weights for {change_lb_weights_plan['serviceID']}.")
            except Exception as e:
                print(f"[Execute]\tException during execution: {str(e)}")
                return False

        return True

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

    def get_adaptation_options(self, endpoint_suffix: "API Endpoint" = "adaptation_options", with_validation=True):
        self.knowledge.adaptation_options = self._perform_get_request(endpoint_suffix)
        if with_validation:
            if(not self.knowledge.adaptation_options_schema): self.get_adaptation_options_schema()
            validate_schema(self.knowledge.adaptation_options, self.knowledge.adaptation_options_schema)
        logging.info("adaptation_options set to: ")
        pp.pprint(self.knowledge.adaptation_options)

    def get_monitor_schema(self, endpoint_suffix = "monitor_schema"):
        self.knowledge.monitor_schema = self._perform_get_request(endpoint_suffix)
        logging.info("monitor_schema set to: ")
        pp.pprint(self.knowledge.monitor_schema)

    def get_execute_schema(self, endpoint_suffix = "execute_schema"):
        self.knowledge.execute_schema = self._perform_get_request(endpoint_suffix)
        logging.info("execute_schema set to: ")
        # pp.pprint(self.knowledge.execute_schema)

    def get_adaptation_options_schema(self, endpoint_suffix: "API Endpoint" = "adaptation_options_schema"):
        self.knowledge.adaptation_options_schema = self._perform_get_request(endpoint_suffix)
        logging.info("adaptation_options_schema set to: ")
        pp.pprint(self.knowledge.adaptation_options_schema)

    def _perform_get_request(self, endpoint_suffix: "API Endpoint"):
        url = '/'.join([self.exemplar.base_endpoint, endpoint_suffix])
        response = get_response_for_get_request(url)
        if response.status_code == 404:
            logging.error("Please check that the endpoint you are trying to reach actually exists.")
            raise EndpointNotReachable
        return response.json()

    @abstractmethod
    def analyze(self):
        """ ... """
        pass

    @abstractmethod
    def plan(self):
        """ ... """
        pass

