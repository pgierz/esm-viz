import sys, os, difflib, argparse

def compare_namelists(used_namelist, original_namelist):
        with open(used_namelist) as unml:
                usedlines = unml.readlines()
        with open(original_namelist) as onml:
                originallines = onml.readlines()
        return difflib.HtmlDiff().make_table(usedlines, originallines, context=True)

