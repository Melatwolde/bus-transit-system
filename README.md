# Bus Transit System

## Part A: Decision Table Test Plan

### Objective

This test plan validates the discount calculation logic for the bus fare system. The decision is based on three input conditions:

- Holiday status: `is_holiday`
- Peak-time status: `is_peak`
- Frequent rider status: `is_frequent_rider`

The purpose is to confirm that every valid input combination produces the correct discount value according to the business rules.

### Business Rules

The discount logic is applied in the following priority order:

1. If the trip is on a holiday, apply the holiday rule.
2. Otherwise, if the trip is during peak time, apply the peak-time rule.
3. Otherwise, apply the off-peak rule.
4. Within each rule group, the frequent rider status determines the final discount percentage.

### Expected Discount Rules

- Holiday + Frequent rider = 30%
- Holiday + Non-frequent rider = 20%
- Peak + Frequent rider = 10%
- Peak + Non-frequent rider = 0%
- Off-peak + Frequent rider = 25%
- Off-peak + Non-frequent rider = 15%

### Decision Table

| Test Case ID | Holiday | Peak | Frequent Rider | Expected Discount | Rule Applied                  |
| ------------ | ------- | ---- | -------------- | ----------------- | ----------------------------- |
| DT-01        | Yes     | Yes  | Yes            | 30%               | Holiday + Frequent rider      |
| DT-02        | Yes     | No   | No             | 20%               | Holiday + Non-frequent rider  |
| DT-03        | No      | Yes  | Yes            | 10%               | Peak + Frequent rider         |
| DT-04        | No      | Yes  | No             | 0%                | Peak + Non-frequent rider     |
| DT-05        | No      | No   | Yes            | 25%               | Off-peak + Frequent rider     |
| DT-06        | No      | No   | No             | 15%               | Off-peak + Non-frequent rider |

### Rule Interpretation

The decision table confirms that holiday status has the highest priority, followed by peak-time status. The frequent rider flag then determines the exact percentage within the selected category. This ensures the system applies business rules consistently and prevents lower-priority conditions from overriding higher-priority ones.

### Traceability to Automated Test

The same six combinations are implemented and validated in [tests/unit/test_discount.py](tests/unit/test_discount.py).

### Expected Outcome

Each decision-table row should produce exactly one valid discount result, and the full combination set should be covered without missing or duplicate branches.
