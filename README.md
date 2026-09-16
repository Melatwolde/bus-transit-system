# Bus Transit System

## Part A: Master Test Plan

### 1. Scope and Objectives

This plan verifies the route timetable, pricing rules, and transit booking flow for the Addis Ababa bus service. It covers the `/routes` experience, the active route list, local Ethiopian peak windows, frequent-rider logic, holiday/weekend/student stacking, discount caps, and the route navigation components used across the app.

The application currently exposes the following active route pairs on the timetable:

- Megenagna to Kara
- Ayertena to Menelik II
- Merkato to Saris
- Megenagna to Legehar
- Tor Hailoch to Bole Sarbet
- Kotebe to Merkato
- Megenagna to 4 Kilo
- Tor Hailoch to Ayertena
- Megenagna to Bole Airport

The business rules under test are:

- Peak windows in Africa/Addis_Ababa are 01:00 PM to 03:00 PM and 05:00 PM to 07:00 PM (inclusive start, exclusive end).
- Off-peak service applies outside those windows.
- Frequent rider status modifies discount behavior in peak and off-peak scenarios.
- Weekend and holiday flags stack with other discounts.
- Student discount adds on top of the base fare adjustment.
- Discount values are capped at the configured maximum of 40% unless overridden.

### 2. Overall Test Approach

The project uses a layered approach:

- Unit tests validate the pricing logic in `src/discount.py` using exhaustive decision-table coverage.
- Boundary tests check the exact peak-window transitions at 01:00, 03:00, 05:00, and 07:00.
- Combination tests verify stacking behavior for weekend, holiday, student, and frequent-rider rules.
- Integration tests validate the `/routes` route grid, status indicators, and navigation link.
- Regression tests preserve the booking and ticket flow.

The minimum target is at least 80% branch coverage for `src/discount.py`, measured using `pytest --cov=src/discount.py --cov-branch`.

### 3. Entry Criteria

The test plan may begin once the following are available:

- Python environment with FastAPI, Jinja2, pytest, and pytest-cov installed
- Source code is available in the workspace
- Template files render correctly and the app starts locally
- There is a clean test state for route and ticket data between runs

### 4. Exit Criteria

The release is considered ready when all of the following are true:

- All unit and integration tests pass.
- Branch coverage for `src/discount.py` is at least 80%.
- Every rule combination in the updated decision table executes successfully.
- Peak boundary conditions pass for all updated Ethiopian windows.
- The route timetable shows all nine active routes and status badges correctly.
- The `data-testid="nav-routes"` navigation link remains available across the primary templates.

### 5. Risk-Based Prioritization Matrix

| Area                | Risk                                               | Priority | Mitigation                                                |
| ------------------- | -------------------------------------------------- | -------- | --------------------------------------------------------- |
| Discount logic      | Incorrect discount calculation or over-discounting | High     | Exhaustive truth-table testing for all rule combinations  |
| Peak boundary logic | Wrong discount applied at the exact window edges   | High     | Boundary tests for 01:00, 03:00, 05:00, and 07:00         |
| Route availability  | Users see stale or missing corridors               | High     | Assert all 9 active route rows appear on `/routes`        |
| Navigation          | Users cannot discover timetable route page         | Medium   | Verify `nav-routes` on public and authenticated templates |
| Booking flow        | Ticket purchase breaks after pricing changes       | Medium   | Regression coverage for booking and payment flow          |
| Input validation    | Invalid discount configuration causes errors       | Medium   | Cap-validation and type-check tests                       |

### 6. Decision Table Coverage

The discount logic is validated with exhaustive rule coverage for the current decision inputs:

- `is_peak`
- `is_frequent_rider`
- `is_holiday`
- `is_weekend`
- `is_student`

This is implemented in [tests/unit/test_discount.py](tests/unit/test_discount.py) and follows the $2^n$ model for exhaustive branch coverage.

The expected base rules are as follows:

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

The modern rules add stacking behavior:

- weekend adds 5%
- holiday adds 5%
- student adds 10%
- total is capped at 40% by default

The route table and discount rules are aligned with the current implementation in [src/app.py](src/app.py), [src/discount.py](src/discount.py), and [templates/routes.html](templates/routes.html).

### 7. Acceptance Summary

The feature is accepted when all route rows, peak/off-peak indicators, and discount tests pass under the updated Ethiopan peak-window conditions and when the project maintains at least 80% branch coverage for the pricing logic.
