import inspect
import json
from typing import List, Dict, Optional, Any, Type, TypeVar

import pandas as pd

from tableserializer.table import Table
from tableserializer import SerializationRecipe
from tableserializer.serializer.metadata import MetadataSerializer, PairwiseMetadataSerializer, JSONMetadataSerializer
from tableserializer.table.preprocessor import TablePreprocessor, ColumnDroppingPreprocessor, \
    StringTruncationPreprocessor
from tableserializer.table.row_sampler import RowSampler, RandomRowSampler, FirstRowSampler, KMeansRowSampler
from tableserializer.serializer.table import RawTableSerializer, JsonRawTableSerializer, MarkdownRawTableSerializer
from tableserializer.serializer.schema import SchemaSerializer, ColumnNameSchemaSerializer, SQLSchemaSerializer

class Serializer:
    """
    Serializer that serializes a given table according to a user-specified format.
    """

    def __init__(self, recipe: SerializationRecipe, metadata_serializer: Optional[MetadataSerializer] = None,
                 schema_serializer: Optional[SchemaSerializer] = None,
                 table_serializer: Optional[RawTableSerializer] = None, row_sampler: Optional[RowSampler] = None,
                 table_preprocessors: Optional[List[TablePreprocessor]] = None):
        """
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
            if self.row_sampler is not None:
                sub_table = self.row_sampler.sample(table)
            for table_preprocessor in self.table_preprocessors:
                sub_table = table_preprocessor.process(sub_table)
            kwargs["table_contents"] = self.table_serializer.serialize_table(sub_table)
        return self.recipe.cook_recipe(**kwargs)


def _extract_instance_save_state(instance: Any) -> Dict[str, Any]:
    constructor_args = inspect.signature(instance.__init__).parameters
    args_data = {}
    for param in constructor_args:
        if param in ['args', 'kwargs']:
            continue
        try:
            args_data[param] = getattr(instance, param)
        except AttributeError:
            raise AttributeError(f"Instance of type {type(instance).__name__} has the constructor parameter {param} but"
                                 f" it does not have the {param} attribute. Make sure that constructor parameters and "
                                 f"class attributes match.")
    return {"name": type(instance).__name__, "args": args_data}

T = TypeVar('T')

class SerializerKitchen:
    """
    Central class for managing serialization components and custom extensions for experiments.
    """

    def __init__(self):
        self._schema_serializer_pantry: Dict[str, Type[SchemaSerializer]] = {}
        self._table_serializer_pantry: Dict[str, Type[RawTableSerializer]] = {}
        self._metadata_serializer_pantry: Dict[str, Type[MetadataSerializer]] = {}
        self._row_sampler_pantry: Dict[str, Type[RowSampler]] = {}
        self._table_preprocessor_pantry: Dict[str, Type[TablePreprocessor]] = {}

        # Register serializers
        self.register_schema_serializer_class(ColumnNameSchemaSerializer)
        self.register_schema_serializer_class(SQLSchemaSerializer)

        self.register_raw_table_serializer_class(JsonRawTableSerializer)
        self.register_raw_table_serializer_class(MarkdownRawTableSerializer)

        self.register_metadata_serializer_class(PairwiseMetadataSerializer)
        self.register_metadata_serializer_class(JSONMetadataSerializer)

        self.register_row_sampler_class(RandomRowSampler)
        self.register_row_sampler_class(FirstRowSampler)
        self.register_row_sampler_class(KMeansRowSampler)

        self.register_table_preprocessor_class(ColumnDroppingPreprocessor)
        self.register_table_preprocessor_class(StringTruncationPreprocessor)

    @staticmethod
    def _create_instance(instance_name: str, registry: Dict[str, Type[T]], **kwargs) -> T:
        if instance_name not in registry.keys():
            raise KeyError(instance_name + " not found in registry")
        return registry[instance_name](**kwargs)

    @staticmethod
    def _register_class(registered_class: Type[T], registry: Dict[str, Type[T]], registered_type: Type) -> None:
        assert isinstance(registered_class, type) and issubclass(registered_class, registered_type), \
            (f"Cannot register {registered_class.__name__} because {registered_class.__name__} is not "
             f"a subclass of {type.__name__}")
        registry[registered_class.__name__] = registered_class

    def register_schema_serializer_class(self, schema_serializer_class: Type[SchemaSerializer]) -> None:
        """
        Register a custom schema serializer class to the kitchen.
        :param schema_serializer_class: Schema serializer class to register.
        :type schema_serializer_class: Type[SchemaSerializer]
        :rtype: None
        """
        self._register_class(schema_serializer_class, self._schema_serializer_pantry, SchemaSerializer)

    def register_raw_table_serializer_class(self, table_serializer_class: Type[RawTableSerializer]) -> None:
        """
        Register a custom raw table serializer class to the kitchen.
        :param table_serializer_class: Raw table serializer class to register.
        :type table_serializer_class: Type[RawTableSerializer]
        :rtype: None
        """
        self._register_class(table_serializer_class, self._table_serializer_pantry, RawTableSerializer)

    def register_metadata_serializer_class(self, metadata_serializer_class: Type[MetadataSerializer]) -> None:
        """
        Register a custom metadata serializer class to the kitchen.
        :param metadata_serializer_class: Metadata serializer class to register.
        :rtype: None
        """
        self._register_class(metadata_serializer_class, self._metadata_serializer_pantry, MetadataSerializer)

    def register_row_sampler_class(self, row_sampler_class: Type[RowSampler]) -> None:
        """
        Register a custom row sampler class to the kitchen.
        :param row_sampler_class: Row sampler class to register.
        :rtype: None
        """
        self._register_class(row_sampler_class, self._row_sampler_pantry, RowSampler)

    def register_table_preprocessor_class(self, table_preprocessor_class: Type[TablePreprocessor]) -> None:
        """
        Register a custom table preprocessor class to the kitchen.
        :param table_preprocessor_class: Table preprocessor class to register.
        :rtype: None
        """
        self._register_class(table_preprocessor_class, self._table_preprocessor_pantry, TablePreprocessor)

    def create_schema_serializer(self, schema_serializer_name: str, **kwargs: Any) -> SchemaSerializer:
        """
        Create a SchemaSerializer for the given schema serializer name. This assumes that a SchemaSerializer with the supplied name is registered.
        :param schema_serializer_name: Name of the registered schema serializer class that should be instantiated.
        :type schema_serializer_name: str
        :param kwargs: Constructor arguments for instantiating the SchemaSerializer class.
        :type kwargs: Any
        :return: SchemaSerializer instance.
        :rtype: SchemaSerializer
        """
        return self._create_instance(schema_serializer_name, self._schema_serializer_pantry, **kwargs)

    def create_table_serializer(self, raw_table_serializer_name: str, **kwargs: Any) -> RawTableSerializer:
        """
        Create a RawTableSerializer for the given table serializer name. This assumes that a RawTableSerializer with the supplied name is registered.
        :param raw_table_serializer_name: Name of the registered RawTableSerializer class that should be instantiated.
        :type raw_table_serializer_name: str
        :param kwargs: Constructor arguments for instantiating the RawTableSerializer class.
        :type kwargs: Any
        :return: RawTableSerializer instance.
        :rtype: RawTableSerializer
        """
        return self._create_instance(raw_table_serializer_name, self._table_serializer_pantry, **kwargs)

    def create_metadata_serializer(self, metadata_serializer_name: str, **kwargs: Any) -> MetadataSerializer:
        """
        Create a MetadataSerializer for the given metadata serializer name. This assumes that a MetadataSerializer with the supplied name is registered.
        :param metadata_serializer_name: Name of the registered MetadataSerializer class that should be instantiated.
        :type metadata_serializer_name: str
        :param kwargs: Constructor arguments for instantiating the MetadataSerializer class.
        :type kwargs: Any
        :return: MetadataSerializer instance.
        :rtype: MetadataSerializer
        """
        return self._create_instance(metadata_serializer_name, self._metadata_serializer_pantry, **kwargs)

    def create_row_sampler(self, row_sampler_name: str, rows_to_sample: int = 10, **kwargs: Any) -> RowSampler:
        """
        Create a RowSampler for the given row sampler name. This assumes that a RowSampler with the supplied name is registered.
        :param row_sampler_name: Name of the registered RowSampler class that should be instantiated.
        :type row_sampler_name: str
        :param rows_to_sample: Number of rows to sample.
        :type rows_to_sample: int
        :param kwargs: Constructor arguments for instantiating the RowSampler class.
        :type kwargs: Any
        :return: RowSampler instance.
        :rtype: RowSampler
        """
        kwargs["rows_to_sample"] = rows_to_sample
        return self._create_instance(row_sampler_name, self._row_sampler_pantry, **kwargs)

    def create_table_preprocessor(self, table_preprocessor_name: str, **kwargs: Any) -> TablePreprocessor:
        """
        Create a TablePreprocessor for the given table preprocessor name. This assumes that a TablePreprocessor with the supplied name is registered.
        :param table_preprocessor_name: Name of the registered TablePreprocessor class that should be instantiated.
        :type table_preprocessor_name: str
        :param kwargs: Constructor arguments for instantiating the TablePreprocessor class.
        :type kwargs: Any
        :return: TablePreprocessor instance.
        :rtype: TablePreprocessor
        """
        return self._create_instance(table_preprocessor_name, self._table_preprocessor_pantry, **kwargs)

    @staticmethod
    def jar_up_as_json(serializer: Serializer) -> str:
        """
        Create a JSON representation of the given serializer. This representation captures the full configuration of the
        serializer, allowing instantiating an equal serializer.
        :param serializer: Serializer to jar up as JSON.
        :type serializer: Serializer
        :return: JSON representation of the given serializer.
        :rtype: str
        """
        serializer_config = {
            "schema_serializer": None,
            "table_serializer": None,
            "metadata_serializer": None,
            "row_sampler": None,
            "table_preprocessors": [],
            "recipe": serializer.recipe.get_raw_recipe()
        }

        if serializer.schema_serializer is not None:
            serializer_config["schema_serializer"] = _extract_instance_save_state(serializer.schema_serializer)
        if serializer.table_serializer is not None:
            serializer_config["table_serializer"] = _extract_instance_save_state(serializer.table_serializer)
        if serializer.metadata_serializer is not None:
            serializer_config["metadata_serializer"] = _extract_instance_save_state(serializer.metadata_serializer)
        if serializer.row_sampler is not None:
            serializer_config["row_sampler"] = _extract_instance_save_state(serializer.row_sampler)
        if len(serializer.table_preprocessors) > 0:
            for table_preprocessor in serializer.table_preprocessors:
                serializer_config["table_preprocessors"].append(_extract_instance_save_state(table_preprocessor))

        return json.dumps(serializer_config)

    def unjar_from_json(self, serializer_json: str) -> Serializer:
        """
        Create a serializer instance from a JSON representation of a serializer.
        :param serializer_json: JSON representation of a serializer.
        :type serializer_json: str
        :return: Serializer instance.
        :rtype: Serializer
        """
        config = json.loads(serializer_json)
        schema_serializer = None
        if config["schema_serializer"] is not None:
            schema_serializer = self.create_schema_serializer(config["schema_serializer"]["name"],
                                                              **config["schema_serializer"]["args"])
        table_serializer = None
        if config["table_serializer"] is not None:
            table_serializer = self.create_table_serializer(config["table_serializer"]["name"],
                                                            **config["table_serializer"]["args"])
        metadata_serializer = None
        if config["metadata_serializer"] is not None:
            metadata_serializer = self.create_metadata_serializer(config["metadata_serializer"]["name"],
                                                                  **config["metadata_serializer"]["args"])
        row_sampler = None
        if config["row_sampler"] is not None:
            row_sampler = self.create_row_sampler(config["row_sampler"]["name"], **config["row_sampler"]["args"])

        table_preprocessors = []
        if len(config["table_preprocessors"]) > 0:
            for table_preprocessor in config["table_preprocessors"]:
                table_preprocessors.append(self.create_table_preprocessor(table_preprocessor["name"],
                                                                          **table_preprocessor["args"]))

        recipe = SerializationRecipe(config["recipe"])

        return Serializer(recipe, metadata_serializer, schema_serializer, table_serializer, row_sampler,
                          table_preprocessors)
