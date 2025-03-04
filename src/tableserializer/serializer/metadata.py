import json
from abc import ABC, abstractmethod
from typing import Dict, Any

from tableserializer.serializer.common import SignatureProvidingInstance


class MetadataSerializer(ABC, SignatureProvidingInstance):
    """
    Serializer for table-related metadata objects. Defines a strategy for serializing the metadata contents in a
    specific way.
    """

    @abstractmethod
    def serialize_metadata(self, metadata: Dict[str, Any]) -> str:
        """
        Serialize the given metadata.

        :param metadata: Metadata to serialize.
        :type metadata: Dict[str, Any]
        :return: String representation of the given metadata.
        :rtype: str
        """
        raise NotImplementedError


class PairwiseMetadataSerializer(MetadataSerializer):
    """
    Metadata serializer that serializes entries in the metadata dictionary as "key: value" pairs.
    """

    def serialize_metadata(self, metadata: Dict[str, Any]) -> str:
        meta_s = ""
        for key, value in metadata.items():
            meta_s += f"{key}: {value}\n"
        return meta_s[:-1]


class JSONMetadataSerializer(MetadataSerializer):
    """
    Metadata serializer that serializes the full metadata dictionary as JSON.
    """

    def serialize_metadata(self, metadata: Dict[str, Any]) -> str:
        return json.dumps(metadata)
