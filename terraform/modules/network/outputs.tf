output "vcn_id" {
  value       = oci_core_vcn.this.id
  description = "OCID of the VCN."
}

output "private_subnet_id" {
  value       = oci_core_subnet.private.id
  description = "OCID of the private subnet. Pass to the functions module."
}
