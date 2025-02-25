# Table preprocessors, e.g., remove indices/ids, preprocess strings,...
# Generally, preprocessors can limit the resulting serialization length

from abc import ABC, abstractmethod
from typing import List

from tableserializer.table import Table


class TablePreprocessor(ABC):

    @abstractmethod
    def process(self, table:Table) -> Table:
        raise NotImplementedError


class ColumnDroppingPreprocessor(TablePreprocessor):

    def __init__(self, columns_to_drop: List[str]):
        self.columns_to_drop = columns_to_drop


    def process(self, table: Table) -> Table:
        columns_to_drop = [column for column in self.columns_to_drop if column in table.as_dataframe().columns]
        return Table(table.as_dataframe().drop(columns_to_drop, axis=1))


class StringLimitPreprocessor(TablePreprocessor):

    def __init__(self, max_len: int):
        self.max_len = max_len


    def process(self, table:Table) -> Table:
        table_df = table.as_dataframe().copy()
        for column in table_df.columns:
            if table_df[column].dtype == str:
                table_df[column] = table_df[column].apply(lambda s: s[:self.max_len])
        return Table(table_df)

