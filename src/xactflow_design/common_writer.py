from __future__ import annotations

from typing import Callable, Optional, Sequence, TypeVar

from lxml import etree

from ipxact.schema.common import ArrayBound, Assertion, Choice, Parameter, PartSelect, SubPortReference, Vector
from ipxact.schema.vlnv import VLNVRef

NAMESPACE = "http://www.accellera.org/XMLSchema/IPXACT/1685-2022"
XSI_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"
SCHEMA_LOCATION = f"{NAMESPACE} {NAMESPACE}/index.xsd"
_NSMAP = {"ipxact": NAMESPACE}

T = TypeVar("T")


def qn(tag: str) -> str:
    """Build a namespace-qualified IP-XACT tag, e.g. qn("design") -> "{ns}design"."""
    return f"{{{NAMESPACE}}}{tag}"


def element(tag: str, text: object = None, /, **attrs: object) -> etree._Element:
    """Create an ipxact-namespaced element; attributes whose value is None are dropped.

    tag and text are positional-only so that **attrs stays free for XML attributes.
    """
    elem = etree.Element(qn(tag), nsmap=_NSMAP)
    for name, value in attrs.items():
        if value is not None:
            elem.set(name, str(value))
    if text is not None:
        elem.text = str(text)
    return elem


def sub(parent: etree._Element, tag: str, text: object = None, /, **attrs: object) -> etree._Element:
    child = element(tag, text, **attrs)
    parent.append(child)
    return child


def add_text(parent: etree._Element, tag: str, value: object, **attrs: object) -> None:
    """Append a simple text child, or nothing when the value is unset."""
    if value is not None:
        sub(parent, tag, value, **attrs)


def add_texts(parent: etree._Element, tag: str, values: Sequence[object]) -> None:
    for value in values:
        sub(parent, tag, value)


def add_items(parent: etree._Element, container_tag: str, items: Sequence[T], writer: Callable[[T], etree._Element]) -> None:
    """Write container_tag holding one writer(item) per item, or nothing when items is empty."""
    if not items:
        return
    container = sub(parent, container_tag)
    for item in items:
        container.append(writer(item))


def add_document_name_group(
    parent: etree._Element,
    vlnv: object,
    display_name: Optional[str],
    short_description: Optional[str],
    description: Optional[str],
) -> None:
    """Write documentNameGroup (vendor, library, name, version, displayName, shortDescription, description)."""
    sub(parent, "vendor", vlnv.vendor)
    sub(parent, "library", vlnv.library)
    sub(parent, "name", vlnv.name)
    sub(parent, "version", vlnv.version)
    add_text(parent, "displayName", display_name)
    add_text(parent, "shortDescription", short_description)
    add_text(parent, "description", description)


def add_name_group(
    parent: etree._Element,
    name: Optional[str],
    display_name: Optional[str] = None,
    short_description: Optional[str] = None,
    description: Optional[str] = None,
) -> None:
    """Write ipxact:nameGroup / nameGroupPort (name, displayName, shortDescription, description)."""
    if name is not None:
        sub(parent, "name", name)
    add_text(parent, "displayName", display_name)
    add_text(parent, "shortDescription", short_description)
    add_text(parent, "description", description)


def write_vendor_extensions(parent: etree._Element, extensions: Sequence[str]) -> None:
    """Re-insert opaque vendor extension fragments verbatim.

    Vendor extension content is not IP-XACT's to define, so it is kept byte-identical rather
    than re-derived. Giving every element that has children an empty text node switches
    libxml2's pretty printer off for the whole fragment, so serializing does not inject
    indentation into somebody else's markup.
    """
    if not extensions:
        return
    container = sub(parent, "vendorExtensions")
    for extension in extensions:
        container.append(etree.fromstring(extension.encode("utf-8")))
    for node in container.iter():
        if len(node) and node.text is None:
            node.text = ""


def write_vlnv_ref(tag: str, ref: VLNVRef) -> etree._Element:
    """Write a configurableLibraryRefType element (VLNV as attributes, e.g. ipxact:componentRef)."""
    elem = element(tag, vendor=ref.vendor, library=ref.library, name=ref.name, version=ref.version)
    if ref.config_element_values:
        values = sub(elem, "configurableElementValues")
        for reference_id, value in ref.config_element_values.items():
            sub(values, "configurableElementValue", value, referenceId=reference_id)
    return elem


def add_part_select(parent: etree._Element, part_select: Optional[PartSelect]) -> None:
    if part_select is None:
        return
    has_range = part_select.range_left is not None or part_select.range_right is not None
    if has_range and (part_select.range_left is None or part_select.range_right is None):
        raise ValueError("a part select range requires both range_left and range_right")
    if not part_select.indices and not has_range:
        raise ValueError("a part select requires indices or a range")
    elem = sub(parent, "partSelect")
    if part_select.indices:
        indices = sub(elem, "indices")
        add_texts(indices, "index", part_select.indices)
    if has_range:
        range_elem = sub(elem, "range")
        sub(range_elem, "left", part_select.range_left)
        sub(range_elem, "right", part_select.range_right)


def add_sub_port_references(parent: etree._Element, refs: Sequence[SubPortReference]) -> None:
    for ref in refs:
        elem = sub(parent, "subPortReference", subPortRef=ref.sub_port_ref)
        add_part_select(elem, ref.part_select)


def _add_vectors(parent: etree._Element, vectors: Sequence[Vector]) -> None:
    # Plain parameterType carries no vectorId attribute (only moduleParameterType does), so it
    # is dropped here rather than written out invalidly.
    if not vectors:
        return
    container = sub(parent, "vectors")
    for vector in vectors:
        vector_elem = sub(container, "vector")
        sub(vector_elem, "left", vector.left)
        sub(vector_elem, "right", vector.right)


def _add_array_bounds(parent: etree._Element, arrays: Sequence[ArrayBound]) -> None:
    if not arrays:
        return
    container = sub(parent, "arrays")
    for array in arrays:
        array_elem = sub(container, "array")
        sub(array_elem, "left", array.left)
        sub(array_elem, "right", array.right)


def _write_parameter(parameter: Parameter) -> etree._Element:
    elem = element(
        "parameter",
        None,
        parameterId=parameter.parameter_id,
        prompt=parameter.prompt,
        choiceRef=parameter.choice_ref,
        order=parameter.order,
        configGroups=" ".join(parameter.config_groups) if parameter.config_groups else None,
        minimum=parameter.minimum,
        maximum=parameter.maximum,
        type=parameter.type if parameter.type != "string" else None,
        sign=parameter.sign,
        prefix=parameter.prefix,
        unit=parameter.unit,
        resolve=parameter.resolve if parameter.resolve != "immediate" else None,
    )
    add_name_group(elem, parameter.name, parameter.display_name, parameter.short_description, parameter.description)
    _add_vectors(elem, parameter.vectors)
    _add_array_bounds(elem, parameter.arrays)
    sub(elem, "value", parameter.value)
    write_vendor_extensions(elem, parameter.vendor_extensions)
    return elem


def add_parameters(parent: etree._Element, parameters: Sequence[Parameter]) -> None:
    add_items(parent, "parameters", parameters, _write_parameter)


def add_choices(parent: etree._Element, choices: Sequence[Choice]) -> None:
    if not choices:
        return
    container = sub(parent, "choices")
    for choice in choices:
        if not choice.enumerations:
            raise ValueError(f"choice {choice.name!r} requires at least one enumeration")
        choice_elem = sub(container, "choice")
        sub(choice_elem, "name", choice.name)
        for enumeration in choice.enumerations:
            sub(choice_elem, "enumeration", enumeration.value, text=enumeration.text, help=enumeration.help)


def add_assertions(parent: etree._Element, assertions: Sequence[Assertion]) -> None:
    if not assertions:
        return
    container = sub(parent, "assertions")
    for assertion in assertions:
        assertion_elem = sub(container, "assertion")
        add_name_group(assertion_elem, assertion.name, assertion.display_name, description=assertion.description)
        sub(assertion_elem, "assert", assertion.assert_expression)
