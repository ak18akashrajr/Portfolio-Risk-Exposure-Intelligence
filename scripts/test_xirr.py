import sys
import os
from datetime import datetime, timedelta

# Mocking the setup
def calculate_xirr(cash_flows):
    if not cash_flows:
        return None

    def npv(rate, cash_flows):
        total_npv = 0
        t0 = min(cf['date'] for cf in cash_flows)
        for cf in cash_flows:
            t = (cf['date'] - t0).days / 365.0
            total_npv += cf['amount'] / ((1 + rate) ** t)
        return total_npv

    cash_flows = [cf for cf in cash_flows if cf['amount'] != 0]
    if not cash_flows:
        return None

    low = -0.99
    high = 10.0
    max_iter = 100
    tol = 1e-6

    f_low = npv(low, cash_flows)
    f_high = npv(high, cash_flows)

    if f_low * f_high > 0:
        return None

    for _ in range(max_iter):
        mid = (low + high) / 2
        f_mid = npv(mid, cash_flows)
        if abs(f_mid) < tol:
            return mid
        if f_low * f_mid < 0:
            high = mid
            f_high = f_mid
        else:
            low = mid
            f_low = f_mid
    return (low + high) / 2

# Test Case 1: 10% growth in 1 year
t0 = datetime.now() - timedelta(days=365)
cf1 = [
    {"date": t0, "amount": -100},
    {"date": datetime.now(), "amount": 110}
]
xirr1 = calculate_xirr(cf1)
print(f"Test 1 (Expected ~10%): {xirr1*100:.2f}%")

# Test Case 2: No growth
cf2 = [
    {"date": t0, "amount": -100},
    {"date": datetime.now(), "amount": 100}
]
xirr2 = calculate_xirr(cf2)
print(f"Test 2 (Expected ~0%): {xirr2*100:.2f}%")

# Test Case 3: Multiple cash flows
# Invest 100 today, 100 after 6 months, total 250 after 1 year
t2 = datetime.now()
t1 = t2 - timedelta(days=182) # ~6 months
t0 = t2 - timedelta(days=365)
cf3 = [
    {"date": t0, "amount": -100},
    {"date": t1, "amount": -100},
    {"date": t2, "amount": 250}
]
xirr3 = calculate_xirr(cf3)
print(f"Test 3 (Expect positive): {xirr3*100:.2f}%")
