---
type: tooling
---

# Taxonomy

Every `tags:` value on every page must appear in the tag list below. Introducing a new tag means adding it here in the same commit, with a one-line meaning. Keep tags few and general; if two tags mean nearly the same thing, merge them. `lint.py check` warns on tags missing from this file and reports listed tags no page uses.

- networking — switches, routing, VLANs, DNS, firewalls
- compute — hypervisors, VMs, containers, bare metal
- storage — disks, pools, NAS, volumes
- backup — backup jobs, replication, recovery
- monitoring — metrics, logs, alerting, dashboards
- security — access control, certificates, VPN, hardening

## Page types

Every page `type:` the schema allows is described here with a one-line meaning, so any OKF consumer can learn this bundle's vocabulary without reading the lint config. The authoritative schema lives in `lint.py`; `lint.py check` warns when the two drift.

- component — one host, VM, container, service, device, subnet, peer, or volume
- topology — a connection map of part of the network, with a Mermaid diagram
- concept — a protocol, pattern, or technique
- runbook — how to do something: bootstrap, recover, upgrade, debug
- incident — something that broke, what happened, and how it was fixed
- synthesis — a cross-cutting analysis, comparison, or evaluation
- source — a citable source page, including decision records
- query — a filed answer worth keeping
