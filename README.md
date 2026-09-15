# Bus Transit System

## Part A: Master Test Plan

### Scope and objectives

Test the `/routes` timetable, navigation, Ethiopian local-time peak status, booking and ticket flow, and discount calculation. The discount rules cover peak/off-peak time, frequent rider status, weekends, public holidays, student fares, stacking, and a configurable cap.

### Test approach

- Exhaustively test the three legacy decision flags with $2^3 = 8$ combinations.
- Exhaustively test the five modern discount flags with $2^5 = 32$ combinations.
- Test peak boundaries at 07:00, 09:00, 17:00, and 19:00 using start-inclusive/end-exclusive windows.
- Verify `/routes` renders all nine active routes, departure frequencies, Peak/Off-Peak status, and `data-testid="nav-routes"`.
- Run unit, integration, and system tests with branch coverage for `src/discount.py`.

### Entry criteria

- `.venv` exists and dependencies in `requirements.txt` are installed.
- FastAPI, Uvicorn, Jinja2, pytest, pytest-cov, and timezone data import successfully.
- The application can start on a free local port.

### Exit criteria

- All automated tests pass.
- `src/discount.py` achieves at least 80% branch coverage.
- All decision-table combinations and peak boundaries pass.
- The routes page returns HTTP 200 and renders all requested route pairs.
- No high-severity defects remain.

### Risk-based prioritization

| Area                      | Risk                                    | Priority | Mitigation                               |
| ------------------------- | --------------------------------------- | -------- | ---------------------------------------- |
| Discount stacking and cap | Incorrect fare or over-discounting      | High     | 32-case truth table plus cap validation  |
| Peak boundaries           | Wrong status around commute windows     | High     | Four boundary tests in Ethiopian time    |
| Booking regression        | Existing users cannot book or pay       | High     | Integration and system lifecycle tests   |
| Route data                | Missing or incorrect corridor           | High     | Assert all nine route pairs on `/routes` |
| Navigation                | Users cannot discover timetable         | Medium   | Check `nav-routes` across page headers   |
| Timezone data             | Page fails on Windows without IANA data | Medium   | Declare and install `tzdata`             |

### Commands

```powershell
& .\.venv\Scripts\python.exe -m pytest tests/unit/test_discount.py --cov=src.discount --cov-branch --cov-report=term-missing
& .\.venv\Scripts\python.exe -m pytest tests/unit tests/integration -v
& .\.venv\Scripts\python.exe -m pytest tests -v
```

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
