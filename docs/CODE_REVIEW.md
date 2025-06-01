# 🔍 Pre-Submission Code Audit Directive (Critical PR Checklist)

**Context:**  
This submission is intended for an upstream repository maintained by an exceptionally rigorous maintainer. Any deviation from best practices or introduction of even subtle technical debt may result in outright rejection and invalidate all previous contributions.

**Objective:**  
Before the final commit is submitted, a **full, exhaustive, line-by-line audit** must be completed. This is a gatekeeping process to ensure the proposed changes are:

- Correct and predictable
- Secure and memory-safe
- Architecturally aligned
- Maintainable at scale
- Style-compliant and platform-safe

All reviewers are **personally accountable** for confirming that every item below has been fully and verifiably satisfied.

---

## ✅ FUNCTIONAL CORRECTNESS

- [ ] All business and logic branches behave as expected under normal, edge, and failure conditions.
- [ ] No regression of existing functionality.
- [ ] Logic is deterministic and not reliant on side effects or external global state.
- [ ] Behavior is reproducible, even under retry or degraded conditions.

---

## 📐 ARCHITECTURAL CONSISTENCY

- [ ] Code respects the boundaries of existing modules and layers.
- [ ] No layering violations, no cross-module leaks, and no circular dependencies.
- [ ] All new abstractions are necessary, well-defined, and coherent.
- [ ] No reimplementation of existing primitives, tools, or libraries.

---

## 🧪 TEST COVERAGE & VALIDATION

- [ ] All new logic has unit tests with high coverage and strong assertions.
- [ ] Integration tests cover end-to-end and cross-module flows.
- [ ] Fuzzing or property-based tests applied where appropriate (e.g., parsers, JSON).
- [ ] Tests run cleanly under sanitized environments (e.g. ASan, UBSan, TSan).
- [ ] Manual validation steps are reproducible, automated where possible.

---

## 🔐 SECURITY

- [ ] All external inputs are validated, sanitized, and schema-constrained.
- [ ] No integer overflows, memory corruption, or use-after-free issues.
- [ ] Authentication, authorization, and permission logic are verified.
- [ ] No insecure default configurations or fallbacks.
- [ ] Secrets, tokens, and credentials are not hardcoded or leaked.

---

## 🧵 CONCURRENCY & THREAD SAFETY

- [ ] No data races or unsynchronized shared mutable state.
- [ ] Correct use of atomics, mutexes, or thread-safe constructs.
- [ ] `thread_local` and static variables are correctly scoped and initialized.
- [ ] No blocking operations in critical paths.
- [ ] Thread-safe behavior is tested under simulated load or stress conditions.

---

## ♻️ MEMORY & RESOURCE MANAGEMENT

- [ ] All memory allocations are properly scoped (RAII / smart pointers).
- [ ] No leaks, double-frees, or manual `delete` unless 100% justified.
- [ ] File descriptors, sockets, and handles are deterministically released.
- [ ] Allocation patterns are cache-friendly and bounded.

---

## 🚦 PERFORMANCE

- [ ] No critical path regressions or unnecessary I/O.
- [ ] Hot paths avoid repeated memory allocations or string copies.
- [ ] Expensive operations are batched, throttled, or cached.
- [ ] Binary size has not increased disproportionately.
- [ ] Benchmark results provided if performance could be impacted.

---

## 🧾 DOCUMENTATION & MAINTAINABILITY

- [ ] All public symbols (classes, methods, fields) are fully documented.
- [ ] README or module-level documentation updated where applicable.
- [ ] Complex algorithms have clear commentary or rationale.
- [ ] Commit messages follow `subsystem: change summary` format.
- [ ] Code is idiomatic, consistent, and avoids unnecessary cleverness.

---

## 🛠️ BUILD & CROSS-PLATFORM INTEGRITY

- [ ] Code compiles cleanly with `-Wall -Wextra -Werror` or equivalent.
- [ ] Works on all supported targets (macOS, Linux, Windows, etc.).
- [ ] No unguarded platform-specific behavior.
- [ ] Build system (CMake, Makefile, etc.) updated and verified.
- [ ] ABI compatibility is maintained for public interfaces if applicable.

---

## ✨ STYLE & REVIEWABILITY

- [ ] Code follows all style guides (`clang-format`, `black`, etc.).
- [ ] No commented-out code, debug prints, or TODOs in production.
- [ ] Patch is logically divided into clean, minimal, self-contained commits.
- [ ] Identifiers are clear, descriptive, and consistent.
- [ ] No magic numbers or ambiguous flags.

---

## 🔄 ROLLBACK SAFETY

- [ ] PR is bisect-safe and revert-friendly.
- [ ] No hidden or partial state transitions.
- [ ] Rollback impact and procedure are documented if changes are stateful.
- [ ] Migration scripts, if added, are idempotent and reversible.

---

## 🧠 FULL CONTEXTUAL VALIDATION

In addition to technical criteria, reviewers must:

- ✅ Read **every modified and newly added file in full**.
- ✅ Validate **internal logic and external interfaces** for correctness.
- ✅ Ensure that **inter-file relationships are contextually coherent**.
- ✅ Confirm there are **no broken assumptions, hidden side effects, or architectural drift**.

> Every change must make sense both in isolation and within the system’s broader context. Partial correctness is insufficient.

---

## 🧰 REVIEWER TOOLING POLICY

You are **encouraged and expected** to use the following tools to assist your review:

- ✅ **MCP (Model-Code-Plugin)** insights from your IDE for navigation, type inference, and dependency tracing.
- ✅ **Static and dynamic analyzers** such as `clang-tidy`, `Valgrind`, `ASan`, `TSan`, `cppcheck`, `pylint`, etc.
- ✅ **Search engines and official documentation** to cross-verify behavior, APIs, edge cases, and specifications.

> Auditing is not a manual-only task. Use all available resources to maximize confidence and completeness.

---

## ⛔ INSTANT REJECTION CRITERIA

If any of the following are present, the PR **must be rejected immediately**:

- [ ] ❌ Global mutable state or untracked side effects
- [ ] ❌ Unchecked pointer dereferencing or unsafe memory manipulation
- [ ] ❌ Silent failure modes (e.g., catch-all error swallowing)
- [ ] ❌ Race-prone `static` or shared state without synchronization
- [ ] ❌ Unjustified platform-specific hacks
- [ ] ❌ Temporary logging or debug code
- [ ] ❌ GOTO usage or unstructured control flow

---

## 🔐 FINAL VERIFICATION

Before submission:

- [ ] A **qualified senior reviewer** has validated every checklist item.
- [ ] All automated tests and static analysis tools pass without exception.
- [ ] Reviewer has full understanding of the patch and its downstream effects.
- [ ] The change is safe, justified, minimal, and improves the project in a measurable way.

> **If in doubt — stop the PR. Incomplete or careless work has no place upstream.**

---

> 💬 *“Software is read more often than it is written. Review like you’ll maintain it for the next 10 years — because you will.”*
