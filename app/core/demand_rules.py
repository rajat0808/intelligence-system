def demand_band(rolling_30_sales, avg_stock):
    velocity = rolling_30_sales / max(avg_stock, 1)
    return "H" if velocity >= 0.25 else "M"
