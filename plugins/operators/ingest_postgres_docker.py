import glob
import os
from typing import Tuple, Union

from airflow.models import BaseOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook


class IngestPostgresDockerOperator(BaseOperator):
    """Ingests files from mounted container volume to target table.
    """

    INGEST_QUERY_JSON = "copy {} {} from '{}'"
    INGEST_QUERY_CSV = "copy {} {} from '{}' delimiter ';'"
    QUERIES = {
        "csv": INGEST_QUERY_CSV,
        "json": INGEST_QUERY_JSON
    }

    def __init__(self,
                 connection_id: str,
                 target_table: str,
                 target_columns: Union[Tuple[str], None],
                 staging_dir: str,
                 container_staging_dir: str,
                 file_pattern: str,
                 file_format: str,
                 *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.connection_id = connection_id
        self.target_table = target_table
        self.target_columns = target_columns
        self.staging_dir = staging_dir
        self.container_staging_dir = container_staging_dir
        self.file_pattern = file_pattern
        self.file_format = file_format

    def execute(self, context, *args, **kwargs):

        # establish connection to PostgreSQL
        self.log.info("Establishing connection to PostgreSQL")
        postgres = PostgresHook(postgres_conn_id=self.connection_id)

        # if target_columns is not specified, all columns are used.
        if self.target_columns:
            target_columns = "({})".format(",".join(self.target_columns))
        else:
            target_columns = ""

        # identify source files
        source_files = glob.glob(os.path.join(self.staging_dir, self.file_pattern))
        self.log.info(f"Identified the following source files: {source_files}")

        # ingest matching files from staging dir
        for source_file in source_files:

            # pattern matching is done on host ->
            # convert filepath to absolute path on container
            source_filepath = os.path.join(self.container_staging_dir,
                                           os.path.basename(source_file))
            self.log.info(f"Ingesting from (container) filepath: {source_filepath}")

            # render and execute the final query
            qry = IngestPostgresDockerOperator.QUERIES[self.file_format]
            ingest_query = qry.format(
                self.target_table,      # e.g. 'f_reviews'
                target_columns,         # e.g. 'itunes_id,podcast_id,...' or '*'
                source_filepath         # e.g. '/opt/data/staging/itunes/1313466221.json'
            )

            postgres.run(ingest_query, autocommit=True)
