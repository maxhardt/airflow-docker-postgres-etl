#!/usr/bin/python3

import asyncio
import json
import logging
import os
from typing import Union

import aiohttp
import pandas as pd


async def get_podcast_metadata(session: aiohttp.ClientSession,
                               url: str,
                               itunes_id: str,
                               staging_dir: str
) -> Union[bool, Exception]:
    """Requests metadata for a given id from iTunes API and writes results to JSON file.

    Args:
        session (aiohttp.ClientSession): aiohttp session object.
        url (str): Complete iTunes lookup API url including the id,
            e.g. https://itunes.apple.com/lookup?id=123456789
        itunes_id (str): iTunes podcast id for which the lookup is performed.
        staging_dir (str): Directory for writing results.

    Returns:
        Union[bool, Exception]: True if metadata was successfully processed,
            Exception otherwise.
    """

    async with session.get(url) as resp:
        data = await resp.json(content_type=None)

        try:
            filepath = os.path.join(staging_dir, f"{itunes_id}.json")
            with open(filepath, "w") as file:
                json.dump(data["results"][0], file)
            logging.info(f"Wrote metadata file for itunes id: {itunes_id}")
            return True

        except Exception as e:
            return e


async def _extract_itunes_metadata(
    itunes_lookup_url: str,
    itunes_ids_filepath: str,
    staging_dir: str,
    n_limit_ids: Union[int, None] = None,
    **kwargs
) -> None:
    """Collects asynchronous tasks for requesting metadata from itunes API.

    Args:
        itunes_lookup_url (str): Base URL to the Itunes lookup API.
        staging_dir (str): Staging directory for reading and writing data.
        itunes_ids_filepath (str): Filepath to unique itunes podcast ids.
        n_limit_ids (Union[int, None], optional): Only use the first `n_limit_ids`
            ids. Defaults to None. May be set to a low number for testing.
    """

    itunes_ids = pd.read_csv(itunes_ids_filepath, header=None)[0].to_list()
    itunes_ids = itunes_ids[:n_limit_ids] if n_limit_ids else itunes_ids 

    async with aiohttp.ClientSession() as session:

        tasks = []
        for itunes_id in itunes_ids:
            lookup_url = f"{itunes_lookup_url}?id={itunes_id}"
            tasks.append(asyncio.ensure_future(get_podcast_metadata(session,
                                                                    lookup_url,
                                                                    str(itunes_id),
                                                                    staging_dir)))

        results = await asyncio.gather(*tasks)
        logging.info("All requests processed successfully: {}".format(
            all(r == True for r in results)))


def extract_itunes_metadata(**kwargs):
    """Wrapper for asynchronously requesting metadata from itunes API."""
    asyncio.run(_extract_itunes_metadata(**kwargs))
