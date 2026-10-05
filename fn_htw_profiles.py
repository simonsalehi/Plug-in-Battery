"""
Load a single HTW household load profile (1 s resolution) for the simulation.

The raw HTW download provides the three phases of all 74 profiles in
PL1.csv, PL2.csv and PL3.csv (one column per profile, one row per second).
load_htw_profile() reads only the column of the requested profile from each
file (chunk by chunk, RAM-friendly) and sums the three phases row by row.

Nothing is written to disk: the profile is returned as an array, passed
through the simulation and saved together with the results.
"""

from itertools import zip_longest

import numpy as np
import pandas as pd

N_PROFILES = 74


def load_htw_profile(profile_number, input_files, chunksize=1_000_000):
    """
    Parameters
    ----------
    profile_number : int
        Number of the household profile (1-74), e.g. 43 for "Pl_43".
    input_files : list of str
        The three phase files (PL1.csv, PL2.csv, PL3.csv).
    chunksize : int
        Rows per chunk; lower it if RAM is tight.

    Returns
    -------
    numpy.ndarray
        Total load power in W, 1 value per second (sum of the three phases).
    """
    if not 1 <= profile_number <= N_PROFILES:
        raise ValueError(f"profile_number must be between 1 and {N_PROFILES}, got {profile_number}.")

    col = profile_number - 1  # 0-based column index

    readers = [
        pd.read_csv(f, header=None, usecols=[col], chunksize=chunksize, dtype="int32")
        for f in input_files
    ]

    parts = []
    for chunks in zip_longest(*readers):
        if any(c is None for c in chunks):
            raise ValueError("The phase files do not have the same number of rows.")
        # Element-wise sum of the matching chunks (PL1 + PL2 + PL3)
        parts.append(sum(c.iloc[:, 0].to_numpy() for c in chunks))

    return np.concatenate(parts)
