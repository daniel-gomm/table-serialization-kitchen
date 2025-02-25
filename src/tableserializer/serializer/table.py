from abc import abstractmethod, ABC

from tableserializer.table import Table

class RawTableSerializer(ABC):
    """
    Serializer for serializing raw tables to string representations.
    """

    @abstractmethod
    def serialize_table(self, table: Table) -> str:
        """
        Serialize a raw table to string.
        :param table: Raw table to serialize.
        :type table: Table
        :return: Serialized raw table.
        :rtype: str
        """
        raise NotImplementedError


class JsonRawTableSerializer(RawTableSerializer):
    """
    Serializer for serializing raw tables to row-wise JSON representations.
    """

    def serialize_table(self, table: Table) -> str:
        table_string = ""
        for index, row in enumerate(table.as_list_of_dicts()):
            table_string += f'{{"{index}": {{'
            for key, value in row.items():
                table_string += f'"{key}": "{value}", '
            table_string = table_string[:-2] + f'}}}}\n'
        return table_string[:-1]

class MarkdownRawTableSerializer(RawTableSerializer):
    """
    Serializer for serializing raw tables to markdown representations.
    """

    def serialize_table(self, table: Table) -> str:
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
