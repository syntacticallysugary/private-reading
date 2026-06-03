output "db_id" {
  value       = oci_nosql_table.this.id
  description = "OCID of the NoSQL jobs table."
}

output "table_name" {
  value       = oci_nosql_table.this.name
  description = "Name of the NoSQL jobs table as provisioned."
}
