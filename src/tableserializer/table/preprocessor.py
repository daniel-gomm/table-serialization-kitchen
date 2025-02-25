# Table preprocessors, e.g., remove indices/ids, preprocess strings,...
# Generally, preprocessors can limit the resulting serialization length

from abc import ABC, abstractmethod
from typing import List

from tableserializer.table import Table


class TablePreprocessor(ABC):
    """
    A table preprocessor transforms a table before serialization. Generally, table preprocessors can augment the tabular
    data, compress it (e.g., by removing id columns), ...
    """

    @abstractmethod
    def process(self, table:Table) -> Table:
        """
        Transform a table before serialization.
        :param table: Table to preprocess.
        :type table: Table
        :return: Preprocessed table.
        :rtype: Table
        """
        raise NotImplementedError


class ColumnDroppingPreprocessor(TablePreprocessor):
    """
    Table preprocessor that transforms a table by dropping specified columns.
    """

    def __init__(self, columns_to_drop: List[str]):
        self.columns_to_drop = columns_to_drop


    def process(self, table: Table) -> Table:
        columns_to_drop = [column for column in self.columns_to_drop if column in table.as_dataframe().columns]
        return Table(table.as_dataframe().drop(columns_to_drop, axis=1))


class StringTruncationPreprocessor(TablePreprocessor):
    """
    Table preprocessor that truncates strings in the table to a set maximum length before serialization.
    """

    def __init__(self, max_len: int):
        self.max_len = max_len


    def process(self, table:Table) -> Table:
        table_df = table.as_dataframe().copy()
        for column in table_df.columns:
            if table_df[column].dtype == str:
                table_df[column] = table_df[column].apply(lambda s: s[:self.max_len])
        return Table(table_df)

