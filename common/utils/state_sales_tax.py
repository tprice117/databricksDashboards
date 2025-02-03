from decimal import Decimal

# List of states
STATE_CHOICES = [
    ("", "----------"),
    ("AL", "Alabama"),
    ("AK", "Alaska"),
    ("AZ", "Arizona"),
    ("AR", "Arkansas"),
    ("CA", "California"),
    ("CO", "Colorado"),
    ("CT", "Connecticut"),
    ("DE", "Delaware"),
    ("DC", "District of Columbia"),
    ("FL", "Florida"),
    ("GA", "Georgia"),
    ("HI", "Hawaii"),
    ("ID", "Idaho"),
    ("IL", "Illinois"),
    ("IN", "Indiana"),
    ("IA", "Iowa"),
    ("KS", "Kansas"),
    ("KY", "Kentucky"),
    ("LA", "Louisiana"),
    ("ME", "Maine"),
    ("MD", "Maryland"),
    ("MA", "Massachusetts"),
    ("MI", "Michigan"),
    ("MN", "Minnesota"),
    ("MS", "Mississippi"),
    ("MO", "Missouri"),
    ("MT", "Montana"),
    ("NE", "Nebraska"),
    ("NV", "Nevada"),
    ("NH", "New Hampshire"),
    ("NJ", "New Jersey"),
    ("NM", "New Mexico"),
    ("NY", "New York"),
    ("NC", "North Carolina"),
    ("ND", "North Dakota"),
    ("OH", "Ohio"),
    ("OK", "Oklahoma"),
    ("OR", "Oregon"),
    ("PA", "Pennsylvania"),
    ("RI", "Rhode Island"),
    ("SC", "South Carolina"),
    ("SD", "South Dakota"),
    ("TN", "Tennessee"),
    ("TX", "Texas"),
    ("UT", "Utah"),
    ("VT", "Vermont"),
    ("VA", "Virginia"),
    ("WA", "Washington"),
    ("WV", "West Virginia"),
    ("WI", "Wisconsin"),
    ("WY", "Wyoming"),
]

STATE_SALES_TAX = {
    "AL": {"name": "Alabama", "rate_100": Decimal("4.0"), "rate": Decimal("0.04")},
    "AK": {"name": "Alaska", "rate_100": Decimal("0.0"), "rate": Decimal("0.00")},
    "AZ": {"name": "Arizona", "rate_100": Decimal("5.6"), "rate": Decimal("0.056")},
    "AR": {"name": "Arkansas", "rate_100": Decimal("6.5"), "rate": Decimal("0.065")},
    "CA": {
        "name": "California",
        "rate_100": Decimal("7.25"),
        "rate": Decimal("0.0725"),
    },
    "CO": {"name": "Colorado", "rate_100": Decimal("2.9"), "rate": Decimal("0.029")},
    "CT": {
        "name": "Connecticut",
        "rate_100": Decimal("6.35"),
        "rate": Decimal("0.0635"),
    },
    "DE": {"name": "Delaware", "rate_100": Decimal("0.0"), "rate": Decimal("0.00")},
    "DC": {
        "name": "District of Columbia",
        "rate_100": Decimal("6.0"),
        "rate": Decimal("0.06"),
    },
    "FL": {"name": "Florida", "rate_100": Decimal("6.0"), "rate": Decimal("0.06")},
    "GA": {"name": "Georgia", "rate_100": Decimal("7.0"), "rate": Decimal("0.07")},
    "HI": {"name": "Hawaii", "rate_100": Decimal("4.0"), "rate": Decimal("0.04")},
    "ID": {"name": "Idaho", "rate_100": Decimal("6.0"), "rate": Decimal("0.06")},
    "IL": {"name": "Illinois", "rate_100": Decimal("6.25"), "rate": Decimal("0.0625")},
    "IN": {"name": "Indiana", "rate_100": Decimal("7.0"), "rate": Decimal("0.07")},
    "IA": {"name": "Iowa", "rate_100": Decimal("6.0"), "rate": Decimal("0.06")},
    "KS": {"name": "Kansas", "rate_100": Decimal("6.5"), "rate": Decimal("0.065")},
    "KY": {"name": "Kentucky", "rate_100": Decimal("6.0"), "rate": Decimal("0.06")},
    "LA": {"name": "Louisiana", "rate_100": Decimal("4.45"), "rate": Decimal("0.0445")},
    "ME": {"name": "Maine", "rate_100": Decimal("5.5"), "rate": Decimal("0.055")},
    "MD": {"name": "Maryland", "rate_100": Decimal("6.0"), "rate": Decimal("0.06")},
    "MA": {
        "name": "Massachusetts",
        "rate_100": Decimal("6.25"),
        "rate": Decimal("0.0625"),
    },
    "MI": {"name": "Michigan", "rate_100": Decimal("6.0"), "rate": Decimal("0.06")},
    "MN": {
        "name": "Minnesota",
        "rate_100": Decimal("6.875"),
        "rate": Decimal("0.06875"),
    },
    "MS": {"name": "Mississippi", "rate_100": Decimal("7.0"), "rate": Decimal("0.07")},
    "MO": {
        "name": "Missouri",
        "rate_100": Decimal("4.225"),
        "rate": Decimal("0.04225"),
    },
    "MT": {"name": "Montana", "rate_100": Decimal("0.0"), "rate": Decimal("0.00")},
    "NE": {"name": "Nebraska", "rate_100": Decimal("5.5"), "rate": Decimal("0.055")},
    "NV": {"name": "Nevada", "rate_100": Decimal("6.85"), "rate": Decimal("0.0685")},
    "NH": {
        "name": "New Hampshire",
        "rate_100": Decimal("0.0"),
        "rate": Decimal("0.00"),
    },
    "NJ": {
        "name": "New Jersey",
        "rate_100": Decimal("6.625"),
        "rate": Decimal("0.06625"),
    },
    "NM": {"name": "New Mexico", "rate_100": Decimal("7.5"), "rate": Decimal("0.075")},
    "NY": {"name": "New York", "rate_100": Decimal("4.0"), "rate": Decimal("0.04")},
    "NC": {
        "name": "North Carolina",
        "rate_100": Decimal("4.25"),
        "rate": Decimal("0.0425"),
    },
    "ND": {
        "name": "North Dakota",
        "rate_100": Decimal("6.5"),
        "rate": Decimal("0.065"),
    },
    "OH": {"name": "Ohio", "rate_100": Decimal("7.25"), "rate": Decimal("0.0725")},
    "OK": {"name": "Oklahoma", "rate_100": Decimal("4.5"), "rate": Decimal("0.045")},
    "OR": {"name": "Oregon", "rate_100": Decimal("0.0"), "rate": Decimal("0.00")},
    "PA": {"name": "Pennsylvania", "rate_100": Decimal("6.0"), "rate": Decimal("0.06")},
    "RI": {"name": "Rhode Island", "rate_100": Decimal("7.0"), "rate": Decimal("0.07")},
    "SC": {
        "name": "South Carolina",
        "rate_100": Decimal("6.0"),
        "rate": Decimal("0.06"),
    },
    "SD": {
        "name": "South Dakota",
        "rate_100": Decimal("4.5"),
        "rate": Decimal("0.045"),
    },
    "TN": {"name": "Tennessee", "rate_100": Decimal("7.0"), "rate": Decimal("0.07")},
    "TX": {"name": "Texas", "rate_100": Decimal("6.25"), "rate": Decimal("0.0625")},
    "UT": {"name": "Utah", "rate_100": Decimal("6.85"), "rate": Decimal("0.0685")},
    "VT": {"name": "Vermont", "rate_100": Decimal("6.0"), "rate": Decimal("0.06")},
    "VA": {"name": "Virginia", "rate_100": Decimal("6.0"), "rate": Decimal("0.06")},
    "WA": {"name": "Washington", "rate_100": Decimal("6.5"), "rate": Decimal("0.065")},
    "WV": {
        "name": "West Virginia",
        "rate_100": Decimal("6.0"),
        "rate": Decimal("0.06"),
    },
    "WI": {"name": "Wisconsin", "rate_100": Decimal("5.5"), "rate": Decimal("0.055")},
    "WY": {"name": "Wyoming", "rate_100": Decimal("4.0"), "rate": Decimal("0.04")},
}


def get_state_sales_tax(state: str):
    """Returns the sales tax for a given state."""
    return STATE_SALES_TAX.get(
        state, {"name": "Unknown", "rate_100": Decimal(0.0), "rate": Decimal(0.0)}
    )


def get_state_sales_tax_by_name(state: str):
    for state_abbr, state_data in STATE_SALES_TAX.items():
        if state_data["name"].lower() == state.lower():
            return state_data
    return {"name": "Unknown", "rate_100": Decimal(0.0), "rate": Decimal(0.0)}
