import os
import subprocess
import pprint, time
from UPISAS.exemplar import Exemplar
import logging
pp = pprint.PrettyPrinter(indent=4)
logging.getLogger().setLevel(logging.INFO)


class RAMSES(Exemplar):
    """
    A class which encapsulates a self-adaptive exemplar run in a docker container.
    """
    _container_name = ""
    def __init__(self, auto_start=True):
        self.base_endpoint = "http://127.0.0.1:50000"
        self.ramses_dir_path = os.path.join(os.path.dirname(__file__), "..", "ramses")
        #self.ramses_dir_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ramses")) #absolute path used to avoid issues when running the script from different locations

        if auto_start:
            self.start_container()
    
    def start_run(self):
        try:
            ramses_interface_path = os.path.join(self.ramses_dir_path, "Interface")
            subprocess.Popen(
                ['python3', 'api.py'],  
                cwd=ramses_interface_path 
            )
            logging.info("RAMSES API endpoints successfully started")
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to start RAMSES API endpoints: {e}")
            raise

    
    def start_container(self):
        try:
            subprocess.run( ['docker', 'compose', 'up', '-d'], cwd = self.ramses_dir_path, check = True )
            logging.info ("Docker container started successfully. Please wait for the APIs and container to initialize properly...")
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to start the docker containers: {e}")
            raise

    def stop_container(self, remove=True):
        try:
            subprocess.run(
                ['docker', 'compose', 'down'],
                cwd = self.ramses_dir_path,
                check=True
            )
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to stop the docker containers: {e}")
            raise
    
    '''
    def pause_container(self):
        """
        Pauses the container.
        """
        try:
            subprocess.run(
                ['docker', 'pause', self.container_name],
                check=True
            )
            logging.info(f"Container '{self.container_name}' paused successfully.")
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to pause container '{self.container_name}': {e}")
            raise

    def unpause_container(self):
        """
        Unpauses the container.
        """
        try:
            subprocess.run(
                ['docker', 'unpause', self.container_name],
                check=True
            )
            logging.info(f"Container '{self.container_name}' unpaused successfully.")
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to unpause container '{self.container_name}': {e}")
            raise

    def get_container_status(self):
        try:
            result = subprocess.run(
                ['docker', 'inspect', '-f', '{{.State.Status}}', self.container_name],
                check=True,
                stdout=subprocess.PIPE,
                text=True
            )
            status = result.stdout.strip()
            logging.info(f"Container '{self.container_name}' is currently '{status}'.")
            return status
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to get status for container '{self.container_name}': {e}")
            raise
 '''   