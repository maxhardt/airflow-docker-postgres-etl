#!/usr/bin/python3

import os
import sqlite3

import pandas as pd


def extract_podcast_ids(sqlite_filepath: str,
                        table_name: str,
                        staging_dir: str,
                        file_name: str) -> None:
    """Extract distinct itunes podcast ids from kaggle sqlite data.

    Args:
        sqlite_filepath (str): Filepath to sqlite kaggle dataset.
        table_name (str): Name of the table containing itunes ids.
        staging_dir (str): Staging directory for writing results.
        file_name (str): Filename of resulting file with ids.
    """

    sqlite_connection = sqlite3.connect(sqlite_filepath)

    df = pd.read_sql(f"select distinct(itunes_id) from {table_name}",
                     con=sqlite_connection)
    df.to_csv(os.path.join(staging_dir, file_name),
              header=False,
              index=False)
