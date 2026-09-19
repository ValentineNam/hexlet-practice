def calculate_partner_discount(total_quantity: int) -> int:
    """Return the discount percent based on total purchased quantity."""
    if total_quantity < 10000:
        return 0
    if 10000 <= total_quantity <= 49999:
        return 5
    if 50000 <= total_quantity <= 299999:
        return 10
    return 15
