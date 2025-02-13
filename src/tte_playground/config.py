from typing import Literal, Optional, Self, List

import yaml
from pydantic import BaseModel

from tte_playground.serializer import TableSerializer, TableSerializerBuilder


class TableSerializationConfig(BaseModel):
    serialization_format: Literal['json', 'markdown']
    row_sampling_strategy: Optional[Literal['random', 'first', 'k-means']] = None
    row_samples_per_table: Optional[int] = None

class ExperimentConfig(BaseModel):
    embedding_model_name: str
    include_context: bool
    context_position: Optional[int] = None
    include_schema: bool
    schema_position: Optional[int] = None
    table_position: Optional[int] = None
    table_serializer: Optional[TableSerializationConfig] = None

    def get_serializer(self) -> TableSerializer:
        builder = TableSerializerBuilder()
        if self.include_context:
            builder.include_context(self.context_position)
        if self.include_schema:
            builder.include_schema(self.schema_position)
        if self.table_serializer is not None:
            if self.table_serializer.serialization_format == 'markdown':
                builder.with_markdown_table_processor(self.table_position)
            elif self.table_serializer.serialization_format == 'json':
                builder.with_json_table_processor(self.table_position)
            else:
                raise AttributeError("Supported serialization formats are 'markdown' or 'json''")
            # Add row-sampler
            if self.table_serializer.row_sampling_strategy == 'random':
                builder.with_random_row_sampler(self.table_serializer.row_samples_per_table)
            elif self.table_serializer.row_sampling_strategy == 'first':
                builder.with_first_row_sampler(self.table_serializer.row_samples_per_table)
            elif self.table_serializer.row_sampling_strategy == 'k-means': # TODO: Fix
                builder.with_kmodes_row_sampler(self.table_serializer.row_samples_per_table)
            else:
                raise AttributeError("Supported sampling strategies are 'random', 'first', 'k-means'")

        return builder.build()

    def _get_included_parts(self) -> List[str]:
        included_parts = [(position, name) for position, name, included in [
            (self.context_position, 'context', self.include_context),
            (self.schema_position, 'schema', self.include_schema),
            (self.table_position, 'table', self.table_serializer is not None)] if included]
        return [name for _, name in sorted(included_parts, key=lambda x: x[0])]

    def get_experiment_slug(self):
        slug = self.embedding_model_name.lower().replace(' ', '_').replace('.', '_').replace('-', '_')
        for part in self._get_included_parts():
            slug += f'_{part}'
        if self.table_serializer is not None:
            slug += f'_{self.table_serializer.serialization_format}'
            if self.table_serializer.row_sampling_strategy is not None:
                slug += f'_{self.table_serializer.row_sampling_strategy}'
                if self.table_serializer.row_samples_per_table is not None:
                    slug += f'_{self.table_serializer.row_samples_per_table}_samples'
        return slug

    def __str__(self) -> str:
        description = "Embedding model: " + self.embedding_model_name + " | Contents: "
        for part in self._get_included_parts():
            description += f'>{part}'
        if self.table_serializer is not None:
            description += f' | Format: {self.table_serializer.serialization_format}'
            if self.table_serializer.row_sampling_strategy is not None:
                description += f' | Row sampling: {self.table_serializer.row_sampling_strategy}'
                if self.table_serializer.row_samples_per_table is not None:
                    description += f' | #Samples: {self.table_serializer.row_samples_per_table}'
        return description

class ExperimentConfigBuilder:

    def __init__(self, embedding_model_name: str, include_context: bool, include_schema: bool):
        self.config = ExperimentConfig(embedding_model_name=embedding_model_name, include_context=include_context,
                                       include_schema=include_schema)

    def context_position(self, position: int) -> Self:
        self.config.context_position = position
        return self

    def schema_position(self, position: int) -> Self:
        self.config.schema_position = position
        return self

    def table_position(self, position: int) -> Self:
        self.config.table_position = position
        return self

    def table_serializer(self, serializer: Literal['json', 'markdown']) -> Self:
        self.config.table_serializer = TableSerializationConfig(serialization_format=serializer)
        return self

    def row_sampling_strategy(self, strategy: Literal['random', 'first', 'k-means']) -> Self:
        self.config.table_serializer.row_sampling_strategy = strategy
        return self

    def row_samples_per_table(self, samples_per_table: int) -> Self:
        self.config.table_serializer.row_samples_per_table = samples_per_table
        return self

    def reset_row_sampler(self) -> Self:
        if self.config.table_serializer is not None:
            self.config.table_serializer.row_sampling_strategy = None
            self.config.table_serializer.row_samples_per_table = None
        return self

    def build(self) -> ExperimentConfig:
        if self.config.include_context and self.config.context_position is None:
            raise AttributeError("'context_position' must be specified when 'include_context' is True")
        if self.config.include_schema and self.config.schema_position is None:
            raise AttributeError("'schema_position' must be specified when 'include_schema' is True")
        if self.config.table_serializer is not None and self.config.table_position is None:
            raise AttributeError("'table_position' must be specified when 'table_serializer' is specified")
        return self.config.model_copy(deep=True)


def load_experiment_config_from_yaml(path: str) -> ExperimentConfig:
    with open(path, 'r') as f:
        yaml_data = yaml.safe_load(f)
    return ExperimentConfig(**yaml_data)

def save_experiment_config_to_yaml(path: str, experiment: ExperimentConfig) -> None:
    with open(path, 'w+') as f:
        yaml.safe_dump(experiment.model_dump(mode='json'), f)
