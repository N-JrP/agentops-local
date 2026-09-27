from backend.tool_models import TOOL_INPUT_MODELS, structured_arguments
from backend.tool_registry import tool_catalog


def test_every_registered_tool_has_json_schema():
    catalog = tool_catalog()
    assert set(catalog) == set(TOOL_INPUT_MODELS)
    for spec in catalog.values():
        assert spec["mode"] == "read_only"
        assert spec["input_schema"]["type"] == "object"


def test_structured_incident_arguments():
    args = structured_arguments("incidents", "latest GitHub incident")
    assert args == {"query": "latest GitHub incident", "limit": 3}
