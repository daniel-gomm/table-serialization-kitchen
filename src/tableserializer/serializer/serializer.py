from typing import List, Dict, Optional, Any

import pandas as pd
from tableserializer.serializer.common import sanitize_string

from tableserializer.table import Table
from tableserializer import SerializationRecipe
from tableserializer.serializer.metadata import MetadataSerializer
from tableserializer.table.preprocessor import TablePreprocessor
from tableserializer.table.row_sampler import RowSampler
from tableserializer.serializer.table import RawTableSerializer
from tableserializer.serializer.schema import SchemaSerializer


class Serializer:
    """
    Serializer that serializes a given table according to a user-specified format.

    :param recipe: The recipe detailing the serialization.
    :type recipe: SerializationRecipe
    :param metadata_serializer: Serializer for the table metadata. Only needed if there is metadata placeholder in the recipe.
    :type metadata_serializer: MetadataSerializer
    :param schema_serializer: Serializer for the table schema. Only needed if there is schema placeholder in the recipe.
    :type schema_serializer: SchemaSerializer
    :param table_serializer: Serializer for the raw table. Only needed if there is table placeholder in the recipe.
    :type table_serializer: RawTableSerializer
    :param row_sampler: Optional module that samples a number of rows from the raw table before serializing.
    :type row_sampler: RowSampler
    :param table_preprocessors: Optional list of table preprocessors that transform the table before serialization.
    :type table_preprocessors: List[TablePreprocessor]
    """

    def __init__(self, recipe: SerializationRecipe, metadata_serializer: Optional[MetadataSerializer] = None,
                 schema_serializer: Optional[SchemaSerializer] = None,
                 table_serializer: Optional[RawTableSerializer] = None, row_sampler: Optional[RowSampler] = None,
                 table_preprocessors: Optional[List[TablePreprocessor]] = None):
        self.recipe = recipe
        self.metadata_serializer = metadata_serializer
        self.schema_serializer = schema_serializer
        self.table_serializer = table_serializer
        self.row_sampler = row_sampler
        if table_preprocessors is None:
            table_preprocessors = []
        self.table_preprocessors = table_preprocessors

    def serialize(self, table: List[Dict[str, str]] | pd.DataFrame | List[List[str]], metadata: Dict[str, Any]) -> str:
        """
        Serialize a given table.

        :param table: Table to serialize.
        :type table: Table
        :param metadata: Metadata of the table to serialize.
        :type metadata: Dict[str, Any]
        :return: String serialization of the table.
        :rtype: str
        """
        table = Table(table)
        kwargs = {}
        if self.metadata_serializer is not None:
            kwargs["metadata_contents"] = self.metadata_serializer.serialize_metadata(metadata)
        if self.schema_serializer is not None:
            kwargs["schema_contents"] = self.schema_serializer.serialize_schema(table, metadata)
        if self.table_serializer is not None:
            sub_table = table
            for table_preprocessor in [processor for processor in self.table_preprocessors
                                       if processor.apply_before_row_sampling]:
                sub_table = table_preprocessor.process(sub_table)
            if self.row_sampler is not None:
                sub_table = self.row_sampler.sample(sub_table)
            for table_preprocessor in [processor for processor in self.table_preprocessors
                                       if not processor.apply_before_row_sampling]:
                sub_table = table_preprocessor.process(sub_table)
            kwargs["table_contents"] = self.table_serializer.serialize_raw_table(sub_table)
        return self.recipe.cook_recipe(**kwargs)

    def __str__(self) -> str:
        signature = str(self.recipe)
        if self.metadata_serializer is not None:
            signature += "_" + str(self.metadata_serializer)
        if self.schema_serializer is not None:
            signature += "_" + str(self.schema_serializer)
        if self.table_serializer is not None:
            signature += "_" + str(self.table_serializer)
            if self.row_sampler is not None:
                signature += "_" + str(self.row_sampler)
        if len(self.table_preprocessors) > 0:
            for table_preprocessor in self.table_preprocessors:
                signature += "_" + str(table_preprocessor)
        return sanitize_string(signature)
