# (c) 2019 The Johns Hopkins University Applied Physics Laboratory LLC (JHU/APL).
# All Rights Reserved. This material may be only be used, modified, or reproduced
# by or for the U.S. Government pursuant to the license rights granted under the
# clauses at DFARS 252.227-7013/7014 or FAR 52.227-14. For any other permission,
# please contact the Office of Technology Transfer at JHU/APL.

# NO WARRANTY, NO LIABILITY. THIS MATERIAL IS PROVIDED “AS IS.” JHU/APL MAKES NO
# REPRESENTATION OR WARRANTY WITH RESPECT TO THE PERFORMANCE OF THE MATERIALS,
# INCLUDING THEIR SAFETY, EFFECTIVENESS, OR COMMERCIAL VIABILITY, AND DISCLAIMS
# ALL WARRANTIES IN THE MATERIAL, WHETHER EXPRESS OR IMPLIED, INCLUDING (BUT NOT
# LIMITED TO) ANY AND ALL IMPLIED WARRANTIES OF PERFORMANCE, MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT OF INTELLECTUAL PROPERTY
# OR OTHER THIRD PARTY RIGHTS. ANY USER OF THE MATERIAL ASSUMES THE ENTIRE RISK
# AND LIABILITY FOR USING THE MATERIAL. IN NO EVENT SHALL JHU/APL BE LIABLE TO ANY
# USER OF THE MATERIAL FOR ANY ACTUAL, INDIRECT, CONSEQUENTIAL, SPECIAL OR OTHER
# DAMAGES ARISING FROM THE USE OF, OR INABILITY TO USE, THE MATERIAL, INCLUDING,
# BUT NOT LIMITED TO, ANY DAMAGES FOR LOST PROFITS.

import glob
import os
import pathlib
from collections import OrderedDict

import matplotlib.pyplot as plt
import pandas as pd
from l2logger.util import *

from . import _localutil


def get_ste_data_names() -> list:
    """Gets the names of the stored STE data in $L2DATA/taskinfo/.

    Returns:
        list: The STE task names.
    """
    return [f.stem for f in pathlib.Path(get_l2root_base_dirs('taskinfo')).glob('*.pkl')]


def load_ste_data(task_name: str) -> pd.DataFrame:
    """Loads the STE data corresponding to the given task name.

    This function searches $L2DATA/taskinfo/ for the given task name and reads the file as a
    DataFrame.

    Args:
        task_name (str): The name of the STE data file.

    Returns:
        pd.DataFrame: The STE data if found, else None.
    """

    if task_name in get_ste_data_names():
        data_file_name = get_l2root_base_dirs('taskinfo', task_name + '.pkl')
        dataframe = pd.read_pickle(data_file_name)
        return dataframe
    else:
        return None


def save_ste_data(log_dir: str) -> None:
    """Saves the STE data in the given log directory as a pickled DataFrame.

    Args:
        log_dir (str): The log directory of the STE data.

    Raises:
        Exception: If scenario contains more than one task.
    """

    # Load data from ste logs
    ste_data = read_log_data(log_dir)

    # Get metric fields
    metric_fields = read_logger_info(log_dir)

    # Validate data format
    validate_log(ste_data, metric_fields)

    # Fill in regime number and sort
    ste_data = fill_regime_num(ste_data)
    ste_data = ste_data.sort_values(by=['regime_num', 'exp_num']).set_index("regime_num", drop=False)

    # Filter out training only data
    ste_data = ste_data[ste_data['block_type'] == 'train']

    # Get task name
    task_name = ste_data.task_name.unique()

    # Check for number of tasks in scenario
    if task_name.size != 1:
        raise Exception('Scenario contains more than one task')

    # Create task info directory if it doesn't exist
    if not os.path.exists(get_l2root_base_dirs('taskinfo')):
        os.makedirs(get_l2root_base_dirs('taskinfo'))

    # Get base directory to store ste data
    filename = get_l2root_base_dirs('taskinfo', task_name[0] + '.pkl')

    # Store ste data in task info directory
    ste_data.to_pickle(filename)

    print(f'Stored STE data for {task_name[0]}')


def plot_performance(dataframe: pd.DataFrame, block_info: pd.DataFrame, do_smoothing: bool = False,
                     col_to_plot: str = 'reward', x_axis_col: str = 'exp_num', input_title: str = None,
                     do_save_fig: bool = True, plot_filename: str = None, input_xlabel: str = 'Episodes',
                     input_ylabel: str = 'Performance', show_block_boundary: bool = True,
                     shade_test_blocks: bool = True, window_len: int = None) -> None:
    """Plots the performance curves for the given DataFrame.

    Args:
        dataframe (pd.DataFrame): The performance data to plot.
        block_info (pd.DataFrame): The block info of the DataFrame.
        do_smoothing (bool, optional): Flag for enabling smoothing. Defaults to False.
        col_to_plot (str, optional): The column name of the metric to plot. Defaults to 'reward'.
        x_axis_col (str, optional): The column name of the x-axis data. Defaults to 'exp_num'.
        input_title (str, optional): The title of the plot. Defaults to None.
        do_save_fig (bool, optional): Flag for enabling saving figure. Defaults to True.
        plot_filename (str, optional): The filename to use for saving. Defaults to None.
        input_xlabel (str, optional): The x-axis label. Defaults to 'Episodes'.
        input_ylabel (str, optional): The y-axis label. Defaults to 'Performance'.
        show_block_boundary (bool, optional): Flag for enabling block boundaries. Defaults to True.
        shade_test_blocks (bool, optional): Flag for enabling block shading. Defaults to True.
        window_len (int, optional): The window length for smoothing the data. Defaults to None.
    """

    unique_tasks = dataframe.loc[:, 'task_name'].unique()
    fig = plt.figure(figsize=(12, 6))
    ax = fig.add_subplot(111)

    color_selection = ['blue', 'green', 'red', 'black', 'magenta', 'cyan', 'orange', 'purple']
    if len(unique_tasks) < len(color_selection):
        task_colors = color_selection[:len(unique_tasks)]
    else:
        task_colors = [color_selection[i % len(color_selection)] for i in range(unique_tasks)]

    for c, t in zip(task_colors, unique_tasks):
        for regime in block_info['regime_num']:
            if block_info.loc[regime, :]['task_name'] == t:
                x = dataframe.loc[(dataframe['task_name'] == t) & (
                    dataframe['regime_num'] == regime), x_axis_col].values
                y = dataframe.loc[(dataframe['task_name'] == t) & (
                    dataframe['regime_num'] == regime), col_to_plot].values

                if do_smoothing:
                    y = _localutil.smooth(y, window_len=window_len)

                ax.scatter(x, y, color=c, marker='*', linestyle='None', label=t)

    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = OrderedDict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys())

    if show_block_boundary:
        unique_blocks = dataframe.loc[:, 'regime_num'].unique()
        df2 = dataframe.set_index("exp_num", drop=False)
        for b in unique_blocks:
            idx = df2[df2['regime_num'] == b].index[0]
            ax.axes.axvline(idx, linewidth=1, linestyle=':')

    if shade_test_blocks:
        blocks = dataframe.loc[:, ['block_num', 'block_type']].drop_duplicates()
        df2 = dataframe.set_index("exp_num", drop=False)

        for _, block in blocks.iterrows():
            if block['block_type'] == 'test':
                df3 = df2[(df2['block_num'] == block['block_num']) &
                          (df2['block_type'] == block['block_type'])]
                x1 = df3.index[0]
                x2 = df3.index[-1]
                ax.axvspan(x1, x2, alpha=0.1, color='black')

    if os.path.dirname(input_title) != "":
        _, plot_filename = os.path.split(input_title)
        input_title = plot_filename
    else:
        plot_filename = input_title

    # Want the saved figured to have a grid so do this before saving
    ax.set(xlabel=input_xlabel, ylabel=input_ylabel, title=input_title)
    ax.grid()

    if do_save_fig:
        if not plot_filename and not input_title:
            plot_filename = 'plot.png'

        print(f'Saving figure with name: {plot_filename.replace(" ", "_")}')

        fig.savefig(plot_filename.replace(" ", "_"))
    else:
        plt.show()
