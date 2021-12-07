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

import json
from functools import reduce
from typing import List, Set, Tuple, Union

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


class MetricsParser:
    dfs = None
    df_tsv = None

    def __init__(self, file_name, tsv: bool = False) -> None:
        if tsv:
            self.df_tsv = pd.read_csv(file_name, sep='\t')
        else:
            with open(file_name) as file:
                self.data = json.load(file)
            self.dfs = [pd.DataFrame(self.json_refactor(run_num))
                        for run_num in self.data]

    def toXL(self) -> None:
        for idx, df in enumerate(self.dfs):
            df.to_excel(str(idx)+'.xlsx', header=True)

    def listflatten(self, l: list) -> List:
        flat = []
        for subl in l:
            if isinstance(subl, list):
                flat += subl
            elif isinstance(subl, float) or isinstance(subl, int):
                flat.append(subl)
            else:
                flat.append(None)
        return flat
        # return [item for subl in l if subl for item in subl else None]

    def dictflatten(self, d: list) -> Tuple[Set, dict]:
        graph_titles = set()
        for d1 in d:
            if d1:
                graph_titles.update(list(d1.keys()))
        graph_data = {k: [] for k in graph_titles}
        for d1 in d:
            if d1:
                for k in d1:
                    if isinstance(d1[k], dict):
                        graph_data[k].append(list(d1[k].values()))
                    elif isinstance(d1[k], list):
                        graph_data[k] += d1[k]
                    else:
                        graph_data[k].append(d1[k])
        return graph_titles, graph_data

    def json_refactor(self, json: dict, parent: str = "root") -> dict:
        new_dict = {}
        for k, v in json.items():
            if isinstance(v, dict):
                for k1, v1 in self.json_refactor(v, parent=k).items():
                    if isinstance(k1, tuple):
                        if isinstance(v1, list) and len(v1) != 1:
                            new_dict[tuple([parent])+k1] = [v1]
                        else:
                            new_dict[tuple([parent])+k1] = v1
                    else:
                        if isinstance(v1, list) and len(v1) != 1:
                            new_dict[(parent, k1)] = [v1]
                        else:
                            new_dict[(parent, k1)] = v1
            else:
                new_dict[(parent, k)] = v
        return new_dict

    # sourced from stackoverflow
    # link: https://stackoverflow.com/questions/7204805/how-to-merge-dictionaries-of-dictionaries
    def mergedict(self, a, b, path=None) -> dict:
        if path is None:
            path = []
        for key in b:
            if key in a:
                if isinstance(a[key], dict) and isinstance(b[key], dict):
                    self.mergedict(a[key], b[key], path + [str(key)])
                # elif a[key] == b[key]:
                #     pass # same leaf value
                # else:
                    # raise Exception('Conflict at %s' % '.'.join(path + [str(key)]))
            else:
                a[key] = b[key]
        return a

    def plotLine(self, data: list) -> None:
        sns.lineplot(x=range(len(data)), y=data)

    def plotHist(self, data: list) -> None:
        sns.histplot(data)

    def plotDist(self, data: list) -> None:
        sns.distplot(data)

    # -----------------------------------------------------
    # JSON methods

    def df2dict_helper(self, key: list, val: any) -> dict:
        new_dict = {}
        if len(key) == 1:
            new_dict[key[0]] = val[0]
        else:
            new_dict[key[0]] = self.df2dict_helper(key[1:], val)
        return new_dict

    def df2dict(self, df: pd.DataFrame) -> dict:
        pre_new_dict = []
        # print(df.columns)
        for col in df.columns:
            val = df[col]
            newcol = [x for x in list(col) if x == x] if isinstance(
                col, tuple) else [col]
            if newcol[0] == 'root':
                newcol.pop(0)
            pre_new_dict.append(self.df2dict_helper(newcol, val))
        # pprint.pprint(pre_new_dict)
        return reduce(self.mergedict, pre_new_dict,)

    def getNormalizationDataRange_helper(self, df: pd.DataFrame, task: str = None) -> Union[dict, Tuple[int, int]]:
        # print(type(df),df.root)
        try:
            if task is None:
                return self.df2dict(df.root.normalization_data_range)
            else:
                return df.root.normalization_data_range[task]["min"].iloc[0, 0], df.root.normalization_data_range[task]["max"].iloc[0, 0]
        except (KeyError, AttributeError) as e:
            pass

    def getNormalizationDataRange(self, task: str = None) -> List[Union[dict, Tuple[int, int]]]:
        return [self.getNormalizationDataRange_helper(run, task) for run in self.dfs]

    # possible types: 'hist','dist','line'
    def plotNormalizationDataRange(self, plottype: str, task: str = None):
        if task:
            # normdatrange = self.flatten(self.getNormalizationDataRange(task))
            normdatrange = [x for x in self.getNormalizationDataRange(task) if x]
            fig, ax = plt.subplots(1, 2, figsize=(18, 10))
            if plottype == 'hist':
                sns.histplot([min for min, _ in normdatrange], ax=ax[0]).set(title='Min')
                sns.histplot([max for _, max in normdatrange], ax=ax[1]).set(title='Max')
            elif plottype == 'dist':
                sns.distplot([min for min, _ in normdatrange], ax=ax[0]).set(title='Min')
                sns.distplot([max for _, max in normdatrange], ax=ax[1]).set(title='Max')
            elif plottype == 'line':
                sns.lineplot(data=[min for min, _ in normdatrange], ax=ax[0]).set(title='Min')
                sns.lineplot(data=[max for _, max in normdatrange], ax=ax[1]).set(title='Max')
        else:
            normdatrange = [x for x in self.getNormalizationDataRange(task) if x]
            graph_titles, graph_data = self.dictflatten(normdatrange)
            fig, ax = plt.subplots(len(graph_titles), 2, figsize=(18, 30))
            if plottype == 'hist':
                i = 0
                for k, v in graph_data.items():
                    sns.histplot([min for min, _ in v], ax=ax[i][0]).set(title=k+' Min')
                    sns.histplot([max for _, max in v], ax=ax[i][1]).set(title=k+' Max')
                    i += 1
            elif plottype == 'dist':
                i = 0
                for k, v in graph_data.items():
                    sns.distplot([min for min, _ in v], ax=ax[i][0]).set(title=k+' Min')
                    sns.distplot([max for _, max in v], ax=ax[i][1]).set(title=k+' Max')
                    i += 1
            elif plottype == 'line':
                i = 0
                for k, v in graph_data.items():
                    sns.lineplot(data=[min for min, _ in v], ax=ax[i][0]).set(title=k+' Min')
                    sns.lineplot(data=[max for _, max in v], ax=ax[i][1]).set(title=k+' Max')
                    i += 1

    def getBackwardTransferRatio_helper(self, df: pd.DataFrame, taska: str = None, taskb: str = None) -> Union[int, dict, list]:
        try:
            if taska is None:
                return df.root.backward_transfer_ratio.iloc[0, 0]
            elif taskb is None:
                return self.df2dict(df.root.task_metrics[taska].backward_transfer_ratio)
            else:
                return df.root.task_metrics[taska].backward_transfer_ratio[taskb].tolist()
        except (KeyError, AttributeError) as e:
            pass

    def getBackwardTransferRatio(self, taska: str = None, taskb: str = None) -> List[Union[int, dict, list]]:
        return [self.getBackwardTransferRatio_helper(run, taska, taskb) for run in self.dfs]

    def plotBackwardTransferRatio(self, plottype: str, taska: str = None, taskb: str = None):
        if taska is None:
            graph_data = [x for x in self.getBackwardTransferRatio() if x]
            fig, ax = plt.subplots(1, 1, figsize=(10, 5))
            if plottype == 'hist':
                sns.histplot([x for x in graph_data], ax=ax)
            elif plottype == 'dist':
                sns.distplot([x for x in graph_data], ax=ax)
            elif plottype == 'line':
                sns.lineplot(data=[x for x in graph_data], ax=ax)
        elif taskb is None:
            graph_titles, graph_data = self.dictflatten(
                [x for x in self.getBackwardTransferRatio(taska) if x])
            # print(graph_titles,graph_data)
            fig, ax = plt.subplots(len(graph_titles), 1, figsize=(18, 5))
            if plottype == 'hist':
                i = 0
                for k, v in graph_data.items():
                    sns.histplot(list(v), ax=ax[i]).set(title=k)
                    i += 1
            elif plottype == 'dist':
                i = 0
                for k, v in graph_data.items():
                    sns.distplot(list(v), ax=ax[i]).set(title=k)
                    i += 1
            elif plottype == 'line':
                i = 0
                for k, v in graph_data.items():
                    sns.lineplot(data=list(v), ax=ax[i]).set(title=k)
                    i += 1
        else:
            graph_data = self.listflatten(
                [x for x in self.getBackwardTransferRatio(taska, taskb) if x])
            fig, ax = plt.subplots(1, 1, figsize=(10, 5))
            if plottype == 'hist':
                sns.histplot([x for x in graph_data], ax=ax)
            elif plottype == 'dist':
                sns.distplot([x for x in graph_data], ax=ax)
            elif plottype == 'line':
                sns.lineplot(data=[x for x in graph_data], ax=ax)

    def getForwardTransferRatio_helper(self, df: pd.DataFrame, taska: str = None, taskb: str = None) -> Union[int, dict, list]:
        try:
            if taska is None:
                return df.root.forward_transfer_ratio.iloc[0, 0]
            elif taskb is None:
                return self.df2dict(df.root.task_metrics[taska].forward_transfer_ratio)
            else:
                return df.root.task_metrics[taska].forward_transfer_ratio[taskb].tolist()[0]
        except (KeyError, AttributeError) as e:
            pass

    def getForwardTransferRatio(self, taska: str = None, taskb: str = None) -> List[Union[int, dict, list]]:
        return [self.getForwardTransferRatio_helper(run, taska, taskb) for run in self.dfs]

    def plotForwardTransferRatio(self, plottype: str, taska: str = None, taskb: str = None):
        if taska is None:
            graph_data = [x for x in self.getForwardTransferRatio() if x]
            fig, ax = plt.subplots(1, 1, figsize=(10, 5))
            if plottype == 'hist':
                sns.histplot([x for x in graph_data], ax=ax)
            elif plottype == 'dist':
                sns.distplot([x for x in graph_data], ax=ax)
            elif plottype == 'line':
                sns.lineplot(data=[x for x in graph_data], ax=ax)
        elif taskb is None:
            graph_titles, graph_data = self.dictflatten(
                [x for x in self.getForwardTransferRatio(taska) if x])
            # print(graph_titles,graph_data)
            fig, ax = plt.subplots(len(graph_titles), 1, figsize=(18, 5))
            if plottype == 'hist':
                i = 0
                for k, v in graph_data.items():
                    sns.histplot(list(v), ax=ax[i]).set(title=k)
                    i += 1
            elif plottype == 'dist':
                i = 0
                for k, v in graph_data.items():
                    sns.distplot(list(v), ax=ax[i]).set(title=k)
                    i += 1
            elif plottype == 'line':
                i = 0
                for k, v in graph_data.items():
                    sns.lineplot(list(v), ax=ax[i]).set(title=k)
                    i += 1
        else:
            graph_data = self.listflatten(
                [x for x in self.getForwardTransferRatio(taska, taskb) if x])
            fig, ax = plt.subplots(1, 1, figsize=(10, 5))
            if plottype == 'hist':
                sns.histplot([x for x in graph_data], ax=ax)
            elif plottype == 'dist':
                sns.distplot([x for x in graph_data], ax=ax)
            elif plottype == 'line':
                sns.lineplot(data=[x for x in graph_data], ax=ax)

    def getBackwardTransferContrast_helper(self, df: pd.DataFrame, taska: str = None, taskb: str = None) -> Union[int, dict, list]:
        try:
            if taska is None:
                return df.root.backward_transfer_contrast.iloc[0, 0]
            elif taskb is None:
                return self.df2dict(df.root.task_metrics[taska].backward_transfer_contrast)
            else:
                return df.root.task_metrics[taska].backward_transfer_contrast[taskb].tolist()[0]
        except (KeyError, AttributeError) as e:
            pass

    def getBackwardTransferContrast(self, taska: str = None, taskb: str = None) -> List[Union[int, dict, list]]:
        return [self.getBackwardTransferContrast_helper(run, taska, taskb) for run in self.dfs]

    def plotBackwardTransferContrast(self, plottype: str, taska: str = None, taskb: str = None):
        if taska is None:
            graph_data = [x for x in self.getBackwardTransferContrast() if x]
            fig, ax = plt.subplots(1, 1, figsize=(10, 5))
            if plottype == 'hist':
                sns.histplot([x for x in graph_data], ax=ax)
            elif plottype == 'dist':
                sns.distplot([x for x in graph_data], ax=ax)
            elif plottype == 'line':
                sns.lineplot(data=[x for x in graph_data], ax=ax)
        elif taskb is None:
            graph_titles, graph_data = self.dictflatten(
                [x for x in self.getBackwardTransferContrast(taska) if x])
            # print(graph_titles,graph_data)
            fig, ax = plt.subplots(len(graph_titles), 1, figsize=(18, 5))
            if plottype == 'hist':
                i = 0
                for k, v in graph_data.items():
                    sns.histplot(list(v), ax=ax[i]).set(title=k)
                    i += 1
            elif plottype == 'dist':
                i = 0
                for k, v in graph_data.items():
                    sns.distplot(list(v), ax=ax[i]).set(title=k)
                    i += 1
            elif plottype == 'line':
                i = 0
                for k, v in graph_data.items():
                    sns.lineplot(list(v), ax=ax[i]).set(title=k)
                    i += 1
        else:
            graph_data = self.listflatten(
                [x for x in self.getBackwardTransferContrast(taska, taskb) if x])
            fig, ax = plt.subplots(1, 1, figsize=(10, 5))
            if plottype == 'hist':
                sns.histplot([x for x in graph_data], ax=ax)
            elif plottype == 'dist':
                sns.distplot([x for x in graph_data], ax=ax)
            elif plottype == 'line':
                sns.lineplot(data=[x for x in graph_data], ax=ax)

    def getForwardTransferContrast_helper(self, df: pd.DataFrame, taska: str = None, taskb: str = None) -> Union[int, dict, list]:
        try:
            if taska is None:
                return df.root.forward_transfer_contrast.iloc[0, 0]
            elif taskb is None:
                return self.df2dict(df.root.task_metrics[taska].forward_transfer_contrast)
            else:
                return df.root.task_metrics[taska].forward_transfer_contrast[taskb].tolist()[0]
        except (KeyError, AttributeError) as e:
            pass

    def getForwardTransferContrast(self, taska: str = None, taskb: str = None) -> List[Union[int, dict, list]]:
        return [self.getForwardTransferContrast_helper(run, taska, taskb) for run in self.dfs]

    def plotForwardTransferContrast(self, plottype: str, taska: str = None, taskb: str = None):
        if taska is None:
            graph_data = [x for x in self.getForwardTransferContrast() if x]
            fig, ax = plt.subplots(1, 1, figsize=(10, 5))
            if plottype == 'hist':
                sns.histplot([x for x in graph_data], ax=ax)
            elif plottype == 'dist':
                sns.distplot([x for x in graph_data], ax=ax)
            elif plottype == 'line':
                sns.lineplot(data=[x for x in graph_data], ax=ax)
        elif taskb is None:
            graph_titles, graph_data = self.dictflatten(
                [x for x in self.getForwardTransferContrast(taska) if x])
            # print(graph_titles,graph_data)
            fig, ax = plt.subplots(len(graph_titles), 1, figsize=(18, 5))
            if plottype == 'hist':
                i = 0
                for k, v in graph_data.items():
                    sns.histplot(list(v), ax=ax[i]).set(title=k)
                    i += 1
            elif plottype == 'dist':
                i = 0
                for k, v in graph_data.items():
                    sns.distplot(list(v), ax=ax[i]).set(title=k)
                    i += 1
            elif plottype == 'line':
                i = 0
                for k, v in graph_data.items():
                    sns.lineplot(list(v), ax=ax[i]).set(title=k)
                    i += 1
        else:
            graph_data = self.listflatten(
                [x for x in self.getForwardTransferContrast(taska, taskb) if x])
            fig, ax = plt.subplots(1, 1, figsize=(10, 5))
            if plottype == 'hist':
                sns.histplot([x for x in graph_data], ax=ax)
            elif plottype == 'dist':
                sns.distplot([x for x in graph_data], ax=ax)
            elif plottype == 'line':
                sns.lineplot(data=[x for x in graph_data], ax=ax)

    def getMaintenanceValMRLEP_helper(self, df: pd.DataFrame, task: str) -> list:
        try:
            if task is None:
                return [df.root.task_metrics[t].maintenance_val_mrlep.iloc[0, 0] for t in self.getUniqueTaskNames()]
            else:
                return df.root.task_metrics[task].maintenance_val_mrlep.iloc[0, 0]
        except (KeyError, AttributeError) as e:
            pass

    def getMaintenanceValMRLEP(self, task: str) -> List[list]:
        return list(filter(None, [self.getMaintenanceValMRLEP_helper(run, task) for run in self.dfs]))

    def plotMaintenanceValMRLEP(self, plottype: str, task: str):
        graph_data = self.listflatten(
            [x for x in self.getMaintenanceValMRLEP(task) if x])
        fig, ax = plt.subplots(1, 1, figsize=(10, 5))
        if plottype == 'hist':
            sns.histplot([x for x in graph_data], ax=ax)
        elif plottype == 'dist':
            sns.distplot([x for x in graph_data], ax=ax)
        elif plottype == 'line':
            sns.lineplot(data=[x for x in graph_data], ax=ax)

    def getMaintenanceValMRTLP_helper(self, df: pd.DataFrame, task: str) -> list:
        try:
            if task is None:
                return [df.root.task_metrics[t].maintenance_val_mrtlp.iloc[0, 0] for t in self.getUniqueTaskNames()]
            else:
                return df.root.task_metrics[task].maintenance_val_mrtlp.iloc[0, 0]
        except (KeyError, AttributeError) as e:
            pass

    def getMaintenanceValMRTLP(self, task: str) -> List[list]:
        return [self.getMaintenanceValMRTLP_helper(run, task) for run in self.dfs]

    def plotMaintenanceValMRTLP(self, plottype: str, task: str):
        graph_data = self.listflatten(
            [x for x in self.getMaintenanceValMRTLP(task) if x])
        fig, ax = plt.subplots(1, 1, figsize=(10, 5))
        if plottype == 'hist':
            sns.histplot([x for x in graph_data], ax=ax)
        elif plottype == 'dist':
            sns.distplot([x for x in graph_data], ax=ax)
        elif plottype == 'line':
            sns.lineplot(data=[x for x in graph_data], ax=ax)

    def getRecoveryTimes_helper(self, df: pd.DataFrame, task: str) -> list:
        try:
            if task is None:
                return [df.root.task_metrics[t].recovery_times.iloc[0, 0] for t in self.getUniqueTaskNames()]
            else:
                return df.root.task_metrics[task].recovery_times.iloc[0, 0]
        except (KeyError, AttributeError) as e:
            pass

    def getRecoveryTimes(self, task: str = None) -> List[list]:
        return self.listflatten([self.getRecoveryTimes_helper(run, task) for run in self.dfs])

    def plotRecoveryTimes(self, plottype: str, task: str = None):
        graph_data = self.listflatten(
            [x for x in self.getRecoveryTimes(task) if x])
        fig, ax = plt.subplots(1, 1, figsize=(10, 5))
        if plottype == 'hist':
            sns.histplot([x for x in graph_data], ax=ax)
        elif plottype == 'dist':
            sns.distplot([x for x in graph_data], ax=ax)
        elif plottype == 'line':
            sns.lineplot(data=[x for x in graph_data], ax=ax)

    def getPerfRecoveryRate_helper(self, df: pd.DataFrame, task: str = None) -> int:
        try:
            if task is None:
                return df.root.perf_recovery.iloc[0, 0]
            else:
                return df.root.task_metrics[task].perf_recovery.iloc[0, 0]
        except (KeyError, AttributeError) as e:
            pass

    def getPerfRecoveryRate(self, task: str = None) -> List[int]:
        return [self.getPerfRecoveryRate_helper(run, task) for run in self.dfs]

    def plotPerfRecoveryRate(self, plottype: str, task: str = None):
        graph_data = [x for x in self.getPerfRecoveryRate(task) if x]
        fig, ax = plt.subplots(1, 1, figsize=(10, 5))
        if plottype == 'hist':
            sns.histplot([x for x in graph_data], ax=ax)
        elif plottype == 'dist':
            sns.distplot([x for x in graph_data], ax=ax)
        elif plottype == 'line':
            sns.lineplot(data=[x for x in graph_data], ax=ax)

    def getPerfMaintenanceMRLEP_helper(self, df: pd.DataFrame, task: str = None) -> int:
        try:
            if task is None:
                return df.root.perf_maintenance_mrlep.iloc[0, 0]
            else:
                return df.root.task_metrics[task].perf_maintenance_mrlep.iloc[0, 0]
        except (KeyError, AttributeError) as e:
            pass

    def getPerfMaintenanceMRLEP(self, task: str = None) -> List[int]:
        return [self.getPerfMaintenanceMRLEP_helper(run, task) for run in self.dfs]

    def plotPerfMaintenanceMRLEP(self, plottype: str, task: str = None):
        graph_data = [x for x in self.getPerfMaintenanceMRLEP(task) if x]
        fig, ax = plt.subplots(1, 1, figsize=(10, 5))
        if plottype == 'hist':
            sns.histplot([x for x in graph_data], ax=ax)
        elif plottype == 'dist':
            sns.distplot([x for x in graph_data], ax=ax)
        elif plottype == 'line':
            sns.lineplot(data=[x for x in graph_data], ax=ax)

    def getPerfMaintenanceMRTLP_helper(self, df: pd.DataFrame, task: str = None) -> int:
        try:
            if task is None:
                return df.root.perf_maintenance_mrtlp.iloc[0, 0]
            else:
                return df.root.task_metrics[task].perf_maintenance_mrtlp.iloc[0, 0]
        except (KeyError, AttributeError) as e:
            pass

    def getPerfMaintenanceMRTLP(self, task: str = None) -> List[int]:
        return [self.getPerfMaintenanceMRTLP_helper(run, task) for run in self.dfs]

    def plotPerfMaintenanceMRTLP(self, plottype: str, task: str = None):
        graph_data = [x for x in self.getPerfMaintenanceMRTLP(task) if x]
        fig, ax = plt.subplots(1, 1, figsize=(10, 5))
        if plottype == 'hist':
            sns.histplot([x for x in graph_data], ax=ax)
        elif plottype == 'dist':
            sns.distplot([x for x in graph_data], ax=ax)
        elif plottype == 'line':
            sns.lineplot(data=[x for x in graph_data], ax=ax)

    def getSTERelPerf_helper(self, df: pd.DataFrame, task: str = None) -> int:
        try:
            if task is None:
                return df.root.ste_rel_perf.iloc[0, 0]
            else:
                return df.root.task_metrics[task].ste_rel_perf.iloc[0, 0]
        except (KeyError, AttributeError) as e:
            pass

    def getSTERelPerf(self, task: str = None) -> List[int]:
        return [self.getSTERelPerf_helper(run, task) for run in self.dfs]

    def plotSTERelPerf(self, plottype: str, task: str = None):
        graph_data = [x for x in self.getSTERelPerf(task) if x]
        fig, ax = plt.subplots(1, 1, figsize=(10, 5))
        if plottype == 'hist':
            sns.histplot([x for x in graph_data], ax=ax)
        elif plottype == 'dist':
            sns.distplot([x for x in graph_data], ax=ax)
        elif plottype == 'line':
            sns.lineplot(data=[x for x in graph_data], ax=ax)

    def getSampleEfficiency_helper(self, df: pd.DataFrame, task: str = None) -> int:
        try:
            if task is None:
                return df.root.sample_efficiency.iloc[0, 0]
            elif task is 'all':
                # print({t:df.root.task_metrics[t].sample_efficiency.iloc[0,0] for t in df.root.task_metrics.columns.levels[0]})
                return {t: df.root.task_metrics[t].sample_efficiency.iloc[0, 0] for t in df.root.task_metrics.columns.levels[0]}
            else:
                return df.root.task_metrics[task].sample_efficiency.iloc[0, 0]
        except (KeyError, AttributeError) as e:
            pass

    def getSampleEfficiency(self, task: str = None) -> List[int]:
        return [self.getSampleEfficiency_helper(run, task) for run in self.dfs]

    def plotSampleEfficiency(self, plottype: str, task: str = None):
        if task is 'all':
            graph_titles, graph_data = self.dictflatten(
                [x for x in self.getSampleEfficiency(task)])
            # print(self.getSampleEfficiency(task) )
            # return
            fig, ax = plt.subplots(len(graph_titles), 1, figsize=(18, 30))
            if plottype == 'hist':
                i = 0
                for k, v in graph_data.items():
                    sns.histplot([x for x in v], ax=ax[i]).set(
                        title=k+' Sample Efficiency')
                    i += 1
            elif plottype == 'dist':
                i = 0
                for k, v in graph_data.items():
                    sns.distplot([x for x in v], ax=ax[i]).set(
                        title=k+' Sample Efficiency')
                    i += 1
            elif plottype == 'line':
                i = 0
                for k, v in graph_data.items():
                    sns.lineplot(data=[x for x in v], ax=ax[i]).set(
                        title=k+' Sample Efficiency')
                    i += 1
        else:
            graph_data = [x for x in self.getSampleEfficiency(task) if x]
            fig, ax = plt.subplots(1, 1, figsize=(10, 5))
            if plottype == 'hist':
                sns.histplot([x for x in graph_data], ax=ax)
            elif plottype == 'dist':
                sns.distplot([x for x in graph_data], ax=ax)
            elif plottype == 'line':
                sns.lineplot(data=[x for x in graph_data], ax=ax)

    def getRunID_helper(self, df: pd.DataFrame) -> str:
        return df.root.run_id.iloc[0, 0]

    def getRunID(self) -> List[str]:
        return [self.getRunID_helper(run) for run in self.dfs]

    def getComplexity_helper(self, df: pd.DataFrame) -> str:
        return df.root.complexity.iloc[0, 0]

    def getComplexity(self) -> List[str]:
        return [self.getComplexity_helper(run) for run in self.dfs]

    def getDifficulty_helper(self, df: pd.DataFrame) -> str:
        return df.root.difficulty.iloc[0, 0]

    def getDifficulty(self,) -> List[str]:
        return [self.getDifficulty_helper(run) for run in self.dfs]

    def getScenarioType_helper(self, df: pd.DataFrame) -> str:
        return df.root.scenario_type.iloc[0, 0]

    def getScenarioType(self) -> List[str]:
        return [self.getScenarioType_helper(run) for run in self.dfs]

    def getMetricsColumn_helper(self, df: pd.DataFrame) -> str:
        return df.root.metrics_column.iloc[0, 0]

    def getMetricsColumn(self) -> List[str]:
        return [self.getMetricsColumn_helper(run) for run in self.dfs]

    def getMinMax_helper(self, df: pd.DataFrame, task: str = None) -> Tuple[int, int]:
        try:
            if task is None:
                return df.root["min"].iloc[0, 0], df.root["max"].iloc[0, 0]
            elif task is 'all':
                return {t: (df.root.task_metrics[t]["min"].iloc[0, 0], df.root.task_metrics[t]["max"].iloc[0, 0]) for t in df.root.task_metrics.columns.levels[0]}
            else:
                return df.root.task_metrics[task]["min"].iloc[0, 0], df.root.task_metrics[task]["max"].iloc[0, 0]
        except (KeyError, AttributeError) as e:
            pass

    def getMinMax(self, task: str = None) -> List[Union[List, Tuple[int, int]]]:
        return [self.getMinMax_helper(run, task) for run in self.dfs]

    def plotMinMax(self, plottype: str, task: str = None):
        if task is 'all':
            graph_titles, graph_data = self.dictflatten(
                [x for x in self.getMinMax(task) if x])
            fig, ax = plt.subplots(len(graph_titles), 2, figsize=(18, 30))
            if plottype == 'hist':
                i = 0
                for k, v in graph_data.items():
                    sns.histplot([min for min, _ in v], ax=ax[i]
                                 [0]).set(title=k+' Min')
                    sns.histplot([max for _, max in v], ax=ax[i]
                                 [1]).set(title=k+' Max')
                    i += 1
            elif plottype == 'dist':
                i = 0
                for k, v in graph_data.items():
                    sns.distplot([min for min, _ in v], ax=ax[i]
                                 [0]).set(title=k+' Min')
                    sns.distplot([max for _, max in v], ax=ax[i]
                                 [1]).set(title=k+' Max')
                    i += 1
            elif plottype == 'line':
                i = 0
                for k, v in graph_data.items():
                    sns.lineplot(data=[min for min, _ in v], ax=ax[i]
                                 [0]).set(title=k+' Min')
                    sns.lineplot(data=[max for _, max in v], ax=ax[i]
                                 [1]).set(title=k+' Max')
                    i += 1
        else:
            graph_data = [x for x in self.getMinMax(task) if x]
            fig, ax = plt.subplots(1, 2, figsize=(10, 5))
            if plottype == 'hist':
                sns.histplot([min for min, _ in graph_data],
                             ax=ax[0]).set(title='Min')
                sns.histplot([max for _, max in graph_data],
                             ax=ax[1]).set(title='Max')
            elif plottype == 'dist':
                sns.distplot([min for min, _ in graph_data],
                             ax=ax[0]).set(title='Min')
                sns.distplot([max for _, max in graph_data],
                             ax=ax[1]).set(title='Max')
            elif plottype == 'line':
                sns.lineplot(data=[min for min, _ in graph_data],
                             ax=ax[0]).set(title='Min')
                sns.lineplot(data=[max for _, max in graph_data],
                             ax=ax[1]).set(title='Max')

    def getNumLXEX_helper(self, df: pd.DataFrame, task: str = None) -> Tuple[int, int]:
        try:
            if task is None:
                return df.root.num_lx.iloc[0, 0], df.root.num_ex.iloc[0, 0]
            elif task is 'all':
                return {t: (df.root.task_metrics[t].num_lx.iloc[0, 0], df.root.task_metrics[t].num_ex.iloc[0, 0]) for t in df.root.task_metrics.columns.levels[0]}
            else:
                return df.root.task_metrics[task].num_lx.iloc[0, 0], df.root.task_metrics[task].num_ex.iloc[0, 0]
        except (KeyError, AttributeError) as e:
            pass

    def getNumLXEX(self, task: str = None) -> List[Union[List, Tuple[int, int]]]:
        return [self.getNumLXEX_helper(run, task) for run in self.dfs]

    def plotNumLXEX(self, plottype: str, task: str = None):
        if task is 'all':
            graph_titles, graph_data = self.dictflatten(
                [x for x in self.getNumLXEX(task) if x])
            fig, ax = plt.subplots(len(graph_titles), 2, figsize=(18, 30))
            if plottype == 'hist':
                i = 0
                for k, v in graph_data.items():
                    sns.histplot([num_lx for num_lx, _ in v],
                                 ax=ax[i][0]).set(title=k+' Num_lx')
                    sns.histplot([num_ex for _, num_ex in v],
                                 ax=ax[i][1]).set(title=k+' Num_ex')
                    i += 1
            elif plottype == 'dist':
                i = 0
                for k, v in graph_data.items():
                    sns.distplot([num_lx for num_lx, _ in v],
                                 ax=ax[i][0]).set(title=k+' Num_lx')
                    sns.distplot([num_ex for _, num_ex in v],
                                 ax=ax[i][1]).set(title=k+' Num_ex')
                    i += 1
            elif plottype == 'line':
                i = 0
                for k, v in graph_data.items():
                    sns.lineplot(data=[num_lx for num_lx, _ in v],
                                 ax=ax[i][0]).set(title=k+' Num_lx')
                    sns.lineplot(data=[num_ex for _, num_ex in v],
                                 ax=ax[i][1]).set(title=k+' Num_ex')
                    i += 1
        else:
            graph_data = [x for x in self.getNumLXEX(task) if x]
            fig, ax = plt.subplots(1, 2, figsize=(10, 5))
            if plottype == 'hist':
                sns.histplot([num_lx for num_lx, _ in graph_data],
                             ax=ax[0]).set(title='Num_lx')
                sns.histplot([num_ex for _, num_ex in graph_data],
                             ax=ax[1]).set(title='Num_ex')
            elif plottype == 'dist':
                sns.distplot([num_lx for num_lx, _ in graph_data],
                             ax=ax[0]).set(title='Num_lx')
                sns.distplot([num_ex for _, num_ex in graph_data],
                             ax=ax[1]).set(title='Num_ex')
            elif plottype == 'line':
                sns.lineplot(data=[num_lx for num_lx, _ in graph_data],
                             ax=ax[0]).set(title='Num_lx')
                sns.lineplot(data=[num_ex for _, num_ex in graph_data],
                             ax=ax[1]).set(title='Num_ex')

    def getSTERelPerfVals_helper(self, df: pd.DataFrame, task: str) -> list:
        try:
            return df.root.task_metrics[task].ste_rel_perf_vals.iloc[0, 0]
        except (KeyError, AttributeError) as e:
            pass

    def getSTERelPerfVals(self, task: str) -> List[list]:
        return [self.getSTERelPerfVals_helper(run, task) for run in self.dfs]

    def plotSTERelPerfVals(self, plottype: str, task: str):
        graph_data = self.listflatten(
            [x for x in self.getSTERelPerfVals(task) if x])
        fig, ax = plt.subplots(1, 1, figsize=(10, 5))
        if plottype == 'hist':
            sns.histplot([x for x in graph_data], ax=ax)
        elif plottype == 'dist':
            sns.distplot([x for x in graph_data], ax=ax)
        elif plottype == 'line':
            sns.lineplot(data=[x for x in graph_data], ax=ax)

    def getSTESatVals_helper(self, df: pd.DataFrame, task: str) -> list:
        try:
            return df.root.task_metrics[task].ste_saturation_vals.iloc[0, 0]
        except (KeyError, AttributeError) as e:
            pass

    def getSTESatVals(self, task: str) -> List[list]:
        return [self.getSTESatVals_helper(run, task) for run in self.dfs]

    def plotSTESatVals(self, plottype: str, task: str):
        graph_data = self.listflatten(
            [x for x in self.getSTESatVals(task) if x])
        fig, ax = plt.subplots(1, 1, figsize=(10, 5))
        if plottype == 'hist':
            sns.histplot([x for x in graph_data], ax=ax)
        elif plottype == 'dist':
            sns.distplot([x for x in graph_data], ax=ax)
        elif plottype == 'line':
            sns.lineplot(data=[x for x in graph_data], ax=ax)

    def getSTEExp2SatVals_helper(self, df: pd.DataFrame, task: str) -> list:
        try:
            return df.root.task_metrics[task].ste_exp_to_sat_vals.iloc[0, 0]
        except (KeyError, AttributeError) as e:
            pass

    def getSTEExp2SatVals(self, task: str) -> List[list]:
        return [self.getSTEExp2SatVals_helper(run, task) for run in self.dfs]

    def plotSTEExp2SatVals(self, plottype: str, task: str):
        graph_data = self.listflatten(
            [x for x in self.getSTEExp2SatVals(task) if x])
        fig, ax = plt.subplots(1, 1, figsize=(10, 5))
        if plottype == 'hist':
            sns.histplot([x for x in graph_data], ax=ax)
        elif plottype == 'dist':
            sns.distplot([x for x in graph_data], ax=ax)
        elif plottype == 'line':
            sns.lineplot(data=[x for x in graph_data], ax=ax)

    def getSESatVals_helper(self, df: pd.DataFrame, task: str) -> list:
        try:
            return df.root.task_metrics[task].se_saturation_vals.iloc[0, 0]
        except (KeyError, AttributeError) as e:
            pass

    def getSESatVals(self, task: str) -> List[list]:
        return [self.getSESatVals_helper(run, task) for run in self.dfs]

    def plotSESatVals(self, plottype: str, task: str):
        graph_data = self.listflatten(
            [x for x in self.getSESatVals(task) if x])
        fig, ax = plt.subplots(1, 1, figsize=(10, 5))
        if plottype == 'hist':
            sns.histplot([x for x in graph_data], ax=ax)
        elif plottype == 'dist':
            sns.distplot([x for x in graph_data], ax=ax)
        elif plottype == 'line':
            sns.lineplot(data=[x for x in graph_data], ax=ax)

    def getSEExp2SatVals_helper(self, df: pd.DataFrame, task: str) -> list:
        try:
            return df.root.task_metrics[task].se_exp_to_sat_vals.iloc[0, 0]
        except (KeyError, AttributeError) as e:
            pass

    def getSEExp2SatVals(self, task: str) -> List[list]:
        return [self.getSEExp2SatVals_helper(run, task) for run in self.dfs]

    def plotSEExp2SatVals(self, plottype: str, task: str):
        graph_data = self.listflatten(
            [x for x in self.getSEExp2SatVals(task) if x])
        fig, ax = plt.subplots(1, 1, figsize=(10, 5))
        if plottype == 'hist':
            sns.histplot([x for x in graph_data], ax=ax)
        elif plottype == 'dist':
            sns.distplot([x for x in graph_data], ax=ax)
        elif plottype == 'line':
            sns.lineplot(data=[x for x in graph_data], ax=ax)

    def getSampleEfficiencyVals_helper(self, df: pd.DataFrame, task: str) -> list:
        try:
            return df.root.task_metrics[task].sample_efficiency_vals.iloc[0, 0]
        except (KeyError, AttributeError) as e:
            pass

    def getSampleEfficiencyVals(self, task: str) -> List[list]:
        return [self.getSampleEfficiencyVals_helper(run, task) for run in self.dfs]

    def plotSampleEfficiencyVals(self, plottype: str, task: str):
        graph_data = self.listflatten(
            [x for x in self.getSampleEfficiencyVals(task) if x])
        fig, ax = plt.subplots(1, 1, figsize=(10, 5))
        if plottype == 'hist':
            sns.histplot([x for x in graph_data], ax=ax)
        elif plottype == 'dist':
            sns.distplot([x for x in graph_data], ax=ax)
        elif plottype == 'line':
            sns.lineplot(data=[x for x in graph_data], ax=ax)

    def getSETaskSat_helper(self, df: pd.DataFrame, task: str):
        try:
            return df.root.task_metrics[task].se_task_saturation.iloc[0, 0]
        except (KeyError, AttributeError) as e:
            pass

    def getSETaskSat(self, task: str):
        return [self.getSETaskSat_helper(run, task) for run in self.dfs]

    def plotSETaskSat(self, plottype: str, task: str):
        graph_data = [x for x in self.getSETaskSat(task) if x]
        fig, ax = plt.subplots(1, 1, figsize=(10, 5))
        if plottype == 'hist':
            sns.histplot([x for x in graph_data], ax=ax)
        elif plottype == 'dist':
            sns.distplot([x for x in graph_data], ax=ax)
        elif plottype == 'line':
            sns.lineplot(data=[x for x in graph_data], ax=ax)

    def getSETaskEPS2Sat_helper(self, df: pd.DataFrame, task: str):
        try:
            return df.root.task_metrics[task].se_task_exp_to_sat.iloc[0, 0]
        except (KeyError, AttributeError) as e:
            pass

    def getSETaskEPS2Sat(self, task: str):
        return [self.getSETaskEPS2Sat_helper(run, task) for run in self.dfs]

    def plotSETaskEPS2Sat(self, plottype: str, task: str):
        graph_data = [x for x in self.getSETaskEPS2Sat(task) if x]
        fig, ax = plt.subplots(1, 1, figsize=(10, 5))
        if plottype == 'hist':
            sns.histplot([x for x in graph_data], ax=ax)
        elif plottype == 'dist':
            sns.distplot([x for x in graph_data], ax=ax)
        elif plottype == 'line':
            sns.lineplot(data=[x for x in graph_data], ax=ax)

    def getRuntime_helper(self, df: pd.DataFrame):
        try:
            return df.root.runtime.iloc[0, 0]
        except (KeyError, AttributeError) as e:
            pass

    def getRuntime(self):
        return [self.getRuntime_helper(run) for run in self.dfs]

    def plotRuntime(self, plottype: str):
        graph_data = [x for x in self.getRuntime() if x]
        fig, ax = plt.subplots(1, 1, figsize=(10, 5))
        if plottype == 'hist':
            sns.histplot([x for x in graph_data], ax=ax)
        elif plottype == 'dist':
            sns.distplot([x for x in graph_data], ax=ax)
        elif plottype == 'line':
            sns.lineplot(data=[x for x in graph_data], ax=ax)

    def getUniqueTaskNames_helper(self, df: pd.DataFrame):
        try:
            return df.root.task_metrics.columns.levels[0]
        except (KeyError, AttributeError) as e:
            pass

    def getUniqueTaskNames(self):
        return set(self.listflatten([list(self.getUniqueTaskNames_helper(run)) for run in self.dfs]))

    # ----------------------------------------------------------------------------
    # TSV methods

    def getRegime(self):
        return self.df_tsv.regime_num

    def getRegimeByTask(self, task: str):
        return self.df_tsv[self.df_tsv.task_name == task].regime_num

    def getRegimeByBlockType(self, blktype: str = None, subtype: str = None):
        if subtype and blktype:
            return self.df_tsv[(self.df_tsv.block_type == blktype) & (self.df_tsv.block_subtype == subtype)].regime_num
        elif subtype:
            return self.df_tsv[self.df_tsv.block_subtype == subtype].regime_num
        else:
            return self.df_tsv[self.df_tsv.block_type == blktype].regime_num

    def getTermPerf(self, runID: str):
        return self.df_tsv[self.df_tsv.run_id == runID].term_perf

    def getTaskNamesUnique(self):
        return list(self.df_tsv.task_name.unique())