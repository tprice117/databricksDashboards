select 
  ug.id as user_group_id,
  og.id as ordergroup_id,
  og.project_id,
  og.agreement as order_group_agreement,
  og.code as order_group_code,
  og.end_date as order_group_end_date,
  og.is_delivery as order_group_is_delivery,
  og.placement_details as order_group_placement_details,
  og.removal_fee as order_group_removal_fee,
  og.shift_count as order_group_shift_count,
  og.start_date as order_group_start_date,

  --order
  o.id as order_id,
  o.accepted_on as order_accepted_on,
  o.billing_comments_internal_use as order_billing_comments_internal_use,
  o.code as order_code,
  o.completed_on as order_completed_on,
  o.created_on as order_created_on,
  o.end_date as order_end_date,
  o.schedule_window as order_schedule_window,
  o.status as order_status,
  o.submitted_on as order_submitted_on,
  o.created_by_id as order_created_by,
  o.submitted_by_id as submitted_by_id,

  --orderline
  oli.id as orderline_id,
  oli.backbill as orderline_backbill,
  oli.is_flat_rate as orderline_is_flat_rate,
  oli.paid as orderline_paid,
  oli.quantity as orderline_quantity,
  oli.rate as orderline_rate,
  oli.rate * oli.quantity as order_line_total,
  oli.platform_fee_percent as orderline_platform_fee_percent,
  oli.tax as orderline_tax,
  oli.stripe_invoice_line_item_id as stripe_invoice_line_item_id,
  oli.order_line_item_type_id as orderline_type,

  --main product
  mp.name as main_product,
  --main product category
  mpc.name as main_product_category,

  --main product category group
  mpcg.name as main_product_category_group,

  --user address 
  ua.state as user_address_state,

  --user
  u.is_staff as user_is_staff,
  u.first_name as user_first_name,
  u.last_name as user_last_name,

  --industry
  i.name as industry_name,

  --user group
  ug.name as user_group_name,
  ug.account_owner_id as user_group_account_owner_id,

  -- account owner
  uo.first_name as account_owner_first_name,
  uo.last_name as account_owner_last_name,

  --seller
  s.name as seller_name,

  --seller location
  sl.name as seller_location_name,

  --orderline item type
  olit.name as orderline_item_type_name

from bronze_prod.postgres_prod_restricted_bronze_public.api_orderlineitem oli
left join bronze_prod.postgres_prod_restricted_bronze_public.api_order o 
  on oli.order_id = o.id
left join bronze_prod.postgres_prod_restricted_bronze_public.api_ordergroup og 
  on o.order_group_id = og.id
left join bronze_prod.postgres_prod_restricted_bronze_public.api_sellerproductsellerlocation spsl
  on og.seller_product_seller_location_id = spsl.id
left join bronze_prod.postgres_prod_restricted_bronze_public.api_sellerproduct sp
  on spsl.seller_product_id = sp.id
left join bronze_prod.postgres_prod_restricted_bronze_public.api_product p 
  on sp.product_id = p.id
left join bronze_prod.postgres_prod_restricted_bronze_public.api_mainproduct mp 
  on p.main_product_id = mp.id
left join bronze_prod.postgres_prod_restricted_bronze_public.api_mainproductcategory mpc
  on mp.main_product_category_id = mpc.id
left join bronze_prod.postgres_prod_restricted_bronze_public.api_mainproductcategorygroup mpcg
  on mpc.group_id = mpcg.id
left join bronze_prod.postgres_prod_restricted_bronze_public.api_useraddress ua
  on og.user_address_id = ua.id
left join bronze_prod.postgres_prod_restricted_bronze_public.api_user u
  on o.created_by_id = u.id
left join bronze_prod.postgres_prod_restricted_bronze_public.api_usergroup ug
  on u.user_group_id = ug.id
left join bronze_prod.postgres_prod_restricted_bronze_public.api_seller s
  on sp.seller_id = s.id
left join bronze_prod.postgres_prod_restricted_bronze_public.api_usergroup ug_seller
  on s.id = ug_seller.seller_id
left join bronze_prod.postgres_prod_restricted_bronze_public.api_user uo
  on ug.account_owner_id = uo.id
left join bronze_prod.postgres_prod_restricted_bronze_public.api_industry i
  on ug.industry_id = i.id
left join bronze_prod.postgres_prod_restricted_bronze_public.api_sellerlocation sl
  on spsl.seller_location_id = sl.id
left join bronze_prod.postgres_prod_restricted_bronze_public.api_orderlineitemtype olit
  on oli.order_line_item_type_id = olit.id