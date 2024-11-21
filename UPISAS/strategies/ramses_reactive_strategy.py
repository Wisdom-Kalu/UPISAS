import logging
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class InstanceStatus:
    BOOTING = "BOOTING"
    ACTIVE = "ACTIVE"
    SHUTDOWN = "SHUTDOWN"
    FAILED = "FAILED"


class AdaptationOption:
    def __init__(self, service_id, option_type, description):
        self.service_id = service_id
        self.option_type = option_type
        self.description = description


class AddInstanceOption(AdaptationOption):
    def __init__(self, service_id):
        super().__init__(service_id, "ADD_INSTANCE", "Add a new instance due to service failure or unavailability")


class Instance:
    def __init__(self, instance_id, status, metrics, boot_time=None):
        self.instance_id = instance_id
        self.status = status
        self.metrics = metrics
        self.boot_time = boot_time or datetime.now()


class Service:
    def __init__(self, service_id, instances):
        self.service_id = service_id
        self.instances = instances


class AnalyseService:
    def __init__(self, metrics_window_size=5, failure_rate_threshold=0.5, unreachable_rate_threshold=0.3):
        self.metrics_window_size = metrics_window_size
        self.failure_rate_threshold = failure_rate_threshold
        self.unreachable_rate_threshold = unreachable_rate_threshold
        self.adaptation_options = defaultdict(list)

    def start_analysis(self, services: Dict[str, Service]):
        logger.debug("Starting Analyse routine")
        self.adaptation_options.clear()

        for service_id, service in services.items():
            self.analyse_service(service)

        if self.adaptation_options:
            print("failure occurred. adaptation needed")
        else:
            print("no adaptation strategy needed")

    def analyse_service(self, service: Service):
        logger.debug(f"Analyzing service {service.service_id}")
        for instance in service.instances:
            if instance.status == InstanceStatus.FAILED:
                logger.debug(f"Service {service.service_id} has a failed instance {instance.instance_id}. Proposing AddInstance option.")
                self.adaptation_options[service.service_id].append(AddInstanceOption(service.service_id))
                return


def fetch_service_data():
    """
    Simulates fetching service data from an imaginary endpoint.
    Replace this function with an actual API call when integrating with a real system.
    """
    # Simulated data
    return {
        "service1": Service("service1", [
            Instance("instance1", InstanceStatus.ACTIVE, [{"failed": False, "unreachable": False}] * 5),
            Instance("instance2", InstanceStatus.FAILED, []),
        ]),
        "service2": Service("service2", [
            Instance("instance1", InstanceStatus.ACTIVE, [{"failed": False, "unreachable": False}] * 5),
        ]),
    }


if __name__ == "__main__":
    # Fetch service data
    services = fetch_service_data()

    # Create AnalyseService and run analysis
    analyse_service = AnalyseService()
    analyse_service.start_analysis(services)
