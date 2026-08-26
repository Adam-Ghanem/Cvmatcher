# ADR 0005: Private Data Deletion Lifecycle

**Status:** Implemented in progress
**Date:** 2026-08-26

## Context

CVMatcher stores sensitive CV objects, server-only extracted text, private target-role text, and derived match analyses. Users need owner-controlled removal without exposing resource existence across accounts or leaving browser-visible source text.

## Proposed boundary

A signed-in owner may explicitly delete a whole CV document or a target role. Both operations require the existing CSRF control and use uniform `404 RESOURCE_NOT_FOUND` responses for missing or unowned resources. Deleting a CV document removes its immutable versions, private extractions, and dependent analyses. Deleting a target role removes its private description and dependent analyses through existing foreign-key cascades.

For CVs, the service resolves and locks the owned database document, collects only server-stored opaque object keys, deletes those private objects through the storage interface, then deletes the database document in the same request transaction boundary. Storage errors must fail safely with a generic recovery error and must not expose paths or keys. The implemented API and client tests cover owner deletion, CSRF, and uniform cross-user protection; deeper dependent-analysis and physical-object assertions remain part of final lifecycle verification.

## Explicit exclusions

This phase does not add account deletion, retention timers, backup erasure automation, soft-delete ambiguity, public restoration, archival, AI, or recommendations. Backup/retention policy remains a production prerequisite.
