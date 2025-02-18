from abc import abstractmethod, ABC
from typing import List, Dict

import pandas as pd

from table_serialization_kitchen.table import Table

class TableSerializer(ABC):

    @abstractmethod
    def serialize_table(self, table: Table) -> str:
        raise NotImplementedError


class JsonTableSerializer(TableSerializer):

    def serialize_table(self, table: Table) -> str:
        """
        Converts a table into a json representation of its contents
        """
        table_string = ""
        for index, row in enumerate(table.as_list_of_dicts()):
            table_string += f'{{"{index}": {{'
            for key, value in row.items():
                table_string += f'"{key}": "{value}", '
            table_string = table_string[:-2] + f'}}}}\n'
        return table_string[:-1]

class MarkdownTableSerializer(TableSerializer):

    def serialize_table(self, table: Table) -> str:
        """
        Converts a table into a markdown representation of its contents
        """
        table_string = "| "
        divider_string = "|"
        for header in table.as_dataframe().columns:
            table_string += f'{header} | '
            divider_string += f'---|'
        table_string += divider_string + " "
        for row in table.as_list_of_dicts():
            table_string = table_string[:-1] + "\n| "
            for value in row.values():
                table_string += f'{value} | '
        return table_string[:-1]

# TODO: Add CSV, HTML serializer
