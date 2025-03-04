import abc
import inspect
import json
import logging
import os
from typing import List, Dict, Any, Type, TypeVar, Callable, Tuple

from tableserializer.utils.functions import get_serializer_experiment_dir_structure
from tableserializer.recipe import SCHEMA_KEY, METADATA_KEY, TABLE_KEY
from tableserializer import SerializationRecipe
from tableserializer.serializer import Serializer
from tableserializer.serializer.metadata import MetadataSerializer, PairwiseMetadataSerializer, JSONMetadataSerializer
from tableserializer.table.preprocessor import TablePreprocessor, ColumnDroppingPreprocessor, \
    StringTruncationPreprocessor
from tableserializer.table.row_sampler import RowSampler, RandomRowSampler, FirstRowSampler, KMeansRowSampler
from tableserializer.serializer.table import RawTableSerializer, JSONRawTableSerializer, MarkdownRawTableSerializer
from tableserializer.serializer.schema import SchemaSerializer, ColumnNameSchemaSerializer, SQLSchemaSerializer
from tableserializer.utils.exceptions import ClassDefinitionError


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


def _verify_constructor_args(cls: Type) -> None:
    # Check that the constructor argument keys and the fields of a given class align
    # --> constructor args ⊆ instance attributes
    cls_copy = cls
    all_constructor_args = set()
    all_instance_attributes = set()
    while cls != abc.ABC:
        # Recursively trace up the class tree and collect constructor arguments and instance attributes set at each level
        if '__init__' not in cls.__dict__:
            cls = cls.__base__
            continue

        constructor_args = inspect.signature(cls.__init__).parameters

        all_constructor_args = all_constructor_args.union(constructor_args)

        init_code = inspect.getsource(cls.__init__)
        lines = init_code.split('\n')
        fields = []
        for line in lines:
            line = line.strip()
            if line.startswith('self.'):
                field_name = line.split('=')[0].split('.')[1].strip()
                fields.append(field_name)

        all_instance_attributes = all_instance_attributes.union(fields)

        cls = cls.__base__

    for constructor_arg in all_constructor_args:
        if constructor_arg == "self":
            continue
        if constructor_arg not in all_instance_attributes:
            raise ClassDefinitionError(f"Class {cls_copy.__name__} has the constructor parameter {constructor_arg} but "
                                       f"lacks a field of the same name.")



T = TypeVar('T')


class ExperimentalSerializerKitchen:
    """
    Central class for managing serialization components and custom extensions for experiments.
    """

    def __init__(self):
        self._schema_serializer_pantry: Dict[str, Type[SchemaSerializer]] = {}
        self._table_serializer_pantry: Dict[str, Type[RawTableSerializer]] = {}
        self._metadata_serializer_pantry: Dict[str, Type[MetadataSerializer]] = {}
        self._row_sampler_pantry: Dict[str, Type[RowSampler]] = {}
        self._table_preprocessor_pantry: Dict[str, Type[TablePreprocessor]] = {}
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self._logger = logging.Logger(self.__class__.__name__, level=logging.INFO)

        # Register serializers
        self.register_schema_serializer_class(ColumnNameSchemaSerializer)
        self.register_schema_serializer_class(SQLSchemaSerializer)

        self.register_raw_table_serializer_class(JSONRawTableSerializer)
        self.register_raw_table_serializer_class(MarkdownRawTableSerializer)

        self.register_metadata_serializer_class(PairwiseMetadataSerializer)
        self.register_metadata_serializer_class(JSONMetadataSerializer)

        self.register_row_sampler_class(RandomRowSampler)
        self.register_row_sampler_class(FirstRowSampler)
        self.register_row_sampler_class(KMeansRowSampler)

        self.register_table_preprocessor_class(ColumnDroppingPreprocessor)
        self.register_table_preprocessor_class(StringTruncationPreprocessor)

    def _create_instance(self, instance_name: str, registry: Dict[str, Type[T]], **kwargs) -> T:
        if instance_name not in registry.keys():
            raise KeyError(instance_name + " not found in registry")
        instance = registry[instance_name](**kwargs)
        self._logger.info(f"Created {instance_name}.")
        return instance

    def _register_class(self, registered_class: Type[T], registry: Dict[str, Type[T]], registered_type: Type) -> None:
        assert isinstance(registered_class, type) and issubclass(registered_class, registered_type), \
            (f"Cannot register {registered_class.__name__} because {registered_class.__name__} is not "
             f"a subclass of {registered_type.__name__}")
        _verify_constructor_args(registered_class)
        registry[registered_class.__name__] = registered_class
        self._logger.info(f"Registered class {registered_class.__name__} as {registered_type.__name__}.")

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
        Create a SchemaSerializer for the given schema serializer name. This assumes that a SchemaSerializer with the
        supplied name is registered.

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
        Create a RawTableSerializer for the given table serializer name. This assumes that a RawTableSerializer with the
        supplied name is registered.

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
        Create a MetadataSerializer for the given metadata serializer name. This assumes that a MetadataSerializer
        with the supplied name is registered.

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
        Create a RowSampler for the given row sampler name. This assumes that a RowSampler with the supplied name is
        registered.

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
        Create a TablePreprocessor for the given table preprocessor name. This assumes that a TablePreprocessor with
        the supplied name is registered.

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

    def create_serializers(self, recipes: List[SerializationRecipe],
                           metadata_serializers: List[MetadataSerializer],
                           schema_serializers: List[SchemaSerializer],
                           table_serializers: List[RawTableSerializer],
                           row_samplers: List[RowSampler],
                           table_preprocessor_constellations: List[List[TablePreprocessor]]) -> List[Serializer]:
        """
        Create serializers with different parameter configurations.

        :param recipes: List of recipes for which to create serializer instances.
        :type recipes: List[SerializationRecipe]
        :param metadata_serializers: List of metadata serializers for which to create serializer instances.
        :type metadata_serializers: List[MetadataSerializer]
        :param schema_serializers: List of schema serializers for which to create serializer instances.
        :type schema_serializers: List[SchemaSerializer]
        :param table_serializers: List of raw table serializers for which to create serializer instances.
        :type table_serializers: List[RawTableSerializer]
        :param row_samplers: List of row samplers for which to create serializer instances.
        :type row_samplers: List[RowSampler]
        :param table_preprocessor_constellations: List of table preprocessor constellations for which to create serializer instances.
        :type table_preprocessor_constellations: List[List[TablePreprocessor]]
        :return: A list of serializers for all possible combinations of components.
        :rtype: List[Serializer]
        """
        serializers = []
        for recipe in recipes:
            recipe_fields = recipe.get_fields()

            r_metadata_serializers = [None]
            r_schema_serializers = [None]
            r_table_serializers = [None]
            r_row_samplers = [None]

            if METADATA_KEY in recipe_fields:
                r_metadata_serializers = metadata_serializers
            if SCHEMA_KEY in recipe_fields:
                r_schema_serializers = schema_serializers
            if TABLE_KEY in recipe_fields:
                r_table_serializers = table_serializers
                r_row_samplers = row_samplers

            for metadata_serializer in r_metadata_serializers:
                for schema_serializer in r_schema_serializers:
                    for table_serializer in r_table_serializers:
                        for row_sampler in r_row_samplers:
                            for table_preprocessors in table_preprocessor_constellations:
                                serializers.append(Serializer(recipe, metadata_serializer, schema_serializer,
                                                              table_serializer,  row_sampler, table_preprocessors))
        self._logger.info(f"Created {len(serializers)} serializer(s).")
        return serializers


    def save_serializer_experiment_configurations(self, serializers: List[Serializer], base_folder: str) -> None:
        """
        Create a folder structure within a base folder and save configurations of the provided serializers into this
        structure.

        :param serializers: Serializers that are saved.
        :type serializers: List[Serializer]
        :param base_folder: Base folder that configuration files will be saved into.
        :type base_folder: str
        :return: None
        :rtype: None
        """
        if not os.path.exists(base_folder):
            os.makedirs(base_folder)

        for serializer in serializers:
            experiment_path = os.path.join(base_folder, get_serializer_experiment_dir_structure(serializer))
            os.makedirs(experiment_path, exist_ok=True)
            serializer_json = self.jar_up_as_json(serializer)
            with open(os.path.join(experiment_path, "serializer.json"), "w+") as f:
                f.write(serializer_json)
        self._logger.info(f"Saved {len(serializers)} serializer(s) to base folder {base_folder}.")

    def get_serializers_from_dir(self, base_folder: str) -> List[Tuple[str, Serializer]]:
        """
        Get a list of serializers that have been saved in a base folder.

        :param base_folder: Base folder where
        :return: A tuple (experiment_folder, )
        """
        experiments = []
        for dirpath, dirnames, filenames in os.walk(base_folder):
            if "serializer.json" in filenames:
                serializer_file = os.path.join(dirpath, filenames[0])
                with open(serializer_file, "r") as f:
                    serializer_json = f.read()
                serializer = self.unjar_from_json(serializer_json)
                experiments.append((dirpath, serializer))
        return experiments

    def run_experiments_with_serializers(self, base_folder: str, experiment_callback: Callable) -> None:
        """
        Provide a callback function and run experiments over all serializers saved in the base folder.

        :param base_folder: Base folder that serializer configuration files reside in.
        :type base_folder: str
        :param experiment_callback: Callback function that is invoked with a tuple (experiment_folder, serializer) (`Tuple[str, Serializer]`) for each experiment. The callback function is provided the experiment folder as string value and the associated `Serializer`.
        :type experiment_callback: Callable
        :return: None
        :rtype: None
        """
        experiments = self.get_serializers_from_dir(base_folder)
        self._logger.info(f"Loaded {len(experiments)} serializer(s). Running experiments.")
        for index, experiment in enumerate(experiments):
            self._logger.info(f"Running experiment {index+1}/{len(experiments)}.")
            experiment_dir, serializer = experiment
            experiment_callback(experiment_dir, serializer)
