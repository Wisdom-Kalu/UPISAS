
from ConfigValidator.Config.RunnerConfig import RunnerConfig as OriginalRunnerConfig
from ProgressManager.Output.CSVOutputManager import CSVOutputManager
from ProgressManager.RunTable.Models.RunProgress import RunProgress

import TestUtilities

if __name__ == '__main__':
    TEST_DIR = TestUtilities.get_test_dir(__file__)

    config_file = TestUtilities.load_and_get_config_file_as_module(TEST_DIR)
    RunnerConfig: OriginalRunnerConfig = config_file.RunnerConfig

    csv_data_manager = CSVOutputManager(RunnerConfig.results_output_path / RunnerConfig.name)
    run_table = csv_data_manager.read_run_table()
    for row in run_table:
        if row['__run_id'] == 'run_1':
            row['__done']  = RunProgress.TODO
            row['avg_cpu'] = 0
    csv_data_manager.write_run_table(run_table)
