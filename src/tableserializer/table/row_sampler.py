import random
from abc import abstractmethod, ABC

import numpy as np
from numpy.random import PCG64, SeedSequence
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.impute import SimpleImputer

from tableserializer.serializer.common import SignatureProvidingInstance
from tableserializer.table import Table

class RowSampler(ABC, SignatureProvidingInstance):
    """
    A row sampler selects a subset of rows based on a predefined policy.

    :param rows_to_sample: Number of rows to sample.
    :type rows_to_sample: int
    """

    def __init__(self, rows_to_sample: int = 10):
        self.rows_to_sample = rows_to_sample


    @abstractmethod
    def sample(self, table: Table) -> Table:
        """
        Sample rows from the given table.

        :param table: The table to sample from.
        :type table: Table
        :return: Table consisting of the sampled rows.
        :rtype: Table
        """
        raise NotImplementedError

class RandomRowSampler(RowSampler):
    """
    Samples rows randomly from the given table.

    :param rows_to_sample: Number of rows to sample.
    :type rows_to_sample: int
    :param deterministic: Set to true to apply a deterministic seed for the sampling process. This ensures replicability.
    :type deterministic: bool
    """

    def __init__(self, rows_to_sample: int = 10, deterministic: bool = True):
        super().__init__(rows_to_sample)
        self.deterministic = deterministic
        self.random = random.Random()

    def sample(self, table: Table) -> Table:
        table_df = table.as_dataframe()
        if len(table_df) <= self.rows_to_sample:
            return table
        seed = None
        if self.deterministic:
            seed = len(table_df) * len(table_df.iloc[0])
        sample_df = table_df.sample(n=self.rows_to_sample, replace=False, random_state=seed)
        return Table(sample_df.reset_index(drop=True))

class FirstRowSampler(RowSampler):
    """
    Sample the first rows from the given table.

    :param rows_to_sample: Number of rows to sample.
    :type rows_to_sample: int
    """

    def sample(self, table: Table) -> Table:
        return Table(table.as_dataframe()[:self.rows_to_sample].reset_index(drop=True))

class KMeansRowSampler(RowSampler):
    """
    Use k-means clustering to sample a diverse set of rows.

    :param rows_to_sample: Number of rows to sample.
    :type rows_to_sample: int
    :param deterministic: Set to true to apply a deterministic seed for the sampling process.
    :type deterministic: bool
    """

    def __init__(self, rows_to_sample: int = 10, deterministic: bool = True):
        super().__init__(rows_to_sample)
        self.deterministic = deterministic
        self.imputer = SimpleImputer(strategy='most_frequent')

    def sample(self, table: Table) -> Table:
        table_df = table.as_dataframe()
        if len(table_df) <= self.rows_to_sample:
            return table
        seed = None
        if self.deterministic:
            seed = len(table_df) * len(table_df.iloc[0])
        random_generator = np.random.Generator(PCG64(SeedSequence(seed)))
        df_copy = table_df.copy()
        for col in table_df.columns:
            unique_values = table_df[col].unique().shape[0]
            if unique_values == table_df.shape[0] or unique_values == 1:
                # Handle id and id-like columns -> dismiss them because they hold no information for clustering
                # Handle columns with only a single value, which makes them not informative as well.
                df_copy.drop(col, axis=1, inplace=True)
            elif table_df[col].isna().sum() > 0:
                # Handle columns with NaN value -> impute missing values
                if df_copy[col].dtype == "object":
                    col_np = df_copy[col].to_numpy()
                    col_np[col_np == None] = "None"
                    df_copy[col] = col_np
                else:
                    df_copy[col] = self.imputer.fit_transform(table_df[col].to_numpy().reshape(-1, 1))
        if df_copy.shape[1] == 0:
            # In case there are no columns with relevant information k-Means is equivalent to random sampling
            return RandomRowSampler(rows_to_sample=self.rows_to_sample).sample(table)

        df_encoded = pd.get_dummies(df_copy, drop_first=True)

        kmeans = KMeans(n_clusters=self.rows_to_sample, random_state=seed).fit(df_encoded)

        table_df['cluster'] = kmeans.labels_

        sampled_rows = (table_df.groupby('cluster').apply(lambda x: x.sample(1, random_state=random_generator))
                        .reset_index(drop=True).drop('cluster', axis=1))

        return Table(sampled_rows)
