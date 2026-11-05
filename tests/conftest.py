from __future__ import annotations

from pathlib import Path

import ipxact
import pytest
from lxml import etree

FIXTURE_PATH = Path(__file__).resolve().parent / "xml" / "top_design.xml"


@pytest.fixture(scope="session")
def design_schema() -> etree.XMLSchema:
    # ipxact-compiler ships the IEEE 1685-2022 XSD; lxml resolves the xs:include chain
    # relative to the file it parsed, so no flattening.
    return etree.XMLSchema(etree.parse(str(ipxact.xsd_path() / "design.xsd")))


@pytest.fixture(scope="session")
def top_design_path() -> Path:
    return FIXTURE_PATH
