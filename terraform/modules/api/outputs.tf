output "gateway_id" {
  value       = oci_apigateway_gateway.this.id
  description = "OCID of the API Gateway."
}

output "gateway_hostname" {
  value       = oci_apigateway_gateway.this.hostname
  description = "Hostname of the API Gateway (without scheme or path)."
}

output "api_base_url" {
  value       = "https://${oci_apigateway_gateway.this.hostname}/v1"
  description = "Full base URL for the API. Deployment routes are active after Step 2 function deploy."
}
