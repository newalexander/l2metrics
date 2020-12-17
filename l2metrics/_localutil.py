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

from typing import Tuple

import numpy as np
import pandas as pd


def smooth(x: np.ndarray, window_len: int = None, window: str = 'hanning') -> np.ndarray:
    # """smooth the data using a window with requested size.
    # Code from https://scipy-cookbook.readthedocs.io/items/SignalSmooth.html
    # This method is based on the convolution of a scaled window with the signal.
    # The signal is prepared by introducing reflected copies of the signal
    # (with the window size) in both ends so that transient parts are minimized
    # in the beginning and end part of the output signal.
    # input:
    #    x: the input signal
    #    window_len: the dimension of the smoothing window
    #    window: the type of window from 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'
    #        flat window will produce a moving average smoothing.
    # output:
    #    the smoothed signal
    # example:
    # t=linspace(-2,2,0.1)
    # x=sin(t)+randn(len(t))*0.1
    # y=smooth(x)
    # see also:
    # numpy.hanning, numpy.hamming, numpy.bartlett, numpy.blackman, numpy.convolve
    # scipy.signal.lfilter
    # NOTE: length(output) != length(input), to correct this: return
    # y[(window_len/2-1):-(window_len/2)] instead of just y.

    if x.ndim != 1:
        raise ValueError("smooth only accepts 1 dimension arrays.")

    if window_len is None or x.size < window_len:
        # raise(ValueError, "Input vector needs to be bigger than window size.")
        window_len = min(int(x.size * 0.2), 100)

    if window_len < 3:
        return x

    if window not in ['flat', 'hanning', 'hamming', 'bartlett', 'blackman']:
        raise ValueError("Window is one of 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'")

    s = np.r_[x[window_len - 1:0:-1], x, x[-2:-window_len - 1:-1]]

    if window == 'flat':  # moving average
        w = np.ones(window_len, 'd')
    else:
        w = eval('np.' + window + '(window_len)')

    y = np.convolve(w / w.sum(), s, mode='valid')

    # Changed to return output of same length as input
    start_ind = int(np.floor(window_len/2-1))
    end_ind = -int(np.ceil(window_len/2))
    return y[start_ind:end_ind]


def get_block_saturation_perf(data: pd.DataFrame, col_to_use: str, prev_sat_val: float = None,
                              window_len: int = None) -> Tuple[float, int, int]:
    # Calculate the "saturation" value
    # Calculate the number of episodes to "saturation"

    mean_reward_per_episode = data.loc[:, ['exp_num', col_to_use]].groupby('exp_num').mean()
    mean_data = np.ravel(mean_reward_per_episode.values)

    # Take the moving average of the mean of the per episode reward
    smoothed_data = smooth(mean_data, window_len=window_len, window='flat')
    saturation_value = np.nanmax(smoothed_data)

    # Calculate the number of episodes to "saturation", which we define as the max of the moving average
    inds = np.where(smoothed_data == saturation_value)
    episodes_to_saturation = inds[0][0]
    episodes_to_recovery = len(data) + 1

    if prev_sat_val:
        inds = np.where(smoothed_data >= prev_sat_val)
        if len(inds[0]):
            episodes_to_recovery = inds[0][0]

    return saturation_value, episodes_to_saturation, episodes_to_recovery


def get_terminal_perf(data: pd.DataFrame, col_to_use: str, prev_val: float = None,
                      do_smoothing: bool = True, window_len: int = None,
                      term_window_ratio: float = 0.1) -> Tuple[float, int, int]:
    # Calculate the terminal performance value
    # Calculate the number of episodes to terminal performance

    mean_reward_per_episode = data.loc[:, ['exp_num', col_to_use]].groupby('exp_num').mean()
    mean_data = np.ravel(mean_reward_per_episode.values)

    # Take the moving average of the mean of the per episode reward
    if do_smoothing:
        mean_data = smooth(mean_data, window_len=window_len, window='flat')

    terminal_value = np.mean(mean_data[int((1-term_window_ratio)*mean_data.size):])

    # Calculate the number of episodes to terminal performance
    episodes_to_terminal_perf = int((1-(term_window_ratio/2))*mean_data.size)

    # Initialize recovery time to one more than number of learning experiences in the data
    episodes_to_recovery = len(data) + 1

    if prev_val is not None:
        inds = np.where(mean_data >= prev_val)
        if len(inds[0]):
            episodes_to_recovery = inds[0][0]

    return terminal_value, episodes_to_terminal_perf, episodes_to_recovery


def fill_metrics_df(metric: dict, metric_string_name: str, metrics_df: pd.DataFrame, dict_key: str = None) -> pd.DataFrame:
    if not dict_key:
        metrics_df[metric_string_name] = np.full_like(metrics_df['regime_num'], np.nan, dtype=np.double)
        for idx in metric.keys():
            metrics_df.loc[idx, metric_string_name] = metric[idx]
    else:
        metrics_df[dict_key][metric_string_name] = np.full_like(metrics_df[dict_key]['regime_num'], np.nan, dtype=np.double)
        for idx in metric.keys():
            metrics_df[dict_key].loc[idx, metric_string_name] = metric[idx]

    return metrics_df


def get_simple_rl_task_names(task_names: list) -> list:
    simple_names = []

    for t in task_names:
        splits = str.split(t, '_')
        simple_names.append(splits[-1])

    return simple_names
