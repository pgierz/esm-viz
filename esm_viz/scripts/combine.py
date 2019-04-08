import os
import sys
sys.path.append("..")
import inspect
import logging

import click

import esm_viz
from esm_viz.visualization.nbmerge import merge_notebooks
from esm_viz.esm_viz import read_simulation_config, MODEL_COMPONENTS

module_path = os.path.dirname(inspect.getfile(esm_viz))

@click.command()
@click.option('--quiet', default=False, is_flag=True)
@click.option('--expid', default="example", help="The YAML file found in ~/.config/monitoring")
def combine(expid, quiet):
    if quiet:
        logging.basicConfig(level=logging.ERROR)
    else:
        logging.basicConfig(level=logging.INFO)
    config = read_simulation_config(os.environ.get("HOME")+"/.config/monitoring/"+expid+".yaml")
    # Remove stuff from the config that we probably won't need:
    for bad_chapter in ['user', 'host', 'basedir', 'model', 'coupling']:
        if bad_chapter in config:
            del config[bad_chapter]
    viz_path = module_path+"/visualization/"
    notebooks_to_merge = [viz_path+"read_config.ipynb"]
    for monitoring_element in config:
        for element in config[monitoring_element]:
            print(monitoring_element, element)
            if os.path.isfile(viz_path+monitoring_element+"_"+element.lower().replace(" ", "_")+".ipynb"):
                notebooks_to_merge.append(viz_path+monitoring_element+"_"+element.lower().replace(" ", "_")+".ipynb")
    with open(expid+".ipynb", "w") as notebook_merged:
        notebook_merged.write(merge_notebooks(notebooks_to_merge))
    with open(".config_ipynb", "w") as config_file:
        config_file.write(' '.join(['test_args.py', os.environ.get("HOME")+"/.config/monitoring/"+expid+".yaml"]))
    os.system('jupyter nbconvert --execute {:s} --to html'.format(expid+".ipynb"))
    os.rename(expid+".html", os.environ.get("HOME")+"/public_html/"+expid+".html")

if __name__ == "__main__":
    combine()
