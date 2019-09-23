"""
Class for Logfiles
"""
import datetime

import pandas as pd
import paramiko

import numpy as np
from matplotlib import cm
from matplotlib import pyplot as plt
from matplotlib.patches import Circle, Wedge, Rectangle


class Logfile(object):
    """Makes a Pandas Dataframe from a logfile"""

    def __init__(self, log, esm_style=True):
        self.log = log
        if esm_style:
            self.log_df = self._generate_dataframe_from_esm_logfile()
        else:
            self.log_df = self._generate_dataframe_from_mpimet_logfile()
        del self.log

    def _generate_dataframe_from_esm_logfile(self):
        df = pd.DataFrame(
            [l.split(" : ") for l in self.log], columns=["Date", "Message"]
        )
        df2 = df["Message"].str.split(expand=True)
        # We drop the first row since it says "Start of Experiment"
        log_df = pd.concat([df[1:]["Date"], df2[1:]], axis=1)
        log_df.columns = [
            "Date",
            "Run Number",
            "Exp Date",
            "Job ID",
            "Seperator",
            "State",
        ]
        log_df.drop("Seperator", axis=1, inplace=True)
        log_df.set_index("Date", inplace=True)
        log_df.index = pd.to_datetime(log_df.index)
        return log_df

    def _generate_dataframe_from_mpimet_logfile(self):
        log_df = pd.read_table(
            self.log,
            sep=r" :  | -",
            skiprows=1,
            infer_datetime_format=True,
            names=["Date", "Message", "State"],
            engine="python",
            index_col=0,
        )
        middle_column = log_df["Message"].apply(lambda x: pd.Series(str(x).split()))
        log_df.drop("Message", axis=1, inplace=True)
        middle_column.columns = ["Run Number", "Exp Date", "Job ID"]
        log_df = pd.concat([log_df, middle_column], axis=1)
        log_df.set_index(pd.to_datetime(log_df.index), inplace=True)
        return log_df

    @classmethod
    def from_file(cls, fin):
        with open(fin) as f:
            log = f.readlines()
        return cls(log)

    def compute_throughput(self):
        starts = self.log_df[self.log_df.State.str.contains("start")]
        ends = self.log_df[self.log_df.State.str.contains("done")]
        # Drop the duplicated starts:
        starts.drop_duplicates(subset="Run Number", keep="last", inplace=True)
        merged = pd.concat([starts, ends])
        groupby = merged.groupby("Run Number")
        run_diffs = {"Run Number": [], "Wall Time": [], "Queue Time": []}
        for name, group in groupby:
            if int(name) > 1:
                previous_group = groupby.get_group(str(int(name) - 1))
                run_diffs["Queue Time"].append(
                    group.index[0] - previous_group.index[-1]
                )
            else:
                run_diffs["Queue Time"].append(datetime.timedelta(0))
            run_diffs["Run Number"].append(int(name))
            run_diffs["Wall Time"].append(group.index[-1] - group.index[0])
        diffs = (
            pd.DataFrame(run_diffs).sort_values("Run Number").set_index("Run Number")
        )
        throughput = (datetime.timedelta(1) / diffs.mean())["Wall Time"]
        return pd.DataFrame({"Simulation Average": diffs.mean()}), throughput, diffs

    def run_stats(self):
        _, _, diffs = self.compute_throughput()
        last_ten_diffs = diffs.tail(10)
        throughput = datetime.timedelta(1) / last_ten_diffs["Wall Time"].mean()
        efficiency = last_ten_diffs["Wall Time"].mean() / (
            last_ten_diffs["Queue Time"].mean() + last_ten_diffs["Wall Time"].mean()
        )

        df = pd.DataFrame.from_dict(
            {
                "Mean Walltime": last_ten_diffs["Wall Time"].mean(),
                "Mean Queuing Time": last_ten_diffs["Queue Time"].mean(),
                "Optimal Throughput": throughput,
                "Actual Throughput (Last 10 Runs)": throughput * efficiency,
                "Run Efficiency (Last 10 Runs)": efficiency * 100,
            },
            orient="index",
            columns=["Run Statistics"],
        )
        return df

    def run_gauge(self):
        run_stats_df = self.run_stats()
        levels = np.arange(0, 105, 5)
        arrow_level = int(
            find_nearest(
                levels, run_stats_df["Run Statistics"]["Run Efficiency (Last 10 Runs)"]
            )
            + 1.0
        )
        levels = ["%.0f" % number for number in levels]
        levels = [l + "%" for l in levels]
        return gauge(
            labels=levels, colors="RdYlGn_r", arrow=arrow_level, title="Run Efficiency"
        )


##################
# Plot for gauge
#################


def find_nearest(array, value):
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return idx


def degree_range(n):
    start = np.linspace(0, 180, n + 1, endpoint=True)[0:-1]
    end = np.linspace(0, 180, n + 1, endpoint=True)[1::]
    mid_points = start + ((end - start) / 2.0)
    return np.c_[start, end], mid_points


def rot_text(ang):
    rotation = np.degrees(np.radians(ang) * np.pi / np.pi - np.radians(90))
    return rotation


def gauge(
    labels=["LOW", "MEDIUM", "HIGH", "VERY HIGH", "EXTREME"],
    colors="jet_r",
    arrow=1,
    title="",
    fname=False,
):

    """
    some sanity checks first

    """

    N = len(labels)

    if arrow > N:
        raise Exception(
            "\n\nThe category ({}) is greated than \
        the length\nof the labels ({})".format(
                arrow, N
            )
        )

    """
    if colors is a string, we assume it's a matplotlib colormap
    and we discretize in N discrete colors
    """

    if isinstance(colors, str):
        cmap = cm.get_cmap(colors, N)
        cmap = cmap(np.arange(N))
        colors = cmap[::-1, :].tolist()
    if isinstance(colors, list):
        if len(colors) == N:
            colors = colors[::-1]
        else:
            raise Exception(
                "\n\nnumber of colors {} not equal \
            to number of categories{}\n".format(
                    len(colors), N
                )
            )

    """
    begins the plotting
    """

    fig, ax = plt.subplots()

    ang_range, mid_points = degree_range(N)

    labels = labels[::-1]

    """
    plots the sectors and the arcs
    """
    patches = []
    for ang, c in zip(ang_range, colors):
        # sectors
        patches.append(Wedge((0.0, 0.0), 0.4, *ang, facecolor="w", lw=2))
        # arcs
        patches.append(
            Wedge((0.0, 0.0), 0.4, *ang, width=0.10, facecolor=c, lw=2, alpha=0.5)
        )

    [ax.add_patch(p) for p in patches]

    """
    set the labels (e.g. 'LOW','MEDIUM',...)
    """

    for mid, lab in zip(mid_points, labels):

        ax.text(
            0.35 * np.cos(np.radians(mid)),
            0.35 * np.sin(np.radians(mid)),
            lab,
            horizontalalignment="center",
            verticalalignment="center",
            fontsize=8,
            rotation=rot_text(mid),
        )

    """
    set the bottom banner and the title
    """
    r = Rectangle((-0.4, -0.1), 0.8, 0.1, facecolor="w", lw=2)
    ax.add_patch(r)

    ax.text(
        0,
        -0.05,
        title,
        horizontalalignment="center",
        verticalalignment="center",
        fontsize=22,
        fontweight="bold",
    )

    """
    plots the arrow now
    """

    pos = mid_points[abs(arrow - N)]

    ax.arrow(
        0,
        0,
        0.225 * np.cos(np.radians(pos)),
        0.225 * np.sin(np.radians(pos)),
        width=0.04,
        head_width=0.09,
        head_length=0.1,
        fc="k",
        ec="k",
    )

    ax.add_patch(Circle((0, 0), radius=0.02, facecolor="k"))
    ax.add_patch(Circle((0, 0), radius=0.01, facecolor="w", zorder=11))

    """
    removes frame and ticks, and makes axis equal and tight
    """

    ax.set_frame_on(False)
    ax.axes.set_xticks([])
    ax.axes.set_yticks([])
    ax.axis("equal")
    plt.tight_layout()
    plt.close(fig)
    return fig
