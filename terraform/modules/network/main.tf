locals {
  prefix = "${var.app_name}-${var.environment}"
}

# ── VCN ───────────────────────────────────────────────────────────────────────

resource "oci_core_vcn" "this" {
  compartment_id = var.compartment_ocid
  display_name   = "${local.prefix}-vcn"
  cidr_blocks    = [var.vcn_cidr]
  dns_label      = replace(var.app_name, "-", "")
}

# ── DHCP options (use OCI's VCN-local resolver) ───────────────────────────────

resource "oci_core_default_dhcp_options" "this" {
  manage_default_resource_id = oci_core_vcn.this.default_dhcp_options_id

  options {
    type        = "DomainNameServer"
    server_type = "VcnLocalPlusInternet"
  }
}

# ── Service gateway (free path to Oracle services: Object Storage, ADB) ───────

data "oci_core_services" "all" {}

locals {
  # The "All <region> Services In Oracle Services Network" service label
  oracle_services_cidr = [
    for s in data.oci_core_services.all.services :
    s if length(regexall("All .* Services In Oracle Services Network", s.name)) > 0
  ][0]
}

resource "oci_core_service_gateway" "this" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.this.id
  display_name   = "${local.prefix}-service-gw"

  services {
    service_id = local.oracle_services_cidr.id
  }
}

# ── NAT gateway (internet egress for Functions — needed to reach job store) ───
# The ARM VM is in a separate Base VCN; its private IP is not routable from here.
# Functions use the ARM VM's public IP, which requires a NAT gateway for egress.
# NAT gateway is ~$0.36/month on OCI pay-as-you-go.

resource "oci_core_nat_gateway" "this" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.this.id
  display_name   = "${local.prefix}-nat-gw"
  block_traffic  = false
}

# ── Route table for private subnet ────────────────────────────────────────────
# Oracle service traffic → service gateway (free).
# All other internet traffic → NAT gateway (needed for job store on ARM VM).
# API Gateway calls Functions via OCI's internal fabric, not through this subnet route.

resource "oci_core_route_table" "private" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.this.id
  display_name   = "${local.prefix}-private-rt"

  route_rules {
    destination       = local.oracle_services_cidr.cidr_block
    destination_type  = "SERVICE_CIDR_BLOCK"
    network_entity_id = oci_core_service_gateway.this.id
  }

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_nat_gateway.this.id
  }
}

# ── Security list for private subnet ─────────────────────────────────────────
# Allows egress to Oracle services and to the job store on the ARM VM's public IP.
# No inbound rules (Functions are invoked by API Gateway via OCI's internal fabric).

resource "oci_core_security_list" "private" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.this.id
  display_name   = "${local.prefix}-private-sl"

  egress_security_rules {
    description      = "Allow egress to Oracle Services Network (Object Storage, ADB)"
    destination      = local.oracle_services_cidr.cidr_block
    destination_type = "SERVICE_CIDR_BLOCK"
    protocol         = "6" # TCP
    stateless        = false
  }

  egress_security_rules {
    description      = "Allow egress to job store on ARM VM public IP"
    destination      = "64.181.220.163/32"
    destination_type = "CIDR_BLOCK"
    protocol         = "6" # TCP
    stateless        = false
    tcp_options {
      min = 8000
      max = 8000
    }
  }
}

# ── Private subnet ────────────────────────────────────────────────────────────

resource "oci_core_subnet" "private" {
  compartment_id             = var.compartment_ocid
  vcn_id                     = oci_core_vcn.this.id
  display_name               = "${local.prefix}-private-subnet"
  cidr_block                 = var.private_subnet_cidr
  dns_label                  = "functions"
  prohibit_public_ip_on_vnic = true
  route_table_id             = oci_core_route_table.private.id
  security_list_ids          = [oci_core_security_list.private.id]
}
