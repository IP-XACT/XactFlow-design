from __future__ import annotations

import ipxact
import pytest
from xactflow import Exporter, discover_exporters

from build_designs import build_wide_design
from xactflow_design import DesignExporter


WIDE_FILE_NAME = "example.org_ip_wide_coverage_design_2.0.xml"


def _design(vendor="example.org", library="ip", name="d", version="1.0") -> ipxact.Design:
    return ipxact.Design(vlnv=ipxact.VLNV(vendor, library, name, version))


def test_exporter_writes_a_file_named_after_the_vlnv(tmp_path):
    design = build_wide_design()
    DesignExporter().export(design, tmp_path)

    written = tmp_path / WIDE_FILE_NAME
    assert written.exists()
    assert ipxact.parse_file(written) == design


def test_exporter_creates_a_missing_output_directory(tmp_path):
    output_dir = tmp_path / "nested" / "out"
    DesignExporter().export(build_wide_design(), output_dir)
    assert (output_dir / WIDE_FILE_NAME).exists()


def test_designs_differing_only_by_version_get_their_own_file(tmp_path):
    DesignExporter().export(_design(version="1.0"), tmp_path)
    DesignExporter().export(_design(version="2.0"), tmp_path)
    assert sorted(path.name for path in tmp_path.iterdir()) == ["example.org_ip_d_1.0.xml", "example.org_ip_d_2.0.xml"]


def test_exporting_the_same_design_again_replaces_its_file(tmp_path):
    DesignExporter().export(_design(), tmp_path)
    DesignExporter().export(_design(), tmp_path)
    assert [path.name for path in tmp_path.iterdir()] == ["example.org_ip_d_1.0.xml"]


@pytest.mark.parametrize("name", ["../../escaped", "a\\b", "", "with space", "a:b"])
def test_vlnv_that_is_not_a_single_file_name_is_rejected(tmp_path, name):
    with pytest.raises(ValueError, match="cannot be used as a file name"):
        DesignExporter().export(_design(name=name), tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_another_design_with_the_same_file_name_is_not_overwritten(tmp_path):
    DesignExporter().export(_design(library="a_b", name="c"), tmp_path)
    with pytest.raises(FileExistsError):
        DesignExporter().export(_design(library="a", name="b_c"), tmp_path)


@pytest.mark.parametrize("content", ["not xml", "<other/>"])
def test_a_file_that_is_not_a_design_is_not_overwritten(tmp_path, content):
    (tmp_path / "example.org_ip_d_1.0.xml").write_text(content)
    with pytest.raises(FileExistsError):
        DesignExporter().export(_design(), tmp_path)
    assert (tmp_path / "example.org_ip_d_1.0.xml").read_text() == content


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
