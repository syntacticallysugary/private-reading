output "namespace" {
  value       = var.namespace
  description = "OCI Object Storage namespace."
}

output "web_bucket_name" {
  value       = oci_objectstorage_bucket.web.name
  description = "Name of the static web assets bucket."
}

output "web_bucket_url" {
  value       = "https://objectstorage.${var.oci_region}.oraclecloud.com/n/${var.namespace}/b/${oci_objectstorage_bucket.web.name}/o"
  description = "Base URL for the static web bucket (object path appended by SPA deploy step)."
}

output "audiobooks_bucket_name" {
  value       = oci_objectstorage_bucket.audiobooks.name
  description = "Name of the private audiobooks bucket."
}
