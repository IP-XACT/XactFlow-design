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


def test_vendor_extensions_keep_processing_instructions_and_comments(tmp_path):
    # ipxact-compiler returns a processing instruction in vendorExtensions as its own fragment.
    extensions = ["<?acme-tool keep?>", "<!-- note -->", '<acme:setting xmlns:acme="http://acme.example/ext">on</acme:setting>']
    design = ipxact.Design(vlnv=ipxact.VLNV("example.org", "ip", "pi", "1.0"), vendor_extensions=extensions)
    assert "<ipxact:vendorExtensions>" + "".join(extensions) + "</ipxact:vendorExtensions>" in design_to_bytes(design).decode()

    reparsed = _write_and_reparse(design, tmp_path)
    assert reparsed.vendor_extensions[0] == "<?acme-tool keep?>"
    assert _write_and_reparse(reparsed, tmp_path) == reparsed


def test_vendor_extensions_keep_text_and_drop_an_xml_declaration():
    design = ipxact.Design(
        vlnv=ipxact.VLNV("example.org", "ip", "text", "1.0"),
        vendor_extensions=["note", '<?xml version="1.0"?><x:a xmlns:x="http://example.org/x"/>', "tail"],
    )
    text = design_to_bytes(design).decode()
    assert '<ipxact:vendorExtensions>note<x:a xmlns:x="http://example.org/x"/>tail</ipxact:vendorExtensions>' in text


def test_foreign_attribute_with_a_processing_instruction_extension():
    parameter_design = _design_with_tagged_parameter('<?acme-tool keep?>')
    assert "<?acme-tool keep?>" in design_to_bytes(parameter_design).decode()


def _design_with_tagged_parameter(extension: str) -> ipxact.Design:
    parameter = ipxact.Parameter(
        name="P",
        value=ipxact.Expression("1"),
        other_attributes={"{http://example.org/vendor}tool": "kept"},
        vendor_extensions=[extension],
    )
    return ipxact.Design(vlnv=ipxact.VLNV("example.org", "ip", "tagged", "1.0"), parameters=[parameter])


def test_foreign_attribute_keeps_a_nested_extension_prefix():
    extension = '<a:outer xmlns:a="http://a"><v:inner xmlns:v="http://example.org/vendor">x</v:inner></a:outer>'
    assert "<v:inner>x</v:inner>" in design_to_bytes(_design_with_tagged_parameter(extension)).decode()


def test_extension_cannot_take_over_the_ipxact_prefix():
    extension = '<ipxact:x xmlns:ipxact="http://example.org/vendor"/>'
    root = etree.fromstring(design_to_bytes(_design_with_tagged_parameter(extension)))
    parameter = root.find("ipxact:parameters/ipxact:parameter", {"ipxact": root.nsmap["ipxact"]})
    assert parameter is not None
    assert parameter.nsmap["ipxact"] == "http://www.accellera.org/XMLSchema/IPXACT/1685-2022"


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


def test_empty_part_select_is_rejected():
    design = ipxact.Design(
        vlnv=ipxact.VLNV("example.org", "ip", "empty_part_select", "1.0"),
        component_instances=[_instance("a")],
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
        component_instances=[_instance("a")],
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


def test_power_domain_link_without_internal_refs_is_rejected():
    design = ipxact.Design(
        vlnv=ipxact.VLNV("example.org", "ip", "empty_power_domain_link", "1.0"),
        component_instances=[
            ipxact.ComponentInstance(
                instance_name="a",
                component_ref=ipxact.VLNVRef("example.org", "ip", "comp", "1.0"),
                power_domain_links=[ipxact.PowerDomainLink(external_power_domain_ref=ipxact.Expression("PD_MAIN"))],
            )
        ],
    )
    with pytest.raises(ValueError, match="internal power domain reference"):
        design_to_bytes(design)


def _instance(name: str) -> ipxact.ComponentInstance:
    return ipxact.ComponentInstance(instance_name=name, component_ref=ipxact.VLNVRef("example.org", "ip", "comp", "1.0"))


def _interconnection(name: str, instance: str = "a") -> ipxact.Interconnection:
    return ipxact.Interconnection(
        name=name,
        active_interface=ipxact.ActiveInterface(component_instance_ref=instance, bus_ref="if0"),
        hier_interfaces=[ipxact.HierInterface(bus_ref="top")],
    )


def _ad_hoc_connection(name: str, instance: str = "a") -> ipxact.AdHocConnection:
    return ipxact.AdHocConnection(
        name=name, internal_port_references=[ipxact.InternalPortReference(component_instance_ref=instance, port_ref="p")]
    )


def _monitor_interconnection(name: str) -> ipxact.MonitorInterconnection:
    return ipxact.MonitorInterconnection(
        name=name,
        monitored_active_interface=ipxact.MonitorInterfaceRef(component_instance_ref="a", bus_ref="if0"),
        monitor_interfaces=[ipxact.MonitorInterfaceRef(component_instance_ref="a", bus_ref="mon")],
    )


def _parameter(parameter_id: str, choice_ref=None) -> ipxact.Parameter:
    return ipxact.Parameter(name=parameter_id, value=ipxact.Expression("1"), parameter_id=parameter_id, choice_ref=choice_ref)


def _choice(name: str) -> ipxact.Choice:
    return ipxact.Choice(name=name, enumerations=[ipxact.ChoiceEnumeration(value=ipxact.Expression("1"))])


@pytest.mark.parametrize(
    "fields, error",
    [
        ({"component_instances": [_instance("a"), _instance("a")]}, "duplicate component instance name 'a'"),
        ({"interconnections": [_interconnection("c", instance="ghost")]}, "unknown component instance 'ghost'"),
        ({"ad_hoc_connections": [_ad_hoc_connection("h", instance="ghost")]}, "unknown component instance 'ghost'"),
        (
            {"interconnections": [_interconnection("c")], "monitor_interconnections": [_monitor_interconnection("c")]},
            "duplicate interconnection name 'c'",
        ),
        ({"ad_hoc_connections": [_ad_hoc_connection("h"), _ad_hoc_connection("h")]}, "duplicate ad hoc connection name 'h'"),
        ({"parameters": [_parameter("P"), _parameter("P")]}, "duplicate parameter id 'P'"),
        ({"choices": [_choice("ch"), _choice("ch")]}, "duplicate choice name 'ch'"),
        ({"parameters": [_parameter("P", choice_ref="ghost")]}, "unknown choice 'ghost'"),
    ],
)
def test_xsd_identity_constraints_are_enforced(fields, error):
    design = ipxact.Design(
        vlnv=ipxact.VLNV("example.org", "ip", "constraints", "1.0"), component_instances=[_instance("a")]
    )
    for name, value in fields.items():
        setattr(design, name, value)
    with pytest.raises(ValueError, match=error):
        design_to_bytes(design)
