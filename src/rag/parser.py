"""OpenAPI parser for converting OpenAPI specs to API entities."""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from src.models import APIEntity, EdgeType, GraphEdge, GraphNode, HTTPMethod, NodeType, Parameter, Schema


class OpenAPIParser:
    """Parse OpenAPI specifications to API entities."""

    def __init__(self):
        self._operation_id_counter = 0

    def parse_file(self, file_path: str) -> List[APIEntity]:
        """Parse an OpenAPI spec file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"OpenAPI spec file not found: {file_path}")

        with open(path) as f:
            if path.suffix in [".yaml", ".yml"]:
                spec = yaml.safe_load(f)
            elif path.suffix == ".json":
                spec = json.load(f)
            else:
                raise ValueError(f"Unsupported file format: {path.suffix}")

        return self.parse_spec(spec)

    def parse_spec(self, spec: Dict[str, Any]) -> List[APIEntity]:
        """Parse OpenAPI spec dictionary."""
        apis: List[APIEntity] = []
        paths = spec.get("paths", {})

        for path, methods in paths.items():
            if not isinstance(methods, dict):
                continue

            for method, operation in methods.items():
                if method.lower() not in ["get", "post", "put", "patch", "delete", "options", "head"]:
                    continue

                try:
                    api = self._parse_operation(path, method.lower(), operation, spec)
                    apis.append(api)
                except Exception as e:
                    # Log error but continue parsing
                    print(f"Failed to parse {method.upper()} {path}: {e}")
                    continue

        return apis

    def _parse_operation(
        self, path: str, method: str, operation: Dict[str, Any], spec: Dict[str, Any]
    ) -> APIEntity:
        """Parse a single API operation."""
        operation_id = operation.get("operationId") or self._generate_operation_id(path, method)
        summary = operation.get("summary", "")
        description = operation.get("description")
        tags = operation.get("tags", [])
        deprecated = operation.get("deprecated", False)

        # Parse parameters
        parameters = self._parse_parameters(operation.get("parameters", []))

        # Parse request body
        request_schema = None
        if "requestBody" in operation:
            request_schema = self._parse_request_body(operation["requestBody"], spec)

        # Parse responses
        response_schema = None
        if "responses" in operation:
            response_schema = self._parse_responses(operation["responses"], spec)

        # Get security
        security = []
        if operation.get("security"):
            for sec in operation["security"]:
                security.extend(sec.keys())

        return APIEntity(
            id=operation_id,
            path=path,
            method=HTTPMethod(method),
            summary=summary,
            description=description,
            tags=tags,
            parameters=parameters,
            request_schema=request_schema,
            response_schema=response_schema,
            security=security,
            deprecated=deprecated,
            version=spec.get("info", {}).get("version"),
        )

    def _parse_parameters(self, parameters: List[Dict[str, Any]]) -> List[Parameter]:
        """Parse API parameters."""
        result = []
        for param in parameters:
            result.append(
                Parameter(
                    name=param.get("name", ""),
                    location=param.get("in", "query"),
                    type=self._get_parameter_type(param),
                    required=param.get("required", False),
                    description=param.get("description"),
                    default=param.get("schema", {}).get("default"),
                    enum=param.get("schema", {}).get("enum"),
                )
            )
        return result

    def _get_parameter_type(self, param: Dict[str, Any]) -> str:
        """Get parameter type from schema."""
        schema = param.get("schema", {})
        if "$ref" in schema:
            # Resolve ref
            return schema["$ref"].split("/")[-1]
        return schema.get("type", "string")

    def _parse_request_body(self, request_body: Dict[str, Any], spec: Dict[str, Any]) -> Optional[Schema]:
        """Parse request body schema."""
        content = request_body.get("content", {})
        if not content:
            return None

        # Get JSON content
        json_content = content.get("application/json")
        if not json_content:
            return None

        schema_data = json_content.get("schema", {})
        return self._parse_schema(schema_data, spec)

    def _parse_schema(self, schema_data: Dict[str, Any], spec: Dict[str, Any]) -> Optional[Schema]:
        """Parse schema."""
        if not schema_data:
            return None

        # Resolve $ref
        if "$ref" in schema_data:
            ref = schema_data["$ref"]
            resolved = self._resolve_ref(ref, spec)
            if resolved:
                schema_data = resolved

        schema_type = schema_data.get("type", "object")
        properties = {}
        required = schema_data.get("required", [])

        if "properties" in schema_data:
            for prop_name, prop_data in schema_data["properties"].items():
                if "$ref" in prop_data:
                    resolved = self._resolve_ref(prop_data["$ref"], spec)
                    if resolved:
                        properties[prop_name] = resolved
                    else:
                        properties[prop_name] = prop_data
                else:
                    properties[prop_name] = prop_data

        return Schema(
            type=schema_type,
            properties=properties,
            required=required,
            description=schema_data.get("description"),
            example=schema_data.get("example"),
        )

    def _parse_responses(self, responses: Dict[str, Any], spec: Dict[str, Any]) -> Optional[Schema]:
        """Parse response schema."""
        # Get 200 or default response
        response = responses.get("200") or responses.get("201") or responses.get("default")
        if not response:
            return None

        content = response.get("content", {})
        json_content = content.get("application/json")
        if not json_content:
            return None

        schema_data = json_content.get("schema", {})
        return self._parse_schema(schema_data, spec)

    def _resolve_ref(self, ref: str, spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Resolve $ref to actual schema."""
        if not ref.startswith("#/"):
            return None

        parts = ref[2:].split("/")
        current = spec

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        return current

    def _generate_operation_id(self, path: str, method: str) -> str:
        """Generate operation ID if not provided."""
        self._operation_id_counter += 1
        # Clean path to create ID
        clean_path = re.sub(r"[/{}\-]", "_", path)
        clean_path = clean_path.strip("_")
        return f"{method}_{clean_path}_{self._operation_id_counter}"

    def extract_graph_nodes(self, api: APIEntity) -> List[GraphNode]:
        """Extract graph nodes from API entity."""
        nodes = []

        # API node
        nodes.append(
            GraphNode(
                id=api.id,
                type=NodeType.API,
                data=api.to_dict(),
            )
        )

        # Tag nodes
        for tag in api.tags:
            nodes.append(
                GraphNode(
                    id=f"tag_{tag}",
                    type=NodeType.TAG,
                    data={"name": tag},
                )
            )

        # Parameter nodes
        for param in api.parameters:
            nodes.append(
                GraphNode(
                    id=f"{api.id}_param_{param.name}",
                    type=NodeType.PARAMETER,
                    data={
                        "name": param.name,
                        "type": param.type,
                        "required": param.required,
                    },
                )
            )

        return nodes

    def extract_graph_edges(self, api: APIEntity) -> List[GraphEdge]:
        """Extract graph edges from API entity."""
        edges = []

        # Tag edges
        for tag in api.tags:
            edges.append(
                GraphEdge(
                    source=api.id,
                    target=f"tag_{tag}",
                    type=EdgeType.HAS_TAG,
                    weight=1.0,
                )
            )

        # Parameter edges
        for param in api.parameters:
            edges.append(
                GraphEdge(
                    source=api.id,
                    target=f"{api.id}_param_{param.name}",
                    type=EdgeType.HAS_PARAM,
                    weight=0.8,
                )
            )

        # Schema edges
        if api.request_schema:
            schema_id = f"{api.id}_request"
            edges.append(
                GraphEdge(
                    source=api.id,
                    target=schema_id,
                    type=EdgeType.USES_SCHEMA,
                    weight=0.7,
                )
            )

        if api.response_schema:
            schema_id = f"{api.id}_response"
            edges.append(
                GraphEdge(
                    source=api.id,
                    target=schema_id,
                    type=EdgeType.USES_SCHEMA,
                    weight=0.7,
                )
            )

        return edges
