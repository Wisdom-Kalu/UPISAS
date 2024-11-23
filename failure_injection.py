import os
import time
import subprocess
from dotenv import load_dotenv

load_dotenv()

class FailureInjector:
    def __init__(self):
        self.failures = [
            {
                "start_time": int(os.getenv("FAILURE_INJECTION_1_START", 0)),
                "duration": int(os.getenv("FAILURE_INJECTION_1_DURATION", 0)),
                "instance_id": os.getenv("ID_OF_INSTANCE_TO_FAIL", "")
            },
            {
                "start_time": int(os.getenv("FAILURE_INJECTION_2_START", 0)),
                "duration": int(os.getenv("FAILURE_INJECTION_2_DURATION", 0)),
                "instance_id": os.getenv("ID_OF_INSTANCE_TO_FAIL", "")
            }
        ]
        self.failure_injection_enabled = os.getenv("FAILURE_INJECTION", "N") == "Y"

    def stop_docker_container(self, instance_id):
        try:
            container_name = instance_id.split("@")[0]
            subprocess.run(["docker", "stop", container_name], check=True)
            print(f"Stopped container: {container_name}")
        except subprocess.CalledProcessError as e:
            print(f"Error stopping container {instance_id}: {e}")

    def start_docker_container(self, instance_id):
        try:
            container_name = instance_id.split("@")[0]
            subprocess.run(["docker", "start", container_name], check=True)
            print(f"Started container: {container_name}")
        except subprocess.CalledProcessError as e:
            print(f"Error starting container {instance_id}: {e}")

    def inject_failures(self):
        if not self.failure_injection_enabled:
            print("Failure injection is disabled.")
            return

        print("Starting Failure Injection Service...")
        start_time = time.time()

        for failure in self.failures:
            while True:
                current_time = time.time() - start_time
                if current_time >= failure["start_time"]:
                    instance_id = failure["instance_id"]
                    print(f"Injecting failure for instance: {instance_id}")
                    self.stop_docker_container(instance_id)

                    if failure["duration"] > 0:
                        time.sleep(failure["duration"])
                        print(f"Restoring instance: {instance_id}")
                        self.start_docker_container(instance_id)

                    break

                time.sleep(1)

        print("Failure Injection Service completed.")
