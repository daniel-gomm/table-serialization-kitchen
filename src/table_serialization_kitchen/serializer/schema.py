from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

import pandas as pd


class SchemaSerializer(ABC):

    def serialize_schema(self, table: List[Dict[str, str]] | pd.DataFrame | List[List[str]],
                         metadata: Optional[Dict[str, Any]] = None) -> str:
        if all(isinstance(row, dict) for row in table):
            table = pd.DataFrame(table)
        elif all(isinstance(row, list) for row in table):
            table = pd.DataFrame(table[1:], columns=table[0])
        return self._serialize_schema(table, metadata)

    @abstractmethod
    def _serialize_schema(self, table: pd.DataFrame, metadata: Optional[Dict[str, Any]] = None) -> str:
        raise NotImplementedError



class ColumnNameSchemaSerializer(SchemaSerializer):

    def __init__(self, column_name_separator: str = "|"):
        self.column_name_separator = column_name_separator


    def _serialize_schema(self, table: pd.DataFrame, metadata: Optional[Dict[str, Any]] = None) -> str:
        columns = table.columns
        return f" {self.column_name_separator} ".join(columns)


class SQLSchemaSerializer(SchemaSerializer):

    def __init__(self, metadata_table_name_field: Optional[str] = None, default_table_name: str = "table"):
        self.metadata_table_name_field = metadata_table_name_field
        self.default_table_name = default_table_name

    def _serialize_schema(self, table: pd.DataFrame, metadata: Optional[Dict[str, Any]] = None) -> str:
        table_name = self.default_table_name
        if self.metadata_table_name_field is not None:
            table_name = metadata[self.metadata_table_name_field]
        return pd.io.sql.get_schema(table.reset_index(), table_name)
