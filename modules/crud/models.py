"""
Module 4: Database CRUD Operations - Data Models & Filter Criteria
===================================================================
Purpose:
    Defines strongly-typed data structures for representing wholesale catalog
    items stored in Cloudflare D1, search/filter criteria, and paginated query results.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class WholesaleProductModel:
    """
    Strongly-typed entity representing a single wholesale product record in Cloudflare D1.
    Matches the schema of the 'wholesale_products' SQLite table.
    """
    id: Optional[int] = None
    asin: str = ""
    parent_asin: Optional[str] = None
    product_id: Optional[str] = None
    favorite: bool = False
    wholesaler_company_name: str = ""
    brand: Optional[str] = None
    brand_restriction: Optional[str] = None
    selling_restriction: Optional[str] = None
    selling_restriction_link: Optional[str] = None
    title: Optional[str] = None
    package_quantity: Optional[int] = None
    amazon_link: Optional[str] = None
    about_this_item: Optional[str] = None
    category: Optional[str] = None
    is_top_level_category: Optional[str] = None
    sales_rank: Optional[int] = None
    sub_category: Optional[str] = None
    sub_category_sales_rank: Optional[int] = None
    cost: Optional[float] = None
    sell_price: Optional[float] = None
    break_even_sell_price: Optional[float] = None
    buybox_landed: Optional[float] = None
    lowest_fba: Optional[float] = None
    lowest_fbm: Optional[float] = None
    seller_proceeds: Optional[float] = None
    current_est_sales: Optional[int] = None
    estimated_monthly_revenue: Optional[float] = None
    profit: Optional[float] = None
    margin_pct: Optional[float] = None
    roi_pct: Optional[float] = None
    referral_fee_pct: Optional[float] = None
    referral_fee: Optional[float] = None
    fba_pick_pack_fee: Optional[float] = None
    inbound_placement_fee: Optional[float] = None
    fulfillment_subtotal: Optional[float] = None
    cost_subtotal: Optional[float] = None
    vat_pct: Optional[float] = None
    vat_amount: Optional[float] = None
    inbound_shipping_estimate: Optional[float] = None
    package_dimensions: Optional[str] = None
    package_weight_lb: Optional[float] = None
    color: Optional[str] = None
    model: Optional[str] = None
    size: Optional[str] = None
    part_number: Optional[str] = None
    material: Optional[str] = None
    manufacturer: Optional[str] = None
    total_offers: Optional[int] = None
    new_fba_offers: Optional[int] = None
    new_fbm_offers: Optional[int] = None
    buybox_contention: Optional[int] = None
    customer_reviews: Optional[str] = None
    average_rating: Optional[float] = None
    total_review_count: Optional[int] = None
    is_hazmat: Optional[str] = None
    keepa: Optional[str] = None
    camelcc: Optional[str] = None
    custom_notes: Optional[str] = None
    product_image_link_1: Optional[str] = None
    product_image_link_2: Optional[str] = None
    product_image_link_3: Optional[str] = None
    product_image_link_4: Optional[str] = None
    product_image_link_5: Optional[str] = None
    analyzing_software_name: Optional[str] = "InternalAMZ"
    last_run: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    extra_attributes: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_d1_row(cls, row_dict: Dict[str, Any]) -> "WholesaleProductModel":
        """
        Instantiate entity from a Cloudflare D1 query result row dictionary.
        """
        known_fields = {
            "id", "asin", "parent_asin", "product_id", "favorite", "wholesaler_company_name",
            "brand", "brand_restriction", "selling_restriction", "selling_restriction_link",
            "title", "package_quantity", "amazon_link", "about_this_item", "category",
            "is_top_level_category", "sales_rank", "sub_category", "sub_category_sales_rank",
            "cost", "sell_price", "break_even_sell_price", "buybox_landed", "lowest_fba",
            "lowest_fbm", "seller_proceeds", "current_est_sales", "estimated_monthly_revenue",
            "profit", "margin_pct", "roi_pct", "referral_fee_pct", "referral_fee",
            "fba_pick_pack_fee", "inbound_placement_fee", "fulfillment_subtotal",
            "cost_subtotal", "vat_pct", "vat_amount", "inbound_shipping_estimate",
            "package_dimensions", "package_weight_lb", "color", "model", "size",
            "part_number", "material", "manufacturer", "total_offers", "new_fba_offers",
            "new_fbm_offers", "buybox_contention", "customer_reviews", "average_rating",
            "total_review_count", "is_hazmat", "keepa", "camelcc", "custom_notes",
            "product_image_link_1", "product_image_link_2", "product_image_link_3",
            "product_image_link_4", "product_image_link_5", "analyzing_software_name", "last_run", "created_at", "updated_at"
        }
        kwargs = {}
        extras = {}
        for k, v in row_dict.items():
            if k in known_fields:
                if k == "favorite":
                    kwargs[k] = bool(v)
                else:
                    kwargs[k] = v
            else:
                extras[k] = v
        kwargs["extra_attributes"] = extras
        return cls(**kwargs)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert entity to dictionary.
        """
        res = {
            "id": self.id,
            "asin": self.asin,
            "parent_asin": self.parent_asin,
            "product_id": self.product_id,
            "favorite": 1 if self.favorite else 0,
            "wholesaler_company_name": self.wholesaler_company_name,
            "analyzing_software_name": self.analyzing_software_name or "InternalAMZ",
            "Analyzing Software Name": self.analyzing_software_name or "InternalAMZ",
            "brand": self.brand,
            "title": self.title,
            "category": self.category,
            "sales_rank": self.sales_rank,
            "cost": self.cost,
            "sell_price": self.sell_price,
            "profit": self.profit,
            "margin_pct": self.margin_pct,
            "roi_pct": self.roi_pct,
            "total_offers": self.total_offers,
            "current_est_sales": self.current_est_sales,
            "estimated_monthly_revenue": self.estimated_monthly_revenue,
            "average_rating": self.average_rating,
            "total_review_count": self.total_review_count,
            "last_run": self.last_run,
        }
        return res

    def to_display_row(self) -> Dict[str, Any]:
        """
        Converts the entity into user-friendly table representation.
        """
        return {
            "Favorite": "⭐" if self.favorite else "",
            "ASIN": self.asin,
            "Product ID": self.product_id or "",
            "Wholesaler Company Name": self.wholesaler_company_name,
            "Analyzing Software Name": self.analyzing_software_name or "InternalAMZ",
            "Brand": self.brand or "",
            "Title": self.title or "",
            "Category": self.category or "",
            "Sales Rank": self.sales_rank,
            "Cost": self.cost,
            "Sell Price": self.sell_price,
            "Referral Fee": self.referral_fee,
            "FBA Pick & Pack Fee ($)": self.fba_pick_pack_fee,
            "Profit ($)": self.profit,
            "Margin (%)": (self.margin_pct / 100.0) if (self.margin_pct and self.margin_pct > 1.0) else self.margin_pct,
            "ROI (%)": (self.roi_pct / 100.0) if (self.roi_pct and self.roi_pct > 1.0) else self.roi_pct,
            "Current Est Sales": self.current_est_sales,
            "Estimated Monthly Revenue ($)": self.estimated_monthly_revenue,
            "Total Offers": self.total_offers,
            "Average Rating": self.average_rating,
            "Total Review Count": self.total_review_count,
            "Last Run": self.last_run,
        }



@dataclass
class ProductFilterCriteria:
    """
    Filter and search options for querying wholesale products from Cloudflare D1.
    """
    keyword: Optional[str] = None            # Search in ASIN, Title, Brand, Product ID
    category: Optional[str] = None           # Specific Amazon category filter
    wholesaler: Optional[str] = None         # Specific wholesaler filter
    min_profit: Optional[float] = None       # Minimum net profit threshold
    min_roi: Optional[float] = None          # Minimum ROI % threshold
    only_profitable: bool = False            # Restrict to profit > 0
    only_favorites: bool = False             # Restrict to favorite == 1
    sort_by: str = "profit"                  # Field to sort by ('profit', 'roi_pct', 'sales_rank', 'cost', 'sell_price', 'last_run')
    sort_ascending: bool = False             # Ascending (True) or Descending (False)
    page: int = 1                            # Current page number (1-indexed)
    page_size: int = 50                      # Records per page


@dataclass
class PaginatedQueryResult:
    """
    Container for paginated query results returned to the user viewer.
    """
    items: List[WholesaleProductModel]
    total_count: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        """Calculate total number of available pages."""
        if self.page_size <= 0:
            return 1
        return max(1, (self.total_count + self.page_size - 1) // self.page_size)
