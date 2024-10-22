import io

from django.utils import timezone
from reportlab.lib import colors
from reportlab.platypus import KeepTogether, Paragraph, Spacer, Table

from common.utils.report_lab.report_lab_utils import ReportLabUtils


def generate_agreement_pdf(
    order_group,
) -> io.BytesIO:
    items = []
    items.append(_get_report_header())
    items.append(Spacer(width=0, height=20))
    items.append(_get_report_subheader())
    items.append(Spacer(width=0, height=20))
    items.extend(_get_fast_facts())
    items.append(Spacer(width=0, height=20))
    items.extend(_get_coverage())
    items.append(Spacer(width=0, height=20))
    items.extend(
        _core_agreement(
            order_group=order_group,
        )
    )
    items.append(Spacer(width=0, height=20))
    items.extend(_get_downstream_disclaimer())
    items.append(Spacer(width=0, height=20))
    items.extend(_get_important_information())
    items.append(Spacer(width=0, height=20))
    items.extend(_get_definitions())
    items.append(Spacer(width=0, height=20))
    items.extend(_get_terms())
    items.append(Spacer(width=0, height=20))
    items.extend(_get_general())
    items.append(Spacer(width=0, height=20))
    items.extend(
        _get_signed_section(
            order_group=order_group,
        )
    )

    return ReportLabUtils.Pdf().create_pdf(
        children=items,
    )


def _get_report_header():
    return Paragraph(
        "Downstream Equipment Sharing Agreement",
        ReportLabUtils.Pdf.title_style(),
    )


def _get_report_subheader():
    return Paragraph(
        "Please refer to this document if you need evidence of your transaction "
        "during or after your Downstream rental (for instance, when interacting "
        "with suppliers, insurance providers, etc.).",
        ReportLabUtils.Pdf.normal_style(),
    )


def _get_fast_facts():
    return [
        Paragraph(
            "Fast Facts",
            ReportLabUtils.Pdf.heading_style(),
        ),
        Paragraph(
            "- All users associated with the delivery address below have "
            "been granted permission to request bookings on the Equipment below "
            'during the agreement period (see "Start date" and "End date") by '
            'the "supplier" (either the equipment owner or an authorized '
            "representative) through the Downstream terms of service.",
        ),
        Paragraph(
            "- Downstream is a digital peer-to-peer equipment sharing "
            "platform, where private equipment owners share their personal "
            "and company's equipment with others in exchange for compensation.",
        ),
        Paragraph(
            "- By listing their equipment on Downstream, the below-named "
            "supplier represents that their equipment is safe, well maintained, "
            "legally registered, and covered by their commercial or personal "
            "insurance.",
        ),
    ]


def _get_coverage():
    return [
        Paragraph(
            "Coverage",
            ReportLabUtils.Pdf.heading_style(),
        ),
        Paragraph(
            "In addition to any commercial or personal insurance coverage the "
            "user may have, Downstream offers supplementary protection with "
            "varying levels of out-of-pocket maximums, which the user may or "
            "may not have purchased. See below for details of this agreement.",
        ),
        Spacer(width=0, height=10),
        Paragraph(
            "PLEASE NOTE",
        ),
        Paragraph(
            "The Company is financially responsible for any covered damage to "
            "the Supplier's equipment, up to their purchased protection plan's "
            "out-of-pocket maximum listed below, regardless of whether or not "
            "the damage was their fault.",
        ),
    ]


def _core_agreement(order_group):
    user_name = (
        order_group.user_address.user_group.name
        if order_group.user_address.user_group
        else f"{order_group.user_address.user.first_name} {order_group.user_address.user.last_name}"
    )
    seller_location_name = (
        order_group.seller_product_seller_location.seller_location.name
    )
    seller_product_name = (
        order_group.seller_product_seller_location.seller_product.product.main_product.name
    )

    items = []
    items.append(
        Paragraph(
            f"{user_name}'s agreement for {seller_location_name}'s {seller_product_name}",
            ReportLabUtils.Pdf.heading_style(),
        )
    )
    items.append(
        _get_agreement_item(
            "EQUIPMENT PROTECTION PLAN | OUT-OF-POCKET MAXIMUM",
            "Up to the full value of the equipment",
        )
    )
    items.append(
        _get_agreement_item(
            "EQUIPMENT RENTAL COVERAGE",
            "No coverage",
        )
    )
    items.append(Spacer(width=0, height=10))
    items.append(
        _get_agreement_item(
            "Booked On",
            order_group.created_on.strftime("%Y-%m-%d"),
        )
    )
    items.append(
        _get_agreement_item(
            "Agreement ID",
            str(order_group.id),
        ),
    )
    items.append(Spacer(width=0, height=10))
    items.append(
        _get_agreement_item(
            "Start Date",
            order_group.start_date.strftime("%Y-%m-%d"),
        )
    )
    items.append(
        _get_agreement_item(
            "Delivery Location",
            order_group.user_address.formatted_address(),
        )
    )
    items.append(
        _get_agreement_item(
            "Company/Individual",
            user_name,
        )
    )
    items.append(
        _get_agreement_item(
            "Authorizing User",
            f"{order_group.user.first_name} {order_group.user.last_name}",
        ),
    )
    items.append(Spacer(width=0, height=10))
    items.append(
        Paragraph(
            "Freight",
            ReportLabUtils.Pdf.heading_style(),
        ),
    )
    items.append(
        _get_agreement_table(
            [
                [
                    "Delivery Fee",
                    "Removal Fee",
                ],
                [
                    (
                        f"${order_group.delivery_fee}"
                        if order_group.delivery_fee
                        else "N/A"
                    ),
                    f"${order_group.removal_fee}" if order_group.removal_fee else "N/A",
                ],
            ]
        ),
    )
    # SellerProductSellerLocation.Service
    if (
        order_group.seller_product_seller_location.seller_product.product.main_product.has_service
        and hasattr(order_group, "service")
    ):
        items.extend(
            [
                items.append(Spacer(width=0, height=10)),
                Paragraph(
                    "Service",
                    ReportLabUtils.Pdf.heading_style(),
                ),
                _get_agreement_table(
                    [
                        [
                            "Price Per Mile",
                            "Flat Rate",
                        ],
                        [
                            (
                                f"${order_group.service.price_per_mile}"
                                if order_group.service.price_per_mile
                                else "N/A"
                            ),
                            (
                                f"${order_group.service.flat_rate_price}"
                                if order_group.service.flat_rate_price
                                else "N/A"
                            ),
                        ],
                    ]
                ),
            ],
        )
    # SellerProductSellerLocation.ServiceTimesPerWeek
    if (
        order_group.seller_product_seller_location.seller_product.product.main_product.has_service_times_per_week
        and hasattr(order_group, "service_times_per_week")
    ):
        items.extend(
            [
                items.append(Spacer(width=0, height=10)),
                Paragraph(
                    "Service",
                    ReportLabUtils.Pdf.heading_style(),
                ),
                _get_agreement_table(
                    [
                        [
                            "1x per week",
                            "2x per week",
                            "3x per week",
                            "4x per week",
                            "5x per week",
                        ],
                        [
                            (
                                f"${order_group.service_times_per_week.one_time_per_week}"
                                if order_group.service_times_per_week.one_time_per_week
                                else "N/A"
                            ),
                            (
                                f"${order_group.service_times_per_week.two_times_per_week}"
                                if order_group.service_times_per_week.two_times_per_week
                                else "N/A"
                            ),
                            (
                                f"${order_group.service_times_per_week.three_times_per_week}"
                                if order_group.service_times_per_week.three_times_per_week
                                else "N/A"
                            ),
                            (
                                f"${order_group.service_times_per_week.four_times_per_week}"
                                if order_group.service_times_per_week.four_times_per_week
                                else "N/A"
                            ),
                            (
                                f"${order_group.service_times_per_week.five_times_per_week}"
                                if order_group.service_times_per_week.five_times_per_week
                                else "N/A"
                            ),
                        ],
                    ],
                ),
            ],
        )
    # SellerProductSellerLocation.RentalOneStep
    if (
        order_group.seller_product_seller_location.seller_product.product.main_product.has_rental_one_step
        and hasattr(order_group, "rental_one_step")
    ):
        items.extend(
            [
                items.append(Spacer(width=0, height=10)),
                Paragraph(
                    "Rental",
                    ReportLabUtils.Pdf.heading_style(),
                ),
                _get_agreement_table(
                    [
                        [
                            "Per Month (any days < 28 days)",
                        ],
                        [
                            (
                                f"${order_group.rental_one_step.rate}"
                                if order_group.rental_one_step.rate
                                else "N/A"
                            ),
                        ],
                    ]
                ),
            ],
        )
    # SellerProductSellerLocation.RentalTwoStep
    if (
        order_group.seller_product_seller_location.seller_product.product.main_product.has_rental
        and hasattr(order_group, "rental")
    ):
        items.extend(
            [
                items.append(Spacer(width=0, height=10)),
                Paragraph(
                    "Rental",
                    ReportLabUtils.Pdf.heading_style(),
                ),
                _get_agreement_table(
                    [
                        [
                            "Included Days",
                            "Price Per Included Day",
                            "Price Per Additional Day",
                        ],
                        [
                            (
                                order_group.rental.included_days
                                if order_group.rental.included_days
                                else "N/A"
                            ),
                            (
                                f"${order_group.rental.price_per_day_included}"
                                if order_group.rental.price_per_day_included
                                else "N/A"
                            ),
                            (
                                f"${order_group.rental.price_per_day_additional}"
                                if order_group.rental.price_per_day_additional
                                else "N/A"
                            ),
                        ],
                    ]
                ),
            ],
        )
    # SellerProductSellerLocation.RentalMultiStep
    if (
        order_group.seller_product_seller_location.seller_product.product.main_product.has_rental_multi_step
        and hasattr(order_group, "rental_multi_step")
    ):
        items.extend(
            [
                items.append(Spacer(width=0, height=10)),
                Paragraph(
                    "Rental",
                    ReportLabUtils.Pdf.heading_style(),
                ),
                _get_agreement_table(
                    [
                        [
                            "Per Hour",
                            "Per Day",
                            "Per Week",
                            "Per Two Weeks",
                            "Per Month",
                        ],
                        [
                            (
                                f"${order_group.rental_multi_step.hour}"
                                if order_group.rental_multi_step.hour
                                else "N/A"
                            ),
                            (
                                f"${order_group.rental_multi_step.day}"
                                if order_group.rental_multi_step.day
                                else "N/A"
                            ),
                            (
                                f"${order_group.rental_multi_step.week}"
                                if order_group.rental_multi_step.week
                                else "N/A"
                            ),
                            (
                                f"${order_group.rental_multi_step.two_weeks}"
                                if order_group.rental_multi_step.two_weeks
                                else "N/A"
                            ),
                            (
                                f"${order_group.rental_multi_step.month}"
                                if order_group.rental_multi_step.month
                                else "N/A"
                            ),
                        ],
                    ]
                ),
            ],
        )
    # SellerProductSellerLocation.Material
    if (
        order_group.seller_product_seller_location.seller_product.product.main_product.has_material
        and hasattr(order_group, "waste_types")
    ):
        items.extend(
            [
                items.append(Spacer(width=0, height=10)),
                Paragraph(
                    "Material",
                    ReportLabUtils.Pdf.heading_style(),
                ),
                _get_agreement_table(
                    [
                        # Waste Types.
                        [
                            waste_type.main_product_waste_type.waste_type.name
                            for waste_type in order_group.waste_types.all()
                        ],
                        [
                            (
                                f"${waste_type.price_per_ton} per ton"
                                if waste_type.price_per_ton
                                else "N/A"
                            )
                            for waste_type in order_group.waste_types.all()
                        ],
                        [
                            (
                                f"{waste_type.tonnage_included} tons included"
                                if waste_type.tonnage_included
                                else "N/A"
                            )
                            for waste_type in order_group.waste_types.all()
                        ],
                    ]
                ),
            ],
        )

    return items


def _get_downstream_disclaimer():
    return [
        Paragraph(
            "Downstream Disclaimer",
            ReportLabUtils.Pdf.heading_style(),
        ),
        Paragraph(
            'The person or entity identified as "Supplier" and the person or '
            'entity identified as "Company" on the Agreement Summary above were '
            "connected online through a website, mobile application, and/or "
            "associated services provided by Downstream Systems, Inc. "
            '(collectively, the "Downstream Services"). As part of connecting '
            "through the Downstream Services, the Supplier and Company agreed "
            "to be bound by the Downstream Terms of Service "
            "(https://trydownstream.io/terms-of-service) and incorporated policies.",
        ),
    ]


def _get_important_information():
    return [
        Paragraph(
            "Important Information",
            ReportLabUtils.Pdf.heading_style(),
        ),
        Paragraph(
            "There is important information below that you should review and understand, "
            "regardless of whether you are a Company or Supplier. The above Agreement "
            "Summary and this Equipment Sharing Agreement are collectively referred to "
            'as the "Agreement" and relate to the Agreement detailed in the Agreement Summary.',
        ),
    ]


def _get_definitions():
    return [
        Paragraph(
            "1. DEFINITIONS",
            ReportLabUtils.Pdf.heading_style(),
        ),
        Paragraph(
            "1.1 “Company” means the entity the authorized individual is entering into this "
            "agreement in addition to Users who are approved by the company to operate the "
            "Equipment.",
        ),
        Paragraph(
            "1.2 “Extras” means but is not limited to optional casters, locks, relocations, "
            "gates and/or other products and services selected by Users.",
        ),
        Paragraph(
            "1.3 “Users” means the person, or entity identified on the Agreement and can be "
            "considered an “Authorizing User”.",
        ),
        Paragraph(
            "1.4 “Supplier” for the purposes of this Agreement means “SUPPLIER” shown on the "
            "top of the Agreement.",
        ),
        Paragraph(
            "1.5 “Agreement Period” means the period between the time Company takes "
            "possession of the Equipment until the Equipment is returned or recovered and "
            "in either case, checked in by Company.",
        ),
        Paragraph(
            "1.6 “Equipment” means the “EQUIPMENT” identified on the Agreement.",
        ),
        Paragraph(
            "1.7 “Authorizing User” means the individual entering this agreement. If the "
            "individual represents no company, they are assumed to be representing themselves. "
            "All the same obligations apply to this individual as the company below.",
        ),
        Paragraph(
            "1.8 “Recyclable Material” means approved materials that can be recycled or "
            "recovered, and are not intended for disposal, provided further, however, such "
            "term specifically excludes Prohibited Materials.",
        ),
        Paragraph(
            "1.9 “Prohibited Material” means: (a) any Alternative Materials not expressly "
            "approved in writing by Suppliers, and (b) any materials or substances that are "
            "hazardous, toxic, explosive, flammable, radioactive, infectious, or which cannot "
            "lawfully be disposed of in a “Subtitle D” landfill, including without limitation, "
            "(i) any material considered a “hazardous waste” under the Resource Conservation "
            "And Recovery Act (42 U.S.C. § 6901 etseq.), (ii) PCBs, (iii) asbestos, (iv) diesel "
            "fuel, gasoline, or other petroleum products or hydrocarbons, (v) Medical Waste, "
            "medications or pharmaceuticals, (vi) any other material or substance that is "
            "hazardous or toxic, and which would form the basis of any claim, under any "
            "Environmental Laws, and (vii) any waste and recycling materials contaminated "
            "by, mixed with or containing Prohibited Materials.",
        ),
        Paragraph(
            "1.10 “Medical Waste” means any material or waste that is or potentially maybe "
            "infectious, biohazardous, biomedical, or any other “medical” or similar waste "
            "regulated under any Environmental Laws, including without limitation: medical "
            "wastes requiring treatment prior to disposal, “red bag” medical waste, blood- "
            "soaked bandages, culture dishes and other glassware, discarded surgical gloves, "
            "discarded surgical instruments, discarded needles (e.g., medical sharps), "
            "cultures, stocks, swabs used to inoculate cultures, removed body organs, and "
            "discarded lancets. For avoidance of doubt, Medical Waste is a Prohibited Material "
            "under this Agreement.",
        ),
        Paragraph(
            "1.11 “Environmental Law” means all applicable federal, state and local laws "
            "and regulations and common law concerning solid or hazardous waste, toxic or "
            "hazardous substances or materials, pollution, or protection of human health and "
            "safety or the environment, including without limitation the Resource Conservation "
            "and Recovery Act (42 U.S.C. § 6901 et seq.), the Toxic Substances Control Act (15 "
            "U.S.C. §2601 et seq.), and the Comprehensive Environmental Response Compensation "
            "and Liability Act (42 U.S.C. § 6901 et seq.).",
        ),
        Paragraph(
            "1.12 “Alternative Material” as defined in this Agreement means used tires, "
            "construction and demolition (C&D) materials, and materials recognized as "
            "“universal waste” or as “special waste” under Environmental Law.",
        ),
        Paragraph(
            "1.13 “Accepted Material” means non-hazardous solid waste and Recyclable Materials. "
            "Accepted Material specifically excludes Prohibited Materials.",
        ),
    ]


def _get_terms():
    return [
        Paragraph(
            "2. TERMS",
            ReportLabUtils.Pdf.heading_style(),
        ),
        Paragraph(
            "2.1 Ownership. The Equipment and any Extras are, by ownership, beneficial "
            "interest or lease, property of Supplier.",
        ),
        Paragraph(
            "2.2 Equipment Condition/Warranty Exclusion. Company agrees it received "
            "the Equipment and any Extras in good physical and mechanical condition, "
            "unless otherwise identified and reported to Downstream at delivery. Company "
            "is taking possession of the Equipment and any Extras “as-is” and has had an "
            "adequate opportunity to inspect the Equipment and any Extras and their operation. "
            "Supplier excludes all warranties, both express and implied, with respect to the "
            "Equipment and any Extras, including any implied warranty of merchantability or "
            "fitness for a particular purpose. Company agrees not to alter or tamper with "
            "the Equipment or any Extras. If Company determines the Equipment or any Extra "
            "is unsafe, company shall stop operating the Equipment and any Extra and notify "
            "Supplier immediately.",
        ),
        Paragraph(
            "2.3 Personal property, including personal information and data. Supplier is "
            "not responsible for any damage to, loss or theft of, any personal property "
            "of Company or Authorized User or data contained therein, whether the damage "
            "or theft occurs during or after termination of the agreement regardless of "
            "fault or negligence. No bailment is or shall be created upon Supplier, whether "
            "actual, constructive, or otherwise, for any personal property carried in or "
            "left in the Equipment or on Suppliers’ premises. Company acknowledges that any "
            "personal data or information downloaded or transferred to the Equipment may not "
            "be secure and may be accessible after the Agreement Period. Company releases "
            "Supplier from any liability resulting from or otherwise arising out of any such "
            "data or information being accessed and/or utilized by a third party.",
        ),
        Paragraph(
            "2.4 Equipment Return; Late Returns. Company agrees to return the Equipment "
            "and any Extras to Supplier on or before end date to the address stated on the "
            "Agreement or on Supplier’s demand and in the same condition as received, ordinary "
            "wear and tear excepted. Extensions to Agreement Period are at Supplier’s option. "
            "If company continues to operate the Equipment after the right to do so is terminated, "
            "Supplier and Downstream have the right to notify police that the Equipment has been "
            "embezzled and/or stolen. Company hereby releases and discharge Supplier from and "
            "indemnify, defend and hold Supplier harmless against any liability arising from "
            "such notice. If a Company fails to return Equipment within 72 hours after the "
            "scheduled end of Agreement Period, Downstream and/or Supplier will report it stolen.",
        ),
        Paragraph(
            "2.5 Company Protection Plans. The Company rental protection plan represents the "
            "amount the Company must pay in the event of damage to the Equipment. If the "
            "Company protection plan has an “Out-of-Pocket Maximum,” that amount represents "
            "the maximum a Company will pay Supplier for amounts owed because of damage to "
            "the equipment. Exceptions and exclusions apply.",
        ),
        Paragraph(
            "2.6 Company Financial Responsibility is Primary. As outlined in Downstream's "
            "Terms of Service, with regard to physical damage to or theft of the Equipment "
            "that occurs during the Agreement Period, Company is financially responsible, "
            "regardless of who is found at fault. This responsibility applies whether Company "
            "has their own insurance or not. Company will work with Downstream to make a "
            "claim for coverage under any policy of insurance that applies to the loss if "
            "any damage occurs to the Equipment during the Agreement Period. Any protection "
            "plan selected by Company when booking equipment, to the extent offered, will not "
            "be available until all personal insurance options, protection and/or coverage "
            "have been exhausted.",
        ),
        Paragraph(
            "2.7 Equipment Information. Supplier listed the Equipment booked by Company "
            "through the Downstream Services. Supplier represents and warrants that the "
            "Equipment meets Downstream's requirements, and that Supplier owns or otherwise "
            "has all the necessary rights and permissions to share the Equipment for compensation.",
        ),
        Paragraph(
            "2.8 Title to Waste Materials. Title to Waste Materials shall, at the time of "
            "collection, transfer directly from Company to Supplier. At Downstream's sole "
            "discretion, title to approved Materials shall, at the time of collection, pass "
            "directly from Company to Downstream. Notwithstanding anything to the contrary "
            "in this Agreement, title to and liability for Prohibited Materials shall always "
            "remain with Company, and Downstream shall not be deemed to own, generate, possess "
            "or control, and shall not be liable to Company or any third party regarding any "
            "(i) Prohibited Materials, or (ii) Waste Materials for which Downstream has "
            "not expressly accepted title in writing.",
        ),
        Paragraph(
            "2.9 Utilization of Platform. Company and Supplier agree all related booking "
            "requests, invoices, payouts, rebates, communication related to this agreement "
            "must be done exclusively within the Downstream Marketplace Platform or with a "
            "Downstream Booking Success Agent during the Agreement Period.",
        ),
        Paragraph(
            "2.10 Pricing Adjustment. Because disposal, processing and fuel costs are a "
            "significant portion of the costs of the services provided, Supplier may increase "
            "the schedule of charges proportionately to reflect any increase in such costs, "
            "plus an appropriate mark-up. Supplier may also adjust the schedule of charges "
            "based on other factors, including, without limitation, increases in landfill "
            "fees, the Consumer Price Index, the Transportation Index and/or other similar "
            "benchmark indices. Where the schedule of charges includes disposal as a "
            "component of the charges, disposal will mean the posted gate rate for the "
            "disposal at the disposal facility that Supplier(s) utilize plus an appropriate "
            "mark-up. Company and Supplier agree that the schedule of charges is based upon "
            "the estimated average Material weight. If Company Material exceeds the average "
            "Material weight agreed to herein, Supplier may increase the schedule of "
            "charges proportionately to reflect the additional average Material weight.",
        ),
        Paragraph(
            "2.11 Early Cancellation Fees. In the event of a termination by Company for any "
            "reason prior to the end of the Initial Term, Company agrees to pay Supplier "
            "50% of the remaining months at an amount equal to 50% percent the average "
            "monthly value of this Agreement over the last 180 days. This does not apply "
            "for on-demand or month to month short term rentals.",
        ),
        Paragraph(
            "2.12 Company Obligations regarding Environmental Laws and Prohibited Materials. "
            "Company represents, warrants, and covenants that: (i) Company will provide "
            "only Accepted Materials (ii) Company will not provide Prohibited Materials; "
            "and (iii) Company will remain in compliance with all Environmental Laws. "
            "Company acknowledges that Downstream from time to time may supplement, modify "
            "or otherwise change its customer policies with regard to what constitutes "
            "Acceptable Materials, Recyclable Materials and/or Prohibited Materials. "
            "Company agrees to check Downstream’s website periodically at "
            "https://help.trydownstream.io/en/articles/7849472- customer-terms-of-service "
            "for any such changes and to comply with any such changes.",
        ),
    ]


def _get_general():
    return [
        Paragraph(
            "3. GENERAL",
            ReportLabUtils.Pdf.heading_style(),
        ),
        Paragraph(
            "In case any provision of this Agreement is held invalid, illegal or "
            "unenforceable, the validity, legality and enforceability of the remaining "
            "provisions shall not in any way be affected or impaired. The waiver by either "
            "party of any right under this Agreement or failure to perform or of a "
            "breach by the other party shall not be deemed a waiver of any other right "
            "under the Agreement or of any other breach or failure by such other party "
            "whether of a similar nature or otherwise. This Agreement cannot be altered "
            "by another document or oral agreement unless agreed to in writing or through "
            "the Downstream Services. In the event of any conflict between the terms of "
            "this Agreement and the terms of the Downstream Terms of Service, the "
            "Downstream Terms of Service control.",
        ),
    ]


def _get_agreement_item(
    header: str,
    subtext: str,
):
    return KeepTogether(
        [
            Paragraph(
                header,
                ReportLabUtils.Pdf.normal_style(bold=True),
            ),
            Paragraph(
                subtext,
                ReportLabUtils.Pdf.normal_style(),
            ),
        ]
    )


def _get_agreement_table(table_data):
    return Table(
        table_data,
        style=[
            ("BACKGROUND", (0, 0), (-1, 0), colors.black),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND", (0, 1), (-1, -1), colors.white),
            # Border.
            ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
            # Only show horizontal lines, not vertical dividing lines.
            ("LINEABOVE", (0, 1), (-1, -1), 0.25, colors.black),
            ("LINEBELOW", (0, -1), (-1, -1), 0.25, colors.black),
        ],
        hAlign="LEFT",
    )


def _get_signed_section(
    order_group,
):
    agreement_signed_on = None
    if order_group.agreement_signed_on:
        # Convert to Central Standard Time.
        central_timezone = timezone.get_fixed_timezone(-360)
        agreement_signed_on = timezone.localtime(
            order_group.agreement_signed_on, central_timezone
        )

    return [
        Paragraph(
            "Customer Signature:",
            ReportLabUtils.Pdf.heading_style(),
        ),
        Spacer(width=0, height=10),
        Paragraph(
            (
                f"Signed digitally by: {order_group.agreement_signed_by.first_name} {order_group.agreement_signed_by.last_name} on {agreement_signed_on.strftime('%Y-%m-%d %H:%M:%S')} (CT)"
                if order_group.agreement_signed_by and order_group.agreement_signed_on
                else "Not yet signed"
            ),
            ReportLabUtils.Pdf.normal_style(),
        ),
    ]
