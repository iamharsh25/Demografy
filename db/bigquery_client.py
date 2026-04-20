"""
BigQuery client for Demografy Insights Chatbot.

What this file does:
- Loads credentials from the .env file
- Creates a connection to Google BigQuery
- Provides a simple run_query() function that runs SQL and returns results as a table
"""

import os
from google.cloud import bigquery
from google.oauth2 import service_account
from dotenv import load_dotenv
import pandas as pd

# Load all variables from the .env file into the environment
load_dotenv()


def get_client() -> bigquery.Client:
    """
    Creates and returns a BigQuery client using the service account JSON key.

    The path to the JSON key is read from the GOOGLE_APPLICATION_CREDENTIALS
    environment variable set in your .env file.

    Returns:
        bigquery.Client: An authenticated BigQuery client ready to run queries.

    Raises:
        FileNotFoundError: If the service account JSON file doesn't exist at the given path.
        Exception: If authentication fails.
    """
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    if not credentials_path:
        raise ValueError(
            "GOOGLE_APPLICATION_CREDENTIALS is not set in your .env file. "
            "Please add the path to your service account JSON key."
        )

    if not os.path.exists(credentials_path):
        raise FileNotFoundError(
            f"Service account JSON file not found at: {credentials_path}\n"
            "Please check the path in your .env file."
        )

    credentials = service_account.Credentials.from_service_account_file(
        credentials_path,
        scopes=["https://www.googleapis.com/auth/bigquery"],
    )

    project = os.getenv("BIGQUERY_PROJECT", "demografy")

    return bigquery.Client(credentials=credentials, project=project)


def run_query(sql: str) -> pd.DataFrame:
    """
    Runs a SQL query against BigQuery and returns the result as a DataFrame.

    A DataFrame is like a table — rows and columns — that Python can work with easily.

    Args:
        sql (str): The SQL query string to run.

    Returns:
        pd.DataFrame: The query results as a table.

    Example:
        df = run_query("SELECT sa2_name, kpi_2_val FROM demografy.prod_tables.a_master_view LIMIT 5")
        print(df)
    """
    client = get_client()
    query_job = client.query(sql)
    result = query_job.result()
    return result.to_dataframe()
