import {
  to = segment_destination_subscription.id-64c45f1ffe1cb5f4488b78f3_vun4iNKmaukjRbGyVfUpEn
  id = "64c45f1ffe1cb5f4488b78f3:vun4iNKmaukjRbGyVfUpEn"
}

resource "segment_destination_subscription" "id-64c45f1ffe1cb5f4488b78f3_vun4iNKmaukjRbGyVfUpEn" {
  action_id      = "sXZzg4LGsu5WVyx5imvkWL"
  destination_id = "64c45f1ffe1cb5f4488b78f3"
  enabled        = false
  model_id       = null
  name           = "Identify Contact"
  settings       = "{\"avatar\":{\"@path\":\"$.traits.avatar\"},\"email\":{\"@path\":\"$.traits.email\"},\"external_id\":{\"@path\":\"$.userId\"},\"last_seen_at\":{\"@path\":\"$.timestamp\"},\"name\":{\"@path\":\"$.traits.name\"},\"phone\":{\"@path\":\"$.traits.phone\"}}"
  trigger        = "type = \"identify\""
}