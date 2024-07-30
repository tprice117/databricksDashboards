def open_invoice_reminder():
    # Get all Stripe invoices that are "open".
    has_more = True
    starting_after = None
    next_page = None
    data = []
    while has_more:
        if next_page:
            invoices = stripe.Invoice.search(
                query='status:"open"', limit=100, page=next_page
            )
        else:
            invoices = stripe.Invoice.search(query='status:"open"', limit=100)
        print(invoices)
        data = data + invoices["data"]
        has_more = invoices["has_more"]
        next_page = invoices["next_page"]
    print(len(data))
