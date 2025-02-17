import json
from abc import ABC, abstractmethod
from typing import Dict, Any


class MetadataSerializer(ABC):

    @abstractmethod
    def serialize_metadata(self, metadata: Dict[str, Any]) -> str:
        raise NotImplementedError


class PairwiseMetadataSerializer(MetadataSerializer):

    def serialize_metadata(self, metadata: Dict[str, Any]) -> str:
        meta_s = ""
        for key, value in metadata.values():
            meta_s += f"{key}: {value}\n"
        return meta_s[:-1]


class JSONMetadataSerializer(MetadataSerializer):

    def serialize_metadata(self, metadata: Dict[str, Any]) -> str:
        return json.dumps(metadata)
