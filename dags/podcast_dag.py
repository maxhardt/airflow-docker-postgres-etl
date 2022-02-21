#!/usr/bin/python3
import datetime
import os

from airflow import DAG
from airflow.utils.task_group import TaskGroup
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator

from dotenv import load_dotenv
from extract_ids import extract_podcast_ids
from extract_itunes import extract_itunes_metadata
from extract_tables import extract_sqlite_table
from operators import IngestPostgresDockerOperator


# set env vars
load_dotenv(".env")
KAGGLE_CONFIG_DIR = os.path.abspath(os.environ["KAGGLE_CONFIG_DIR"])
BASE_STAGING_DIR = os.path.abspath(os.environ["BASE_STAGING_DIR"])
KAGGLE_STAGING_DIR = os.path.abspath(os.environ["KAGGLE_STAGING_DIR"])
TABLES_STAGING_DIR = os.path.abspath(os.environ["TABLES_STAGING_DIR"])
ITUNES_STAGING_DIR = os.path.abspath(os.environ["ITUNES_STAGING_DIR"])
CONTAINER_STAGING_DIR = os.path.abspath(os.environ["CONTAINER_STAGING_DIR"])

default_args = {
    "owner": "airflow",
    "depends_on_past": False
}

with DAG(
    dag_id="podcast_reviews",
    default_args=default_args,
    description="Podcast review dataset with iTunes lookup API",
    schedule_interval=datetime.timedelta(days=30),
    start_date=datetime.datetime(2022, 1, 1),
    catchup=False,
) as dag:

    # cleans staging data (but leaves the raw kaggle dataset)
    # and removes the docker container for clean pipeline runs
    cleanup = BashOperator(
        task_id="clean_up",
        bash_command="""
        rm {}/*.csv;
        rm {}/*.json;
        if [[ $(docker ps -a -f "name=podcastdb") ]]; then docker rm -f podcastdb; fi
        """.format(
            TABLES_STAGING_DIR,
            ITUNES_STAGING_DIR
        )
    )

    create_database = BashOperator(
        task_id="create_database",
        bash_command="""
        docker run \
            -e POSTGRES_PASSWORD={} -e POSTGRES_DB={} \
            -v {}:{} \
            -p {}:{} -d --name podcastdb postgres
        """.format(
            os.environ["PASSWORD"],
            os.environ["DB"],
            BASE_STAGING_DIR, CONTAINER_STAGING_DIR,
            os.environ["PORT"], os.environ["PORT"])
    )

    create_tables = PostgresOperator(
        task_id="create_tables",
        postgres_conn_id="postgres",
        autocommit=True,
        sql="./sql/create_tables.sql"
    )

    download_kaggle = BashOperator(
        task_id="download_kaggle",
        bash_command="""
        conda run -n {} kaggle datasets download {} --path {} --unzip
        """.format(
            os.environ["CONDA_ENV_NAME"],
            os.environ["KAGGLE_DATASET"],
            KAGGLE_STAGING_DIR
        ),
        env={"KAGGLE_CONFIG_DIR": KAGGLE_CONFIG_DIR}
    )

    with TaskGroup(group_id="extract_source_tables") as extract_tables_tasks:
        for table_name in ["reviews", "podcasts", "categories"]:
            extract_table = PythonOperator(
                task_id=f"extract_table_{table_name}",
                python_callable=extract_sqlite_table, 
                op_kwargs={
                    "sqlite_filepath": os.path.join(KAGGLE_STAGING_DIR, "database.sqlite"),
                    "table_name": table_name,
                    "staging_dir": TABLES_STAGING_DIR,
                    "cols_to_datetime": ["created_at"] if table_name == "reviews" else None
                }
            )

    extract_podcasts = PythonOperator(
        task_id="extract_podcast_ids",
        python_callable=extract_podcast_ids,
        op_kwargs={
            "sqlite_filepath": os.path.join(KAGGLE_STAGING_DIR, "database.sqlite"),
            "table_name": "podcasts",
            "staging_dir": TABLES_STAGING_DIR,
            "file_name": "podcast_ids.csv"
        }
    )

    extract_itunes_metadata = PythonOperator(
        task_id="extract_itunes_metadata",
        python_callable=extract_itunes_metadata,
        op_kwargs={
            "itunes_lookup_url": "https://itunes.apple.com/lookup",
            "itunes_ids_filepath": os.path.join(TABLES_STAGING_DIR, "podcast_ids.csv"),
            "staging_dir": ITUNES_STAGING_DIR,
            "n_limit_ids": 10
        }
    )

    with TaskGroup(group_id="load_staging_tables") as load_staging_tasks:
        for staging_table, target_columns, staging_dir, container_staging_dir, file_pattern, file_format in [
            (
                "s_reviews",
                ("podcast_id", "title", "content", "rating", "author_id", "created_at"),
                TABLES_STAGING_DIR,
                os.path.join(CONTAINER_STAGING_DIR, "tables"),
                "*reviews.csv",
                "csv"
            ),
            (
                "s_podcasts_kaggle",
                 None,
                 TABLES_STAGING_DIR,
                 os.path.join(CONTAINER_STAGING_DIR, "tables"),
                 "*podcasts.csv",
                 "csv"
            ),
            (
                "s_podcasts_itunes",
                ("metadata", ),
                ITUNES_STAGING_DIR,
                os.path.join(CONTAINER_STAGING_DIR, "itunes"),
                "*.json",
                "json"
            )
        ]:
            ingest_staging_table = IngestPostgresDockerOperator(
                task_id=f"ingest_staging_table_{staging_table}",
                connection_id="postgres",
                target_table=staging_table,
                target_columns=target_columns,
                staging_dir=staging_dir,
                container_staging_dir=container_staging_dir,
                file_pattern=file_pattern,
                file_format=file_format
            )

    with TaskGroup(group_id="transform_final_tables") as transform_tasks:
        for final_table, sql in [
            ("d_podcasts", "./sql/transform_podcasts.sql"),
            ("f_reviews", "./sql/transform_reviews.sql")
        ]:
            transform_task = PostgresOperator(
                task_id=f"transform_{final_table}",
                postgres_conn_id="postgres",
                sql=sql
            )

    # setup
    cleanup >> [create_database,  download_kaggle]
    create_database >> create_tables

    # transforn, extract
    download_kaggle >> extract_tables_tasks
    download_kaggle >> extract_podcasts
    extract_podcasts >> extract_itunes_metadata

    # load
    create_tables >> load_staging_tasks
    extract_tables_tasks >> load_staging_tasks
    extract_itunes_metadata >> load_staging_tasks

    # transform
    load_staging_tasks >> transform_tasks
