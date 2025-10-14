"""Test that List[ModelClass] annotations generate proper $ref references."""
import pathlib
import tempfile
import textwrap

from scripts.swagger_sync import collect_model_components


def test_list_model_class_generates_ref():
    """Test that List[ShiftCodeGame] generates items: {$ref: '#/components/schemas/ShiftCodeGame'}."""
    # Create temporary model file with List[ModelClass] annotation
    with tempfile.TemporaryDirectory() as temp_dir:
        models_root = pathlib.Path(temp_dir)

        # Create a test model file
        test_file = models_root / "test_model.py"
        test_file.write_text(textwrap.dedent("""
            import typing
            from bot.lib.models.openapi import component

            @openapi.component("TestGame", description="A test game.")
            class TestGame:
                def __init__(self, id: str, name: str):
                    self.id: str = id
                    self.name: str = name

            @openapi.component("TestPayload", description="A test payload.")
            class TestPayload:
                def __init__(self, games: typing.List[TestGame], title: str):
                    self.games: typing.List[TestGame] = games
                    self.title: str = title
        """))

        # Collect model components
        components, _ = collect_model_components(models_root)

        # Verify that both components were created
        assert "TestGame" in components
        assert "TestPayload" in components

        # Verify the TestPayload games field uses $ref
        test_payload = components["TestPayload"]
        games_property = test_payload["properties"]["games"]

        assert games_property["type"] == "array"
        assert "items" in games_property
        assert games_property["items"] == {"$ref": "#/components/schemas/TestGame"}


def test_list_primitive_uses_string():
    """Test that List[str] still generates items: {type: string}."""
    with tempfile.TemporaryDirectory() as temp_dir:
        models_root = pathlib.Path(temp_dir)

        # Create a test model file
        test_file = models_root / "test_model.py"
        test_file.write_text(textwrap.dedent("""
            import typing
            from bot.lib.models.openapi import component

            @openapi.component("TestPayload", description="A test payload.")
            class TestPayload:
                def __init__(self, tags: typing.List[str], count: int):
                    self.tags: typing.List[str] = tags
                    self.count: int = count
        """))

        # Collect model components
        components, _ = collect_model_components(models_root)

        # Verify the TestPayload tags field uses string type
        test_payload = components["TestPayload"]
        tags_property = test_payload["properties"]["tags"]

        assert tags_property["type"] == "array"
        assert "items" in tags_property
        assert tags_property["items"] == {"type": "string"}


def test_shift_code_models_specifically():
    """Test the specific ShiftCodePayload and ShiftCodeGame models work correctly."""
    # Use the actual models root
    models_root = pathlib.Path("bot/lib/models")
    components, _ = collect_model_components(models_root)

    # Verify both components exist
    assert "ShiftCodePayload" in components
    assert "ShiftCodeGame" in components

    # Verify the ShiftCodePayload games field uses $ref
    shift_code_payload = components["ShiftCodePayload"]
    games_property = shift_code_payload["properties"]["games"]

    assert games_property["type"] == "array"
    assert "items" in games_property
    assert games_property["items"] == {"$ref": "#/components/schemas/ShiftCodeGame"}
