# SPDX-License-Identifier: GPL-3.0
"""Deterministic encounter rules. All web requests and logs are fictional."""

from dataclasses import dataclass

READ = "read_log"
INSPECT = "inspect_request"
RETRY = "retry_request"
PATCH = "patch_code"
REPEAT_CRASH = "repeat_crash"
DOUBLE_STAMP = "double_stamp"
STACK_SURGE = "stack_surge"

LABELS = {
    READ: "Read Log",
    INSPECT: "Inspect Request",
    RETRY: "Retry Request",
    PATCH: "Patch Code",
}
COUNTER_LABELS = {
    REPEAT_CRASH: "Repeat Crash",
    DOUBLE_STAMP: "Double Stamp",
    STACK_SURGE: "Stack Surge",
}


@dataclass(frozen=True)
class Receipt:
    order_id: int
    request_id: str


ECHO_RECEIPTS = (Receipt(311, "ord-74"), Receipt(312, "ord-74"))


@dataclass(frozen=True)
class Step:
    move: str
    evidence: str
    options: tuple[str, ...] = ()
    answer: int = 0
    explanation: str = ""


@dataclass(frozen=True)
class Case:
    monster: str
    title: str
    objective: str
    symptom: str
    counter: str
    steps: tuple[Step, ...]
    reward: tuple[str, ...]
    opening_receipts: tuple[Receipt, ...] = ()

    def move_label(self, move: str) -> str:
        if self.opening_receipts and move == INSPECT:
            return "Compare Receipts"
        return LABELS[move]


CASES = (
    Case(
        "agnite",
        "Crash Loop",
        "Locate the failing line.",
        "The cart goes blank as soon as you open it.",
        REPEAT_CRASH,
        (
            Step(
                READ,
                "TypeError: Cannot read properties of undefined\n"
                "at renderCart (cart.js:42)\nat openCart (menu.js:16)\n"
                "at HTMLButtonElement.onclick (index.html:8)\n"
                "Where was the exception thrown?",
                ("menu.js:16", "cart.js:42", "index.html:8"),
                1,
                "cart.js:42 is the first frame and the line that threw. "
                "The other frames show how the code reached it.",
            ),
        ),
        (INSPECT, RETRY),
    ),
    Case(
        "aardart",
        "Echo Order",
        "Find the original order.",
        "You pressed Checkout once. The response timed out.",
        DOUBLE_STAMP,
        (
            Step(
                INSPECT,
                "POST /orders: response timed out (request ord-74).\n"
                "Orders #311 and #312 both have attempt ID ord-74.",
            ),
            Step(
                READ,
                "ord-74: INSERT committed, order #311.\n"
                "ord-74: second INSERT committed, order #312.\n"
                "ord-74: confirmation response timed out.\n"
                "What should the app do with the original attempt?",
                (
                    "Look up order #311",
                    "Submit a fresh order",
                    "Clear browser cache",
                ),
                explanation="Found order #311 using the original attempt. "
                "The lookup created zero new orders.",
            ),
        ),
        (PATCH,),
        ECHO_RECEIPTS,
    ),
    Case(
        "ampystoma",
        "Checkout Blackout",
        "Diagnose, repair, and verify checkout.",
        "Checkout returns an error after a coupon is removed.",
        STACK_SURGE,
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
                "The request ID ties the HTTP 500 to a null coupon. The log "
                "also confirms the order was rolled back.",
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
                "total.js:18 now reads coupon?.amount ?? 0.\n"
                "Retry to check the order and total.",
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
    revealed: int = 0
    turns: int = 0
    drops: int = 0
    retries: tuple[Receipt, ...] = ()
    pending: bool = False
    message: str = ""

    @property
    def receipts(self) -> tuple[Receipt, ...]:
        return self.case.opening_receipts + self.retries

    @property
    def duplicates(self) -> int:
        return max(0, len(self.receipts) - 1)

    @property
    def crash_count(self) -> int:
        return 1 + self.drops if self.case.counter == REPEAT_CRASH else 0

    @property
    def solved(self) -> bool:
        return self.progress == len(self.case.steps)

    @property
    def step(self) -> Step:
        return self.case.steps[self.progress]

    @property
    def evidence_notes(self) -> list[str]:
        return [step.evidence for step in self.case.steps[: self.revealed]]

    def use(self, move: str, known: set[str]) -> None:
        if move not in known or self.solved or self.pending:
            return
        self.turns += 1
        if move == self.step.move:
            self.revealed = max(self.revealed, self.progress + 1)
            self.message = self.step.evidence
            self.pending = bool(self.step.options)
            if self.pending:
                self.disrupt()
            else:
                self.advance()
            return
        if move == RETRY and self.case.opening_receipts:
            self.add_retry_receipt()
        elif move == RETRY:
            self.message = (
                "Checkout failed again. The underlying error is still present."
            )
        elif self.case.opening_receipts and not self.revealed:
            self.message = (
                "Match the receipts to a request before opening the log."
            )
        else:
            self.message = "No new evidence yet. Follow the clue from the last useful step."
        self.disrupt()

    def answer(self, index: int) -> None:
        if not self.pending:
            return
        self.pending = False
        if index == self.step.answer:
            self.message = self.step.explanation or "Diagnosis accepted."
            self.progress += 1
        elif self.case.opening_receipts and index == 1:
            self.add_retry_receipt()
            self.disrupt()
        else:
            self.message = (
                "That choice does not match the evidence. Inspect it again."
            )

    def add_retry_receipt(self) -> None:
        order = self.receipts[-1].order_id + 1
        request = 75 + len(self.retries)
        self.retries += (Receipt(order, f"ord-{request}"),)
        self.message = (
            f"A fresh POST saved another copy of this cart as order #{order}."
        )

    def advance(self) -> None:
        self.progress += 1
        if not self.solved:
            self.disrupt()

    def disrupt(self) -> None:
        self.drops += 1
