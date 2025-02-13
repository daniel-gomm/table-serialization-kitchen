import random
from abc import abstractmethod, ABC
from typing import List, Dict

import numpy as np
from numpy.random import PCG64, SeedSequence
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.impute import SimpleImputer

from tte_playground.table.processor import _dataframe_to_list_of_dicts


class RowSampler(ABC):

    def __init__(self, rows_to_sample: int = 10):
        self.rows_to_sample = rows_to_sample


    @abstractmethod
    def sample(self, table: List[Dict[str, str]]):
        raise NotImplementedError

class RandomRowSampler(RowSampler):

    def __init__(self, rows_to_sample: int = 10, seed: int = None):
        super().__init__(rows_to_sample)
        self.random = random.Random(seed)

    def sample(self, table: List[Dict[str, str]]) -> List[Dict[str, str]]:
        if len(table) <= self.rows_to_sample:
            return table
        sampled_indices = self.random.sample(range(len(table)), self.rows_to_sample)
        sampled_slice = [table[index] for index in sampled_indices]
        return sampled_slice

class FirstRowSampler(RowSampler):

    def sample(self, table: List[Dict[str, str]]) -> List[Dict[str, str]]:
        return table[:self.rows_to_sample]

class KMeansRowSampler(RowSampler):

    def __init__(self, rows_to_sample: int = 10, seed: int = None):
        super().__init__(rows_to_sample)
        self.seed = seed
        self.imputer = SimpleImputer(strategy='most_frequent')
        ss = SeedSequence(seed)
        self.random_generator = np.random.Generator(PCG64(ss))

    def sample(self, table: List[Dict[str, str]]) -> List[Dict[str, str]]:
        if len(table) <= self.rows_to_sample:
            return table
        df = pd.DataFrame(table)
        df_copy = df.copy()
        for col in df.columns:
            unique_values = df[col].unique().shape[0]
            if unique_values == df.shape[0] or unique_values == 1:
                # Handle id and id-like columns -> dismiss them because they hold no information for clustering
                # Handle columns with only a single value, which makes them not informative as well.
                df_copy.drop(col, axis=1, inplace=True)
            elif df[col].isna().sum() > 0:
                # Handle columns with NaN value -> impute missing values
                if df_copy[col].dtype == "object":
                    col_np = df_copy[col].to_numpy()
                    col_np[col_np == None] = "None"
                    df_copy[col] = col_np
                else:
                    df_copy[col] = self.imputer.fit_transform(df[col].to_numpy().reshape(-1, 1))
        if df_copy.shape[1] == 0:
            # In case there are no columns with relevant information k-Means is equivalent to random sampling
            return RandomRowSampler(rows_to_sample=self.rows_to_sample, seed=self.seed).sample(table)

        df_encoded = pd.get_dummies(df_copy, drop_first=True)

        kmeans = KMeans(n_clusters=self.rows_to_sample, random_state=self.seed).fit(df_encoded)

        df['cluster'] = kmeans.labels_

        sampled_rows = (df.groupby('cluster').apply(lambda x: x.sample(1, random_state=self.random_generator))
                        .reset_index(drop=True).drop('cluster', axis=1))

        return _dataframe_to_list_of_dicts(sampled_rows)
