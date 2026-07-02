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

# ── Service gateway (free path to Oracle services: Object Storage) ────────────

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

# ── NAT gateway removed ───────────────────────────────────────────────────────
# Functions were previously in a private subnet and needed a NAT gateway (~$1/month)
# to make outbound calls to the ARM VM job store over its public IP. Moving Functions
# to the public subnet (shared with API Gateway) eliminates this cost entirely —
# the Internet Gateway handles egress for free. Functions cannot receive unsolicited
# inbound connections regardless of subnet: OCI only invokes them via its internal
# fabric through API Gateway, so there is no security regression from this change.
