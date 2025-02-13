from abc import abstractmethod, ABC
from typing import List, Dict

import pandas as pd


def _dataframe_to_list_of_dicts(df: pd.DataFrame) -> List[Dict[str, str]]:
    table_list = [{}] * len(df)
    for column in df.columns:
        for index, value in enumerate(df[column]):
            table_list[index][column] = value
    return table_list

def _nested_list_to_list_of_dicts(nested_list: List[Dict[str, str]]) -> List[Dict[str, str]]:
    table_list = []
    for row in nested_list[1:]:
        row_dict = {}
        for index, header in enumerate(nested_list[0]):
            row_dict[header] = row[index]
        table_list.append(row_dict)
    return table_list

class TableProcessor(ABC):

    def serialize_table(self, table: List[Dict[str, str]] | pd.DataFrame | List[List[str]]) -> str:
        if type(table) == pd.DataFrame:
            table = _dataframe_to_list_of_dicts(table)
        elif all(isinstance(row, list) for row in table):
            table = _nested_list_to_list_of_dicts(table)
        return self._serialize_table(table)

    @abstractmethod
    def _serialize_table(self, table: List[Dict]) -> str:
        raise NotImplementedError

class SchemaSerializer(ABC):

    def serialize_schema(self, table: List[Dict[str, str]] | pd.DataFrame | List[List[str]]) -> str:
        #TODO: Transform table to correct format
        return self._serialize_schema(table)

    @abstractmethod
    def _serialize_schema(self, table: List[Dict]) -> str:
        raise NotImplementedError


class ColumnNameSchemaSerializer(SchemaSerializer):
    #TODO: Implement
    raise NotImplementedError


class SQLSchemaSerializer(SchemaSerializer):
    #TODO: Implement
    raise NotImplementedError


class JsonTableProcessor(TableProcessor):

    def _serialize_table(self, table: List[Dict[str, str]]) -> str:
        """
        Converts a table into a json representation of its contents
        """
        table_string = ""
        for index, row in enumerate(table):
            table_string += f'{{"{index}": {{'
            for key, value in row.items():
                table_string += f'"{key}": "{value}", '
            table_string = table_string[:-2] + f'}}}}\n'
        return table_string[:-1]

class MarkdownTableProcessor(TableProcessor):

    def _serialize_table(self, table: List[Dict]) -> str:
        """
        Converts a table into a markdown representation of its contents
        """
        table_string = "| "
        divider_string = "|"
        for header in table[0].keys():
            table_string += f'{header} | '
            divider_string += f'---|'
        table_string += divider_string + " "
        for row in table:
            table_string = table_string[:-1] + "\n| "
            for value in row.values():
                table_string += f'{value} | '
        return table_string[:-1]