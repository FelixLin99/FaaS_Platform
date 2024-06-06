import numpy as np
import matplotlib.pyplot as plt
import sys
import os

def plot_graph(data, output_file, mode):
    # create a figure and axis object
    fig, ax = plt.subplots()

    # iterate through each key in the dictionary
    for k in data.keys():
        # plot the line for the corresponding value
        ax.plot(data[k][:, 0], data[k][:, 1], label=k)
    # add a legend
    ax.legend()
    # add axis labels and a title
    plt.xlabel("Number of workers")
    plt.ylabel("Execution time (s)")
    plt.title(f"Scaling performance on executing `{mode} tasks` \n 5 tasks per worker")
    plt.grid()
    fig.show()
    fig.savefig(output_file, dpi=100)



if __name__=="__main__":
    noop = {
        'local': np.array([
            [2, 0.073],
            [3, 0.114],
            [4, 0.140],
            [5, 0.227]
        ]),
        'pull': np.array([
            [2, 0.374],
            [3, 0.402],
            [4, 0.440],
            [5, 0.508]
        ]),
        'push': np.array([
            [2, 0.258],
            [3, 0.295],
            [4, 0.333],
            [5, 0.419]
        ])
    }

    sleep_1s = {
        'local': np.array([
            [2, 5.32],
            [3, 5.44],
            [4, 5.55],
            [5, 5.71]
        ]),
        'pull': np.array([
            [2, 5.40],
            [3, 5.53],
            [4, 5.64],
            [5, 5.79]
        ]),
        'push': np.array([
            [2, 5.29],
            [3, 5.40],
            [4, 5.55],
            [5, 5.72]
        ])
    }

    intensive_1s = {
        'local': np.array([
            [2, 5.30],
            [3, 5.35],
            [4, 5.45],
            [5, 5.57]
        ]),
        'pull': np.array([
            [2, 5.40],
            [3, 5.53],
            [4, 5.67],
            [5, 5.80]
        ]),
        'push': np.array([
            [2, 5.31],
            [3, 5.44],
            [4, 5.58],
            [5, 5.68]
        ])
    }

    # data, output_file, mode
    plot_graph(noop, './noop.png', 'no-op')
    plot_graph(sleep_1s, './sleep_1s.png', 'sleep_1s')
    plot_graph(intensive_1s, './intensive_1s.png', 'intensive_1s')


'''
{
    :
        [speedup1, speedup2, ..., speedup5],
    8:
        [speedup1, speedup2, ..., speedup5]
}
'''