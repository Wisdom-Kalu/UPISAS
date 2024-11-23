from EventManager.Models.RunnerEvents import RunnerEvents
from EventManager.EventSubscriptionController import EventSubscriptionController
from ConfigValidator.Config.Models.RunTableModel import RunTableModel
from ConfigValidator.Config.Models.FactorModel import FactorModel
from ConfigValidator.Config.Models.RunnerContext import RunnerContext
from ConfigValidator.Config.Models.OperationType import OperationType
from ExtendedTyping.Typing import SupportsStr
from ProgressManager.Output.OutputProcedure import OutputProcedure as output

from typing import Dict, List, Any, Optional
from pathlib import Path
from os.path import dirname, realpath

'''
Test Description:

Test functionality for shuffling
  * When recovering from a crash, the order of the run table should remain the same
'''

class RunnerConfig:
    ROOT_DIR = Path(dirname(realpath(__file__)))

    # ================================ USER SPECIFIC CONFIG ================================
    name:                       str             = "new_runner_experiment"
    results_output_path:        Path             = ROOT_DIR / 'experiments'
    operation_type:             OperationType   = OperationType.AUTO
    time_between_runs_in_ms:    int             = 100

    def __init__(self):
        """Executes immediately after program start, on config load"""

        EventSubscriptionController.subscribe_to_multiple_events([
            (RunnerEvents.BEFORE_EXPERIMENT, self.before_experiment),
            (RunnerEvents.BEFORE_RUN       , self.before_run       ),
            (RunnerEvents.START_RUN        , self.start_run        ),
            (RunnerEvents.START_MEASUREMENT, self.start_measurement),
            (RunnerEvents.INTERACT         , self.interact         ),
            (RunnerEvents.STOP_MEASUREMENT , self.stop_measurement ),
            (RunnerEvents.STOP_RUN         , self.stop_run         ),
            (RunnerEvents.POPULATE_RUN_DATA, self.populate_run_data),
            (RunnerEvents.AFTER_EXPERIMENT , self.after_experiment )
        ])
        self.run_table_model = None  # Initialized later

        output.console_log("Custom config loaded")

    def create_run_table_model(self) -> RunTableModel:
        factor1 = FactorModel("example_factor1", ["level1", "level2", "level3"])
        factor2 = FactorModel("example_factor2", [True, False])
        self.run_table_model = RunTableModel(
            factors=[factor1, factor2],
            data_columns=['avg_cpu', 'avg_mem'],
            shuffle=True
        )
        return self.run_table_model

    def before_experiment(self) -> None:
        output.console_log("Config.before_experiment() called!")

    def before_run(self) -> None:
        output.console_log("Config.before_run() called!")

    def start_run(self, context: RunnerContext) -> None:
        output.console_log("Config.start_run() called!")

    def start_measurement(self, context: RunnerContext) -> None:
        output.console_log("Config.start_measurement() called!")

    def interact(self, context: RunnerContext) -> None:
        output.console_log("Config.interact() called!")

    def stop_measurement(self, context: RunnerContext) -> None:
        output.console_log("Config.stop_measurement called!")

    def stop_run(self, context: RunnerContext) -> None:
        output.console_log("Config.stop_run() called!")

    def populate_run_data(self, context: RunnerContext) -> Optional[Dict[str, SupportsStr]]:
        output.console_log("Config.populate_run_data() called!")
        return {
            'avg_cpu': 13,
            'avg_mem': 18.1
        }

    def after_experiment(self) -> None:
        output.console_log("Config.after_experiment() called!")

    # ================================ DO NOT ALTER BELOW THIS LINE ================================
    experiment_path:            Path             = None
