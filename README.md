# Bus Transit System

## Part A: Master Test Plan

### Scope and Objectives

This plan covers route discovery at `/routes`, navigation to the timetable, fare-discount calculation, and the booking/ticket flow. It verifies that peak windows, frequent rider status, weekend and public holiday flags, student discounts, stacking, and the 40% cap produce deterministic fares. It also verifies that all decision branches are exercised.

### Test Approach

- Unit tests use an exhaustive $2^3$ decision table for `is_peak`, `is_frequent_rider`, and `is_holiday`.
- Boundary tests cover 07:00, 09:00, 17:00, and 19:00 using inclusive-start/exclusive-end peak windows.
- Combination tests cover weekend, student, holiday, and cap stacking.
- Integration tests verify `/routes` returns the timetable and every primary page exposes `data-testid="nav-routes"`.
- Existing booking, payment, scan, authentication, and invalid-input tests remain regression coverage.
- The target is at least 80% branch coverage for `src/discount.py`, measured with `pytest --cov=src/discount.py --cov-branch`.

### Entry Criteria

- Source, templates, and test dependencies are available.
- The configured Python environment can import FastAPI, Jinja2, pytest, and pytest-cov.
- The application starts and the test database/state is isolated or reset between tests.

### Exit Criteria

- All unit and integration tests pass.
- Branch coverage for `src/discount.py` is at least 80%.
- All eight rows of the three-variable truth table execute successfully.
- Peak boundary, stacking, cap, route timetable, and navigation checks pass.
- No open high-severity defects remain.

### Risk-Based Prioritization Matrix

| Area                      | Risk                                                | Priority | Mitigation                                                |
| ------------------------- | --------------------------------------------------- | -------- | --------------------------------------------------------- |
| Discount stacking and cap | Incorrect fares or over-discounting                 | High     | Exhaustive table plus cap and additive-combination tests  |
| Peak boundaries           | Peak surcharge/discount applied at the wrong minute | High     | Boundary tests at all four window edges                   |
| Booking regression        | Existing customers cannot book or pay               | High     | Run integration and system booking flows                  |
| Route availability        | Users see stale or missing corridors                | Medium   | Assert all active route rows and frequencies on `/routes` |
| Navigation                | Users cannot discover the timetable                 | Medium   | Assert `nav-routes` on public and authenticated templates |
| Invalid input             | Malformed times or fares cause unhandled errors     | Medium   | Add validation tests as time input becomes user-entered   |

### Decision Table

| Peak | Frequent | Holiday | Expected legacy discount |
| ---- | -------- | ------- | ------------------------ |
| No   | No       | No      | 15%                      |
| No   | No       | Yes     | 20%                      |
| No   | Yes      | No      | 25%                      |
| No   | Yes      | Yes     | 30%                      |
| Yes  | No       | No      | 0%                       |
| Yes  | No       | Yes     | 20%                      |
| Yes  | Yes      | No      | 10%                      |
| Yes  | Yes      | Yes     | 30%                      |

The exhaustive rows are implemented in [tests/unit/test_discount.py](tests/unit/test_discount.py). Modern optional flags add 5% for weekend, 5% for holiday, and 10% for students, with a configurable 40% default cap.
