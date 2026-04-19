

from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image
import pytest

from stackops.scripts.python.helpers.helpers_search.qr_code import generate_qrcode_grid


def test_generate_qrcode_grid_rejects_empty_input(tmp_path: Path) -> None:
    output_path = tmp_path / "codes.svg"

    with pytest.raises(ValueError, match="strings list cannot be empty"):
        generate_qrcode_grid(strings=[], output_path=str(output_path), format="svg")


def test_generate_qrcode_grid_writes_svg_with_truncated_labels(tmp_path: Path) -> None:
    output_path = tmp_path / "nested" / "codes.svg"

    returned_path = generate_qrcode_grid(
        strings=["alpha", "very-long-label"],
        output_path=str(output_path),
        per_row=2,
        qr_size=60,
        label_height=24,
        padding=8,
        label_max_chars=5,
        format="svg",
    )

    assert returned_path == str(output_path)
    assert output_path.is_file()

    root = ET.fromstring(output_path.read_text(encoding="utf-8"))
    labels = [node.text for node in root.findall(".//{http://www.w3.org/2000/svg}text")]

    assert labels == ["alpha", "very-"]


def test_generate_qrcode_grid_writes_png_with_expected_dimensions(tmp_path: Path) -> None:
    output_path = tmp_path / "nested" / "codes.png"

    returned_path = generate_qrcode_grid(
        strings=["one", "two"], output_path=str(output_path), per_row=1, qr_size=40, label_height=20, padding=10, label_max_chars=10, format="png"
    )

    assert returned_path == str(output_path)
    assert output_path.is_file()

    with Image.open(output_path) as image:
        assert image.size == (60, 150)
