output "application_id" {
  value       = oci_functions_application.this.id
  description = "OCID of the Functions application."
}

output "function_id" {
  value       = length(oci_functions_function.api) > 0 ? oci_functions_function.api[0].id : ""
  description = "OCID of the API function. Empty until a real image is deployed in Step 2."
}

output "function_endpoint" {
  value       = length(oci_functions_function.api) > 0 ? oci_functions_function.api[0].invoke_endpoint : ""
  description = "Direct invocation endpoint for the function. Empty until Step 2."
}
