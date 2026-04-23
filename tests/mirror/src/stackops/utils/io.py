import json

from stackops.utils.io import remove_c_style_comments


def test_remove_c_style_comments_keeps_comment_markers_inside_strings() -> None:
    raw_jsonc = """
    {
      // top level comment
      "database": "postgresql://username:password@localhost:5432/dbname",
      "url": "https://mcp.example.local/mcp",
      "escaped": "quote: \\" // still string",
      "value": 1 /* block comment */
    }
    """

    parsed: object = json.loads(remove_c_style_comments(raw_jsonc))

    assert parsed == {
        "database": "postgresql://username:password@localhost:5432/dbname",
        "url": "https://mcp.example.local/mcp",
        "escaped": 'quote: " // still string',
        "value": 1,
    }
