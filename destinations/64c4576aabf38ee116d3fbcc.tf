import {
  to = segment_destination.id-64c4576aabf38ee116d3fbcc
  id = "64c4576aabf38ee116d3fbcc"
}

resource "segment_destination" "id-64c4576aabf38ee116d3fbcc" {
  enabled = false
  metadata = {
    contacts          = null
    id                = "61957755c4d820be968457de"
    partner_owned     = false
    region_endpoints  = ["US"]
    supported_regions = ["us-west-2", "eu-west-1"]
  }
  name      = "Salesforce Instance #1"
  settings  = "{\"isSandbox\":false}"
  source_id = "8q3UXRXD37LonNbkW3MpmT"
}