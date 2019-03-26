"""
This script compares namelist found in the experiment directory it is currently
in to another one. Alteratively, you can set both the ``source`` and ``target``
experiments to compare via the command line.

Usage Example
-------------

Given a source experiment ``foo``, running in::

    /work/ba0989/a270077/esm-experiments/foo/analysis/general

the script will find all namelist.* files found in::

    /work/ba0989/a270077/esm-experiments/foo/config/*

and compare them to whatever experiment is given as a ``target``.

"""
from pathlib import Path
import argparse
import os
import subprocess
import sys

try:
    import f90nml
except ImportError:
    try:
        subprocess.check_output("pip install --user f90nml")
    except OSError:
        sys.exit("Could not install requirement f90nml")

__version__ = "0.1.0"
__author__ = "Paul Gierz"


def determine_running_location():
    """
    Determines where this script is being run from.

    Returns
    -------
    working_path, running_in_exp_dir : tuple(Path, Bool)
        A tuple of:
        1. Path pointing to either:
           a. the location where this script is being run from
           b. the top of an esm-experiment
        2. A Boolean determining if the script is being run from within an
           ESM-Style experiment
    """
    working_path = Path.cwd()
    dir_path = Path(os.path.dirname(os.path.realpath(__file__)))
    esm_dirs_to_find = set([
            "bin", "config", "forcing", "input", "log",
            "mon", "outdata", "restart", "scripts", "work"])
    found_exp_base_path = False
    old_working_dir = dir_path
    while not found_exp_base_path:
        # Determine just the basenames of all directories currently being
        # checked against:
        dirs_in_this_directory = [str(x.name) for x in working_path.iterdir() if x.is_dir()]
        # Check if the directories we need to find are a subset of all
        # directories in the directory currently being checked:
        if esm_dirs_to_find <= set(dirs_in_this_directory):
            found_exp_base_path = True
            exp_base_path = working_path
            return(exp_base_path, True)
        else:
            # We didn't find what we were looking for, go up a level and check
            # again:
            working_path = working_path.parent
            if working_path == Path(working_path.root):
                # Got to root of the file system; probably running from outside
                # of an experiment directory:
                return (Path.cwd, False)


def parse_arguments():
    """
    Parse arguments given to this script

    Parameters
    ----------
    running_in_esm_dir : Bool
        A boolean determining if we are running in an esm-style directory. In
        this case, the source directory is optional.

    Returns
    -------
    source_config_dir : str
        The directory where the source namelists (those of the experiment
        currently be checked) will probably be in
    target_config_dir : str
        The directory where the target namelists (those to compare against)
        will probably be in.
    """
    working_path, running_in_exp_dir = determine_running_location()
    parser = argparse.ArgumentParser(description=
            """This script compares two sets of namelists
            and displays the differences, chapter by chapter. If namelists are
            logically identical and differ only in capitalization and entry
            order, this is noted. If you are running it from anywhere inside of
            an esm-style experiment tree, you only need to give the --target
            parameter. Otherwise, you must give both --source and --target.
            Order of the passed arguments does not matter.
            """
            )
    parser.add_argument("--source", required=not running_in_exp_dir,
                        help="The top of the experiment where the `source` namelists should be taken from")
    parser.add_argument("--target", required=True,
                        help="The top of the experiment where the `target` namelists should be taken from")
    args = parser.parse_args()
    if args.source:
        return (args.source + "/config/", args.target + "/config/")
    else:
        return (str(working_path) + "/config/", args.target + "/config/")


def find_namelist_files(toplevel_dir):
    """
    Finds all namelist files in a particular experiment

    Parameters
    ----------
    toplevel_dir : str
        A string pointing to the top of the experiment

    Returns
    -------
    namelists : list of f90nml.Namelist objects
        A list of namelist objects to be compared
    """
    found_namelists = []
    for root, dirs, files in os.walk(toplevel_dir):
        for this_file in files:
            if not this_file.startswith("namelist."):
                continue
            if any([c.isdigit() for c in this_file]):
                continue
            found_namelists.append(root+"/"+this_file)
    return found_namelists


def determine_identical_namelists(source_namelists, target_namelists):
    """
    Determines which namelists are perfectly identlical

    Parameters
    ----------
    source_namelists : list
        A list of namelists from the source experiment
    target_namelists : list
        A list of namelists from the target experiment

    Returns
    -------
    identical_namelists : list
        A list of namelists that are the same
    unique_source_namelists : list
        A list of namelists that are **only** found in the source experiment
    unique_target_namelists : list
        A list of namelists that are **only** found in the target experiment

    Note
    ----
    The lists ``source_namelists`` and ``target_namelists`` are modified **IN
    PLACE** as this function runs.
    """
    source_namelist_basenames = [os.path.basename(x) for x in source_namelists]
    target_namelist_basenames = [os.path.basename(x) for x in target_namelists]

    identically_named_namelists, unique_source_namelists, unique_target_namelists = \
            determine_identical_and_unique_elements(source_namelist_basenames,
                    target_namelist_basenames)
    identical_namelists = []
    for namelist in identically_named_namelists:
        source_namelist_full_path = [s for s in source_namelists if namelist in s][0]
        target_namelist_full_path = [s for s in target_namelists if namelist in s][0]
        this_nml = f90nml.read(source_namelist_full_path)
        other_nml = f90nml.read(target_namelist_full_path)
        if this_nml == other_nml:
            source_namelists.remove(source_namelist_full_path)
            target_namelists.remove(target_namelist_full_path)
            identical_namelists.append(namelist)
    return (identical_namelists, unique_source_namelists, unique_target_namelists)

def determine_identical_and_unique_elements(A, B):
    """
    Given two lists determine which entries are in common and which are unique

    Parameters
    ----------
    A : list
        The first list to check
    B : list
        The second list to check

    Returns
    -------
    common : list
        Common elements
    unique_A : list
        Elements unique to A
    unique_B : list
        Elements unique to B
    """
    common = list(set(A).intersection(set(B)))
    unique_A = list(set(A) - set(B))
    unique_B = list(set(B) - set(A))
    return common, unique_A, unique_B

def determine_namelist_differences(
        source_namelist, target_namelist,
        bad_chapters=["set_stream", "mvstreamctl", "set_stream_element"]):
    """
    Determines differences in namelists

    Parameters
    ----------
    source_namelist : str
        The "source" namelist to use. This is "yours"
    target_namelist : str
        The "target" namelist to use. This is "the other one"
    bad_chapters : list
        A list of strings with chapter names that should not be compared

    Returns
    -------
    namelist_diffs : list
        A list of strings containing diff information; to be printed later.
    """
    source_nml = f90nml.read(source_namelist)
    target_nml = f90nml.read(target_namelist)
    for chapter in bad_chapters:
        for this_nml in source_nml, target_nml:
            if chapter in this_nml:
                del this_nml[chapter]
    common_chapters, unique_source_chapters, unique_target_chapters = \
            determine_identical_and_unique_elements(source_nml, target_nml)
    namelist_diffs = ["\n", os.path.basename(source_namelist)]
    namelist_diffs.append(80*"-")
    for this_chapter in common_chapters:
        namelist_diffs.append("&"+this_chapter)
        entry_diffs = []
        common_entries, unique_source_entries, unique_target_entries = \
            determine_identical_and_unique_elements(source_nml[this_chapter], target_nml[this_chapter])
        for this_entry in common_entries:
            source_nml_value = source_nml[this_chapter][this_entry]
            target_nml_value = target_nml[this_chapter][this_entry]
            if source_nml_value != target_nml_value:
                entry_diffs.append("\t\t Source: %s: %s" % (this_entry, source_nml_value))
                entry_diffs.append("\t\t Target: %s: %s" % (this_entry, target_nml_value))
        if unique_source_entries:
            entry_diffs.append("\n\t\t Unique to Source:")
            for this_entry in unique_source_entries:
                entry_diffs.append("\t\t %s: %s" % (this_entry, source_nml[this_chapter][this_entry]))
        if unique_target_entries:
            entry_diffs.append("\n\t\t Unique to Target:")
            for this_entry in unique_target_entries:
                entry_diffs.append("\t\t %s: %s" % (this_entry, target_nml[this_chapter][this_entry]))
        if entry_diffs:
            namelist_diffs += entry_diffs
        else:
            namelist_diffs.append("\n\t\t All entries are the same!")
        namelist_diffs.append("\\")
    for unique_chapters, nml, tag in zip([unique_source_chapters, unique_target_chapters], [source_nml, target_nml], ["Source", "Target"]):
        if unique_chapters:
            for chapter in unique_chapters:
                namelist_diffs.append("\n\t\t The following chapter is unique to %s" % tag)
                namelist_diffs.append("&"+chapter)
                for entry, value in nml[chapter].items():
                    namelist_diffs.append("\t\t %s: %s" % (entry, value))
    return namelist_diffs



def main():
    """
    Runs the program:
    1. Parses arguments
    2. Finds source namelist files
    3. Finds target namelist files
    4. Determines which namelist files are exactly identical
    5. Displays differences for non-identical namelists
    6. Prints information regarding unique namelists for each experiment; if no
       corresponding namelist could be found.
    """
    source_dir, target_dir = parse_arguments()
    source_namelists = find_namelist_files(source_dir)
    target_namelists = find_namelist_files(target_dir)
    identical_namelists, unique_source_namelists, unique_target_namelists = determine_identical_namelists(source_namelists, target_namelists)

    print(80*"*")
    print("Comparing namelists of:")
    print("%s".center(40 - int((len(source_dir)/2))) % source_dir)
    print("- and - ".center(40))
    print("%s".center(40 - int((len(target_dir)/2))) % target_dir)
    print("\n", 80*"*", "\n\n")

    if identical_namelists:
        print(80*"=")
        print("The following namelists are logically identical:")
        for namelist in identical_namelists:
            print("- %s" % namelist)
    if source_namelists:
        print(80*"=")
        print("These namelists are different:")
        for source_namelist, target_namelist in zip(source_namelists, target_namelists):
            these_diffs = determine_namelist_differences(source_namelist, target_namelist)
            for diff in these_diffs:
                print(diff)
    if unique_source_namelists:
        print(80*"=")
        print("These namelists are unique to %s" % source_dir)
        for namelist in unique_source_namelists: 
            print("- %s" % namelist)
    if unique_target_namelists:
        print(80*"=")
        print("These namelists are unique to %s" % target_dir)
        for namelist in unique_target_namelists: 
            print("- %s" % namelist)

if __name__ == "__main__":
    main()
