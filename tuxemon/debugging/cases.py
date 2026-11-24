# SPDX-License-Identifier: GPL-3.0
"""Deterministic encounter rules. All web requests and logs are fictional."""

from dataclasses import dataclass

READ = "read_log"
INSPECT = "inspect_request"
RETRY = "retry_request"
PATCH = "patch_code"

LABELS = {
    READ: "Read Log",
    INSPECT: "Inspect Request",
    RETRY: "Retry Request",
    PATCH: "Patch Code",
}


@dataclass(frozen=True)
class Step:
    move: str
    evidence: str
    options: tuple[str, ...] = ()
    answer: int = 0


@dataclass(frozen=True)
class Case:
    monster: str
    title: str
    objective: str
    symptom: str
    disruption: str
    steps: tuple[Step, ...]
    reward: tuple[str, ...]


CASES = (
    Case(
        "agnite",
        "Crash Loop",
        "Locate the failing line.",
        "The cart goes blank as soon as you open it.",
        "Repeat Crash added another copy of the exception.",
        (
            Step(
                READ,
                "TypeError: Cannot read properties of undefined\n"
                "at renderCart (cart.js:42)\nat openCart (menu.js:16)\n"
                "at HTMLButtonElement.onclick (index.html:8)\n"
                "Where was the exception thrown?",
                ("menu.js:16", "cart.js:42", "index.html:8"),
                1,
            ),
        ),
        (INSPECT, RETRY),
    ),
    Case(
        "aardart",
        "Echo Order",
        "Account for the original order.",
        "Checkout timed out. The order might already be saved.",
        "Repeat Click added another timeout to the browser log.",
        (
            Step(
                INSPECT,
                "POST /orders: response timed out (request ord-74).\n"
                "The browser cannot tell whether the server saved the order.",
            ),
            Step(
                READ,
                "ord-74: INSERT committed, order #311.\n"
                "ord-74: confirmation response timed out.\n"
                "What should the app do with the original attempt?",
                (
                    "Look up order #311",
                    "Submit a fresh order",
                    "Clear browser cache",
                ),
            ),
        ),
        (PATCH,),
    ),
    Case(
        "ampystoma",
        "Checkout Blackout",
        "Diagnose, repair, and verify checkout.",
        "Checkout returns an error after a coupon is removed.",
        "Stack Surge raised the failed checkout counter.",
        (
            Step(INSPECT, "POST /checkout returned 500. Request ID: cart-19."),
            Step(
                READ,
                "cart-19: TypeError at total.js:18, inside applyDiscount.\n"
                "coupon was null. Transaction rolled back.\n"
                "Which evidence explains the response?",
                (
                    "The browser cache is stale",
                    "Discount code dereferences null",
                    "The order was already saved",
                ),
                1,
            ),
            Step(
                PATCH,
                "total.js:18 reads coupon.amount. What change fits the evidence?",
                (
                    "Retry until it works",
                    "Hide the error message",
                    "Treat a missing coupon as zero discount",
                ),
                2,
            ),
            Step(
                RETRY,
                "POST /checkout returned 201. One order was created.\n"
                "The total matches the cart with no discount.",
            ),
        ),
        (INSPECT, PATCH),
    ),
)


@dataclass
class Encounter:
    case: Case
    progress: int = 0
    turns: int = 0
    drops: int = 0
    duplicates: int = 0
    pending: bool = False
    message: str = ""

    @property
    def solved(self) -> bool:
        return self.progress == len(self.case.steps)

    @property
    def step(self) -> Step:
        return self.case.steps[self.progress]

    def use(self, move: str, known: set[str]) -> None:
        if move not in known or self.solved or self.pending:
            return
        self.turns += 1
        if move == self.step.move:
            self.message = self.step.evidence
            self.pending = bool(self.step.options)
            if self.pending:
                self.disrupt()
            else:
                self.advance()
            return
        if move == RETRY and self.case == CASES[1]:
            self.duplicates += 1
            self.message = "Retry created a duplicate order. The first order was already saved."
        elif move == RETRY:
            self.message = (
                "Checkout failed again. The underlying error is still present."
            )
        else:
            self.message = "No new evidence yet. Follow the clue from the last useful step."
        self.disrupt()

    def answer(self, index: int) -> None:
        if not self.pending:
            return
        self.pending = False
        if index == self.step.answer:
            self.message = (
                self.step.evidence.splitlines()[0] + "\nDiagnosis accepted."
            )
            self.progress += 1
        else:
            self.message = (
                "That choice does not match the evidence. Inspect it again."
            )

    def advance(self) -> None:
        self.progress += 1
        if not self.solved:
            self.disrupt()

    def disrupt(self) -> None:
        self.drops += 1
