from typing import List

import os

from tableserializer.serializer import Serializer

def get_serializer_experiment_dir_structure(serializer: Serializer) -> str:
    folder_structure = str(serializer.recipe)
    if serializer.metadata_serializer is not None:
        folder_structure = os.path.join(folder_structure, str(serializer.metadata_serializer))
    if serializer.schema_serializer is not None:
        folder_structure = os.path.join(folder_structure, str(serializer.schema_serializer))
    if serializer.table_serializer is not None:
        folder_structure = os.path.join(folder_structure, str(serializer.table_serializer))
        if serializer.row_sampler is not None:
            folder_structure = os.path.join(folder_structure, str(serializer.row_sampler))
    if len(serializer.table_preprocessors) > 0:
        for table_preprocessor in serializer.table_preprocessors:
            folder_structure = os.path.join(folder_structure, str(table_preprocessor))
    return folder_structure
