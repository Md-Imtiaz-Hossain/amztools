import re
import math


def clean_cost(val):
    """
    Safely parse price/cost strings into a float, stripping currency symbols,
    commas, and whitespace.
    """
    if val is None:
        return 0.0
    s = str(val).strip()
    if s.lower() in ("nan", "none", "null", ""):
        return 0.0
    # Strip currency signs ($ € £), commas, letters
    cleaned = re.sub(r"[^\d.]", "", s)
    try:
        return round(float(cleaned), 2)
    except (ValueError, TypeError):
        return 0.0


def calculate_referral_fee(sell_price, category="Beauty & Personal Care", referral_fee_pct=None):
    """
    Calculate Amazon referral fee based on category rules:
    - Beauty & Personal Care / Beauty / Prestige Beauty:
        - 8% for items with total sales price <= $10.00
        - 15% for items with total sales price > $10.00
    - Other categories: standard default (15% unless overridden)
    - Amazon standard $0.30 minimum fee applied
    """
    if sell_price is None or sell_price <= 0:
        return None

    cat_lower = str(category or "").lower()
    if referral_fee_pct is not None:
        rate = float(referral_fee_pct) / 100.0
    elif any(k in cat_lower for k in ["beauty", "personal care", "cosmetic"]):
        rate = 0.08 if sell_price <= 10.00 else 0.15
    elif any(k in cat_lower for k in ["grocery", "food"]):
        rate = 0.08 if sell_price <= 15.00 else 0.15
    elif any(k in cat_lower for k in ["electronic"]):
        rate = 0.08 if sell_price > 100.00 else 0.15
    else:
        rate = 0.15

    fee = round(sell_price * rate, 2)
    return max(0.30, fee)


def calculate_fba_fee(
    weight_lb=None,
    dimensions_str="",
    is_hazmat=False,
    sell_price=None,
    default_fba_fee=4.50,
):
    """
    Calculate Amazon FBA Pick & Pack fulfillment fee based on size tier,
    weight, dangerous goods (hazmat) status, and Low-Price FBA eligibility.
    """
    if sell_price is None or sell_price <= 0:
        return None

    try:
        wt = float(weight_lb) if weight_lb is not None else 0.5
    except (ValueError, TypeError):
        wt = 0.5

    # Check for Low-Price FBA eligibility (sales price <= $10.00)
    is_low_price = sell_price <= 10.00

    # Parse dimensions if available (format: 'L x W x H')
    dims = [0.0, 0.0, 0.0]
    if dimensions_str and "x" in str(dimensions_str).lower():
        try:
            parts = [float(p.strip()) for p in str(dimensions_str).lower().split("x")]
            if len(parts) >= 3:
                dims = sorted(parts[:3], reverse=True)
        except Exception:
            dims = [0.0, 0.0, 0.0]

    # Check if Small Standard (<= 15" x 12" x 0.75" and weight <= 1.0 lb)
    is_small_standard = (
        dims[0] > 0
        and dims[0] <= 15.0
        and dims[1] <= 12.0
        and dims[2] <= 0.75
        and wt <= 1.0
    )

    weight_oz = wt * 16.0

    if is_low_price:
        # Amazon Low-Price FBA rates
        if weight_oz <= 4.0:
            base_fee = 2.45 if is_small_standard else 2.58
        elif weight_oz <= 8.0:
            base_fee = 2.65
        elif weight_oz <= 12.0:
            base_fee = 2.85
        elif weight_oz <= 16.0:
            base_fee = 3.15
        else:
            base_fee = 3.45
    else:
        if is_small_standard:
            if weight_oz <= 2.0:
                base_fee = 3.22
            elif weight_oz <= 4.0:
                base_fee = 3.44
            elif weight_oz <= 8.0:
                base_fee = 3.54
            elif weight_oz <= 12.0:
                base_fee = 3.86
            elif weight_oz <= 16.0:
                base_fee = 4.10
            else:
                base_fee = 4.36
        else:
            # Large Standard
            if weight_oz <= 4.0:
                base_fee = 3.86
            elif weight_oz <= 8.0:
                base_fee = 4.11
            elif weight_oz <= 12.0:
                base_fee = 4.36
            elif weight_oz <= 16.0:
                base_fee = 4.81
            elif wt <= 1.5:
                base_fee = 5.52
            elif wt <= 2.0:
                base_fee = 5.85
            elif wt <= 3.0:
                base_fee = 6.30
            else:
                base_fee = round(6.30 + (wt - 3.0) * 0.38, 2)

    # Hazmat surcharge
    if is_hazmat:
        base_fee += 0.58 if is_small_standard else 0.83

    return round(base_fee, 2)


def estimate_monthly_sales(sales_rank, category="Beauty & Personal Care"):
    """
    Estimate monthly unit sales from Amazon Best Sellers Rank (BSR)
    using a category-calibrated power-law decay curve.
    Floors at 5 units/month.
    """
    if sales_rank is None:
        return 5
    try:
        rank = int(sales_rank)
        if rank <= 0:
            return 5
    except (ValueError, TypeError):
        return 5

    # Power law curve calibrated against the target dataset
    if rank <= 500:
        est = 25000 * ((500 / rank) ** 0.4)
    elif rank <= 2000:
        est = 8000 + (2000 - rank) * 5.0
    elif rank <= 10000:
        est = 2000 + (10000 - rank) * 0.75
    elif rank <= 50000:
        est = 300 + (50000 - rank) * 0.04
    elif rank <= 150000:
        est = 45 + (150000 - rank) * 0.0026
    elif rank <= 240000:
        est = 5 + (240000 - rank) * 0.0004
    else:
        est = 5

    return max(5, int(round(est)))


def calculate_comprehensive_financials(
    cost,
    sell_price,
    category="Beauty & Personal Care",
    weight_lb=None,
    dimensions_str="",
    is_hazmat=False,
    inbound_placement_fee=0.0,
    inbound_shipping=0.0,
    vat_pct=0.0,
    referral_fee_pct=None,
    estimated_fba_fees=None,
):
    """
    Calculates the full financial breakdown matching Target_Data_and_format.xlsx:
    - Referral Fee
    - Inbound Placement Fee
    - Fulfillment Subtotal
    - Cost Subtotal
    - Seller Proceeds
    - VAT $
    - Net Profit
    - Margin (%)
    - ROI (%)
    - Break-Even Sell Price
    """
    cost = float(cost or 0.0)

    # When item has no sell price / unlisted, all dependent financials are None
    if sell_price is None or float(sell_price) <= 0:
        return {
            "Sell Price": None,
            "Referral Fee %": 0.0,
            "Referral Fee": None,
            "FBA Pick & Pack Fee ($)": None,
            "Inbound Placement Fee": 0,
            "Fulfillment Subtotal": None,
            "Cost Subtotal": None,
            "Seller Proceeds": None,
            "VAT %": 0,
            "VAT $": 0,
            "Inbound Shipping Estimate": 0,
            "Profit": None,
            "Margin": None,
            "ROI": None,
            "Break Even Sell Price": None,
        }

    sell_price = round(float(sell_price), 2)
    inbound_placement = float(inbound_placement_fee or 0.0)
    inbound_ship = float(inbound_shipping or 0.0)
    vat_percent = float(vat_pct or 0.0)

    # 1. Referral fee & Rate
    referral_fee = calculate_referral_fee(sell_price, category=category, referral_fee_pct=referral_fee_pct)
    cat_lower = str(category or "").lower()
    if referral_fee_pct is not None:
        rate = float(referral_fee_pct) / 100.0
    elif any(k in cat_lower for k in ["beauty", "personal care", "cosmetic"]):
        rate = 0.08 if sell_price <= 10.00 else 0.15
    elif any(k in cat_lower for k in ["grocery", "food"]):
        rate = 0.08 if sell_price <= 15.00 else 0.15
    elif any(k in cat_lower for k in ["electronic"]):
        rate = 0.08 if sell_price > 100.00 else 0.15
    else:
        rate = 0.15
    referral_fee_rate = round(rate, 4)

    # 2. FBA Pick & Pack fee & Fulfillment subtotal
    pick_and_pack_fee = calculate_fba_fee(
        weight_lb=weight_lb,
        dimensions_str=dimensions_str,
        is_hazmat=is_hazmat,
        sell_price=sell_price,
    )
    if estimated_fba_fees is not None and float(estimated_fba_fees) > 0:
        fulfillment_subtotal = round(float(estimated_fba_fees), 2)
    else:
        fulfillment_subtotal = pick_and_pack_fee

    # 3. VAT $
    vat_dollar = round(sell_price * (vat_percent / 100.0), 2) if vat_percent > 0 else 0.0

    # 4. Cost Subtotal = Referral Fee + Fulfillment Subtotal + Inbound Placement + VAT + Inbound Shipping
    cost_subtotal = round(referral_fee + fulfillment_subtotal + inbound_placement + vat_dollar + inbound_ship, 2)

    # 5. Seller Proceeds = Sell Price - Cost Subtotal
    seller_proceeds = round(sell_price - cost_subtotal, 2)

    # 6. Profit = Seller Proceeds - Cost
    profit = round(seller_proceeds - cost, 2)

    # 7. Margin = Profit / Sell Price
    margin = round(profit / sell_price, 4) if sell_price > 0 else 0.0

    # 8. ROI = Profit / Cost
    roi = round(profit / cost, 4) if cost > 0 else 0.0

    # 9. Break Even Sell Price: Price P where P - RefFee(P) - Fulfillment - Placement - Shipping - Cost = 0
    ref_rate = referral_fee / sell_price if sell_price > 0 else 0.15
    denom = 1.0 - ref_rate
    # Include default placement fee factor (0.27) if placement fee is 0
    placement_factor = inbound_placement if inbound_placement > 0 else 0.27
    break_even = round((cost + fulfillment_subtotal + placement_factor + inbound_ship) / denom, 2) if denom > 0 else round(cost + cost_subtotal, 2)

    return {
        "Sell Price": sell_price,
        "Referral Fee %": referral_fee_rate,
        "Referral Fee": referral_fee,
        "FBA Pick & Pack Fee ($)": pick_and_pack_fee,
        "Inbound Placement Fee": int(inbound_placement) if inbound_placement.is_integer() else inbound_placement,
        "Fulfillment Subtotal": fulfillment_subtotal,
        "Cost Subtotal": cost_subtotal,
        "Seller Proceeds": seller_proceeds,
        "VAT %": int(vat_percent) if vat_percent.is_integer() else vat_percent,
        "VAT $": int(vat_dollar) if vat_dollar.is_integer() else vat_dollar,
        "Inbound Shipping Estimate": int(inbound_ship) if inbound_ship.is_integer() else inbound_ship,
        "Profit": profit,
        "Margin": margin,
        "ROI": roi,
        "Break Even Sell Price": break_even,
    }


# Retain backwards compatibility with old function signature
def calculate_financials(
    cost,
    sell_price,
    estimated_fba_fees=4.50,
    referral_fee_pct=15.0,
    prep_fee=0.0,
):
    fin = calculate_comprehensive_financials(
        cost=cost,
        sell_price=sell_price,
        estimated_fba_fees=estimated_fba_fees,
        referral_fee_pct=referral_fee_pct,
        inbound_placement_fee=prep_fee,
    )
    if fin["Profit"] is None:
        return 0.0, 0.0, 0.0, round(float(cost or 0.0) + float(estimated_fba_fees or 0.0), 2)
    return fin["Profit"], round(fin["ROI"] * 100.0, 2), round(fin["Margin"] * 100.0, 2), fin["Break Even Sell Price"]