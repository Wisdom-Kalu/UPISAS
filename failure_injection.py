import os
import time
import subprocess
from dotenv import load_dotenv

class FailureInjector:
    def __init__(self):
        # Load initial configuration
        load_dotenv()
        self.reload_config()

    def reload_config(self):
        """
        Reloads configuration dynamically from the .env file.
        """
        load_dotenv(override=True)  # Reload the .env file
        self.failure_injection_enabled = os.getenv("FAILURE_INJECTION", "N") == "Y"
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

    def pause_docker_container(self, instance_id):
        try:
            container_name = instance_id.split("@")[0]
            subprocess.run(["docker", "pause", container_name], check=True)
            print(f"Stopped container: {container_name}")
        except subprocess.CalledProcessError as e:
            print(f"Error stopping container {instance_id}: {e}")

    def unpause_docker_container(self, instance_id):
        try:
            container_name = instance_id.split("@")[0]
            subprocess.run(["docker", "unpause", container_name], check=True)
            print(f"Started container: {container_name}")
        except subprocess.CalledProcessError as e:
            print(f"Error starting container {instance_id}: {e}")

    def inject_failures(self):
        print("Starting Failure Injection Service...")
        start_time = time.time()

        while True:
            # Reload configuration dynamically
            self.reload_config()

            if not self.failure_injection_enabled:
                print("Failure injection is disabled. Reloading configuration...")
                time.sleep(10)
                continue

            print("Failure injection is enabled.")
            current_time = time.time() - start_time

            for failure in self.failures:
                if current_time >= failure["start_time"]:
                    instance_id = failure["instance_id"]
                    print(f"Injecting failure for instance: {instance_id}")
                    self.pause_docker_container(instance_id)

                    if failure["duration"] > 0:
                        time.sleep(failure["duration"])
                        print(f"Restoring instance: {instance_id}")
                        self.unpause_docker_container(instance_id)

            time.sleep(10)
