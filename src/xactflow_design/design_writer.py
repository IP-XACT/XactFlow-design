from __future__ import annotations

from pathlib import Path
from typing import Sequence, Union

from lxml import etree

from ipxact.schema.design import (
    ActiveInterface,
    AdHocConnection,
    ComponentInstance,
    Design,
    ExternalPortReference,
    HierInterface,
    Interconnection,
    InternalPortReference,
    MonitorInterconnection,
    MonitorInterfaceRef,
    PowerDomainLink,
)

from .common_writer import (
    NAMESPACE,
    add_assertions,
    add_choices,
    add_document_name_group,
    add_items,
    add_name_group,
    add_parameters,
    add_part_select,
    add_sub_port_references,
    add_text,
    add_texts,
    element,
    sub,
    write_vendor_extensions,
    write_vlnv_ref,
)


def write_design(design: Design) -> etree._Element:
    """Build the ipxact:design root element for a Design.

    Child order follows design.xsd's design element sequence: documentNameGroup,
    componentInstances, interconnections, adHocConnections, choices, parameters,
    assertions, vendorExtensions.
    """
    root = element("design")
    add_document_name_group(root, design.vlnv, design.display_name, design.short_description, design.description)
    add_items(root, "componentInstances", design.component_instances, _write_component_instance)
    _add_interconnections(root, design.interconnections, design.monitor_interconnections)
    _add_ad_hoc_connections(root, design.ad_hoc_connections)
    add_choices(root, design.choices)
    add_parameters(root, design.parameters)
    add_assertions(root, design.assertions)
    write_vendor_extensions(root, design.vendor_extensions)
    etree.cleanup_namespaces(root, top_nsmap={"ipxact": NAMESPACE})
    return root


def _write_power_domain_link(link: PowerDomainLink) -> etree._Element:
    if not link.internal_power_domain_refs:
        raise ValueError(
            f"power domain link to {link.external_power_domain_ref!r} requires at least one"
            " internal power domain reference"
        )
    elem = element("powerDomainLink")
    sub(elem, "externalPowerDomainReference", link.external_power_domain_ref)
    add_texts(elem, "internalPowerDomainReference", link.internal_power_domain_refs)
    return elem


def _write_component_instance(instance: ComponentInstance) -> etree._Element:
    elem = element("componentInstance")
    sub(elem, "instanceName", instance.instance_name)
    add_text(elem, "displayName", instance.display_name)
    add_text(elem, "shortDescription", instance.short_description)
    add_text(elem, "description", instance.description)
    elem.append(write_vlnv_ref("componentRef", instance.component_ref))
    add_items(elem, "powerDomainLinks", instance.power_domain_links, _write_power_domain_link)
    write_vendor_extensions(elem, instance.vendor_extensions)
    return elem


def _write_internal_port_reference(ref: InternalPortReference) -> etree._Element:
    elem = element("internalPortReference", portRef=ref.port_ref, componentInstanceRef=ref.component_instance_ref)
    add_sub_port_references(elem, ref.sub_port_refs)
    add_part_select(elem, ref.part_select)
    write_vendor_extensions(elem, ref.vendor_extensions)
    return elem


def _write_external_port_reference(ref: ExternalPortReference) -> etree._Element:
    elem = element("externalPortReference", portRef=ref.port_ref)
    add_sub_port_references(elem, ref.sub_port_refs)
    add_part_select(elem, ref.part_select)
    write_vendor_extensions(elem, ref.vendor_extensions)
    return elem


def _write_ad_hoc_connection(connection: AdHocConnection) -> etree._Element:
    elem = element("adHocConnection")
    add_name_group(elem, connection.name, connection.display_name, connection.short_description, connection.description)
    add_text(elem, "tiedValue", connection.tied_value)
    if not connection.internal_port_references and not connection.external_port_references:
        raise ValueError(
            f"ad hoc connection {connection.name!r} requires at least one internal or external port reference"
        )
    references = sub(elem, "portReferences")
    for internal_ref in connection.internal_port_references:
        references.append(_write_internal_port_reference(internal_ref))
    for external_ref in connection.external_port_references:
        references.append(_write_external_port_reference(external_ref))
    write_vendor_extensions(elem, connection.vendor_extensions)
    return elem


def _add_ad_hoc_connections(parent: etree._Element, connections: Sequence[AdHocConnection]) -> None:
    add_items(parent, "adHocConnections", connections, _write_ad_hoc_connection)


def _write_active_interface(tag: str, interface: ActiveInterface) -> etree._Element:
    elem = element(tag, componentInstanceRef=interface.component_instance_ref, busRef=interface.bus_ref)
    add_text(elem, "description", interface.description)
    if interface.exclude_ports:
        exclude_ports = sub(elem, "excludePorts")
        add_texts(exclude_ports, "excludePort", interface.exclude_ports)
    write_vendor_extensions(elem, interface.vendor_extensions)
    return elem


def _write_hier_interface(interface: HierInterface) -> etree._Element:
    elem = element("hierInterface", busRef=interface.bus_ref)
    add_text(elem, "description", interface.description)
    write_vendor_extensions(elem, interface.vendor_extensions)
    return elem


def _write_interconnection(interconnection: Interconnection) -> etree._Element:
    if not interconnection.other_active_interfaces and not interconnection.hier_interfaces:
        raise ValueError(
            f"interconnection {interconnection.name!r} requires a second active interface"
            " or a hierarchical interface"
        )
    elem = element("interconnection")
    add_name_group(
        elem,
        interconnection.name,
        interconnection.display_name,
        interconnection.short_description,
        interconnection.description,
    )
    elem.append(_write_active_interface("activeInterface", interconnection.active_interface))
    for other in interconnection.other_active_interfaces:
        elem.append(_write_active_interface("activeInterface", other))
    for hier in interconnection.hier_interfaces:
        elem.append(_write_hier_interface(hier))
    write_vendor_extensions(elem, interconnection.vendor_extensions)
    return elem


def _write_monitor_interface_ref(tag: str, ref: MonitorInterfaceRef) -> etree._Element:
    elem = element(tag, componentInstanceRef=ref.component_instance_ref, busRef=ref.bus_ref, path=ref.path)
    add_text(elem, "description", ref.description)
    write_vendor_extensions(elem, ref.vendor_extensions)
    return elem


def _write_monitor_interconnection(interconnection: MonitorInterconnection) -> etree._Element:
    if not interconnection.monitor_interfaces:
        raise ValueError(f"monitor interconnection {interconnection.name!r} requires at least one monitor interface")
    elem = element("monitorInterconnection")
    add_name_group(
        elem,
        interconnection.name,
        interconnection.display_name,
        interconnection.short_description,
        interconnection.description,
    )
    elem.append(_write_monitor_interface_ref("monitoredActiveInterface", interconnection.monitored_active_interface))
    for monitor in interconnection.monitor_interfaces:
        elem.append(_write_monitor_interface_ref("monitorInterface", monitor))
    write_vendor_extensions(elem, interconnection.vendor_extensions)
    return elem


def _add_interconnections(
    parent: etree._Element,
    interconnections: Sequence[Interconnection],
    monitor_interconnections: Sequence[MonitorInterconnection],
) -> None:
    # The interconnections container interleaves ipxact:interconnection and
    # ipxact:monitorInterconnection freely, but Design keeps them in two separate lists with
    # no record of their original relative order, so all interconnections are written before
    # all monitorInterconnections.
    if not interconnections and not monitor_interconnections:
        return
    container = sub(parent, "interconnections")
    for interconnection in interconnections:
        container.append(_write_interconnection(interconnection))
    for monitor_interconnection in monitor_interconnections:
        container.append(_write_monitor_interconnection(monitor_interconnection))


def design_to_bytes(design: Design) -> bytes:
    """Serialize a Design to a pretty-printed IP-XACT XML document."""
    return etree.tostring(
        write_design(design).getroottree(),
        pretty_print=True,
        xml_declaration=True,
        encoding="UTF-8",
    )


def write_design_file(design: Design, path: Union[str, Path]) -> Path:
    path = Path(path)
    path.write_bytes(design_to_bytes(design))
    return path
