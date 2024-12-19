class Knowledge:
    def __init__(self, monitored_data, analysis_data, plan_data, adaptation_options):
        self.monitored_data = monitored_data  # Stores monitoring data
        self.analysis_data = analysis_data  # Stores results from the analyze phase
        self.plan_data = plan_data  # Stores planned actions
        self.adaptation_options = adaptation_options  # Stores executed actions/results
        self.standby_pool = {}  # Tracks standby instances for critical services


