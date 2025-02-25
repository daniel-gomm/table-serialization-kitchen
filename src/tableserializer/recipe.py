import string

SCHEMA_KEY = "SCHEMA"
METADATA_KEY = "META"
TABLE_KEY = "TABLE"


class SerializationRecipe:
    """
    The SerializationRecipe details the structure of the table serialization.
    """

    def __init__(self, recipe: str):
        """
        An instruction of how to structure the table serialization.
        :param recipe: String representation of the overall structure of the serialization with placeholders that are
        dynamically filled in on a per-table basis.
        """
        self._recipe = recipe
        self._validate_recipe()

    def _validate_recipe(self) -> None:
        fields = [field_name for _, field_name, _, _ in string.Formatter().parse(self._recipe) if field_name is not None]
        for field in fields:
            if field not in [SCHEMA_KEY, METADATA_KEY, TABLE_KEY]:
                raise ValueError(f"The recipe includes the field name '{field}' which is not defined. "
                                 f"The defined fields names are '{SCHEMA_KEY}' and '{METADATA_KEY}' and '{TABLE_KEY}'.'")
        self._fields = fields

    def cook_recipe(self, schema_contents: str = None, metadata_contents: str = None,
                    table_contents: str = None) -> str:
        """
        Fill-in the values for the placeholder values.
        :param schema_contents: Schema contents to fill in.
        :type schema_contents: str
        :param metadata_contents: Metadata contents to fill in.
        :type metadata_contents: str
        :param table_contents: Table contents to fill in.
        :type table_contents: str
        :return: Table serialization according to the schema.
        :rtype: str
        """
        kwargs = {}
        if schema_contents is not None:
            if SCHEMA_KEY not in self._fields:
                raise AttributeError("Schema is not part of the recipe.")
            kwargs[SCHEMA_KEY] = schema_contents
        if metadata_contents is not None:
            if METADATA_KEY not in self._fields:
                raise AttributeError("Metadata is not part of the recipe.")
            kwargs[METADATA_KEY] = metadata_contents
        if table_contents is not None:
            if TABLE_KEY not in self._fields:
                raise AttributeError("Table is not part of the recipe.")
            kwargs[TABLE_KEY] = table_contents
        return self._recipe.format(**kwargs)

    def get_raw_recipe(self) -> str:
        """
        Get the raw recipe.
        :return: The raw recipe as a string.
        :rtype: str
        """
        return self._recipe
