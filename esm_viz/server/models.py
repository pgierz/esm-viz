from esm_viz.visualization.scheduler_queue import SlurmQueue, RemoteSlurmQueue

class QueueModel(object):
    def __init__(self, batch_system, remote, username=None, hostname=None):
        if batch_system == "slurm":
            if remote:
                queue = RemoteSlurmQueue(username, hostname)
            else:
                queue = SlurmQueue()
        else:
            raise TypeError("Unknown batch system recieved!")

    self.queue = queue
