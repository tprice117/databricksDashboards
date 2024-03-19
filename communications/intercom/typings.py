from typing import TypedDict, Optional, Dict, List
from decimal import Decimal


CustomAttributesType = TypedDict(
    "CustomAttributes",
    {
        # Seller ID = UserGroup.seller.id (String)
        "Seller ID": str,
        # Autopay = UserGroup.autopay (Boolean)
        "Autopay": bool,
        # Net Terms Days = UserGroup.net_terms (String) - (e.g., Net 14, Net 30)
        "Net Terms Days": int,
        # Invoice Frequency in Days = UserGroup.invoice_frequency (String) - (e.g., Weekly, Monthly)
        "Invoice Frequency in Days": Optional[int],
        # Credit Line Amount = UserGroup.credit_line_limit (Decimal)
        "Credit Line Amount": Optional[Decimal],
        # Insurance and Tax Request Status = UserGroup.compliance_status (String) - (e.g., Requested, In-progress)
        "Insurance and Tax Request Status": str,
        # Tax Exempt Status = UserGroup.tax_exempt_status (String) - (e.g., None, Exempt, Reverse)
        "Tax Exempt Status": str,
        # Invoice Day of Month = UserGroup.invoice_day_of_month (Integer) - (e.g., 1, 15)
        "Invoice Day of Month": Optional[int],
        # Project Based Billing = UserGroup.invoice_at_project_completion (Boolean)
        "Project Based Billing": bool,
        # Share Code = UserGroup.share_code (Text)
        "Share Code": Optional[str],
    },
)


class CompanyType(TypedDict):
    type: str
    id: str
    name: str
    app_id: Optional[str]  # Optional because app_id might not be present
    plan: Dict[str, str]  # Nested dictionary for plan details
    company_id: str
    remote_created_at: int
    created_at: int
    updated_at: int
    last_request_at: int
    size: int
    website: str
    industry: str
    monthly_spend: float
    session_count: int
    user_count: int
    custom_attributes: CustomAttributesType
    tags: Dict[str, List[Dict[str, str]]]  # Tags represented as a list of dictionaries
    segments: Dict[str, List[Dict[str, str]]]  # Segments represented as a list of dictionaries


class Location(TypedDict):
    type: str
    country: Optional[str]
    region: Optional[str]
    city: Optional[str]
    country_code: Optional[str]
    continent_code: Optional[str]


class SocialProfile(TypedDict):
    # Since data is empty, leave type unspecified (can be anything)
    type: str
    data: List


class ContactType(TypedDict):
    type: str
    id: str
    workspace_id: str
    external_id: Optional[str]
    role: str
    email: str
    phone: Optional[str]
    name: Optional[str]
    avatar: Optional[str]
    owner_id: Optional[str]
    social_profiles: SocialProfile
    has_hard_bounced: bool
    marked_email_as_spam: bool
    unsubscribed_from_emails: bool
    created_at: int
    updated_at: int
    signed_up_at: Optional[int]
    # Many last_* fields can be null, mark as Optional
    last_seen_at: Optional[int]
    last_replied_at: Optional[int]
    last_contacted_at: Optional[int]
    last_email_opened_at: Optional[int]
    last_email_clicked_at: Optional[int]
    language_override: Optional[str]
    browser: Optional[str]
    browser_version: Optional[str]
    browser_language: Optional[str]
    os: Optional[str]
    location: Location
    # Many android/ios fields can be null, mark as Optional
    android_app_name: Optional[str]
    android_app_version: Optional[str]
    android_device: Optional[str]
    android_os_version: Optional[str]
    android_sdk_version: Optional[str]
    android_last_seen_at: Optional[int]
    ios_app_name: Optional[str]
    ios_app_version: Optional[str]
    ios_device: Optional[str]
    ios_os_version: Optional[str]
    ios_sdk_version: Optional[str]
    ios_last_seen_at: Optional[int]
    custom_attributes: Dict[str, str]  # Can hold various strings
    tags: Dict[str, List]  # Empty list for now, type can be adjusted later
    notes: Dict[str, List]  # Empty list for now, type can be adjusted later
    companies: Dict[str, List]  # Empty list for now, type can be adjusted later
    opted_out_subscription_types: Dict[str, List]  # Empty list for now, type can be adjusted later
    opted_in_subscription_types: Dict[str, List]  # Empty list for now, type can be adjusted later
    utm_campaign: Optional[str]
    utm_content: Optional[str]
    utm_medium: Optional[str]
    utm_source: Optional[str]
    utm_term: Optional[str]
    referrer: Optional[str]
