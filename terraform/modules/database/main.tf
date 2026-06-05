locals {
  prefix     = "${var.app_name}-${var.environment}"
  table_name = replace("${var.app_name}_${var.environment}_jobs", "-", "_")
}

# ── OCI NoSQL Database (Always Free tier) ────────────────────────────────────
# Always Free: 3 tables, 25 read units, 25 write units, 5 GB each.
# Resource principal auth from Functions — no credentials or wallet needed.

resource "oci_nosql_table" "this" {
  compartment_id = var.compartment_ocid
  name           = local.table_name

  ddl_statement = "CREATE TABLE IF NOT EXISTS ${local.table_name} (user_id STRING, job_id STRING, status STRING, text STRING, text_length INTEGER, created_at STRING, updated_at STRING, error STRING, audio_path STRING, audio_expires_at STRING, PRIMARY KEY (SHARD(user_id), job_id))"

  table_limits {
    max_read_units     = 25
    max_write_units    = 25
    max_storage_in_gbs = 5
  }

  is_auto_reclaimable = true
}
