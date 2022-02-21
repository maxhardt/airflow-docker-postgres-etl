#!/usr/bin/python3

import logging
import os
import sqlite3
from typing import List, Union

import pandas as pd


def extract_sqlite_table(sqlite_filepath: str,
                         table_name: str,
                         staging_dir: str,
                         cols_to_datetime: Union[List[str], None]) -> None:
    """Extracts tables from sqlite database to csv files.

    Args:
        sqlite_filepath (str): Filepath to sqlite database.
        table_names (str): Table name to extract.
        staging_dir (str): Target csv directory.
        cols_to_datetime (Union[List[str], None]): Columns containing timestamps.
    """
    sqlite_connection = sqlite3.connect(sqlite_filepath)
    df = pd.read_sql(f"select * from {table_name}",
                     con=sqlite_connection)

    # remove all non-ascii characters where applicable
    for col in df.columns:
        try:
            df[col].str
        except Exception as e:
            logging.info(f"Column '{col}' is not a string type. Skipping it.")
            continue
        logging.info(f"Applying string-preprocessing to column '{col}'")
        df[col] = df[col].str.encode("ascii", "ignore").str.decode("ascii")

    # remove special characters and target delimiter char
    df = df.replace(regex={
        r"\\": "",
        "\t": ". ",
        "\n": ". ",
        "\r": "",
        ";": "," 
    })

    # parse timestamps to datetime
    if cols_to_datetime:
        for col in cols_to_datetime:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # drop any rows with missing values
    df = df.dropna(axis=0, how="any")

    df.to_csv(os.path.join(staging_dir, f"{table_name}.csv"),
                header=False, index=False, sep=";")
