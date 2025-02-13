from typing import List, Dict, Self

import pandas as pd

from tte_playground.table.row_sampler import RowSampler, RandomRowSampler, FirstRowSampler, KMeansRowSampler
from tte_playground.table.processor import TableProcessor, JsonTableProcessor, MarkdownTableProcessor


class TableSerializer:

    def __init__(self, include_context: bool = False, context_position: int = 0, include_schema: bool = False,
                 schema_position: int = 1, table_processor: TableProcessor = None, row_sampler: RowSampler = None,
                 table_position: int = 1):
        self.include_context = include_context
        self.include_schema = include_schema
        self.table_processor = table_processor
        self.row_sampler = row_sampler
        self.context_position = context_position
        self.schema_position = schema_position
        self.table_position = table_position

    def _assemble_string(self, context: str, schema: str, table: str) -> str:
        output = ""
        for s, _ in sorted(zip([context, schema, table],
                               [self.context_position, self.schema_position, self.table_position]), key=lambda x: x[1]):
            output += s + "\n"
        return output.replace("\n\n", "\n").strip()


    def serialize_table(self, table: List[Dict[str, str]] | pd.DataFrame | List[List[str]], context: Dict) -> str:
        context_s = ""
        if self.include_context:
            context_s = "Context: " + str(context)
        schema_s = ""
        if self.include_schema:
            schema_s = "Column names: "
            for header in table[0].keys():
                schema_s += header + " , "
            schema_s = schema_s[:-3]
        table_s = ""
        if self.table_processor is not None:
            table_to_serialize = table
            if self.row_sampler is not None:
                table_to_serialize = self.row_sampler.sample(table)
            table_s = "Table: " + self.table_processor.serialize_table(table_to_serialize)
        return self._assemble_string(context_s, schema_s, table_s)


class TableSerializerBuilder:

    def __init__(self):
        self._include_context = False
        self._include_schema = False
        self._table_processor = None
        self._row_sampler = None#
        self._current_position = 0
        self._context_position = 0
        self._schema_position = 0
        self._table_position = 0

    def include_context(self, at: int | None = None) -> Self:
        self._include_context = True
        if at is None:
            self._context_position = self._current_position
            self._current_position += 1
        else:
            self._context_position = at
        return self

    def include_schema(self, at: int | None = None) -> Self:
        self._include_schema = True
        if at is None:
            self._schema_position = self._current_position
            self._current_position += 1
        else:
            self._schema_position = at
        return self

    def with_json_table_processor(self, at: int | None = None) -> Self:
        self._table_processor = JsonTableProcessor()
        if at is None:
            self._table_position = self._current_position
            self._current_position += 1
        else:
            self._table_position = at
        return self

    def with_markdown_table_processor(self, at: int | None = None) -> Self:
        self._table_processor = MarkdownTableProcessor()
        if at is None:
            self._table_position = self._current_position
            self._current_position += 1
        else:
            self._table_position = at
        return self

    def with_random_row_sampler(self, rows_to_sample: int = 10, seed: int = None) -> Self:
        self._row_sampler = RandomRowSampler(rows_to_sample, seed)
        return self

    def with_first_row_sampler(self, rows_to_sample: int = 10) -> Self:
        self._row_sampler = FirstRowSampler(rows_to_sample)
        return self

    def with_kmeans_row_sampler(self, rows_to_sample: int = 10, seed: int = None) -> Self:
        self._row_sampler = KMeansRowSampler(rows_to_sample, seed)
        return self

    def build(self) -> TableSerializer:
        return TableSerializer(self._include_context, self._context_position, self._include_schema, self._schema_position,
                               self._table_processor, self._row_sampler, self._table_position)