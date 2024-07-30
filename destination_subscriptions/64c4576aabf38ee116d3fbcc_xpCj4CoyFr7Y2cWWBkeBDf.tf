import {
  to = segment_destination_subscription.id-64c4576aabf38ee116d3fbcc_xpCj4CoyFr7Y2cWWBkeBDf
  id = "64c4576aabf38ee116d3fbcc:xpCj4CoyFr7Y2cWWBkeBDf"
}

resource "segment_destination_subscription" "id-64c4576aabf38ee116d3fbcc_xpCj4CoyFr7Y2cWWBkeBDf" {
  action_id      = "g1sxmVyCGxututXRQhYSGH"
  destination_id = "64c4576aabf38ee116d3fbcc"
  enabled        = true
  model_id       = null
  name           = "Account"
  settings       = "{\"account_number\":{\"@path\":\"$.groupId\"},\"batch_size\":\"5000\",\"billing_city\":{\"@if\":{\"else\":{\"@path\":\"$.properties.address.city\"},\"exists\":{\"@path\":\"$.traits.address.city\"},\"then\":{\"@path\":\"$.traits.address.city\"}}},\"billing_country\":{\"@if\":{\"else\":{\"@path\":\"$.properties.address.country\"},\"exists\":{\"@path\":\"$.traits.address.country\"},\"then\":{\"@path\":\"$.traits.address.country\"}}},\"billing_postal_code\":{\"@if\":{\"else\":{\"@path\":\"$.properties.address.postal_code\"},\"exists\":{\"@path\":\"$.traits.address.postal_code\"},\"then\":{\"@path\":\"$.traits.address.postal_code\"}}},\"billing_state\":{\"@if\":{\"else\":{\"@path\":\"$.properties.address.state\"},\"exists\":{\"@path\":\"$.traits.address.state\"},\"then\":{\"@path\":\"$.traits.address.state\"}}},\"billing_street\":{\"@if\":{\"else\":{\"@path\":\"$.properties.address.street\"},\"exists\":{\"@path\":\"$.traits.address.street\"},\"then\":{\"@path\":\"$.traits.address.street\"}}},\"bulkUpsertExternalId\":{\"externalIdName\":\"\",\"externalIdValue\":\"\"},\"description\":{\"@if\":{\"else\":{\"@path\":\"$.properties.description\"},\"exists\":{\"@path\":\"$.traits.description\"},\"then\":{\"@path\":\"$.traits.description\"}}},\"enable_batching\":false,\"name\":{\"@path\":\"$.traits.name\"},\"number_of_employees\":{\"@if\":{\"else\":{\"@path\":\"$.properties.employees\"},\"exists\":{\"@path\":\"$.traits.employees\"},\"then\":{\"@path\":\"$.traits.employees\"}}},\"operation\":\"create\",\"phone\":{\"@if\":{\"else\":{\"@path\":\"$.properties.phone\"},\"exists\":{\"@path\":\"$.traits.phone\"},\"then\":{\"@path\":\"$.traits.phone\"}}},\"recordMatcherOperator\":\"OR\",\"website\":{\"@if\":{\"else\":{\"@path\":\"$.properties.website\"},\"exists\":{\"@path\":\"$.traits.website\"},\"then\":{\"@path\":\"$.traits.website\"}}}}"
  trigger        = "type = \"page\""
}