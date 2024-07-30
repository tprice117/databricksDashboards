import {
  to = segment_label.id-environment_dev
  id = "environment:dev"
}

resource "segment_label" "id-environment_dev" {
  description = null
  key         = "environment"
  value       = "dev"
}