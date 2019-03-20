import subprocess
import pandas as pd
import getpass

class slurm():
        def __init__(self):
                self.update_queue_info()

        def update_queue_info(self):
                username = getpass.getuser()
                squeue_output = subprocess.run(["squeue", "-u", username, "-o", "%all"], stdout=subprocess.PIPE)
                squeue_output_formatted = [i.split("|") for i in squeue_output.stdout.decode("utf-8").split("\n")]
                headers = squeue_output_formatted.pop(0)
                del squeue_output_formatted[-1]
                df = pd.DataFrame(squeue_output_formatted, columns=headers)
                df = df.loc[:,~df.columns.duplicated()]
                df["START_TIME"] = pd.to_datetime(df["START_TIME"])
                self.queue_status = df

        def __repr__(self):
                return self.queue_status[["JOBID", "PARTITION", "USER", "NAME", "TIME"]].to_string()

        def _repr_html_(self):
                return self.queue_status[["JOBID", "PARTITION", "USER", "NAME", "STATE", "TIME", "START_TIME"]].to_html()

        def __str__(self):
                return "SLURM Batch System"
