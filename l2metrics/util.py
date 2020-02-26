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

import pandas as pd
import os
import json
from learnkit.data_util.utils import get_l2data_root
import matplotlib.pyplot as plt
from . import _localutil


def get_l2root_base_dirs(directory_to_append, sub_to_get=None):
    # This function uses a learnkit utility function to get the base $L2DATA path and goes one level down, with the
    # option to return the path string for the directory or the file underneath:
    # e.g. $L2DATA/logs/some_log_directory
    # or   $L2DATA/taskinfo/info.json
    file_info_to_return = os.path.join(get_l2data_root(), directory_to_append)

    if sub_to_get:
        base_dir = file_info_to_return
        file_info_to_return = os.path.join(base_dir, sub_to_get)

    return file_info_to_return


def load_chance_data():
    # This function will return a dictionary of "chance" definitions for all of the available classification tasks
    # stored in this JSON file, located at $L2DATA/taskinfo/chance.json
    json_file = get_l2root_base_dirs('taskinfo', 'chance.json')

    # Load the defaults from the json file, return them as a dictionary
    with open(json_file) as f:
        chance_dict = json.load(f)

    return chance_dict


def load_default_ste_data():
    # This function will return a dictionary of the Single-Task-Expert data from all of the available single task
    # baselines that have been stored in this JSON file, located at $L2DATA/taskinfo/info.json
    json_file = get_l2root_base_dirs('taskinfo', 'info.json')

    # Load the defaults from the json file, return them as a dictionary
    with open(json_file) as f:
        ste_dict = json.load(f)

    return ste_dict


def load_default_random_agent_data():
    # This function will return a dictionary of the Random Agent data from all of the available baselines that have \
    # been stored in this JSON file, located at $L2DATA/taskinfo/random_agent.json
    json_file = get_l2root_base_dirs('taskinfo', 'random_agent.json')

    # Load the defaults from the json file, return them as a dictionary
    with open(json_file) as f:
        random_agent_dict = json.load(f)

    return random_agent_dict


def plot_performance(dataframe, do_smoothing=True, col_to_plot='reward', x_axis_col='task', input_title=None,
                     do_save_fig=False, plot_filename=None, input_xlabel='Episodes', input_ylabel='Performance',
                     show_block_boundary=False, do_task_colors=False, new_smoothing_value=None):
    # This function takes a dataframe and plots the desired columns. Has an option to save the figure in the current
    # directory and/or customize the title, axes labeling, filename, etc. Color is supported for agent tasks only.

    if do_task_colors:
        color_selection = ['blue', 'green', 'red', 'black', 'magenta', 'cyan', 'orange', 'purple']
        unique_tasks = dataframe.loc[:, 'class_name'].unique()
        if len(unique_tasks) < len(color_selection):
            task_colors = color_selection[:len(unique_tasks)]
        else:
            task_colors = [color_selection[i % len(color_selection)] for i in range(unique_tasks)]
        fig = plt.figure(figsize=(12, 6))
        ax = fig.add_subplot(111)

        for c, t in zip(task_colors, unique_tasks):
            data = dataframe.loc[dataframe['class_name'] == t, col_to_plot].values
            x_axis = dataframe.loc[dataframe['class_name'] == t, x_axis_col].values
            if do_smoothing:
                if new_smoothing_value:
                    data = _localutil.smooth(data, window_len=new_smoothing_value)
                else:
                    data = _localutil.smooth(data)
            ax.scatter(x_axis, data, color=c, marker='*', linestyle='None')
    else:
        data = dataframe[col_to_plot].values
        if do_smoothing:
            if new_smoothing_value:
                data = _localutil.smooth(data, window_len=new_smoothing_value)
            else:
                data = _localutil.smooth(data)
        x_axis = dataframe[x_axis_col].values

        fig = plt.figure(figsize=(8, 4))
        ax = fig.add_subplot(111)
        ax.scatter(x_axis, data, marker='*', linestyle='None')

    if show_block_boundary:
        unique_blocks = dataframe.loc[:, 'block'].unique()
        df2 = dataframe.set_index("task", drop=False)
        for b in unique_blocks:
            idx = df2[df2['block'] == b].index[0]
            ax.axes.axvline(idx, linewidth=1, linestyle=':')

    # Want the saved figured to have a grid so do this before saving
    ax.set(xlabel=input_xlabel, ylabel=input_ylabel, title=input_title)
    ax.grid()

    if do_save_fig:
        if not plot_filename:
            if not input_title:
                plot_filename = 'plot.png'
            else:
                plot_filename = input_title

        fig.savefig(plot_filename)

    # TODO: This is a blocking call. Perhaps better to just save by default and not show?
    # plt.show()


def read_log_data(input_dir, analysis_variables=None):
    # This function scrapes the TSV files containing syllabus metadata and system performance log data and returns a
    # pandas dataframe with the merged data
    logs = None
    blocks = None
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if file == 'data-log.tsv':
                has_data = True
                task = os.path.split(root)[-1]
                if analysis_variables is not None:
                    df = pd.read_csv(os.path.join(root, file), sep='\t')[
                        ['timestamp', 'class_name', 'phase', 'worker', 'block', 'task', 'seed'] + analysis_variables]
                else:
                    df = pd.read_csv(os.path.join(root, file), sep='\t')
                if logs is None:
                    logs = df
                else:
                    logs = pd.concat([logs, df])
            if file == 'block-report.tsv':
                df = pd.read_csv(os.path.join(root, file), sep='\t')
                if blocks is None:
                    blocks = df
                else:
                    blocks = pd.concat([blocks, df])

    return logs.merge(blocks, on=['phase', 'class_name', 'worker', 'block'])
