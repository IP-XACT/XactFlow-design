"""Hand-built ipxact.Design objects used by the writer tests.

These are built directly rather than parsed from XML, so they exercise fields the top_design.xml
fixture does not reach.
"""

from __future__ import annotations

import ipxact

# ipxact-compiler serializes each vendorExtensions child with the namespace declarations that
# are in scope at that point, so an extension read back out of a design always carries the
# ipxact declaration too. Spelling it out here keeps round-trip comparison exact.
VENDOR_EXTENSION = (
    '<vendor:note xmlns:vendor="http://example.org/vendor"'
    ' xmlns:ipxact="http://www.accellera.org/XMLSchema/IPXACT/1685-2022">kept verbatim</vendor:note>'
)


def build_wide_design() -> ipxact.Design:
    """A Design covering every section design.xsd defines."""
    return ipxact.Design(
        vlnv=ipxact.VLNV("example.org", "ip", "wide_coverage_design", "2.0"),
        display_name="Wide coverage design",
        short_description="Every writable design section",
        description="Hand-built design exercising the writer end to end.",
        component_instances=[
            ipxact.ComponentInstance(
                instance_name="cpu0",
                component_ref=ipxact.VLNVRef("example.org", "ip", "cpu", "1.0", {"WIDTH": "32"}),
                power_domain_links=[
                    ipxact.PowerDomainLink(
                        external_power_domain_ref="PD_MAIN",
                        internal_power_domain_refs=["PD_CORE", "PD_CACHE"],
                    )
                ],
                display_name="CPU0",
                short_description="the processor",
                description="the main processor instance",
                vendor_extensions=[VENDOR_EXTENSION],
            ),
            ipxact.ComponentInstance(
                instance_name="mem0",
                component_ref=ipxact.VLNVRef("example.org", "ip", "mem", "1.0"),
            ),
        ],
        interconnections=[
            ipxact.Interconnection(
                name="cpu_mem_bus",
                active_interface=ipxact.ActiveInterface(
                    component_instance_ref="cpu0",
                    bus_ref="initiator",
                    exclude_ports=["debug_out"],
                    description="cpu side",
                    vendor_extensions=[VENDOR_EXTENSION],
                ),
                other_active_interfaces=[
                    ipxact.ActiveInterface(component_instance_ref="mem0", bus_ref="target")
                ],
                hier_interfaces=[
                    ipxact.HierInterface(bus_ref="top_bus", description="exported one level up")
                ],
                display_name="CPU-memory bus",
                short_description="main bus",
                description="connects the cpu initiator to the memory target",
                vendor_extensions=[VENDOR_EXTENSION],
            )
        ],
        monitor_interconnections=[
            ipxact.MonitorInterconnection(
                name="bus_monitor",
                monitored_active_interface=ipxact.MonitorInterfaceRef(
                    component_instance_ref="cpu0", bus_ref="initiator"
                ),
                monitor_interfaces=[
                    ipxact.MonitorInterfaceRef(
                        component_instance_ref="mem0",
                        bus_ref="target",
                        path="sub/instance",
                        description="a monitor tap",
                        vendor_extensions=[VENDOR_EXTENSION],
                    )
                ],
                display_name="Bus monitor",
                description="watches the main bus",
                vendor_extensions=[VENDOR_EXTENSION],
            )
        ],
        ad_hoc_connections=[
            ipxact.AdHocConnection(
                name="reset_net",
                internal_port_references=[
                    ipxact.InternalPortReference(
                        component_instance_ref="cpu0",
                        port_ref="rst_n",
                        sub_port_refs=[
                            ipxact.SubPortReference(
                                sub_port_ref="valid",
                                part_select=ipxact.PartSelect(indices=["0", "1"]),
                            )
                        ],
                        part_select=ipxact.PartSelect(range_left="7", range_right="0"),
                        vendor_extensions=[VENDOR_EXTENSION],
                    ),
                    ipxact.InternalPortReference(component_instance_ref="mem0", port_ref="rst_n"),
                ],
                external_port_references=[
                    ipxact.ExternalPortReference(
                        port_ref="ext_rst_n",
                        part_select=ipxact.PartSelect(range_left="0", range_right="0"),
                        vendor_extensions=[VENDOR_EXTENSION],
                    )
                ],
                tied_value="open",
                display_name="Reset net",
                short_description="global reset",
                description="ties every instance reset together",
                vendor_extensions=[VENDOR_EXTENSION],
            )
        ],
        choices=[
            ipxact.Choice(
                name="burst_choices",
                enumerations=[
                    ipxact.ChoiceEnumeration(value="1", text="single", help="single beat"),
                    ipxact.ChoiceEnumeration(value="4"),
                ],
            )
        ],
        parameters=[
            ipxact.Parameter(
                name="BURST_LEN",
                value="4",
                display_name="Burst length",
                short_description="beats per burst",
                description="the configured burst length",
                vectors=[ipxact.Vector(left="3", right="0")],
                arrays=[ipxact.ArrayBound(left="1", right="0")],
                parameter_id="BURST_LEN",
                prompt="Burst length:",
                choice_ref="burst_choices",
                order=1.0,
                config_groups=["basic"],
                minimum="1",
                maximum="16",
                type="int",
                sign="unsigned",
                prefix="kilo",
                unit="hertz",
                resolve="user",
                vendor_extensions=[VENDOR_EXTENSION],
            )
        ],
        assertions=[
            ipxact.Assertion(
                name="burst_len_positive",
                assert_expression="BURST_LEN > 0",
                display_name="Burst length positive",
                description="the burst length must be positive",
            )
        ],
        vendor_extensions=[VENDOR_EXTENSION],
    )
