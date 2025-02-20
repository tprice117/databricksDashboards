select 
--ordergroup
og.id as ordergroup_id
,og.project_id
,og.agreement as order_group_agreement
,og.code as order_group_code
,og.end_date as order_group_end_date
,og.is_delivery as order_group_is_delivery
,og.placement_details as order_group_placement_details
,og.removal_fee as order_group_removal_fee
,og.shift_count as order_group_shift_count
,og.start_date as order_group_start_date

--order
,o.id as order_id
,o.accepted_on as order_accepted_on
,o.billing_comments_internal_use as order_billing_comments_internal_use
,o.code as order_code 
,o.completed_on as order_completed_on
,o.created_on as order_created_on
,o.end_date as order_end_date
,o.schedule_window as order_schedule_window
,o.status as order_status
,o.submitted_on as order_submitted_on
,o.created_by_id as order_created_by
,o.submitted_by_id as submitted_by_id
--order line items
,oli.id as orderline_id
,oli.backbill as orderline_backbill
,oli.is_flat_rate as orderline_is_flat_rate
,oli.paid as orderline_paid
,oli.quantity as orderline_quantity
,oli.rate as orderline_rate
,oli.rate * oli.quantity as order_line_total
,oli.platform_fee_percent as orderline_platform_fee_percent
,oli.tax as orderline_tax
,oli.stripe_invoice_line_item_id as stripe_invoice_line_item_id

--main product
,mp.name as main_product
--main product category
,mpc.name as main_product_category

--user address 
,ua.state as user_address_state

--user
,u.is_staff as user_is_staff

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
left join bronze_prod.postgres_prod_restricted_bronze_public.api_useraddress ua
  on og.user_address_id = ua.id