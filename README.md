# xactflow-design

A [XactFlow](https://github.com/IP-XACT/XactFlow) exporter plugin that serializes an
`ipxact.Design` object into a valid [IEEE 1685-2022](https://standards.ieee.org/ieee/1685/10307/)
IP-XACT `design` XML document.

[`ipxact-compiler`](https://github.com/IP-XACT/ipxact-compiler) reads IP-XACT XML and hands back
Python objects, it never writes XML. This package is the other direction: given a `Design`, it
writes the XML back out.

## Installation

```bash
pip install xactflow-design
```

For local development, `requirements-dev.txt` overrides `ipxact-compiler` and `xactflow` to
local installations. It can be modified to adapt the paths or to keep either version on PyPI.

```bash
pip install -r requirements-dev.txt -e .
```

Requires Python >= 3.9.

## Usage

```python
from pathlib import Path

import ipxact
from xactflow_design import DesignExporter

design = ipxact.parse_file("top_design.xml")
# some manipulation on the design object can be done
DesignExporter().export(design, Path("out")) # writes out/top_design.xml
```

The output file is named after the design's VLNV name (`<vlnv.name>.xml`) inside `output_dir`,
which is created if it does not exist.

Lower-level entry points are available for callers that want the tree or the bytes rather than a
file:

```python
from xactflow_design import design_to_bytes, write_design, write_design_file

element = write_design(design)              # the lxml ipxact:design root element
data = design_to_bytes(design)              # pretty-printed bytes, with an XML declaration
path = write_design_file(design, "out.xml") # writes and returns the path
```

Once installed, the exporter registers itself under the `xactflow.exporters` entry point group as
`design`, so `xactflow design ...` becomes available as a XactFlow CLI subcommand. Note that
XactFlow's CLI always links a design before calling an exporter, so for now the way to use
this package is to call `DesignExporter().export(...)` directly on a `Design`.

`export()` raises `TypeError` for anything that is not an `ipxact.Design`. Accepting an
`LinkedDesign` (re-materializing a fully resolved design back to XML, or writing out a
matching `designConfiguration` alongside it) is a planned later addition, not an oversight.

## Design notes

- **Element order comes from the XSD, not from the dataclasses.** `design`'s sequence puts
  `displayName`/`shortDescription`/`description` right after the VLNV, and `componentInstance`
  puts `componentRef` before `powerDomainLinks`, while the corresponding dataclasses declare those
  fields in a different order. The same mismatch repeats in `interconnection` and
  `monitorInterconnection`, whose `nameGroup` opens the element while the Python fields are
  trailing optionals. Every writer here follows the schema.
- **Expressions are written verbatim.** Anything typed `Expression` in `ipxact-compiler`
  (`tiedValue`, `externalPowerDomainReference`, a `parameter`'s `value`, a `partSelect`'s
  `left`/`right`, ...) is a raw string and is emitted unchanged, never evaluated or reformatted.
- **Vendor extensions stay identical.** Their content is not IP-XACT's to define, so each
  fragment is re-inserted as parsed.
- **Defaults are omitted.** Attributes whose value equals the schema default
  (`resolve="immediate"`, `type="string"`) are left out, which keeps the output close to
  hand-written IP-XACT and still round-trips exactly.
- **Interconnections and monitor interconnections share one XML container but two Python
  lists.** `design.xsd`'s `interconnections` element freely interleaves `interconnection` and
  `monitorInterconnection` children, but `Design` keeps them as two separate lists with no record
  of their original relative order. The writer emits every `interconnection` first, then every
  `monitorInterconnection`; the content is unaffected, only the interleaving is not preserved.
- **Required XSD cardinalities raise `ValueError` when left unsatisfied, instead of emitting
  invalid XML.** An `interconnection` needs a second active interface or a hierarchical interface,
  an `adHocConnection` needs at least one internal or external port reference, a
  `monitorInterconnection` needs at least one monitor interface, a `powerDomainLink` needs at
  least one internal power domain reference, a `choice` needs at least one enumeration, and a
  `partSelect` needs indices or a complete range. Rather than silently writing an incomplete
  element for any of these, the writer raises a specific error naming the missing field.

## Development

```bash
pip install -r requirements-dev.txt -e .
pytest
```

The tests round-trip both `ipxact-compiler`'s `top_design.xml` fixture and a hand-built design
through the writer and back through the parser, validate the written XML against `design.xsd`
with `lxml.etree.XMLSchema.assertValid`, and re-run `xactflow.SCR.run_single_doc_checks` on the
result. They expect `ipxact-compiler` and the IEEE 1685-2022 schema (`IEEE_1685-2022/schema/
1685-2022/`) as sibling checkouts; set `IPXACT_SCHEMA_DIR` to point the schema somewhere else.

## License

LGPL-3.0. See [LICENSE](LICENSE).
