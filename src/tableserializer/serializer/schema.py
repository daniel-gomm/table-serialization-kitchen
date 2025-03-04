from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

import pandas as pd

from tableserializer.serializer.common import SignatureProvidingInstance
from tableserializer.table import Table


class SchemaSerializer(ABC, SignatureProvidingInstance):
    """
    Serializer for the schema captured in the table.
    """

    @abstractmethod
    def serialize_schema(self, table: Table, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Serialize the schema captured in the table.

        :param table: The table whose schema should be serialized.
        :type table: Table
        :param metadata: Optional metadata about the table.
        :type metadata: Optional[Dict[str, Any]]
        :return: Serialized schema string.
        :rtype: str
        """
        raise NotImplementedError



class ColumnNameSchemaSerializer(SchemaSerializer):
    """
    Schema serializer that serializes the schema as a separated list of column names.

    :param column_name_separator: Separator between column names.
    :type column_name_separator: str
    """

    def __init__(self, column_name_separator: str = "|"):
        self.column_name_separator = column_name_separator

    def serialize_schema(self, table: Table, metadata: Optional[Dict[str, Any]] = None) -> str:
        columns = table.as_dataframe().columns
        return f" {self.column_name_separator} ".join(columns)


class SQLSchemaSerializer(SchemaSerializer):
    """
    Schema serializer that serializes the schema as a SQL CREATE TABLE statement.

    :param metadata_table_name_field: Optional: Provide the name of the field in the metadata that specifies the table name.
    :type metadata_table_name_field: Optional[str]
    :param default_table_name: Default table name used in schema when no specific table name is available through the metadata.
    :type default_table_name: str
    """

    def __init__(self, metadata_table_name_field: Optional[str] = None, default_table_name: str = "table"):
        self.metadata_table_name_field = metadata_table_name_field
        self.default_table_name = default_table_name

    def serialize_schema(self, table: Table, metadata: Optional[Dict[str, Any]] = None) -> str:
        table_name = self.default_table_name
        if self.metadata_table_name_field is not None:
            table_name = metadata[self.metadata_table_name_field]
        return pd.io.sql.get_schema(table.as_dataframe().reset_index(), table_name)
