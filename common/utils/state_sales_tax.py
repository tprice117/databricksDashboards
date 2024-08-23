STATE_SALES_TAX = {
    "AL": {"name": "Alabama", "sales_tax_rate": 4.0},
    "AK": {"name": "Alaska", "sales_tax_rate": 0.0},
    "AZ": {"name": "Arizona", "sales_tax_rate": 5.6},
    "AR": {"name": "Arkansas", "sales_tax_rate": 6.5},
    "CA": {"name": "California", "sales_tax_rate": 7.25},
    "CO": {"name": "Colorado", "sales_tax_rate": 2.9},
    "CT": {"name": "Connecticut", "sales_tax_rate": 6.35},
    "DE": {"name": "Delaware", "sales_tax_rate": 0.0},
    "DC": {"name": "District of Columbia", "sales_tax_rate": 6.0},
    "FL": {"name": "Florida", "sales_tax_rate": 6.0},
    "GA": {"name": "Georgia", "sales_tax_rate": 7.0},
    "HI": {"name": "Hawaii", "sales_tax_rate": 4.0},
    "ID": {"name": "Idaho", "sales_tax_rate": 6.0},
    "IL": {"name": "Illinois", "sales_tax_rate": 6.25},
    "IN": {"name": "Indiana", "sales_tax_rate": 7.0},
    "IA": {"name": "Iowa", "sales_tax_rate": 6.0},
    "KS": {"name": "Kansas", "sales_tax_rate": 6.5},
    "KY": {"name": "Kentucky", "sales_tax_rate": 6.0},
    "LA": {"name": "Louisiana", "sales_tax_rate": 4.45},
    "ME": {"name": "Maine", "sales_tax_rate": 5.5},
    "MD": {"name": "Maryland", "sales_tax_rate": 6.0},
    "MA": {"name": "Massachusetts", "sales_tax_rate": 6.25},
    "MI": {"name": "Michigan", "sales_tax_rate": 6.0},
    "MN": {"name": "Minnesota", "sales_tax_rate": 6.875},
    "MS": {"name": "Mississippi", "sales_tax_rate": 7.0},
    "MO": {"name": "Missouri", "sales_tax_rate": 4.225},
    "MT": {"name": "Montana", "sales_tax_rate": 0.0},
    "NE": {"name": "Nebraska", "sales_tax_rate": 5.5},
    "NV": {"name": "Nevada", "sales_tax_rate": 6.85},
    "NH": {"name": "New Hampshire", "sales_tax_rate": 0.0},
    "NJ": {"name": "New Jersey", "sales_tax_rate": 6.625},
    "NM": {"name": "New Mexico", "sales_tax_rate": 7.5},
    "NY": {"name": "New York", "sales_tax_rate": 4.0},
    "NC": {"name": "North Carolina", "sales_tax_rate": 4.25},
    "ND": {"name": "North Dakota", "sales_tax_rate": 6.5},
    "OH": {"name": "Ohio", "sales_tax_rate": 7.25},
    "OK": {"name": "Oklahoma", "sales_tax_rate": 4.5},
    "OR": {"name": "Oregon", "sales_tax_rate": 0.0},
    "PA": {"name": "Pennsylvania", "sales_tax_rate": 6.0},
    "RI": {"name": "Rhode Island", "sales_tax_rate": 7.0},
    "SC": {"name": "South Carolina", "sales_tax_rate": 6.0},
    "SD": {"name": "South Dakota", "sales_tax_rate": 4.5},
    "TN": {"name": "Tennessee", "sales_tax_rate": 7.0},
    "TX": {"name": "Texas", "sales_tax_rate": 6.25},
    "UT": {"name": "Utah", "sales_tax_rate": 6.85},
    "VT": {"name": "Vermont", "sales_tax_rate": 6.0},
    "VA": {"name": "Virginia", "sales_tax_rate": 6.0},
    "WA": {"name": "Washington", "sales_tax_rate": 6.5},
    "WV": {"name": "West Virginia", "sales_tax_rate": 6.0},
    "WI": {"name": "Wisconsin", "sales_tax_rate": 5.5},
    "WY": {"name": "Wyoming", "sales_tax_rate": 4.0},
}


def get_state_sales_tax(state: str):
    return STATE_SALES_TAX.get(state, {"name": "Unknown", "sales_tax_rate": 0.0})[
        "sales_tax_rate"
    ]


def get_state_sales_tax_by_name(state: str):
    for state_abbr, state_data in STATE_SALES_TAX.items():
        if state_data["name"].lower() == state.lower():
            return state_data["sales_tax_rate"]
    return 0
