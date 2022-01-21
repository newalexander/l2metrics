"""
Copyright © 2021 The Johns Hopkins University Applied Physics Laboratory LLC

Permission is hereby granted, free of charge, to any person obtaining a copy 
of this software and associated documentation files (the “Software”), to 
deal in the Software without restriction, including without limitation the 
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or 
sell copies of the Software, and to permit persons to whom the Software is 
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in 
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR 
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE 
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, 
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR 
IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

"""
This is a Python script for computing and aggregating lifelong learning metrics
across multiple runs of different learning scenarios.

Additionally, this script contains helper functions for the Jupyter notebook,
evaluation.ipynb.
"""

import argparse
import fnmatch
import inspect
import json
import logging
import os
from pathlib import Path
from typing import List, Tuple
from zipfile import ZipFile

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import scipy
import seaborn as sns
from IPython import get_ipython
from IPython.display import display
from l2metrics import util
from l2metrics.report import MetricsReport

sns.set_style("dark")
sns.set_context("paper")

logger = logging.getLogger(__name__)

cc = util.color_cycler()

if get_ipython() is None:
    from tqdm import tqdm
else:
    from tqdm.notebook import tqdm


def load_computational_costs(eval_dir: Path) -> pd.DataFrame:
    """Load the computational cost data from the given log directory.

    Args:
        eval_dir (Path): Path to directory containing computational cost data.

    Returns:
        pd.DataFrame: DataFrame containing computational costs for system and agent.
    """

    # Initialize computational cost dataframe
    comp_cost_df = pd.DataFrame()

    # Concatenate computational cost data
    docs_dir = eval_dir / 'docs'
    comp_cost_files = list(docs_dir.glob('computation*.csv'))

    if comp_cost_files:
        comp_cost_df = pd.concat((pd.read_csv(f) for f in comp_cost_files), ignore_index=True)
    else:
        logger.warning(f"No computational cost files found in directory: {eval_dir}\n")

    return comp_cost_df


def load_performance_thresholds(eval_dir: Path) -> pd.DataFrame:
    """Load the performance threshold data from the given log directory.

    Args:
        eval_dir (Path): Path to directory containing performance thresholds.

    Returns:
        pd.DataFrame: DataFrame containing performance thresholds for system and agent.
    """

    # Initialize computational cost dataframe
    perf_thresh_df = pd.DataFrame()

    # Concatenate computational cost data
    docs_dir = eval_dir / 'docs'
    perf_thresh_file = docs_dir / 'performance_thresholds.csv'

    if perf_thresh_file.exists():
        perf_thresh_df = pd.read_csv(perf_thresh_file)
    else:
        logger.warning(f"No performance threshold file found in directory: {eval_dir}\n")

    return perf_thresh_df


def load_task_similarities(eval_dir: Path) -> pd.DataFrame:
    """Load the task similarity matrix from the given log directory.

    Args:
        eval_dir (Path): Path to directory containing task similarity matrix.

    Returns:
        pd.DataFrame: DataFrame containing task similarities.
    """

    # Initialize task similarity dataframe
    task_similarity_df = pd.DataFrame()

    # Concatenate computational cost data
    docs_dir = eval_dir / 'docs'
    task_similarity_file = docs_dir / 'task_relationships.csv'

    if task_similarity_file.exists():
        task_similarity_df = pd.read_csv(task_similarity_file)
    else:
        logger.warning(f"No task similarity file found in directory: {eval_dir}\n")

    return task_similarity_df


def unzip_logs(eval_dir: Path) -> None:
    """Walk through log directory and unzip log archives.

    Args:
        eval_dir (Path): Path to directory containing log archives.
    """
    for root, _, files in os.walk(eval_dir):
        for filename in fnmatch.filter(files, '*.zip'):
            ZipFile(os.path.join(root, filename)).extractall(root)
            logger.info(f'Unzipped file: {filename}')


def store_ste_data(log_dir: Path) -> None:
    """Save all single-task expert data in provided log directory.

    Args:
        log_dir (Path): Path to agent configuration directory containing STE logs.

    Raises:
        FileNotFoundError: If log directory structure does not follow the expected
            structure described in the evaluation protocol.
    """

    # Check for STE logs
    ste_log_dir = log_dir / 'ste_logs' / 'ste_logs'

    if ste_log_dir.exists():
        # Store all the STE data found in the directory
        logger.info('Storing STE data...')
        for ste_dir in ste_log_dir.iterdir():
            if ste_dir.is_dir():
                # Store STE data in append mode
                util.store_ste_data(log_dir=ste_dir, mode='a')
        logger.info('Done storing STE data!\n')
    else:
        # STE log path not found - possibly because compressed archive has not been
        # extracted in the same location yet
        raise FileNotFoundError(f"STE logs not found in expected location!")


def compute_scenario_metrics(**kwargs) -> Tuple[pd.DataFrame, dict, pd.DataFrame, pd.DataFrame]:
    """Compute lifelong learning metrics for single LL logs found at input path.

    Args:
        log_dir (Path): Path to scenario directory.
        variant_mode (str, optional): Mode for computing metrics with respect to task variants.
            Defaults to 'aware'.
        ste_averaging_method (str, optional): Method for averaging multiple runs of STE data.
            Valid values are 'metrics' and 'time'. Defaults to 'metrics'.
        perf_measure (str, optional): Name of column to use for metrics calculations.
        aggregation_method (str, optional): Method for aggregating within-lifetime metrics.
            Valid values are 'mean' and 'median'. Defaults to 'mean'.
        maintenance_method (str, optional): Method for computing maintenance values.
            Valid values are 'mrlep', 'mrtlp', and 'both'. Defaults to 'mrlep'.
        transfer_method (str, optional): Method for computing forward and backward transfer.
            Valid values are 'ratio', 'contrast', and 'both'. Defaults to 'ratio'.
        normalization_method (str, optional): Method for normalizing data.
            Valid values are 'task', 'run', and 'none'. Defaults to 'task'.
        smoothing_method (str, optional): Method for smoothing data, window type.
            Valid values are 'flat', 'hanning', 'hamming', 'bartlett', 'blackman', and 'none'.
            Defaults to 'flat'.
        window_length (int, optional): Window length for smoothing data. Defaults to None.
        clamp_outliers (bool, optional): Flag for enabling outlier removal. Defaults to False.
        output_dir (str, optional): Output directory of results. Defaults to ''.
        show_eval_lines (bool, optional): Flag for enabling lines between evaluation blocks to show
            changing slope of evaluation performance. Defaults to True.
        do_plot (bool, optional): Flag for enabling plotting. Defaults to True.
        do_save_plots (bool, optional): Flag for enabling saving of plots. Defaults to True.
        task_colors (dict, optional): Dict of task names and colors for plotting. Defaults to {}.

    Returns:
        Tuple[pd.DataFrame, dict, pd.DataFrame, pd.DataFrame]: DataFrame containing lifelong metrics
            from scenarios and log data.
    """

    log_dir = kwargs.get('log_dir', Path(''))
    task_colors = kwargs.get('task_colors', {})
    output_dir = kwargs.get('output_dir', '')
    show_eval_lines = kwargs.get('show_eval_lines', True)
    do_plot = kwargs.get('do_plot', True)
    do_save_plots = kwargs.get('do_save_plots', True)

    # Initialize metrics report
    report = MetricsReport(**kwargs)

    # Calculate metrics
    report.calculate()
    ll_metrics_df = report.ll_metrics_df
    ll_metrics_dict = report.ll_metrics_dict
    regime_metrics_df = report.regime_metrics_df

    # Append SG name to dataframe
    # TODO: Figure out solution that isn't as hard-coded
    ll_metrics_df['sg_name'] = log_dir.parts[-6].split('_')[1]
    ll_metrics_dict['sg_name'] = log_dir.parts[-6].split('_')[1]
    regime_metrics_df['sg_name'] = log_dir.parts[-6].split('_')[1]

    # Append agent configuration to dataframe
    ll_metrics_df['agent_config'] = log_dir.parts[-4]
    ll_metrics_dict['agent_config'] = log_dir.parts[-4]
    regime_metrics_df['agent_config'] = log_dir.parts[-4]

    # Get log data
    log_data_df = report._log_data
    log_data_df['run_id'] = log_dir.name

    if do_plot:
        # Update task color dictionary
        for task_name, c in zip(list(set(report._unique_tasks) - set(task_colors.keys())), cc):
            task_colors[task_name] = c['color']

        report.plot(save=do_save_plots, show_eval_lines=show_eval_lines,
                    output_dir=output_dir, task_colors=task_colors)
        report.plot_ste_data(save=do_save_plots,
                             output_dir=output_dir, task_colors=task_colors)
        plt.close('all')

    return ll_metrics_df, ll_metrics_dict, regime_metrics_df, log_data_df


def compute_eval_metrics(**kwargs) -> Tuple[pd.DataFrame, List, pd.DataFrame, pd.DataFrame]:
    """Compute lifelong learning metrics for all LL logs in provided evaluation log directory.

    This function iterates through all the lifelong learning logs it finds in the provided
    directory, computes the LL metrics for those logs, then sorts the metrics by scenario
    type, complexity, and difficulty. Scenarios with missing scenario information
    might be ignored in the evaluation.

    Args:
        eval_dir (Path): Path to evaluation directory containing LL logs.
        agent_config_dir (str): Agent configuration directory of data. A value of '' will evaluate all
            logs in every agent configuration directory.
        ste_dir (str): Agent configuration directory of STE data. A value of '' will save all STE
            logs in every agent configuration directory.
        do_store_ste (bool, optional): Flag for enabling save of STE data. Defaults to True.

    Raises:
        FileNotFoundError: If log directory structure does not follow the expected
            structure described in the evaluation protocol.

    Returns:
        Tuple[pd.DataFrame, List, pd.DataFrame]: DataFrame containing lifelong metrics from all
            parsed scenarios, sorted by scenario type, complexity, and difficulty. List of lifetime
            and task-level metrics for each scenario. Log data from each scenario.
    """

    eval_dir = kwargs.get('eval_dir', Path(''))
    agent_config_dir = kwargs.get('agent_config_dir', '')
    ste_dir = kwargs.get('ste_dir', '')
    do_store_ste = kwargs.get('do_store_ste', False)

    # Initialize LL metric dataframe
    ll_metrics_df = pd.DataFrame()
    ll_metrics_dicts = []
    regime_metrics_df = pd.DataFrame()
    log_data_df = pd.DataFrame()
    task_colors = {}

    # Iterate through agent configuration directories
    for agent_config in tqdm(list(eval_dir.glob('agent_config*')), desc='Agents'):
        # Save STE data if enabled
        if do_store_ste:
            if ste_dir in ['', agent_config.name]:
                store_ste_data(eval_dir / agent_config.name)

        if agent_config_dir in ['', agent_config.name]:
            # Check for LL logs
            ll_log_dir = agent_config / 'll_logs'

            if ll_log_dir.exists():
                logger.info(
                    f'Computing metrics from LL logs for {agent_config.name}...')

                # Compute and store the LL metrics for all scenarios found in the directory
                for path in tqdm(list(ll_log_dir.iterdir()), desc=agent_config.name):
                    if path.is_dir():
                        # Check if current path is log directory for single run
                        if all(x in [f.name for f in path.glob('*.json')] for x in ['logger_info.json', 'scenario_info.json']):
                            metrics_df, metrics_dict, regime_df, data_df = compute_scenario_metrics(
                                log_dir=path, task_colors=task_colors, **kwargs)
                            ll_metrics_df = ll_metrics_df.append(metrics_df, ignore_index=True)
                            ll_metrics_dicts.append(metrics_dict)
                            regime_metrics_df = regime_metrics_df.append(regime_df, ignore_index=True)
                            log_data_df = log_data_df.append(data_df, ignore_index=True)
                        else:
                            # Iterate through subdirectories containing LL logs
                            for sub_path in tqdm(list(path.iterdir()), desc=path.name):
                                if sub_path.is_dir():
                                    metrics_df, metrics_dict, regime_df, data_df = compute_scenario_metrics(
                                        log_dir=sub_path, task_colors=task_colors, **kwargs)
                                    ll_metrics_df = ll_metrics_df.append(metrics_df, ignore_index=True)
                                    ll_metrics_dicts.append(metrics_dict)
                                    regime_metrics_df = regime_metrics_df.append(regime_df, ignore_index=True)
                                    log_data_df = log_data_df.append(data_df, ignore_index=True)
            else:
                raise FileNotFoundError(
                    f"LL logs not found in expected location!")

            # Sort data by scenario type, complexity, difficulty
            if not ll_metrics_df.empty:
                try:
                    ll_metrics_df = ll_metrics_df.sort_values(
                        by=['scenario_type', 'complexity', 'difficulty'])
                except KeyError as e:
                    logger.exception("KeyError occurred while sorting LL metrics")

    return ll_metrics_df, ll_metrics_dicts, regime_metrics_df, log_data_df


def evaluate() -> None:
    """Runs an evaluation on the provided log directory with the given parameters.

    This function loops through the subdirectories in the given directory, stores all STE data,
    computes LL metrics on all LL data, sorts the metrics by scenario complexity/difficulty,
    displays the aggregated data as tables, plots the results, then saves the metrics to the given
    output location.

    """
    # Instantiate parser
    parser = argparse.ArgumentParser(
        description='Run L2M evaluation from the command line')

    # Evaluation directory can be absolute or relative paths
    parser.add_argument('-l', '--eval-dir', default='', type=str,
                        help='Evaluation directory containing logs. Defaults to "".')

    # Specific agent configuration to evaluate
    parser.add_argument('-f', '--agent-config-dir', default='', type=str,
                        help='Agent configuration directory of data. Defaults to "".')

    # Agent configuration directory for STE data
    parser.add_argument('-s', '--ste-dir', default='', type=str,
                        help='Agent configuration directory of STE data. Defaults to "".')

    # Method for handling task variants
    parser.add_argument('-r', '--variant-mode', default='aware', type=str, choices=['aware', 'agnostic'],
                        help='Mode for computing metrics with respect to task variants. \
                            Defaults to aware.')

    # Method for handling multiple STE runs
    parser.add_argument('-v', '--ste-averaging-method', default='metrics', choices=['metrics', 'time'],
                        help='Method for handling STE runs, LL metric averaging (metrics) or ' \
                            'time-series averaging (time). Defaults to metrics.')

    # Choose application measure to use as performance column
    parser.add_argument('-p', '--perf-measure', default='reward', type=str,
                        help='Name of column to use for metrics calculations. Defaults to reward.')

    # Method for aggregating within-lifetime metrics
    parser.add_argument('-a', '--aggregation-method', default='mean', type=str, choices=['mean', 'median'],
                        help='Method for aggregating within-lifetime metrics. Defaults to mean.')

    # Method for calculating performance maintenance
    parser.add_argument('-m', '--maintenance-method', default='mrlep', type=str, choices=['mrlep', 'mrtlp', 'both'],
                        help='Method for computing performance maintenance. Defaults to mrlep.')

    # Method for calculating forward and backward transfer
    parser.add_argument('-t', '--transfer-method', default='ratio', type=str, choices=['ratio', 'contrast', 'both'],
                        help='Method for computing forward and backward transfer. Defaults to ratio.')

    # Method for normalization
    parser.add_argument('-n', '--normalization-method', default='task', type=str, choices=['task', 'run', 'none'],
                        help='Method for normalizing data. Defaults to task.')

    # Method for smoothing
    parser.add_argument('-g', '--smoothing-method', default='flat', type=str, choices=['flat', 'hanning', 'hamming', 'bartlett', 'blackman', 'none'],
                        help='Method for smoothing data, window type. Defaults to flat.')

    # Flag for smoothing evaluation block data
    parser.add_argument('-G', '--smooth-eval-data', dest='do_smooth_eval_data', default=False, action='store_true',
                        help='Smooth evaluation block data. Defaults to false.')

    # Window length for smoothing
    parser.add_argument('-w', '--window-length', default=None, type=int,
                        help='Window length for smoothing data. Defaults to None.')

    # Flag for removing outliers
    parser.add_argument('-x', '--clamp-outliers', action='store_true',
                        help='Remove outliers in data for metrics by clamping to quantiles. Defaults \
                            to false.')

    # Data range file for normalization
    parser.add_argument('-d', '--data-range-file', default=None, type=str,
                        help='JSON file containing task performance ranges for normalization. \
                            Defaults to None.')

    # Output directory
    parser.add_argument('-O', '--output-dir', default='results', type=str,
                        help='Directory for output files. Defaults to results.')

    # Output filename
    parser.add_argument('-o', '--output', default='ll_metrics', type=str,
                        help='Output filename for results. Defaults to ll_metrics.')

    # Flag for enabling unzipping of logs
    parser.add_argument('-u', '--do-unzip', action='store_true',
                        help='Unzip all data found in evaluation directory')

    # Flag for showing evaluation block lines
    parser.add_argument('-e', '--show-eval-lines', dest='show_eval_lines', default=True, action='store_true',
                        help='Show lines between evaluation blocks. Defaults to true.')
    parser.add_argument('--no-show-eval-lines', dest='show_eval_lines', action='store_false',
                        help='Do not show lines between evaluation blocks')

    # Flag for disabling STE save
    parser.add_argument('-T', '--do-store-ste', dest='do_store_ste', default=True, action='store_true',
                        help='Store STE data. Defaults to true.')
    parser.add_argument('--no-store-ste', dest='do_store_ste', action='store_false',
                        help='Do not store STE data')

    # Flag for enabling/disabling plotting
    parser.add_argument('-P', '--do-plot', dest='do_plot', default=True, action='store_true',
                        help='Plot performance. Defaults to true.')
    parser.add_argument('--no-plot', dest='do_plot', action='store_false',
                        help='Do not plot performance')

    # Flag for enabling plot save
    parser.add_argument('-L', '--do-save-plots', dest='do_save_plots', default=True, action='store_true',
                        help='Save scenario and STE plots. Defaults to true.')
    parser.add_argument('--no-save-plots', dest='do_save_plots', action='store_false',
                        help='Do not save scenario and STE plots')

    # Flag for enabling/disabling save
    parser.add_argument('-S', '--do-save', dest='do_save', default=True, action='store_true',
                        help='Save metrics outputs. Defaults to true.')
    parser.add_argument('--no-save', dest='do_save', action='store_false',
                        help='Do not save metrics outputs')

    # Settings file arguments
    parser.add_argument('-c', '--load-settings', default=None, type=str,
                        help='Load evaluation settings from JSON file. Defaults to None.')
    parser.add_argument('-C', '--do-save-settings', dest='do_save_settings', default=True, action='store_true',
                        help='Save L2Metrics settings to JSON file. Defaults to true.')
    parser.add_argument('--no-save-settings', dest='do_save_settings', action='store_false',
                        help='Do not save L2Metrics settings to JSON file')

    # Parse arguments
    args = parser.parse_args()
    kwargs = vars(args)

    if args.load_settings:
        with open(args.load_settings, 'r') as settings_file:
            kwargs.update(json.load(settings_file))

    kwargs['eval_dir'] = Path(args.eval_dir)
    kwargs['output_dir'] = Path(args.output_dir)

    # Create output directory if it doesn't exist
    if args.do_save_plots or args.do_save or args.do_save_settings:
        args.output_dir.mkdir(parents=True, exist_ok=True)

    # Load data range data for normalization and standardize names to lowercase
    if args.data_range_file:
        with open(args.data_range_file) as data_range_file:
            data_range = json.load(data_range_file)
            data_range = {key.lower(): val for key, val in data_range.items()}
    else:
        data_range = None
    kwargs['data_range'] = data_range

    # Unzip logs
    if args.do_unzip:
        unzip_logs(args.eval_dir)

    # Compute LL metric data
    matplotlib.use('Agg')
    ll_metrics_df, ll_metrics_dicts, regime_metrics_df, log_data_df = compute_eval_metrics(**kwargs)

    # Display aggregated data
    try:
        display(ll_metrics_df.groupby(by=['scenario_type', 'complexity', 'difficulty']).agg(['mean', 'std']))
        display(ll_metrics_df.groupby(by=['scenario_type', 'complexity', 'difficulty']).agg(['median', scipy.stats.iqr]))
    except KeyError as e:
        logger.exception("KeyError occurred while grouping LL metrics")

    # Save data
    if args.do_save:
        if not ll_metrics_df.empty:
            with open(args.output_dir / (args.output + '.tsv'), 'w', newline='\n') as metrics_file:
                ll_metrics_df.set_index(['sg_name', 'agent_config', 'run_id']).sort_values(
                    ['agent_config', 'run_id']).to_csv(metrics_file, sep='\t')
        if ll_metrics_dicts:
            with open(args.output_dir / (args.output + '.json'), 'w', newline='\n') as metrics_file:
                json.dump(ll_metrics_dicts, metrics_file)
        if not regime_metrics_df.empty:
            with open(args.output_dir / (args.output + '_regime.tsv'), 'w', newline='\n') as metrics_file:
                regime_metrics_df.set_index(['sg_name', 'agent_config', 'run_id']).sort_values(
                    ['agent_config', 'run_id']).to_csv(metrics_file, sep='\t')
        if not log_data_df.empty:
            log_data_df.reset_index(drop=True).to_feather(args.output_dir / (args.output + '_data.feather'))

    # Save settings for evaluation
    if args.do_save_settings:
        with open(args.output_dir / (args.output + '_settings.json'), 'w') as outfile:
            kwargs['eval_dir'] = str(kwargs.get('eval_dir', ''))
            kwargs['output_dir'] = str(kwargs.get('output_dir', ''))
            json.dump(kwargs, outfile)


if __name__ == '__main__':
    # Configure logger
    logging.basicConfig(level=logging.INFO)

    try:
        evaluate()
    except (KeyError, ValueError) as e:
        logger.exception(e)
