from __future__ import annotations

from pathlib import Path

import ipxact
import pytest
import xactflow.SCR
from lxml import etree

from build_designs import build_wide_design
from xactflow_design import design_to_bytes, write_design_file


def _write_and_reparse(design: ipxact.Design, tmp_path: Path) -> ipxact.Design:
    path = write_design_file(design, tmp_path / "written.xml")
    return ipxact.parse_file(path)


def test_fixture_round_trips(top_design_path, design_schema, tmp_path):
    design = ipxact.parse_file(top_design_path)
    path = write_design_file(design, tmp_path / "top_design.xml")

    design_schema.assertValid(etree.parse(str(path)))
    assert ipxact.parse_file(path) == design


def test_fixture_output_passes_scr_checks(top_design_path, tmp_path):
    design = ipxact.parse_file(top_design_path)
    assert xactflow.SCR.run_single_doc_checks(_write_and_reparse(design, tmp_path)) == []


def test_wide_design_is_schema_valid(design_schema, tmp_path):
    path = write_design_file(build_wide_design(), tmp_path / "wide.xml")
    design_schema.assertValid(etree.parse(str(path)))


def test_wide_design_round_trips(tmp_path):
    design = build_wide_design()
    assert _write_and_reparse(design, tmp_path) == design


def test_wide_design_output_passes_scr_checks(tmp_path):
    reparsed = _write_and_reparse(build_wide_design(), tmp_path)
    assert xactflow.SCR.run_single_doc_checks(reparsed) == []


def test_vendor_extensions_are_not_reformatted(tmp_path):
    extension = '<vendor:tag xmlns:vendor="http://example.org/vendor" n="1"><vendor:inner/></vendor:tag>'
    design = ipxact.Design(
        vlnv=ipxact.VLNV("example.org", "ip", "extended", "1.0"),
        vendor_extensions=[extension],
    )
    assert extension in design_to_bytes(design).decode()

    # Reading an extension back adds the ipxact declaration that was in scope around it, which
    # is ipxact-compiler's own behavior; from there the fragment must stay byte-stable.
    reparsed = _write_and_reparse(design, tmp_path)
    assert "<vendor:inner/></vendor:tag>" in reparsed.vendor_extensions[0]
    assert _write_and_reparse(reparsed, tmp_path) == reparsed


def test_interconnections_and_monitor_interconnections_share_one_container(design_schema, tmp_path):
    design = ipxact.Design(
        vlnv=ipxact.VLNV("example.org", "ip", "mixed", "1.0"),
        component_instances=[
            ipxact.ComponentInstance(
                instance_name="a", component_ref=ipxact.VLNVRef("example.org", "ip", "comp", "1.0")
            ),
            ipxact.ComponentInstance(
                instance_name="b", component_ref=ipxact.VLNVRef("example.org", "ip", "comp", "1.0")
            ),
        ],
        interconnections=[
            ipxact.Interconnection(
                name="conn0",
                active_interface=ipxact.ActiveInterface(component_instance_ref="a", bus_ref="if0"),
                other_active_interfaces=[ipxact.ActiveInterface(component_instance_ref="b", bus_ref="if0")],
            )
        ],
        monitor_interconnections=[
            ipxact.MonitorInterconnection(
                name="mon0",
                monitored_active_interface=ipxact.MonitorInterfaceRef(component_instance_ref="a", bus_ref="if0"),
                monitor_interfaces=[ipxact.MonitorInterfaceRef(component_instance_ref="b", bus_ref="if0")],
            )
        ],
    )
    path = write_design_file(design, tmp_path / "mixed.xml")
    design_schema.assertValid(etree.parse(str(path)))
    assert ipxact.parse_file(path) == design


def test_part_select_with_only_one_range_side_is_rejected():
    design = ipxact.Design(
        vlnv=ipxact.VLNV("example.org", "ip", "bad_range", "1.0"),
        ad_hoc_connections=[
            ipxact.AdHocConnection(
                name="tie",
                internal_port_references=[
                    ipxact.InternalPortReference(
                        component_instance_ref="a",
                        port_ref="p",
                        part_select=ipxact.PartSelect(range_left="7"),
                    )
                ],
            )
        ],
    )
    with pytest.raises(ValueError, match="range_left and range_right"):
        design_to_bytes(design)


def test_empty_part_select_is_rejected():
    design = ipxact.Design(
        vlnv=ipxact.VLNV("example.org", "ip", "empty_part_select", "1.0"),
        ad_hoc_connections=[
            ipxact.AdHocConnection(
                name="tie",
                internal_port_references=[
                    ipxact.InternalPortReference(
                        component_instance_ref="a", port_ref="p", part_select=ipxact.PartSelect()
                    )
                ],
            )
        ],
    )
    with pytest.raises(ValueError, match="indices or a range"):
        design_to_bytes(design)


def test_choice_without_enumerations_is_rejected():
    design = ipxact.Design(
        vlnv=ipxact.VLNV("example.org", "ip", "empty_choice", "1.0"),
        choices=[ipxact.Choice(name="empty")],
    )
    with pytest.raises(ValueError, match="at least one enumeration"):
        design_to_bytes(design)


def test_interconnection_with_only_the_primary_active_interface_is_rejected():
    design = ipxact.Design(
        vlnv=ipxact.VLNV("example.org", "ip", "lonely_interconnection", "1.0"),
        interconnections=[
            ipxact.Interconnection(
                name="conn0",
                active_interface=ipxact.ActiveInterface(component_instance_ref="a", bus_ref="if0"),
            )
        ],
    )
    with pytest.raises(ValueError, match="second active interface"):
        design_to_bytes(design)


def test_ad_hoc_connection_without_port_references_is_rejected():
    design = ipxact.Design(
        vlnv=ipxact.VLNV("example.org", "ip", "empty_adhoc", "1.0"),
        ad_hoc_connections=[ipxact.AdHocConnection(name="tie", tied_value="open")],
    )
    with pytest.raises(ValueError, match="internal or external port reference"):
        design_to_bytes(design)


def test_monitor_interconnection_without_monitors_is_rejected():
    design = ipxact.Design(
        vlnv=ipxact.VLNV("example.org", "ip", "empty_monitor", "1.0"),
        monitor_interconnections=[
            ipxact.MonitorInterconnection(
                name="mon0",
                monitored_active_interface=ipxact.MonitorInterfaceRef(component_instance_ref="a", bus_ref="if0"),
            )
        ],
    )
    with pytest.raises(ValueError, match="at least one monitor interface"):
        design_to_bytes(design)
