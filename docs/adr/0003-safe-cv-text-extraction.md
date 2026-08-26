# ADR 0003: Safe CV Text Extraction

**Status:** Accepted for Phase 3
**Date:** 2026-08-26

## Context

Phase 2 accepts and privately stores user-owned PDF and DOCX CV files but deliberately does not interpret their contents. Phase 3 introduces text extraction only. It does not introduce job description intake, semantic skill inference, matching, scoring, OpenAI, recommendations, document download, billing, queues, or agent orchestration.

Extracted CV text remains sensitive personal data. It is untrusted document content, never application instructions and never a source of authority for candidate claims.

## Threat model

| Boundary | Abuse case | Phase 3 control |
|---|---|---|
| Stored document → parser | Malformed PDF/DOCX crashes or consumes CPU/memory | Parse in a short-lived child process with wall-clock timeout and Linux CPU/address-space limits; retain Phase 2 upload size and DOCX archive limits. |
| DOCX ZIP/XML → extractor | Archive expansion, unsafe paths, entity-like payloads, excessive text | Revalidate DOCX container limits; read only `word/document.xml`; reject DTD declarations; cap extracted character count. |
| PDF → extractor | Excessive page count, malformed syntax, extraction exceptions | Use `pypdf` only in the constrained child process; cap pages and output characters; map parser errors to safe failure states. |
| User → extraction API | IDOR, repeated expensive parsing, unowned version selection | Derive ownership from the validated session, require CSRF, query document/version by both ID and principal, and return uniform `404` for inaccessible resources. |
| Extracted text → API/browser/logs | PII leakage or prompt injection | Persist text as server-only data; return status and counts only; never log text, display it by default, or place it in prompts. |
| Extraction state → user | Confusing silent failure | Persist explicit `pending`, `processing`, `succeeded`, or `failed` status with a safe user-facing message and a retry action. |

## Decisions

| Area | Decision | Rationale |
|---|---|---|
| Invocation | The user explicitly starts extraction for one owned CV version via a protected API endpoint. | Keeps control visible and avoids hidden expensive work during upload. |
| Execution | Extraction is synchronous from the user’s perspective, but runs in a short-lived constrained child process invoked from a worker thread. | The Phase 3 workload is bounded by 10 MiB and strict parser limits; a queue is not yet justified. |
| PDF parser | Add `pypdf` as the single new runtime dependency. | It is a maintained pure-Python reader and avoids making an external system binary a production dependency. |
| DOCX parser | Use the existing safe ZIP validation plus standard-library XML processing. | The required document body is simple XML; no full Office editing dependency is justified. |
| Limits | Maximum 100 PDF pages, 250,000 extracted characters, 8 seconds wall time, 4 seconds CPU time, and 256 MiB parser address space. | Bounds the initial synchronous extraction surface while retaining normal CV capacity. |
| Persistence | Add one extraction record per immutable CV document version. Store private extracted text and safe metadata/status; do not expose raw text in response models. | Preserves future deterministic matching input without making sensitive text a browser/API payload. |
| Failures | Persist a safe failure status and generic recovery message; retain the source document unchanged. | A parsing failure must not destroy the user’s original CV or leak parser internals. |

## Consequences

Phase 3 creates a bounded extraction foundation, not a general document-processing platform. Processing a CV is an explicit user action; no queue or background runner is introduced. At sustained load, observed latency or retry pressure may justify a future async worker/queue decision.

No parser can prove a hostile document harmless. Production release of extraction still requires threat-model review of the deployment sandbox, process permissions, monitoring, retention/deletion operations, and malware-scanning policy. The child-process limits are a risk reduction, not a malware guarantee.

## References

[1]: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html "OWASP File Upload Cheat Sheet"
[2]: https://docs.python.org/3/library/resource.html "Python resource module"
[3]: https://pypdf.readthedocs.io/ "pypdf documentation"
