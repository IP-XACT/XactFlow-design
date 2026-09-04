from __future__ import annotations

import ipxact
import pytest
from xactflow import Exporter, discover_exporters

from build_designs import build_wide_design
from xactflow_design import DesignExporter


def test_exporter_writes_a_file_named_after_the_vlnv(tmp_path):
    design = build_wide_design()
    DesignExporter().export(design, tmp_path)

    written = tmp_path / "wide_coverage_design.xml"
    assert written.exists()
    assert ipxact.parse_file(written) == design


def test_exporter_creates_a_missing_output_directory(tmp_path):
    output_dir = tmp_path / "nested" / "out"
    DesignExporter().export(build_wide_design(), output_dir)
    assert (output_dir / "wide_coverage_design.xml").exists()


def test_exporter_rejects_a_non_design_subject(tmp_path):
    with pytest.raises(TypeError, match=r"ipxact\.Design"):
        DesignExporter().export(object(), tmp_path)


def test_exporter_rejects_a_component(tmp_path):
    component = ipxact.Component(vlnv=ipxact.VLNV("example.org", "ip", "comp", "1.0"))
    with pytest.raises(TypeError):
        DesignExporter().export(component, tmp_path)


def test_exporter_is_registered_under_the_entry_point_group():
    assert discover_exporters()["design"] is DesignExporter
    assert issubclass(DesignExporter, Exporter)
    assert DesignExporter.name == "design"
