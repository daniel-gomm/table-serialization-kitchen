# Table preprocessors, e.g., remove indices/ids, preprocess strings,...
# Generally, preprocessors can limit the resulting serialization length

from abc import ABC, abstractmethod
from typing import List, Optional

import pandas as pd


class TablePreprocessor(ABC):

    @abstractmethod
    def process(self, table:pd.DataFrame, **kwargs) -> pd.DataFrame:
        raise NotImplementedError


class ColumnDroppingPreprocessor(TablePreprocessor):

    def __init__(self, columns_to_drop: Optional[List[str]] = None):
        if columns_to_drop is None:
            columns_to_drop = []
        self.columns_to_drop = columns_to_drop


    def process(self, table:pd.DataFrame, columns_to_drop: Optional[List[str]] = None, **kwargs) -> pd.DataFrame:
        if columns_to_drop is None:
            columns_to_drop = self.columns_to_drop
        else:
            columns_to_drop = columns_to_drop + self.columns_to_drop
        columns_to_drop = [column for column in columns_to_drop if column in table.columns]
        return table.drop(columns_to_drop, axis=1)


class StringLimitPreprocessor(TablePreprocessor):

    def __init__(self, max_len: Optional[int] = None):
        self.max_len = max_len


    def process(self, table:pd.DataFrame, max_len: Optional[int] = None, **kwargs) -> pd.DataFrame:
        if max_len is None:
            max_len = self.max_len
        if max_len is None:
            raise ValueError("'max_len' has to be specified either on instantiation of the preprocessor or "
                             "when calling 'process'.")
        table = table.copy()
        for column in table.columns:
            if table[column].dtype == str:
                table[column] = table[column].apply(lambda s: s[:max_len])
        return table

