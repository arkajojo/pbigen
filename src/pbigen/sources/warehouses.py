"""Concrete SQL warehouse adapters.

Each class builds a SQLAlchemy URL (for read-only introspection here) and the matching
Power BI Power Query (M) expression (for the generated model to connect at refresh time).
Credentials come from explicit args or environment variables — never hard-coded.

Author: Arka Gupta
"""
from __future__ import annotations

import os

from .sql_base import SqlSource


def _env(value: str | None, var: str) -> str | None:
    return value if value is not None else os.environ.get(var)


class PostgresSource(SqlSource):
    kind = "postgres"

    def __init__(self, table, host="localhost", port=5432, database="postgres",
                 schema="public", user=None, password=None):
        self.host, self.port, self.database = host, port, database
        user = _env(user, "PGUSER") or "postgres"
        password = _env(password, "PGPASSWORD") or ""
        url = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{database}"
        super().__init__(url, table, schema=schema)

    def power_query(self) -> str:
        return (
            "let\n"
            f'  Source = PostgreSQL.Database("{self.host}", "{self.database}"),\n'
            f'  Data = Source{{[Schema="{self.db_schema}", Item="{self.table}"]}}[Data]\n'
            "in Data"
        )


class RedshiftSource(SqlSource):
    kind = "redshift"

    def __init__(self, table, host=None, port=5439, database="dev", schema="public",
                 user=None, password=None):
        self.host = _env(host, "REDSHIFT_HOST")
        self.port, self.database = port, database
        user = _env(user, "REDSHIFT_USER") or "awsuser"
        password = _env(password, "REDSHIFT_PASSWORD") or ""
        url = f"redshift+redshift_connector://{user}:{password}@{self.host}:{port}/{database}"
        super().__init__(url, table, schema=schema)

    def power_query(self) -> str:
        return (
            "let\n"
            f'  Source = AmazonRedshift.Database("{self.host}:{self.port}", "{self.database}"),\n'
            f'  Data = Source{{[Schema="{self.db_schema}", Item="{self.table}"]}}[Data]\n'
            "in Data"
        )


class SnowflakeSource(SqlSource):
    kind = "snowflake"

    def __init__(self, table, account=None, warehouse=None, database=None, schema="PUBLIC",
                 user=None, password=None, role=None):
        self.account = _env(account, "SNOWFLAKE_ACCOUNT")
        self.warehouse = _env(warehouse, "SNOWFLAKE_WAREHOUSE")
        self.database = _env(database, "SNOWFLAKE_DATABASE")
        user = _env(user, "SNOWFLAKE_USER")
        password = _env(password, "SNOWFLAKE_PASSWORD")
        role = _env(role, "SNOWFLAKE_ROLE")
        q = f"?warehouse={self.warehouse}" + (f"&role={role}" if role else "")
        url = f"snowflake://{user}:{password}@{self.account}/{self.database}/{schema}{q}"
        super().__init__(url, table, schema=schema)

    def power_query(self) -> str:
        return (
            "let\n"
            f'  Source = Snowflake.Databases("{self.account}.snowflakecomputing.com", "{self.warehouse}"),\n'
            f'  DB = Source{{[Name="{self.database}"]}}[Data],\n'
            f'  Sch = DB{{[Name="{self.db_schema}", Kind="Schema"]}}[Data],\n'
            f'  Data = Sch{{[Name="{self.table}", Kind="Table"]}}[Data]\n'
            "in Data"
        )


class SynapseSource(SqlSource):
    """Azure Synapse / SQL Server / Fabric SQL endpoint (all speak T-SQL)."""

    kind = "synapse"

    def __init__(self, table, server=None, database=None, schema="dbo", user=None, password=None,
                 driver="ODBC Driver 18 for SQL Server"):
        self.server = _env(server, "SYNAPSE_SERVER")
        self.database = _env(database, "SYNAPSE_DATABASE")
        user = _env(user, "SYNAPSE_USER")
        password = _env(password, "SYNAPSE_PASSWORD")
        drv = driver.replace(" ", "+")
        url = f"mssql+pyodbc://{user}:{password}@{self.server}/{self.database}?driver={drv}&Encrypt=yes"
        super().__init__(url, table, schema=schema, quote="[")  # T-SQL uses [brackets]

    def _q(self, ident: str) -> str:  # override: bracket-quoting
        return f"[{ident}]"

    def power_query(self) -> str:
        return (
            "let\n"
            f'  Source = Sql.Database("{self.server}", "{self.database}"),\n'
            f'  Data = Source{{[Schema="{self.db_schema}", Item="{self.table}"]}}[Data]\n'
            "in Data"
        )


class DatabricksSource(SqlSource):
    kind = "databricks"

    def __init__(self, table, host=None, http_path=None, token=None, catalog="hive_metastore",
                 schema="default"):
        self.host = _env(host, "DATABRICKS_HOST")
        self.http_path = _env(http_path, "DATABRICKS_HTTP_PATH")
        self.catalog = catalog
        token = _env(token, "DATABRICKS_TOKEN")
        url = f"databricks://token:{token}@{self.host}?http_path={self.http_path}&catalog={catalog}&schema={schema}"
        super().__init__(url, table, schema=schema, quote="`")

    def _q(self, ident: str) -> str:
        return f"`{ident}`"

    def power_query(self) -> str:
        return (
            "let\n"
            f'  Source = Databricks.Catalogs("{self.host}", "{self.http_path}", null),\n'
            f'  Cat = Source{{[Name="{self.catalog}", Kind="Database"]}}[Data],\n'
            f'  Sch = Cat{{[Name="{self.db_schema}", Kind="Schema"]}}[Data],\n'
            f'  Data = Sch{{[Name="{self.table}", Kind="Table"]}}[Data]\n'
            "in Data"
        )


class ClickHouseSource(SqlSource):
    kind = "clickhouse"

    def __init__(self, table, host=None, port=8443, database="default", user=None, password=None,
                 secure=True):
        self.host = _env(host, "CLICKHOUSE_HOST")
        self.port, self.database, self.secure = port, database, secure
        user = _env(user, "CLICKHOUSE_USER") or "default"
        password = _env(password, "CLICKHOUSE_PASSWORD") or ""
        proto = "clickhouse+native" if port in (9000, 9440) else "clickhouse+http"
        url = f"{proto}://{user}:{password}@{self.host}:{port}/{database}"
        if secure:
            url += "?secure=true"
        super().__init__(url, table, schema=None, quote="`")

    def _q(self, ident: str) -> str:
        return f"`{ident}`"

    def power_query(self) -> str:
        # Power BI connects to ClickHouse via its ClickHouse connector (ODBC under the hood)
        return (
            "let\n"
            f'  Source = ClickHouse.Database("{self.host}", {self.port}, [Database="{self.database}"]),\n'
            f'  Data = Source{{[Name="{self.table}"]}}[Data]\n'
            "in Data"
        )


class AthenaSource(SqlSource):
    """AWS Athena (Presto/Trino SQL over data in S3)."""

    kind = "athena"

    def __init__(self, table, region=None, database="default", s3_staging_dir=None, workgroup="primary"):
        self.region = _env(region, "AWS_REGION") or "us-east-1"
        self.database = database
        self.s3_staging_dir = _env(s3_staging_dir, "ATHENA_S3_STAGING_DIR")
        self.workgroup = workgroup
        url = (f"awsathena+rest://@athena.{self.region}.amazonaws.com:443/{database}"
               f"?s3_staging_dir={self.s3_staging_dir}&work_group={workgroup}")
        super().__init__(url, table, schema=database, quote='"')

    def power_query(self) -> str:
        # Power BI's Amazon Athena connector is DSN-based; users set the DSN name.
        return (
            "let\n"
            '  Source = AmazonAthena.Databases("Athena"),  // replace with your Athena ODBC DSN\n'
            f'  DB = Source{{[Name="{self.database}"]}}[Data],\n'
            f'  Data = DB{{[Name="{self.table}"]}}[Data]\n'
            "in Data"
        )
