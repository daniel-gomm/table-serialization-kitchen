![Cover Image](.assets/documentation/cover_image.webp "Table Serialization Kitchen Cover")

# Table Serialization Kitchen

Use the Table Serialization Kitchen to boil your tabular data down to serializations. Provide a recipe and some 
ingredients and serialize your tables in no-time. You can easily spice things up by extending Table Serialization 
Kitchen with your own serialization ideas!

This blog post gives an [example of how to use table serialization kitchen for rapid experimentation with table 
serializations.](https://daniel-gomm.github.io/blog/2025/Table-Serialization-Kitchen/)

> **Disclaimer:** 
> This project is still in the baking! Some things will still change

## What is it useful for?
The Table Serializer Kitchen package is essential for converting tabular data into textual formats that Large Language 
Models (LLMs) can understand and process effectively. This process, known as table serialization, is crucial for tasks
like question answering, and text-to-SQL generation. Additionally, table serializations are useful as basis for 
text-embeddings for dense retrieval over tabular data. By experimenting with different serialization strategies, you can
significantly enhance the performance of LLMs and embedding models on tabular data, making your models more accurate and
relevant. 

Table serialization kitchen provides a robust foundation for exploring various table serialization approaches. It allows
you to easily adjust how tables are serialized, set up replicable experiments, and identify the optimal serialization
method for your specific use case. Whether you're a data scientist, NLP practitioner, or machine learning engineer,
the Table Serializer Kitchen helps you unlock the full potential of LLMs for tasks involving structured data.

## Installation

Install table serialization kitchen from pypi:

```shell
pip install tableserializer
```

### Install from source

To install Table Serialization Kitchen from source, clone the repository and run the following command from the root 
directory of the repository:

```shell
pip install -e .
```

## Usage

This description provides a high-level overview of the table serialization kitchen. For more details, consult
[the documentation](https://daniel-gomm.github.io/table-serialization-kitchen/). If you want to see an example of the
package in action have a look at [this blog post](https://daniel-gomm.github.io/blog/2025/Table-Serialization-Kitchen/).

The central components for creating serializers with table serialization kitchen are [recipes](#recipe), 
component serializers for [metadata](#metadata-serializers), [schema](#schema-serializers), and
[raw tables](#raw-table-serializers), [row samplers](#row-sampler), and [table preprocessors](#table-preprocessors).
These components are combined into a central [Serializer](#serializer) object.

### Serializer

The `Serializer` class is the central instance in table serialization kitchen. It integrates the different components
into a single instance that handles the serialization.

```python
from tableserializer.serializer import Serializer
from tableserializer.serializer.table import MarkdownRawTableSerializer
from tableserializer.serializer.metadata import PairwiseMetadataSerializer
from tableserializer.recipe import SerializationRecipe
from tableserializer.table.row_sampler import RandomRowSampler
from tableserializer.table.preprocessor import StringTruncationPreprocessor

# Define recipe
recipe = SerializationRecipe("Metadata:\n{META}\n\nTable:\n{TABLE}")

# Create metadata serializer
metadata_serializer = PairwiseMetadataSerializer()

# Create raw table serializer
table_serializer = MarkdownRawTableSerializer()

# Create row sampler
row_sampler = RandomRowSampler(rows_to_sample=2, deterministic=False)

# Create table preprocessor
table_preprocessor = StringTruncationPreprocessor(max_len=100, apply_before_row_sampling=False)

# Put everything together into a Serializer
serializer = Serializer(recipe=recipe,
                        metadata_serializer=metadata_serializer,
                        table_serializer=table_serializer,
                        row_sampler=row_sampler,
                        table_preprocessors=[table_preprocessor])
```

A serializer can be called, providing a `Table` and some optional metadata as input. It outputs a serialization
according to its specification.

```python
import pandas as pd
from tableserializer.table import Table

example_df = pd.DataFrame([[2012, "From the Rough", "Edward"],
                           [1997, "The Borrowers", "Peagreen Clock"],
                           [2013, "In Secret", "Camille Raquin"]], columns=["Year", "Title", "Role"])

example_table = Table(example_df)

example_metadata = {"table_page_title": "Tom Felton", "table_section_title": "Films"}

# Serialize the example table
serialization = serializer.serialize(table=example_table, metadata=example_metadata)

print(serialization)
```

**Output:**
```
Metadata:
table_page_title: Tom Felton
table_section_title: Films

Table:
| Year | Title| Role |
|---|---|---|
| 2013 | In Secret| Camille Raquin |
| 2012 | From the Rough | Edward |
```

### Recipe

The recipe provides the overarching outline for the serialization. The recipe is defined as an `SerializationRecipe` 
instance. The recipe contains placeholder values that are dynamically filled-in during serialization.

```python
from tableserializer import SerializationRecipe

# Recipe with all placeholders
recipe = SerializationRecipe(
"""Metadata: 
{META}

Schema:
{SCHEMA}

Table:
{TABLE}
""")

# Recipe with a placeholder for raw table contents only
simple_recipe = SerializationRecipe(
"""Table:
{TABLE}
""")
```

You can place the placeholders values `{META}`, `{SCHEMA}`, and `{TABLE}` in the recipe. You design everything around
these placeholders to your taste. You also do not need to use all the placeholders in a recipe.

The placeholders get filled-in at serialization time. The `META` placeholder reserves a space for metadata related to
the table. The `{SCHEMA}` placeholder provides a space for the serialized schema of the table. Finally, the `{TABLE}`
placeholder reserves a space for serialized raw table contents. The value that is filled into each of the placeholders
of each of these components is generated by a component-specific serializer.

### Component Serializers

Component serializers are tasked with serializing a specific component within the full serialization recipe. You can 
use one of the pre-built component serializers, or implement your own serializer. 

#### Metadata Serializers

A metadata serializer serializes table-related metadata. Metadata serializers extend the `MetadataSerializer` base class.
Metadata is expected to have the format of a dictionary `Dict[str, Any]`. It is serialized by the 
`serialize_metadata` function that a `MetadataSerializer` implementation must override.

```python
from typing import Dict, Any
from tableserializer.serializer.metadata import MetadataSerializer

class ExampleMetadataSerializer(MetadataSerializer):

    def serialize_metadata(self, metadata: Dict[str, Any]) -> str:
        # This metadata serializer serializes the metadata as a newline separated concatenation of the values in the 
        # metadata dictionary
        serialization = ""
        for value in metadata.values():
            serialization += str(value) + "\n"
        return serialization[:-1]
```

Table serialization kitchen provides two default implementations of the `MetadataSerializer` base class:

- `PairwiseMetadataSerializer`: Serializes the metadata as "key: value" pairs
- `JSONMetadataSerializer`: Serializes the metadata dictionary as JSON string.

#### Schema Serializers

A schema serializer creates a serialization of the schema of a table. Schema serializers extend the `SchemaSerializer`
base class. Schemas are serialized through the `serialize_schema` function that a `SchemaSerializer` implementation must
override.

```python
from typing import Dict, Any, Optional
from tableserializer.table import Table
from tableserializer.serializer.schema import SchemaSerializer


class ExampleSchemaSerializer(SchemaSerializer):
    
    def serialize_schema(self, table: Table, metadata: Optional[Dict[str, Any]] = None) -> str:
        # This schema serializer serializes the schema as a comma separated list of column names
        serialization = ""
        for column_name in table.as_dataframe().columns():
            serialization += column_name + ", "
        return serialization[:-2]
```

Table serialization kitchen provides two default implementations of the `SchemaSerializer` base class:

- `ColumnNameSchemaSerializer`: Serializes the schema as a concatenation of the column names in the table, delimited by 
a specified delimiter.
- `SQLSchemaSerializer`: Serializes the schema as a SQL `CREATE TABLE` statement.

#### Raw Table Serializers

A raw table serializer generates a serialized representation of a raw table and its contents. Raw table serializers 
extend the `RawTableSerializer` base class. Table contents are serialized through the `serialize_raw_table` function
that a `RawTableSerializer` implementation must override.

```python
from tableserializer.table import Table
from tableserializer.serializer.table import RawTableSerializer


class ExampleRawTableSerializer(RawTableSerializer):
    
    def serialize_raw_table(self, table: Table) -> str:
        # This raw table serializer serializes the table as csv
        return table.as_dataframe().to_csv(index=False)
```

Table serialization kitchen provides a collection of default implementations of the `RawTableSerializer` base class:

- `MarkdownRawTableSerializer`: Serializes the table contents in Markdown table format.
- `JSONRawTableSerializer`: Serializes raw tables to row-wise JSON representations
- `CSVRawTableSerializer`: Serializes the table contents in csv format.
- `LatexRawTableSerializer`: Serializes the table contents as LaTeX table.

##### Row Sampler

A row sampler is tasked with sampling a set number of rows from a table to limit the size of the table for the
serialization. Row samplers extend the `RowSampler` base class. Rows are sampled through the `sample` function that a
`RowSerializer` implementation must override.

```python
from tableserializer.table.row_sampler import RowSampler
from tableserializer.table import Table

class ExampleRowSampler(RowSampler):
    
    def sample(self, table: Table) -> Table:
        # This row sampler samples the last rows from the dataframe
        last_rows_only_df = table.as_dataframe()[-self.rows_to_sample:].reset_index(drop=True)
        return Table(last_rows_only_df)
```

Table serialization kitchen provides a collection of default implementations of the `RowSampler` base class:

- `RandomRowSampler`: Samples rows at random.
- `FirstRowSampler`: Samples the first rows of the table.
- `KMeansRowSampler`: Samples a diverse set of rows by employing k-means clustering.

### Table Preprocessors

Table preprocessors are employed to transform the raw table before serialization. One motivation for this is to compress
the table contents. For example, a table containing overly long string values may make the table serializations too long
for embedding models. Table preprocessors extend the `TablePreprocessor` base class. An implementation must override the
`process` function. The `apply_before_row_sampling` field specifies if the table preprocessor is executed before or
after rows are sampled. Filtering columns may make sense to be done before row sampling, whereas preprocessors that
compress strings (e.g., by generating summaries) may best be applied after row sampling.

```python
from tableserializer.table.preprocessor import TablePreprocessor
from tableserializer.table import Table

class ExampleTablePreprocessor(TablePreprocessor):
    
    def __init__(self):
        super().__init__(apply_before_row_sampling=True)
    
    def process(self, table: Table) -> Table:
        # Preprocessor that removes the first column of the table
        table_df = table.as_dataframe()
        transformed_df = table_df.drop(columns=table_df.columns[0])
        return Table(transformed_df)
```

Table serialization kitchen provides two default implementations of the `TablePreprocessor` base class:

- `ColumnDroppingPreprocessor`: Transforms a table by dropping specified columns.
- `StringTruncationPreprocessor`: Truncates all strings in the table to a set maximum length before serialization.

### Table Serialization Kitchen

> WIP: Section still in the baking!

> Hungry for more? Have a look at the 
> [table serialization kitchen API documentation](https://daniel-gomm.github.io/table-serialization-kitchen/).
