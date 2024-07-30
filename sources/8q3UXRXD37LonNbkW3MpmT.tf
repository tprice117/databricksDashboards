import {
  to = segment_source.id-8q3UXRXD37LonNbkW3MpmT
  id = "8q3UXRXD37LonNbkW3MpmT"
}

resource "segment_source" "id-8q3UXRXD37LonNbkW3MpmT" {
  enabled = true
  labels = [
    {
      key   = "environment"
      value = "prod"
    },
  ]
  metadata = {
    id = "IqDTy1TpoU"
  }
  name     = "Webflow"
  settings = "{\"website_url\":\"https://trydownstream.io\"}"
  slug     = "webflow"
}