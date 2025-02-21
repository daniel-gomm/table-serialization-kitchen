from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

import pandas as pd

from tableserializer.table import Table


class SchemaSerializer(ABC):

    @abstractmethod
    def serialize_schema(self, table: Table, metadata: Optional[Dict[str, Any]] = None) -> str:
        raise NotImplementedError



class ColumnNameSchemaSerializer(SchemaSerializer):

    def __init__(self, column_name_separator: str = "|"):
        self.column_name_separator = column_name_separator

    def serialize_schema(self, table: Table, metadata: Optional[Dict[str, Any]] = None) -> str:
        columns = table.as_dataframe().columns
        return f" {self.column_name_separator} ".join(columns)


class SQLSchemaSerializer(SchemaSerializer):

    def __init__(self, metadata_table_name_field: Optional[str] = None, default_table_name: str = "table"):
        self.metadata_table_name_field = metadata_table_name_field
        self.default_table_name = default_table_name

    def serialize_schema(self, table: Table, metadata: Optional[Dict[str, Any]] = None) -> str:
        table_name = self.default_table_name
        if self.metadata_table_name_field is not None:
            table_name = metadata[self.metadata_table_name_field]
        return pd.io.sql.get_schema(table.as_dataframe().reset_index(), table_name)
