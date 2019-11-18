from . import core, util, _localutil
import numpy as np

"""
Standard metrics for Agent Learning (RL tasks)
"""


class AgentMetric(core.Metric):
    """
    A single metric for an Agent (aka. Reinforcement Learning) learner
    """

    def __init__(self):
        pass
        # self.validate()

    def plot(self, result):
        pass

    def validate(self, phase_info):
        # TODO: Add structure validation of phase_info
        pass


class GlobalMean(AgentMetric):
    name = "Global Mean Performance"
    capability = "continual_learning"
    requires = {'syllabus_type': 'agent', 'syllabus_subtype': 'all'}
    description = "Calculates the performance across all tasks and phases"

    def __init__(self):
        super().__init__()
        # self.validate()

    def validate(self, phase_info):
        # TODO: Add structure validation of phase_info
        pass

    def calculate(self, dataframe, phase_info, metrics_dict):
        return {'global_perf': np.mean(dataframe.loc[:, "reward"])}


class WithinBlockSaturation(AgentMetric):
    name = "Average Within Block Saturation Calculation"
    capability = "continual_learning"
    requires = {'syllabus_type': 'agent', 'syllabus_subtype': 'CL'}
    description = "Calculates the performance within each block"

    def __init__(self):
        super().__init__()
        # self.validate()

    def validate(self, phase_info):
        # TODO: Add structure validation of phase_info
        pass

    def calculate(self, dataframe, phase_info, metrics_dict):
        base_query_str = 'block == '
        saturation_value = {}
        eps_to_saturation = {}
        all_sat_vals = []
        all_eps_to_sat = []

        # Iterate over all of the blocks and compute the within block performance
        for idx in range(phase_info.loc[:, 'block'].max()+1):
            # Need to get the part of the data corresponding to the block
            block_data = dataframe[dataframe["block"] == idx]

            # Make within block calculations
            sat_value, eps_to_sat, _ = _localutil.get_block_saturation_performance(block_data)

            # Record them
            saturation_value[idx] = sat_value
            all_sat_vals.append(sat_value)
            eps_to_saturation[idx] = eps_to_sat
            all_eps_to_sat.append(eps_to_sat)

        metrics_dict = {"saturation_value": saturation_value, "eps_to_saturation": eps_to_saturation}
        metric_to_return = {'global_within_block_saturation': np.mean(all_sat_vals),
                            'global_num_eps_to_saturation': np.mean(all_eps_to_sat)}

        return metric_to_return, metrics_dict


class STERelativePerf(AgentMetric):
    name = "Performance relative to S.T.E"
    capability = "adapt_to_new_tasks"
    requires = {'syllabus_type': 'agent', 'syllabus_subtype': 'ANT_B'}
    description = "Calculates the performance of each task relative to it's corresponding single task expert"

    def __init__(self):
        super().__init__()
        # self.validate()

    def validate(self, phase_info):
        # Load the single task experts and compare them to the ones in the logs
        ste_dict = util.load_default_ste_data()
        unique_tasks = phase_info.loc[:, 'task_name'].unique()

        # Make sure STE baselines are available for all tasks, else complain
        if unique_tasks.any() not in ste_dict:
            raise Exception

        # TODO: Add structure validation of phase_info

        return ste_dict

    def calculate(self, dataframe, phase_info, metrics_dict):
        # Validate the STE
        ste_dict = self.validate(phase_info)
        STE_normalized_saturation = {}
        all_STE_normalized_saturations = []

        for idx in range(phase_info.loc[:, 'block'].max()):
            # Get which task this block is and grab the STE performance for that task
            this_task = phase_info.loc[idx, "task_name"]
            this_ste_comparison = ste_dict[this_task]

            # Compare the saturation value of this block to the STE performance and store it

            STE_normalized_saturation[idx] = metrics_dict["saturation_value"][idx] / this_ste_comparison
            all_STE_normalized_saturations.append(STE_normalized_saturation[idx])

        metrics_dict["STE_normalized_saturation"] = STE_normalized_saturation
        metric_to_return = {'global_STE_normalized_saturation': np.mean(all_STE_normalized_saturations)}

        return metric_to_return, metrics_dict


class PerfMaintenanceANT(AgentMetric):
    name = "Performance Maintenance relative to previously trained task - only for ANT syllabi"
    capability = "continual_learning"
    requires = {'syllabus_type': 'agent', 'syllabus_subtype': 'ANT'}
    description = "Calculates the performance of each task, in each evaluation block, " \
                  "relative to the previously trained task"

    def __init__(self):
        super().__init__()
        # self.validate()

    def validate(self, phase_info):
        # TODO: Add structure validation of phase_info
        # Must ensure that the training phase has only one block or else handle multiple
        pass

    def calculate(self, dataframe, phase_info, metrics_dict):
        # This metric must compute in each evaluation block the performance of the tasks
        # relative to the previously trained ones
        previously_trained_tasks = np.array([])
        previously_trained_task_ids = np.array([])
        this_metric = {}
        all_maintenance_vals = []

        # Iterate over the phases, just the evaluation portion. We need to do this in order.
        for phase in phase_info.sort_index().loc[:, 'phase_number'].unique():
            # Get the task names that were used for the train portion of the phase
            trained_tasks = phase_info[(phase_info.phase_type == 'train') &
                                       (phase_info.phase_number == phase)].loc[:, 'task_name'].to_numpy()
            trained_task_ids = phase_info[(phase_info.phase_type == 'train') &
                                          (phase_info.phase_number == phase)].loc[:, 'block'].to_numpy()

            # Validation would have ensured that the training phase has exactly one training phase
            previously_trained_tasks = np.append(previously_trained_tasks, trained_tasks)
            previously_trained_task_ids = np.append(previously_trained_task_ids, trained_task_ids)

            this_phase_test_tasks = phase_info[(phase_info.phase_type == 'test') &
                                               (phase_info.phase_number == phase)].loc[:, 'task_name'].to_numpy()
            this_phase_test_task_ids = phase_info[(phase_info.phase_type == 'test') &
                                                  (phase_info.phase_number == phase)].loc[:, 'block'].to_numpy()

            for idx, task in enumerate(this_phase_test_tasks):

                if task in previously_trained_tasks:
                    # Get the inds in the previously_trained_tasks array to get the saturation values for comparison
                    inds_where_task = np.where(previously_trained_tasks == task)

                    # TODO: Handle multiple comparison points
                    block_ids_for_comparison = previously_trained_task_ids[inds_where_task]
                    previously_trained_sat_values = metrics_dict['saturation_value'][block_ids_for_comparison[0]]

                    new_sat_value = metrics_dict['saturation_value'][this_phase_test_task_ids[idx]]

                    this_comparison = previously_trained_sat_values - new_sat_value
                    key_str = task + '_phase_' + str(phase) + '_maintenance'
                    this_metric[key_str] = this_comparison
                    all_maintenance_vals.append(this_comparison)

        metric_to_return = {'mean_performance_difference': np.mean(all_maintenance_vals)}
        print(this_metric)
        metrics_dict['performance_maintenance'] = this_metric

        return metric_to_return, metrics_dict


class AgentMetricsReport(core.MetricsReport):
    """
    Aggregates a list of metrics for an Agent learner
    """

    def __init__(self, **kwargs):
        # Defines log_dir, syllabus_subtype, and initializes the _metrics list
        super().__init__(**kwargs)

        # Gets all data from the relevant log files
        self._log_data = util.read_log_data(util.get_l2root_base_dirs('logs', self.log_dir))
        _, self.phase_info = _localutil.parse_blocks(self._log_data)

        # Adds default metrics to list based on passed syllabus subtype
        self._add_default_metrics()

        # Do an initial check to make sure that reward has been logged
        if 'reward' not in self._log_data.columns:
            raise Exception('Reward column is required in the log data!')

        # Initialize a results dictionary that can be returned at the end of the calculation step and an internal
        # dictionary that can be passed around for internal calculations
        self._results = {}
        self._metrics_dict = {}
        self._phase_info = None

    def _add_default_metrics(self):
        # TODO: Add validation in the constructors to make sure syllabus has expected structure?
        if self.syllabus_subtype == "CL":
            self.add(WithinBlockSaturation())

        elif self.syllabus_subtype == "ANT_A":
            self.add(WithinBlockSaturation())
            self.add(STERelativePerf())
            self.add(PerfMaintenanceANT())

        elif self.syllabus_subtype == "ANT_B":
            self.add(WithinBlockSaturation())
            self.add(STERelativePerf())

        elif self.syllabus_subtype == "ANT_C":
            self.add(WithinBlockSaturation())
            self.add(STERelativePerf())

        else:
            raise NotImplementedError

    def calculate(self):
        for metric in self._metrics:
            this_result, self._metrics_dict = metric.calculate(self._log_data, self.phase_info, self._metrics_dict)
            self._results[metric.name] = this_result

    def report(self):
        # Call a describe method to inform printing
        for r_key in self._results:
            print('\nMetric: {:s}'.format(r_key))
            print('Value: {:s}'.format(str(self._results[r_key])))

    def plot(self):
        # TODO: Actually, you know, implement plotting
        pass

    def add(self, metrics_list):
        self._metrics.append(metrics_list)
