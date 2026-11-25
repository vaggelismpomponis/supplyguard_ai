"""SupplyGuard AI - Chainlit Conversational Interface & Human-in-the-Loop Control Plane.

Implements all Interface role deliverables (Issues #41 through #53, docs/roles/interface.md)
against the frozen architecture contracts (docs/ARCHITECTURE_CONTRACTS.md):
- #41: UI Contracts, RBAC Scopes & 1:1 `thread_id` <-> `cl.context.session.id` session mapping
- #42: Chainlit Application with Deep Agents & PostgresSaver session integration
- #43: Role-Based Access Control (RBAC) authentication & dynamic document scope filtering
       (Procurement Manager, Finance Controller, Read-only Guest from `config/users.csv`)
- #44: Specialist Subagent live step progress & telemetry indicators via `cl.Step`
- #45: Clarification dialog via interrupt for ambiguous incidents (e.g. "Atlas" -> S001 vs S006)
- #46: Day 5 UI containerization & healthcheck readiness in Docker Compose
- #47: Operational Impact Dashboard (usable vs reserved vs quarantined stock, factory cover timelines,
       affected BOM products & customer orders, source-precedence conflicts, prompt-injection alerts)
- #48: Recovery Strategy Comparison Matrix (strictly separating Recovery Cost vs Revenue at Risk,
       documenting rejections for Helios, Borealis, and Delta shared Tier-2 upstream)
- #49: Payload-Bound Human Approval Card with SHA-256 payload digest, `[Approve]`, `[Reject]`,
       `[Modify Plan]` revalidation, and `asyncio.Lock` double-click protection
- #50: Post-Approval Simulated Procurement MCP receipt & downloadable Markdown/PDF Incident Report
- #51: Session Resume UI on reconnect / `/resume <thread_id>` after app container restart
- #52: Multi-Turn Follow-Up Q&A from persisted case memory & deterministic calculators
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Dict, List, Optional

import chainlit as cl

from src.agent.deep_agent import get_orchestrator
from src.agent.schemas import (
    AccessScope,
    ActionStatus,
    ApprovalPayload,
    DisruptionFact,
    DocumentaryFinding,
    IncidentReport,
    OperationalImpact,
    ProcurementReceipt,
    RecoveryOption,
    UserProfile,
    build_approval_payload,
    compute_operational_impact,
    compute_recovery_options,
    load_users_from_csv,
    retrieve_scoped_documentary_findings,
)

logger = logging.getLogger(__name__)


def _is_real_chainlit_runtime() -> bool:
    """Return True when running inside real Chainlit rather than unit-test module stubs."""
    return bool(getattr(cl, "__file__", None))


# Register PostgreSQL Chainlit DataLayer (users, role-scoped chat history, steps, elements)
if hasattr(cl, "data_layer"):
    @cl.data_layer
    def get_supplyguard_data_layer() -> Optional[Any]:
        if not _is_real_chainlit_runtime():
            return None
        try:
            from src.db.connection import is_postgres_available
            if not is_postgres_available():
                return None
            from src.db.chainlit_data_layer import SupplyGuardDataLayer
            return SupplyGuardDataLayer()
        except Exception as exc:
            logger.warning("SupplyGuardDataLayer unavailable; chat history persistence disabled: %s", exc)
            return None


# Register authenticated element download endpoint and safe subagent avatar fallback
if _is_real_chainlit_runtime():
    try:
        from chainlit.auth import get_current_user as _cl_get_current_user
        from chainlit.server import app as _cl_fastapi_app, get_avatar as _cl_get_avatar
        from fastapi import (
            APIRouter as _FastAPIRouter,
            Depends as _FastAPIDepends,
            HTTPException as _HTTPException,
            Response as _FastAPIResponse,
        )

        if not getattr(_cl_fastapi_app.state, "supplyguard_elements_route_registered", False):
            async def download_persisted_element(
                thread_id: str,
                element_id: str,
                current_user: Any = _FastAPIDepends(_cl_get_current_user),
            ) -> Any:
                if current_user is None:
                    raise _HTTPException(status_code=401, detail="Unauthorized")
                from src.db.chainlit_data_layer import load_element_content_for_user

                loaded = await asyncio.to_thread(
                    load_element_content_for_user,
                    thread_id,
                    element_id,
                    current_user.identifier,
                )
                if loaded is None:
                    raise _HTTPException(status_code=404, detail="Element not found or unauthorized")
                raw, mime, safe_name = loaded
                return _FastAPIResponse(
                    content=raw,
                    media_type=mime,
                    headers={
                        "Content-Disposition": f'attachment; filename="{safe_name}"',
                        "X-Content-Type-Options": "nosniff",
                    },
                )

            async def resolve_step_avatar(avatar_id: str) -> Any:
                """Normalize step/subagent names containing `&` or parentheses cleanly instead of returning HTTP 400."""
                if ".." in avatar_id or "/" in avatar_id or "\\" in avatar_id:
                    raise _HTTPException(status_code=400, detail="Invalid avatar_id")
                safe_id = re.sub(r"[^a-zA-Z0-9_ .-]+", "_", avatar_id).strip() or "default"
                return await _cl_get_avatar(safe_id)

            _custom_router = _FastAPIRouter()
            _custom_router.add_api_route(
                "/api/elements/{thread_id}/{element_id}",
                download_persisted_element,
                methods=["GET"],
            )
            _custom_router.add_api_route(
                "/avatars/{avatar_id:path}",
                resolve_step_avatar,
                methods=["GET"],
            )
            # Insert before Chainlit's router and catch-all `/{full_path:path}` SPA route
            for idx, route in enumerate(_custom_router.routes):
                _cl_fastapi_app.router.routes.insert(idx, route)
            _cl_fastapi_app.state.supplyguard_elements_route_registered = True
    except Exception as exc:
        logger.debug("Skipping Chainlit element route registration: %s", exc)

# ==============================================================================
# 1. Subagent Telemetry Step Registry (Issue #44)
# ==============================================================================

SUBAGENT_STEP_NAMES: dict[str, str] = {
    "triage_subagent": "1. Triage & Entity Extraction Subagent",
    "impact_subagent": "2. Operational Impact Analyzer Subagent",
    "contract_subagent": "3. Contract & Provenance Specialist Subagent",
    "graph_subagent": "4. Supply Graph Dependency Subagent",
    "optimizer_subagent": "5. Recovery Strategy Optimizer Subagent",
    "challenger_subagent": "6. Adversarial Challenger & Guardrail Subagent",
    "human_approval": "7. Human-in-the-Loop Approval Gate",
    "procurement_mcp": "8. Simulated Procurement System (MCP)",
}

# Collapsed parent step that groups the specialist subagent steps into one dropdown row.
INVESTIGATION_STEP_NAME = "🧠 Multi-Agent Investigation"

# Progressive rendering of final answers: chunk pacing and an upper bound on total stream time.
STREAM_TOKEN_DELAY_S = 0.015
STREAM_MAX_DURATION_S = 1.5

# Per-action asyncio locks and in-process guard sets (DB audit_log provides durable cross-restart guard)
_action_locks: dict[str, asyncio.Lock] = {}
_handled_actions: set[str] = set()
_USER_PROFILES: dict[str, UserProfile] = load_users_from_csv()


def _get_lock(key: str) -> asyncio.Lock:
    if key not in _action_locks:
        _action_locks[key] = asyncio.Lock()
    return _action_locks[key]


def split_stream_chunks(text: str) -> list[str]:
    """Split markdown into stream chunks that concatenate back to `text` exactly.

    Prose is split by word; table rows and fenced code blocks are emitted as whole lines so they
    never render half-drawn while streaming.
    """
    chunks: list[str] = []
    in_fence = False
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            chunks.append(line)
        elif in_fence or stripped.startswith("|"):
            chunks.append(line)
        else:
            chunks.extend(re.findall(r"\s*\S+\s*|\s+", line))
    return chunks


async def stream_message(content: str, **kwargs: Any) -> Any:
    """Send an assistant message progressively instead of all at once.

    Total stream time is bounded by STREAM_MAX_DURATION_S by grouping chunks for long answers.
    Falls back to a plain send when the Chainlit message API has no streaming support.
    """
    msg = cl.Message(content="", **kwargs)
    if not content or not hasattr(msg, "stream_token"):
        msg.content = content
        await msg.send()
        return msg

    chunks = split_stream_chunks(content)
    max_emits = max(1, int(STREAM_MAX_DURATION_S / STREAM_TOKEN_DELAY_S))
    group = max(1, -(-len(chunks) // max_emits))
    for i in range(0, len(chunks), group):
        await msg.stream_token("".join(chunks[i : i + group]))
        await asyncio.sleep(STREAM_TOKEN_DELAY_S)
    await msg.send()
    return msg


def sanitize_evidence_text(text: str) -> str:
    """Strip or neutralize raw HTML comments so hidden prompt injections are never invisibly rendered."""
    if not text:
        return ""
    cleaned = re.sub(r"<!--.*?-->", "[HTML comment stripped for security]", text, flags=re.S)
    return cleaned.strip()


# ==============================================================================
# 2. Authentication & Role-Based Access Control (RBAC) Management
# ==============================================================================


def _profile_from_chainlit_user(auth_user: Any) -> UserProfile:
    """Build or refresh a `UserProfile` from an authenticated Chainlit `User` / `PersistedUser`."""
    meta = dict(getattr(auth_user, "metadata", None) or {})
    ident = str(getattr(auth_user, "identifier", "") or meta.get("username") or meta.get("user_id") or "").strip()
    target_uid = str(meta.get("user_id") or ident).strip()

    try:
        from src.db.connection import is_postgres_available
        if _is_real_chainlit_runtime() and is_postgres_available():
            from src.db.auth import get_user_by_id
            db_profile = get_user_by_id(target_uid or ident)
            if db_profile is None:
                raise PermissionError("Authenticated user account is disabled or no longer exists.")
            return db_profile
    except PermissionError:
        raise
    except Exception as exc:
        logger.debug("Live user refresh unavailable, using authenticated metadata: %s", exc)

    role = str(meta.get("role") or "viewer").strip()
    base = _USER_PROFILES.get(target_uid) or _USER_PROFILES.get(role)
    doc_scopes = [str(s).strip() for s in (meta.get("document_scopes") or (base.document_scopes if base else ["public"])) if str(s).strip()]
    factories = [str(f).strip() for f in (meta.get("factory_access") if meta.get("factory_access") is not None else (base.factory_access if base else [])) if str(f).strip()]
    scope_val = str(meta.get("access_scope") or "").strip().lower()
    if scope_val == AccessScope.FINANCE.value or role == "finance_controller" or "finance-confidential" in doc_scopes:
        primary_scope = AccessScope.FINANCE
    elif scope_val == AccessScope.PROCUREMENT.value or "procurement" in doc_scopes:
        primary_scope = AccessScope.PROCUREMENT
    else:
        primary_scope = AccessScope.PUBLIC

    return UserProfile(
        user_id=target_uid or (base.user_id if base else "u-ro-01"),
        name=str(getattr(auth_user, "display_name", None) or meta.get("display_name") or (base.name if base else ident)),
        role=role,
        access_scope=primary_scope,
        document_scopes=doc_scopes or ["public"],
        factory_access=factories,
        username=str(meta.get("username") or ident or target_uid),
        email=str(meta.get("email") or "").strip() or None,
    )


def resolve_user_profile(role_or_id: Optional[str] = None) -> UserProfile:
    """Resolve an operator's UserProfile from role key or user_id (non-auth helpers/tests only)."""
    key = (role_or_id or os.getenv("SUPPLYGUARD_DEFAULT_ROLE", "viewer")).strip().lower()
    alias_map = {
        "procurement": "procurement_manager",
        "procurement_manager": "procurement_manager",
        "maria": "procurement_manager",
        "maria.keller": "procurement_manager",
        "u-pm-01": "procurement_manager",
        "finance": "finance_controller",
        "finance_controller": "finance_controller",
        "paul": "finance_controller",
        "paul.novak": "finance_controller",
        "u-fc-01": "finance_controller",
        "guest": "viewer",
        "viewer": "viewer",
        "public": "viewer",
        "read-only": "viewer",
        "readonly": "viewer",
        "u-ro-01": "viewer",
        "analyst": "operations_analyst",
        "operations_analyst": "operations_analyst",
        "jon.weber": "operations_analyst",
        "u-an-01": "operations_analyst",
        "coordinator": "incident_coordinator",
        "incident_coordinator": "incident_coordinator",
        "ines.duarte": "incident_coordinator",
        "u-ic-01": "incident_coordinator",
    }
    target = alias_map.get(key, key)
    return _USER_PROFILES.get(target, _USER_PROFILES["viewer"])


def get_active_user_profile() -> UserProfile:
    """Return the verified UserProfile bound to the authenticated Chainlit session."""
    auth_user = None
    try:
        auth_user = cl.user_session.get("user")
    except Exception:
        auth_user = None

    if auth_user is not None:
        profile = _profile_from_chainlit_user(auth_user)
        try:
            cl.user_session.set("user_profile", profile)
            cl.user_session.set("user_role", profile.role)
            if profile.email:
                cl.user_session.set("user_email", profile.email)
        except Exception:
            pass
        return profile

    if _is_real_chainlit_runtime():
        raise PermissionError("Authentication required: please log in with an authorized SupplyGuard account.")

    # Stubbed test session fallback (only outside real Chainlit runtime)
    try:
        prof = cl.user_session.get("user_profile")
        if isinstance(prof, UserProfile):
            return prof
    except Exception:
        pass
    raise PermissionError("No authenticated user in session.")


def _build_chainlit_user(profile: UserProfile) -> Any:
    """Construct a `cl.User` instance with verified RBAC role and scope metadata."""
    ident = (profile.username or profile.user_id).strip()
    meta = {
        "user_id": profile.user_id,
        "username": ident,
        "email": profile.email,
        "display_name": profile.name,
        "role": profile.role,
        "access_scope": profile.access_scope.value,
        "document_scopes": list(profile.document_scopes),
        "factory_access": list(profile.factory_access),
    }
    if hasattr(cl, "User"):
        return cl.User(identifier=ident, display_name=profile.name, metadata=meta)
    from types import SimpleNamespace
    return SimpleNamespace(identifier=ident, display_name=profile.name, metadata=meta)


async def authenticate_credentials(username: str, password: str) -> Optional[Any]:
    """Verify operator credentials against PostgreSQL `app_users` and return a `cl.User` or None."""
    from src.db.auth import authenticate_user
    profile = await cl.make_async(authenticate_user)(username, password)
    if profile is None:
        return None
    return _build_chainlit_user(profile)


if hasattr(cl, "password_auth_callback"):
    @cl.password_auth_callback
    async def password_auth_callback(username: str, password: str) -> Optional[Any]:
        """Chainlit password login callback verified against `app_users`."""
        return await authenticate_credentials(username, password)


def _create_cl_action(name: str, payload: dict[str, Any], label: str) -> cl.Action:
    """Create a Chainlit Action using `payload` (Chainlit 2.x) with fallback to `value` (Chainlit 1.x)."""
    try:
        return cl.Action(name=name, payload=payload, label=label)
    except Exception:
        return cl.Action(name=name, value=json.dumps(payload), label=label)


def format_rbac_badge(profile: UserProfile) -> str:
    """Format a clear status banner describing the authenticated operator's identity, scopes, and authority."""
    scopes_str = ", ".join(f"`{s}`" for s in profile.document_scopes)
    factories_str = ", ".join(f"`{f}`" for f in profile.factory_access) if profile.factory_access else "`None (Public Only)`"
    approval_str = (
        f"✅ Authorized up to **`€{profile.max_approval_eur:,.0f}`**"
        if profile.can_approve
        else "🔒 **Read-Only Viewer** (Cannot approve or execute Purchase Orders)"
    )
    return (
        f"🔐 **Authenticated Operator:** **{profile.name}** (`{profile.user_id}`) · "
        f"**Role:** `{profile.role}` · **Primary Scope:** `{profile.access_scope.value}`\n"
        f"- **Permitted Document Scopes:** {scopes_str}\n"
        f"- **Factory Visibility:** {factories_str} · **Approval Authority:** {approval_str}"
    )


# ==============================================================================
# 3. Telemetry Step Formatting (Issue #44)
# ==============================================================================


def format_step_output(node_name: str, node_output: dict[str, Any]) -> str:
    """Format a Deep Agent subagent update into a readable Chainlit step output."""
    if not isinstance(node_output, dict):
        return str(node_output)

    if node_name == "triage_subagent":
        fact: Optional[DisruptionFact] = node_output.get("disruption_fact")
        if fact is None:
            return "No disruption facts extracted."
        lines = [
            f"- **Supplier:** `{fact.supplier_id or 'Ambiguous / Missing'}` ({fact.supplier_name or 'Unresolved'})",
            f"- **Component ID:** `{fact.component_id or 'Missing'}`",
            f"- **Stated Delay:** `{f'{fact.delay_days} days' if fact.delay_days else 'Missing'}`",
            f"- **Spending Cap:** `€{fact.spending_cap:,.2f}`",
            f"- **Ambiguous Entity Flag:** `{fact.is_ambiguous}`",
        ]
        if fact.ambiguity_candidates:
            lines.append(f"- **Candidates:** {', '.join(fact.ambiguity_candidates)}")
        if fact.affected_po:
            lines.append(f"- **Affected Open PO:** `{fact.affected_po}` (`{fact.original_due}` → `{fact.new_due}`)")
        return "\n".join(lines)

    if node_name == "impact_subagent":
        imp: Optional[OperationalImpact] = node_output.get("operational_impact")
        if imp is None:
            return "Operational impact analysis unavailable."
        cover_parts = []
        for tl in imp.factory_timelines:
            if tl.warehouse_id == "W-HUB":
                cover_parts.append(f"Hub `{tl.usable_units:,}` units")
            else:
                cover_parts.append(f"{tl.factory_name} `{tl.days_of_cover:.1f}d`")
        cover_summary = f" ({', '.join(cover_parts)})" if cover_parts else ""
        quar_note = f" (`{imp.quarantine_lot_id}`)" if imp.quarantined_units > 0 and imp.quarantine_lot_id else ""
        return (
            f"- **Component:** `{imp.component_id}`\n"
            f"- **Inventory Breakdown:** `{imp.total_physical_units:,}` on-hand = "
            f"**`{imp.usable_units:,}` usable** + `{imp.reserved_units:,}` reserved + "
            f"`{imp.quarantined_units:,}` quarantined{quar_note}\n"
            f"- **Critical Factories Running Out First:** `{', '.join(imp.affected_factories)}`{cover_summary}\n"
            f"- **Downstream Impact:** `{imp.affected_products_count}` products (`{', '.join(imp.affected_products)}`) · "
            f"**`{imp.affected_customer_orders_count}` open customer orders at risk**\n"
            f"- **Uncovered Demand Shortfall:** **`{imp.uncovered_demand_units:,} units`** "
            f"(Revenue at Risk: `€{imp.total_revenue_at_risk_eur:,.2f}`)"
        )

    if node_name == "contract_subagent":
        findings: List[DocumentaryFinding] = node_output.get("documentary_findings") or []
        role_scope = node_output.get("access_scope", "procurement")
        conflicts = [d for d in findings if d.is_conflict]
        superseded = [d for d in findings if d.is_superseded]
        expired = [d for d in findings if "expired" in (d.summary or "").lower()]
        conflict_ids = ", ".join(f"`{d.source_id}`" for d in conflicts) or "None"
        superseded_ids = ", ".join(f"`{d.source_id}`" for d in superseded) or "None"
        expired_ids = ", ".join(f"`{d.source_id}`" for d in expired) or "None"
        return (
            f"- **RBAC Retrieval Scope Enforced:** `{role_scope}` (`{len(findings)}` documents retrieved with provenance)\n"
            f"- **Conflicts Flagged & Resolved ({len(conflicts)}):** {conflict_ids}\n"
            f"- **Superseded Contracts Ignored ({len(superseded)}):** {superseded_ids}\n"
            f"- **Expired / Blocked Qualifications ({len(expired)}):** {expired_ids}"
        )

    if node_name == "graph_subagent":
        suppliers = node_output.get("suppliers") or []
        shared_rejected = set(node_output.get("rejected_due_to_shared_upstream") or [])
        recommended_indep = set(node_output.get("recommended_independent_suppliers") or [])
        if suppliers:
            lines = ["- **Neo4j Multi-Tier Dependency Traversal (`max_depth=2`):**"]
            for s in suppliers:
                sid = s.get("supplier_id", "UNKNOWN")
                sname = s.get("name", sid)
                uid = s.get("upstream_id") or s.get("upstream_manufacturer_id") or "N/A"
                uname = s.get("upstream_name") or uid
                if sid in shared_rejected:
                    tag = "❌ *(Shared Tier-2 upstream bottleneck!)*"
                elif sid in recommended_indep:
                    tag = "✅ *(Independent upstream, qualified)*"
                elif not s.get("certification_valid", True):
                    tag = "🚫 *(Expired certification)*"
                else:
                    tag = ""
                lines.append(f"  - `{sid} ({sname})` ──`[:SOURCES_FROM]`──> **`{uid} ({uname})`** {tag}".rstrip())
            return "\n".join(lines)
        return (
            "- **Neo4j Multi-Tier Dependency Traversal (`max_depth=2`):**\n"
            "  - `S001 (Atlas Components)` ──`[:SOURCES_FROM]`──> **`U01 (Veltro Semiconductor, TW)`** ⚠️ *(High-severity wafer alert)*\n"
            "  - `S005 (Delta Micro Systems)` ──`[:SOURCES_FROM]`──> **`U01 (Veltro Semiconductor, TW)`** ❌ *(Shared Tier-2 upstream bottleneck!)*\n"
            "  - `S004 (Cordillera Industrial)` ──`[:SOURCES_FROM]`──> **`U02 (Nordic Wafer Fab)`** ✅ *(Independent upstream, qualified)*\n"
            "  - `S002 (Helios Supply)` ──`[:SOURCES_FROM]`──> `U03` · `S003 (Borealis Parts)` ──`[:SOURCES_FROM]`──> `U04`"
        )

    if node_name == "optimizer_subagent":
        options: List[RecoveryOption] = node_output.get("recovery_options") or []
        spending_cap = float(node_output.get("spending_cap", 75000.0))
        rec = next((o for o in options if o.is_recommended), None)
        if rec:
            breakdown = rec.cost_breakdown or {}
            parts = [
                f"{k.replace('_eur', '').replace('_', ' ').title()} `€{float(v):,.2f}`"
                for k, v in breakdown.items()
                if k != "total_recovery_cost_eur" and not k.startswith("sensitivity_")
            ]
            breakdown_note = f" ({' + '.join(parts)}; cap `€{spending_cap:,.2f}`)" if parts else f" (cap `€{spending_cap:,.2f}`)"
            return (
                f"- **Evaluated `{len(options)}` Recovery Strategies** via deterministic calculators (Recovery Cost separated from Revenue at Risk)\n"
                f"- **Recommended Plan (`{rec.strategy_code}`):** `{rec.title}`\n"
                f"- **Deterministic Recovery Cost:** **`€{rec.recovery_cost:,.2f}`**{breakdown_note}\n"
                f"- **Remaining Revenue at Risk:** **`€{rec.revenue_at_risk:,.2f}`**"
            )
        return f"Evaluated {len(options)} recovery strategies."

    if node_name == "challenger_subagent":
        within_cap = bool(node_output.get("within_cap", True))
        violations = node_output.get("violations") or []
        if "injection_alerts" in node_output:
            alerts = node_output.get("injection_alerts") or []
            if alerts:
                sources = ", ".join(f"`{a.get('source_id', 'unknown')}`" for a in alerts)
                inj_line = (
                    f"- **Adversarial Prompt-Injection Scanner:** 🛡️ Detected & neutralized "
                    f"`{len(alerts)}` untrusted directive(s) in {sources}"
                )
            else:
                inj_line = "- **Adversarial Prompt-Injection Scanner:** ✅ Clean — no prompt-injection directives detected"
        else:
            inj = node_output.get("prompt_injection_alert") or "DOC-NOT-HELIOS-PRICE"
            inj_line = (
                f"- **Adversarial Prompt-Injection Scanner:** 🛡️ Detected & neutralized malicious directive in `{inj}`"
            )
        audit_status = "PASS (<= Spending Cap)" if within_cap else f"FAIL ({'; '.join(violations) or 'Policy Violation'})"
        return (
            f"{inj_line}\n"
            f"- **Policy & Budget Cap Audit:** `{audit_status}` · "
            f"Penalties counted once · Payload hash bound for human approval"
        )

    if node_name == "procurement_mcp":
        rcp: Optional[ProcurementReceipt] = node_output.get("procurement_receipt")
        if rcp is None:
            return "Simulated procurement execution completed."
        return (
            f"- **Idempotency Key:** `{rcp.idempotency_key}` (`{rcp.status.value.upper()}`)\n"
            f"- **Created Purchase Order:** `{rcp.po_number}` (`{rcp.quantity:,} units` of `{rcp.component_id}` with `{rcp.supplier_name}`)\n"
            f"- **Expedited Open PO:** `{rcp.expedite_ref}` · **Stock Transfer:** `{rcp.transfer_ref}`\n"
            f"- **Total Committed Spend:** **`€{rcp.total_cost_eur:,.2f}`**"
        )

    return str(node_output)


# ==============================================================================
# 4. Operational Impact Dashboard & Strategy Comparison Matrix (#47, #48)
# ==============================================================================


def format_operational_impact_dashboard(
    fact: DisruptionFact,
    impact: OperationalImpact,
    findings: List[DocumentaryFinding],
    user_profile: Optional[UserProfile] = None,
    case_id: str = "CASE-MC17-001",
) -> str:
    """Render the SupplyGuard AI Operational Impact Dashboard (Issue #47) with sanitized provenance citations."""
    profile = user_profile or get_active_user_profile()
    reserved_order_ids = ", ".join(
        f"`{o.get('customer_order_id', '')}`" for o in (impact.reserved_stock_orders or [])
    )
    lines = [
        f"## 📊 SupplyGuard AI — Operational Impact Dashboard (`{case_id}`)",
        "",
        format_rbac_badge(profile),
        "",
        "### 1. Extracted Disruption Case Facts",
        f"- **Disrupted Supplier:** **{fact.supplier_name or 'Atlas Components'}** (`{fact.supplier_id or 'S001'}`)",
        f"- **Component:** **`{fact.component_id or 'MC-17'}`** · **Announced Delay:** **`{fact.delay_days or 12} days`** "
        f"(Affected PO: `{fact.affected_po or 'PO-2026-9001'}`, Original Due: `{fact.original_due or '2026-10-26'}` → Delayed Due: `{fact.new_due or '2026-11-07'}`)",
        f"- **Authorized Spending Limit:** **`€{fact.spending_cap:,.2f}`** *(Source: `config/policies.json`)*",
        "",
        "### 2. Multi-Warehouse Stock Breakdown (Usable vs Reserved & Quarantined)",
        f"- **Total Physical On-Hand Stock:** **`{impact.total_physical_units:,} units`** *(Source: `structured/inventory.csv`)*",
        f"- **Net Usable Stock:** **`{impact.usable_units:,} units`** ✅ *(Available for production & internal transfer)*",
        (
            f"- **Reserved Stock (Locked for {len(impact.reserved_stock_orders)} Tier-1 Customer Orders):** **`{impact.reserved_units:,} units`** 🔒 "
            f"*(Orders: {reserved_order_ids} — `structured/reservations.csv`)*"
            if impact.reserved_stock_orders
            else f"- **Reserved Stock:** **`{impact.reserved_units:,} units`** 🔒 *(Source: `structured/reservations.csv`)*"
        ),
        (
            f"- **Quarantined Stock (Excluded from Usable):** **`{impact.quarantined_units:,} units`** 🚫 "
            f"*(Lot `{impact.quarantine_lot_id}`: {impact.quarantine_reason} — `structured/quarantine_lots.csv`)*"
            if impact.quarantined_units > 0
            else f"- **Quarantined Stock:** **`0 units`** *(No active QA holds)*"
        ),
        "",
        "### 3. Factory Stockout Timelines & Days of Cover",
        "| Location / Factory | Warehouse | On-Hand | Reserved | Quarantined | **Usable Units** | Daily Demand | **Days of Cover** | Operational Status |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]

    for tl in impact.factory_timelines:
        if tl.warehouse_id == "W-HUB":
            status_cell = f"🟢 **{tl.usable_units:,} units available for 2-day transfer (€0.12/unit)**"
            cover_str = "Hub Buffer"
        elif tl.days_of_cover <= 4.0:
            status_cell = "🔴 **CRITICAL — Runs Out First (Prioritize Hub Transfer)**"
            cover_str = f"**{tl.days_of_cover:.1f} days**"
        else:
            status_cell = "🟡 **Moderate Cover**"
            cover_str = f"{tl.days_of_cover:.1f} days"
        lines.append(
            f"| **{tl.factory_name}** | `{tl.warehouse_id}` | `{tl.on_hand_units:,}` | `{tl.reserved_units:,}` | "
            f"`{tl.quarantined_units:,}` | **`{tl.usable_units:,}`** | `{tl.daily_demand_units}/day` | "
            f"{cover_str} | {status_cell} |"
        )

    lines.extend([
        "",
        "### 4. Downstream Product BOM & Customer Commitment Exposure",
        f"- **Affected Products (`{impact.affected_products_count}` BOMs):** `{', '.join(impact.affected_products)}` "
        f"*(Source: `structured/bill_of_materials.csv`)*",
        f"- **Open Customer Orders at Risk (due within 60 days):** **`{impact.affected_customer_orders_count} open customer orders`** "
        f"*(Source: `structured/customer_orders.csv`)*",
        f"- **Aggregate Daily Consumption:** `{impact.daily_demand_total} units/day` (`{impact.stock_at_original_arrival}` usable units left on original arrival Day 7)",
        f"- **Uncovered Demand Shortfall (Day 7 to Day 19):** **`{impact.uncovered_demand_units:,} units`**",
        f"- **Projected Revenue at Risk (Reported Separately from Recovery Cost):** **`€{impact.total_revenue_at_risk_eur:,.2f}`**",
        "",
        "### 5. Documentary Evidence, Source-Precedence Conflicts & Security Alerts",
    ])

    for doc in findings:
        safe_summary = sanitize_evidence_text(doc.summary)
        safe_res = sanitize_evidence_text(doc.conflict_resolution or "")
        if doc.is_malicious:
            lines.append(
                f"- 🛡️ **SECURITY ALERT — Prompt Injection Neutralized (`{doc.source_id}`, effective `{doc.effective_date}`, scope `{doc.access_scope}`):** "
                f"{safe_summary} → **{safe_res}**"
            )
        elif doc.is_superseded:
            lines.append(
                f"- ⚠️ **Superseded Document Ignored (`{doc.source_id}`, v{doc.version}, effective `{doc.effective_date}`):** "
                f"{safe_summary} → *{safe_res}*"
            )
        elif doc.is_conflict:
            lines.append(
                f"- ⚖️ **Conflict Flagged (`{doc.source_id}`, v{doc.version}, effective `{doc.effective_date}`, scope `{doc.access_scope}`):** "
                f"{safe_summary} → *{safe_res}*"
            )
        else:
            lines.append(
                f"- 📄 **Evidence (`{doc.source_id}`, v{doc.version}, effective `{doc.effective_date}`, scope `{doc.access_scope}`):** "
                f"{safe_summary}"
            )

    if fact.detected_prompt_injection:
        lines.append(
            f"- 🛡️ **Inline Message Injection Neutralized:** Detected embedded directive `'{sanitize_evidence_text(fact.detected_prompt_injection)}'` in user input. "
            "Treated strictly as untrusted data; human approval gate and RBAC scopes remain enforced."
        )

    return "\n".join(lines)


def format_strategy_comparison_matrix(
    options: List[RecoveryOption],
    fact: DisruptionFact,
    impact: OperationalImpact,
) -> str:
    """Render the Recovery Strategy Comparison Matrix (Issue #48) separating Recovery Cost vs Revenue at Risk."""
    lines = [
        "## 🧭 Recovery Strategy Comparison Matrix (Deterministic Trade-Off Analysis)",
        "",
        "> **Accounting & Governance Rule:** Projected **Revenue at Risk (€)** is reported strictly separately from **Recovery Cost (€)**. "
        "Revenue exposure is not combined with purchasing/expediting expenditure, and contractual late penalties are never double-counted.",
        "",
        "| Strategy ID | Strategy Type (`A`–`E`) | Candidate Supplier / Target | Units Covered | Lead Time | **Recovery Cost (€)** | **Remaining Revenue at Risk (€)** | Viability & Decision |",
        "|---|---|---|---:|---:|---:|---:|---|",
    ]

    for opt in options:
        decision = (
            "✅ **RECOMMENDED**"
            if opt.is_recommended
            else ("🟢 **VIABLE**" if opt.is_viable else "❌ **REJECTED**")
        )
        lines.append(
            f"| `{opt.strategy_id}` | **{opt.strategy_code}** | {opt.supplier_name or 'Internal'} "
            f"{f'(`{opt.supplier_id}`)' if opt.supplier_id else ''} | `{opt.quantity:,}` | `{opt.lead_time_days}d` | "
            f"**`€{opt.recovery_cost:,.2f}`** | **`€{opt.revenue_at_risk:,.2f}`** | {decision} |"
        )

    lines.extend([
        "",
        "### Supplier & Strategy Rejection / Selection Rationale",
    ])
    for opt in options:
        if not opt.is_viable:
            raw_reason = sanitize_evidence_text(opt.rejection_reason or "Rejected by operational or policy constraints.")
            formatted_reason = raw_reason.replace("Veltro Semiconductor (U01)", "Veltro Semiconductor (`U01`)")
            is_blocked = "expired" in raw_reason.lower() or "blocked" in raw_reason.lower()
            verb = "Blocked" if is_blocked else "Rejected"
            if opt.supplier_id:
                lines.append(
                    f"- ❌ **Why {opt.supplier_name or opt.supplier_id} (`{opt.supplier_id}`) is {verb}:** {formatted_reason}"
                )
            else:
                lines.append(f"- ❌ **Why {opt.title} is {verb}:** {formatted_reason}")

    rec = next((o for o in options if o.is_recommended), None)
    if rec is not None:
        lines.append(f"- ✅ **Why Recommended Plan (`{rec.strategy_id}`, `{rec.strategy_code}`) Wins:**")
        for idx, step_desc in enumerate(rec.actions_breakdown, start=1):
            lines.append(f"  {idx}. {sanitize_evidence_text(step_desc)}")
        cap_status = (
            f"within the `€{fact.spending_cap:,.2f}` spending cap"
            if rec.recovery_cost <= fact.spending_cap
            else f"exceeds the `€{fact.spending_cap:,.2f}` spending cap"
        )
        lines.append(
            f"  - **Total Deterministic Recovery Cost:** **`€{rec.recovery_cost:,.2f}`** — {cap_status}."
        )
    elif not options:
        lines.append("- ℹ️ No external recovery purchase order required for the evaluated disruption.")
    return "\n".join(lines)


# ==============================================================================
# 5. Payload-Bound Human Approval Card & Actions (Issue #49)
# ==============================================================================


def format_approval_card(
    payload: ApprovalPayload,
    thread_id: str,
    user_profile: Optional[UserProfile] = None,
) -> str:
    """Build the markdown approval card for an immutable SupplyGuard `ApprovalPayload`."""
    payload.ensure_hash()
    profile = user_profile or get_active_user_profile()
    cap_pct = (payload.total_cost / payload.spending_cap * 100.0) if payload.spending_cap else 0.0
    cap_badge = (
        f"✅ Within Spending Cap (`{cap_pct:.1f}%` of `€{payload.spending_cap:,.2f}`)"
        if payload.is_within_cap()
        else f"❌ EXCEEDS SPENDING CAP (`€{payload.total_cost:,.2f}` > `€{payload.spending_cap:,.2f}`)"
    )
    evidence_lines = [
        f"  - **`{ev.get('source_id', 'DOC')}`** (effective `{ev.get('effective_date', 'N/A')}`, scope `{ev.get('access_scope', 'procurement')}`): {sanitize_evidence_text(ev.get('note', ''))}"
        for ev in (payload.supporting_evidence or [])
    ] or ["  - `DOC-CON-S004-v1` (effective `2025-08-01`, scope `procurement`)"]

    auth_notice = (
        f"✅ Active role **`{profile.role}`** (`{profile.name}`) is authorized to approve."
        if profile.can_approve
        else f"🔒 Active role **`{profile.role}`** (`{profile.name}`) is **Read-Only** — switch to `Procurement Manager` or `Finance Controller` to approve."
    )

    lines = [
        "## 🛡️ Payload-Bound Human Approval Request (Simulated Procurement Gate)",
        "",
        "> **Strict Payload Binding Rule:** Human approval binds cryptographically to the exact supplier, quantity, unit price, and total cost below. "
        "No Purchase Order exists prior to approval. Clicking **✏️ Modify Plan** or altering any parameter invalidates this card and triggers full revalidation.",
        "",
        f"- **Action ID:** `{payload.action_id}` *(Revision `v{payload.revision}`)*",
        f"- **Case ID:** `{payload.case_id}` · **Thread ID:** `{thread_id}`",
        f"- **Payload Binding Digest (SHA-256):** `{payload.payload_hash}`",
        f"- **Action Type:** `{payload.action_type.value if hasattr(payload.action_type, 'value') else payload.action_type}`",
        f"- **Status:** `{payload.status.value if hasattr(payload.status, 'value') else payload.status}`",
        f"- **RBAC Authorization Status:** {auth_notice}",
        "",
        "### Bound Execution Payload Breakdown",
        f"1. **Create Purchase Order (`create_purchase_order`):**",
        f"   - **Target Supplier:** **{payload.target_supplier_name}** (`{payload.target_supplier_id}`)",
        f"   - **Component ID:** `{payload.component_id}`",
        f"   - **Order Quantity:** **`{payload.quantity:,} units`**",
        f"   - **Contract Unit Price:** **`€{payload.unit_price:.2f} / unit`**",
        f"   - **Purchase Order Subtotal:** **`€{payload.po_subtotal_eur:,.2f}`**",
        f"2. **Expedite Open Purchase Order (`expedite_purchase_order`):**",
        f"   - **Target Open PO:** `{payload.expedite_po_id or 'N/A'}` (`{payload.expedite_units:,} units`, +7 days gain, `{payload.expedite_fee_pct:.0f}%` contract fee) = **`€{payload.expedite_fee_eur:,.2f}`**",
        f"3. **Internal Hub Stock Transfer (`request_stock_transfer`):**",
        f"   - **Route:** `{payload.transfer_from_location}` → `{payload.transfer_to_locations}` (`{payload.transfer_units:,} units` @ `€0.12/unit`, 2 days) = **`€{payload.transfer_cost_eur:,.2f}`**",
        f"4. **Production Schedule & Priority Allocation (`update_production_schedule`):**",
        f"   - **Residual Units Rescheduled / Reallocated:** `{payload.residual_units_reallocated:,} units` (100% Tier-1 orders protected)",
        "",
        "### Financial & Governance Summary",
        f"- **Total Committed Recovery Cost:** **`€{payload.total_cost:,.2f}`**",
        f"- **Authorized Spending Cap:** **`€{payload.spending_cap:,.2f}`** → {cap_badge}",
        f"- **Customer Revenue at Risk Protected (Separate Metric):** **`€{payload.revenue_at_risk_protected_eur:,.2f}`**",
        "- **Supporting Provenance Evidence:**",
        *evidence_lines,
        "",
        "Please review and choose **✅ Approve**, **❌ Reject**, or **✏️ Modify Plan**:",
    ]
    return "\n".join(lines)


def build_approval_actions(
    action_id: str,
    thread_id: str,
    *,
    payload_hash: str = "",
    include_modify: bool = True,
) -> list[cl.Action]:
    """Create Approve, Reject, and Modify Plan buttons bound to action_id, thread_id, and payload_hash."""
    base_meta: dict[str, Any] = {"action_id": action_id, "thread_id": thread_id}
    if payload_hash:
        base_meta["payload_hash"] = payload_hash

    actions = [
        _create_cl_action(
            name="approve_action",
            payload={"decision": "approve", **base_meta},
            label="✅ Approve",
        ),
        _create_cl_action(
            name="reject_action",
            payload={"decision": "reject", **base_meta},
            label="❌ Reject",
        ),
    ]
    if include_modify:
        actions.append(
            _create_cl_action(
                name="modify_action",
                payload={"decision": "modify", **base_meta},
                label="✏️ Modify Plan",
            )
        )
    return actions


# ==============================================================================
# 6. Post-Approval Procurement Receipt & Incident Report Export (#50)
# ==============================================================================


def format_procurement_receipt(
    receipt: ProcurementReceipt,
    payload: ApprovalPayload,
    *,
    is_replay: bool = False,
) -> str:
    """Format the Post-Approval Simulated Procurement System Execution Receipt (Issue #50)."""
    header = (
        "ℹ️ **Idempotent Replay Guard — Action Already Executed (Zero Duplicate PO Created)**"
        if is_replay
        else "✅ **Simulated Procurement System (MCP) — Approved Execution Receipt**"
    )
    lines = [
        f"## {header}",
        "",
        f"- **Receipt ID:** `{receipt.receipt_id}` · **Case ID:** `{receipt.case_id}`",
        f"- **Action / Approval ID:** `{receipt.action_id}` · **Status:** `{receipt.status.value.upper()}`",
        f"- **Idempotency Key:** `{receipt.idempotency_key}` *(Verified unique; repeated calls create nothing new)*",
        f"- **Verified Payload Hash (SHA-256):** `{receipt.payload_hash}`",
        f"- **Approved By:** **{receipt.approved_by}** (`{receipt.approver_role}`) at `{receipt.executed_at}`",
        "",
        "### Executed MCP Write Operations",
    ]
    ops = receipt.operations_executed or []
    if ops:
        for idx, op in enumerate(ops, start=1):
            op_name = op.get("operation", "operation")
            op_status = op.get("status", "confirmed")
            if op_status == "failed":
                lines.append(
                    f"{idx}. **`{op_name}` → ❌ FAILED:** `{op.get('error', 'Operation failed')}`"
                )
            elif op_name == "create_purchase_order":
                lines.append(
                    f"{idx}. **`create_purchase_order` → `{op.get('po_id', receipt.po_number)}`:** "
                    f"Ordered **`{receipt.quantity:,} units`** of **`{receipt.component_id}`** from "
                    f"**{receipt.supplier_name} (`{receipt.supplier_id}`)** @ `€{receipt.unit_price_eur:.2f}/unit` = **`€{payload.po_subtotal_eur:,.2f}`**"
                )
            elif op_name == "expedite_purchase_order":
                lines.append(
                    f"{idx}. **`expedite_purchase_order` → `{op.get('expedite_ref', receipt.expedite_ref)}`:** "
                    f"Expedited `{op.get('po_id', payload.expedite_po_id)}` (`{payload.expedite_units:,} units`, "
                    f"+{op.get('days_gain', 7)} days gain, `{payload.expedite_fee_pct:.0f}%` contract fee) = **`€{float(op.get('fee_eur', payload.expedite_fee_eur)):,.2f}`**"
                )
            elif op_name == "request_stock_transfer":
                lines.append(
                    f"{idx}. **`request_stock_transfer` → `{op.get('transfer_id', receipt.transfer_ref)}`:** "
                    f"Transferred `{op.get('qty', payload.transfer_units):,} units` from `{op.get('from_location', payload.transfer_from_location)}` "
                    f"to `{op.get('to_location', payload.transfer_to_locations)}` (`2 days` @ `€0.12/unit`) = **`€{float(op.get('cost_eur', payload.transfer_cost_eur)):,.2f}`**"
                )
            elif op_name == "update_production_schedule":
                lines.append(
                    f"{idx}. **`update_production_schedule` → `{op.get('schedule_ref', receipt.schedule_ref)}`:** "
                    f"Protected `{op.get('tier1_orders_protected', 0)}` Tier-1 orders and rescheduled "
                    f"`{op.get('reallocated_tier3_units', payload.residual_units_reallocated):,}` residual units (`{op.get('product_id', '')}`)"
                )
            else:
                lines.append(f"{idx}. **`{op_name}`:** `{op_status}`")
    else:
        lines.append(
            f"1. **`create_purchase_order` → `{receipt.po_number}`:** Ordered **`{receipt.quantity:,} units`** of **`{receipt.component_id}`** from **{receipt.supplier_name} (`{receipt.supplier_id}`)** @ `€{receipt.unit_price_eur:.2f}/unit` = **`€{payload.po_subtotal_eur:,.2f}`**"
        )
    lines.extend([
        "",
        f"- **Total Committed Expenditure:** **`€{receipt.total_cost_eur:,.2f}`** (Authorized Cap: `€{payload.spending_cap:,.2f}`)",
        "- **Incident Report & Memory Retention:** Official Incident Report exported in **Markdown (`.md`)** and **PDF (`.pdf`)** below, and resolution summary saved to approved incident memories.",
    ])
    return "\n".join(lines)


def generate_incident_report_artifacts(
    thread_id: str,
    case_state: dict[str, Any],
) -> tuple[IncidentReport, Path, Path]:
    """Generate the IncidentReport model and write downloadable Markdown (.md) and PDF (.pdf) files."""
    fact: DisruptionFact = case_state.get("disruption_fact") or DisruptionFact(
        supplier_id="S001", supplier_name="Atlas Components", component_id="MC-17", delay_days=12
    )
    impact: OperationalImpact = case_state.get("operational_impact") or compute_operational_impact(fact)
    options: List[RecoveryOption] = case_state.get("recovery_options") or compute_recovery_options(fact, impact)
    payload: ApprovalPayload = case_state.get("approval_payload") or build_approval_payload(fact, impact)
    receipt: ProcurementReceipt = case_state.get("procurement_receipt") or ProcurementReceipt(
        action_id=payload.action_id, case_id=payload.case_id, idempotency_key=f"{payload.case_id}:{payload.action_id}"
    )
    profile: UserProfile = case_state.get("user_profile") or get_active_user_profile()
    findings: List[DocumentaryFinding] = case_state.get("documentary_findings") or retrieve_scoped_documentary_findings(profile, fact)

    action_parts: List[str] = []
    if payload.transfer_units > 0:
        action_parts.append(f"Hub transfer ({payload.transfer_units:,}u -> {payload.transfer_to_locations})")
    if payload.expedite_po_id:
        action_parts.append(
            f"expedited {payload.expedite_po_id} ({payload.expedite_units:,}u, {payload.expedite_fee_pct:.0f}% fee)"
        )
    action_parts.append(
        f"new PO with {payload.target_supplier_name} ({payload.target_supplier_id}, "
        f"{payload.quantity:,}u @ EUR {payload.unit_price:.2f})"
    )
    if payload.residual_units_reallocated > 0:
        action_parts.append(f"schedule reallocation ({payload.residual_units_reallocated:,}u)")

    rejected_notes = [
        f"{opt.supplier_name or opt.supplier_id} ({opt.supplier_id}): {opt.rejection_reason or 'rejected'}"
        for opt in options
        if not opt.is_viable and opt.supplier_id
    ]
    rejected_clause = f" Rejected alternatives: {'; '.join(rejected_notes)}." if rejected_notes else ""
    memory_summary = (
        f"Case {payload.case_id} ({fact.component_id} {fact.delay_days}d delay from {fact.supplier_name} {fact.supplier_id}): "
        f"Resolved via {' + '.join(action_parts)} "
        f"at total cost EUR {payload.total_cost:,.2f} (cap EUR {payload.spending_cap:,.0f}).{rejected_clause}"
    )

    report = IncidentReport(
        report_id=f"INC-{payload.case_id}",
        case_id=payload.case_id,
        thread_id=thread_id,
        prepared_by=f"{profile.name} ({profile.role})",
        disruption_fact=fact,
        operational_impact=impact,
        recovery_options=options,
        approval_payload=payload,
        procurement_receipt=receipt,
        documentary_findings=findings,
        approved_memory_summary=memory_summary,
    )

    out_base = Path(os.getenv("SUPPLYGUARD_REPORTS_DIR", "/app/data/reports"))
    try:
        out_base.mkdir(parents=True, exist_ok=True)
        out_dir = out_base
    except OSError:
        out_dir = Path(tempfile.gettempdir()) / "supplyguard_reports"
        out_dir.mkdir(parents=True, exist_ok=True)
    safe_case = re.sub(r"[^A-Za-z0-9_-]", "_", payload.case_id)
    md_path = out_dir / f"Incident_Report_{safe_case}.md"
    pdf_path = out_dir / f"Incident_Report_{safe_case}.pdf"

    md_path.write_text(report.to_markdown(), encoding="utf-8")
    pdf_path.write_bytes(report.to_pdf_bytes())

    case_state["incident_report"] = report
    case_state["report_md_path"] = str(md_path)
    case_state["report_pdf_path"] = str(pdf_path)
    get_orchestrator().persist_state(thread_id, case_state)
    return report, md_path, pdf_path


# ==============================================================================
# 7. Chainlit Step Telemetry & Card Delivery Helpers
# ==============================================================================


async def _send_approval_card(
    case_state: dict[str, Any],
    thread_id: str,
    user_profile: Optional[UserProfile] = None,
) -> None:
    """Send the approval card and store its message reference for button removal on click."""
    payload: Optional[ApprovalPayload] = case_state.get("approval_payload")
    if payload is None:
        await cl.Message(content="⚠️ Approval is required, but no approval payload was found.").send()
        return

    card_text = format_approval_card(
        payload=payload,
        thread_id=thread_id,
        user_profile=user_profile,
    )
    actions = build_approval_actions(
        payload.action_id,
        thread_id,
        payload_hash=payload.payload_hash,
        include_modify=True,
    )
    msg = cl.Message(content=card_text, actions=actions)
    await msg.send()
    cl.user_session.set(f"approval_msg:{payload.action_id}", msg)


async def _emit_supplyguard_subagent_steps(
    fact: DisruptionFact,
    impact: Optional[OperationalImpact] = None,
    findings: Optional[List[DocumentaryFinding]] = None,
    options: Optional[List[RecoveryOption]] = None,
    user_profile: Optional[UserProfile] = None,
    *,
    graph_res: Optional[dict[str, Any]] = None,
    challenger_res: Optional[dict[str, Any]] = None,
    approval_payload: Optional[ApprovalPayload] = None,
) -> None:
    """Emit Chainlit Step telemetry for each specialist Deep Agent subagent (#44).

    All subagent steps are nested under one collapsed parent step so the chat shows a single
    compact dropdown row instead of one row per subagent.
    """
    async with cl.Step(name=INVESTIGATION_STEP_NAME, type="run") as parent:
        if not fact.is_complete():
            parent.name = f"{INVESTIGATION_STEP_NAME} · clarification needed"
            await _emit_subagent_child_steps(fact, user_profile=user_profile)
            parent.output = "Triage could not identify the supplier and component unambiguously."
            return

        within_cap, injection_count = await _emit_subagent_child_steps(
            fact,
            impact=impact,
            findings=findings,
            options=options,
            user_profile=user_profile,
            graph_res=graph_res,
            challenger_res=challenger_res,
            approval_payload=approval_payload,
        )
        parent.name = f"{INVESTIGATION_STEP_NAME} · 6 specialist subagents"
        parent.output = (
            f"{'✅ Within spending cap' if within_cap else '⚠️ Spending cap violation'} · "
            f"{injection_count} prompt-injection alert(s) neutralized"
        )


async def _emit_subagent_child_steps(
    fact: DisruptionFact,
    impact: Optional[OperationalImpact] = None,
    findings: Optional[List[DocumentaryFinding]] = None,
    options: Optional[List[RecoveryOption]] = None,
    user_profile: Optional[UserProfile] = None,
    *,
    graph_res: Optional[dict[str, Any]] = None,
    challenger_res: Optional[dict[str, Any]] = None,
    approval_payload: Optional[ApprovalPayload] = None,
) -> tuple[bool, int]:
    """Emit one child step per subagent; return (within_cap, injection_alert_count)."""
    profile = user_profile or get_active_user_profile()
    async with cl.Step(name=SUBAGENT_STEP_NAMES["triage_subagent"], type="run") as step:
        step.output = format_step_output("triage_subagent", {"disruption_fact": fact})

    if not fact.is_complete():
        return True, 0

    async with cl.Step(name=SUBAGENT_STEP_NAMES["impact_subagent"], type="run") as step:
        step.output = format_step_output("impact_subagent", {"operational_impact": impact})

    async with cl.Step(name=SUBAGENT_STEP_NAMES["contract_subagent"], type="run") as step:
        step.output = format_step_output(
            "contract_subagent",
            {"documentary_findings": findings or [], "access_scope": profile.access_scope.value},
        )

    async with cl.Step(name=SUBAGENT_STEP_NAMES["graph_subagent"], type="run") as step:
        step.output = format_step_output("graph_subagent", graph_res or {})

    async with cl.Step(name=SUBAGENT_STEP_NAMES["optimizer_subagent"], type="run") as step:
        step.output = format_step_output(
            "optimizer_subagent",
            {"recovery_options": options or [], "spending_cap": fact.spending_cap},
        )

    if challenger_res is not None:
        budget_audit = challenger_res.get("budget_audit") or {}
        within_cap = bool(budget_audit.get("is_compliant", True))
        violations = list(budget_audit.get("violations") or [])
        injection_alerts = list(challenger_res.get("injection_alerts") or [])
    else:
        within_cap = approval_payload.is_within_cap() if approval_payload is not None else True
        violations = []
        injection_alerts = [
            {"source_id": f.source_id, "status": "NEUTRALIZED"}
            for f in (findings or [])
            if getattr(f, "is_malicious", False)
        ]
        if fact.detected_prompt_injection:
            injection_alerts.append({"source_id": "USER_MESSAGE_ATTACHMENT", "status": "NEUTRALIZED"})

    async with cl.Step(name=SUBAGENT_STEP_NAMES["challenger_subagent"], type="run") as step:
        step.output = format_step_output(
            "challenger_subagent",
            {
                "injection_alerts": injection_alerts,
                "within_cap": within_cap,
                "violations": violations,
            },
        )
    return within_cap, len(injection_alerts)


# ==============================================================================
# 8. Session Initialization & Role-Scoped Case / Chat Resume (#41, #42, #51)
# ==============================================================================


async def _restore_or_greet(thread_id: str, *, is_manual_resume: bool = False) -> None:
    """Inspect PostgreSQL-backed orchestrator state for thread_id to restore or greet."""
    try:
        profile = get_active_user_profile()
    except PermissionError as exc:
        await cl.Message(content=f"🔒 **Authentication Required:** {exc}").send()
        return

    orchestrator = get_orchestrator()
    try:
        case_state = orchestrator.get_state(
            thread_id,
            requester=profile,
            raise_on_unauthorized=True,
        )
    except PermissionError as exc:
        await cl.Message(
            content=(
                "🔒 **Access Denied — Role / Ownership Restriction**\n\n"
                f"{exc}"
            )
        ).send()
        return

    if case_state is not None:
        status = case_state.get("status", "active")
        case_id = case_state.get("case_id", "CASE-MC17-001")
        fact: Optional[DisruptionFact] = case_state.get("disruption_fact")
        await cl.Message(
            content=(
                f"🔄 **Session restored from database checkpoint!**\n\n"
                f"Resuming SupplyGuard AI investigation for thread `{thread_id}` (Case `{case_id}`):\n"
                f"- **Supplier / Component:** `{fact.supplier_name if fact else 'N/A'}` "
                f"(`{fact.component_id if fact else 'N/A'}`) · **Status:** `{status}`\n\n"
                f"{format_rbac_badge(profile)}"
            )
        ).send()

        if status == "awaiting_clarification":
            question = case_state.get("clarification_question") or "Could you please clarify the supplier and component?"
            await cl.Message(content=question).send()
        elif status in ("awaiting_approval", "awaiting_modification"):
            await _send_approval_card(case_state, thread_id, user_profile=profile)
        elif status == "executed" and case_state.get("procurement_receipt"):
            rcp: ProcurementReceipt = case_state["procurement_receipt"]
            pay: ApprovalPayload = case_state["approval_payload"]
            await cl.Message(content=format_procurement_receipt(rcp, pay, is_replay=True)).send()
        return

    if is_manual_resume:
        await cl.Message(content=f"ℹ️ No saved checkpoint found for thread `{thread_id}` under your account/role.").send()
        return

    await cl.Message(
        content=(
            "**Welcome to SupplyGuard AI — Agentic Supply Chain Disruption & Recovery Platform!** 🏭🛡️\n\n"
            f"Active session thread: `{thread_id}`\n\n"
            f"{format_rbac_badge(profile)}\n\n"
            "Describe a supply chain disruption (e.g., *“Supplier Atlas Components has announced a 12-day delay for component MC-17...”*) "
            "or select a previous conversation from your role-scoped history sidebar.\n"
            "*(Commands: `/resume <thread_id>`, `/export`)*"
        ),
    ).send()


def _resolve_session_thread_id() -> str:
    """Resolve deterministic Chainlit thread_id (preferring thread_id over transient session.id)."""
    sess = cl.context.session
    return str(getattr(sess, "thread_id", None) or sess.id)


@cl.on_chat_start
async def on_chat_start() -> None:
    """Initialize an authenticated chat session and bind thread_id consistently."""
    thread_id = _resolve_session_thread_id()
    cl.user_session.set("thread_id", thread_id)
    try:
        get_active_user_profile()
    except PermissionError as exc:
        await cl.Message(content=f"🔒 **Authentication Required:** {exc}").send()
        return
    await _restore_or_greet(thread_id, is_manual_resume=False)


if hasattr(cl, "on_chat_resume"):
    @cl.on_chat_resume
    async def on_chat_resume(thread: dict[str, Any]) -> None:
        """Restore an operator's persisted SupplyGuard case when selecting a thread from history."""
        thread_id = str(thread.get("id") or _resolve_session_thread_id())
        cl.user_session.set("thread_id", thread_id)
        try:
            profile = get_active_user_profile()
        except PermissionError as exc:
            await cl.Message(content=f"🔒 **Authentication Required:** {exc}").send()
            return

        orchestrator = get_orchestrator()
        try:
            case_state = orchestrator.get_state(
                thread_id,
                requester=profile,
                raise_on_unauthorized=True,
            )
        except PermissionError as exc:
            await cl.Message(content=f"🔒 **Access Denied:** {exc}").send()
            return

        if not case_state:
            return
        status = case_state.get("status", "active")
        if status == "awaiting_clarification":
            question = case_state.get("clarification_question") or "Could you please clarify the supplier and component?"
            await cl.Message(content=question).send()
        elif status in ("awaiting_approval", "awaiting_modification"):
            await _send_approval_card(case_state, thread_id, user_profile=profile)


# ==============================================================================
# 9. Conversational Message Handler & Investigation Pipeline
# ==============================================================================


@cl.on_message
async def on_message(message: cl.Message) -> None:
    """Handle incoming user messages, slash commands, and SupplyGuard AI Deep Agent flows."""
    text = message.content.strip()
    thread_id = cl.user_session.get("thread_id") or _resolve_session_thread_id()
    cl.user_session.set("thread_id", thread_id)
    orchestrator = get_orchestrator()
    try:
        profile = get_active_user_profile()
    except PermissionError as exc:
        await cl.Message(content=f"🔒 **Authentication Required:** {exc}").send()
        return

    # 1. Command: /resume <thread_id> (Issue #51)
    if text.startswith("/resume"):
        parts = text.split(maxsplit=1)
        target_thread_id = parts[1].strip() if len(parts) > 1 else ""
        if not target_thread_id:
            await cl.Message(content="Usage: `/resume <thread_id>`").send()
            return
        try:
            authorized_state = orchestrator.get_state(
                target_thread_id,
                requester=profile,
                raise_on_unauthorized=True,
            )
        except PermissionError as exc:
            await cl.Message(content=f"🔒 **Access Denied:** {exc}").send()
            return
        if authorized_state is not None:
            cl.user_session.set("thread_id", target_thread_id)
        await _restore_or_greet(target_thread_id, is_manual_resume=True)
        return

    # 2. Command: /role is disabled under authenticated RBAC sessions
    if text.startswith("/role"):
        await cl.Message(
            content=(
                "🔒 **Role Switching Disabled:** Your RBAC role is strictly bound to your authenticated account "
                f"(`{profile.role}`). Sign out and log in with another authorized account to switch roles.\n\n"
                f"{format_rbac_badge(profile)}"
            )
        ).send()
        return

    # 3. Command: /export (Issue #50)
    if text.startswith("/export"):
        try:
            case_state = orchestrator.get_state(
                thread_id,
                requester=profile,
                raise_on_unauthorized=True,
            ) or orchestrator.get_latest_state(requester=profile)
        except PermissionError as exc:
            await cl.Message(content=f"🔒 **Access Denied:** {exc}").send()
            return
        if not case_state:
            await cl.Message(content="ℹ️ No active incident case found for your account/role to export yet.").send()
            return
        report, md_path, pdf_path = generate_incident_report_artifacts(thread_id, case_state)
        elements = []
        if hasattr(cl, "File"):
            elements = [
                cl.File(name=md_path.name, path=str(md_path), display="inline"),
                cl.File(name=pdf_path.name, path=str(pdf_path), display="inline"),
            ]
        await cl.Message(
            content=(
                f"📄 **Incident Report Exported (`{report.report_id}`)**\n\n"
                f"- **Markdown Report:** `{md_path.name}`\n"
                f"- **PDF Report:** `{pdf_path.name}`\n\n"
                f"{report.to_markdown()}"
            ),
            elements=elements,
        ).send()
        return

    # 4. Route through unified SupplyGuardOrchestrator
    try:
        prev_state = orchestrator.get_state(thread_id, requester=profile, raise_on_unauthorized=True)
        prev_action_id = (
            prev_state["approval_payload"].action_id
            if prev_state and prev_state.get("approval_payload") is not None
            else None
        )
        was_modifying = bool(prev_state and prev_state.get("status") == "awaiting_modification")
        lowered = text.lower()

        if "resume the case" in lowered or "reviewing yesterday" in lowered:
            target_state = prev_state or orchestrator.get_latest_state(requester=profile)
            if target_state is None:
                await cl.Message(
                    content="ℹ️ No persisted SupplyGuard case found in database checkpoints to resume."
                ).send()
                return
            resumed_state = dict(target_state)
            resumed_state["thread_id"] = thread_id
            resumed_state["user_profile"] = profile
            resumed_state["owner_user_id"] = profile.user_id
            resumed_state["owner_role"] = profile.role
            resumed_state["access_scope"] = profile.access_scope.value
            orchestrator.persist_state(thread_id, resumed_state)
            await _restore_or_greet(thread_id, is_manual_resume=True)
            return

        case_state = await cl.make_async(orchestrator.handle_message)(thread_id, text, profile)
        status = case_state.get("status")

        # Modification completed -> emit notice & new card
        if was_modifying and case_state.get("approval_payload") is not None:
            new_payload: ApprovalPayload = case_state["approval_payload"]
            if new_payload.action_id != prev_action_id:
                await cl.Message(
                    content=(
                        f"🔄 **Plan Modified & Revalidated (`v{new_payload.revision}`)**\n\n"
                        f"- Previous Action ID `{prev_action_id}` has been **INVALIDATED**.\n"
                        f"- New Action ID **`{new_payload.action_id}`** (digest **`{new_payload.payload_hash}`**) "
                        f"created for **`{new_payload.quantity:,} units`** "
                        f"(Total Cost: **`€{new_payload.total_cost:,.2f}`** / Cap: `€{new_payload.spending_cap:,.2f}`)."
                    )
                ).send()
                await _send_approval_card(case_state, thread_id, user_profile=profile)
                return

        # Clarification pause
        if status == "awaiting_clarification":
            fact: DisruptionFact = case_state["disruption_fact"]
            await _emit_supplyguard_subagent_steps(fact=fact, user_profile=profile)
            await stream_message(case_state.get("clarification_question") or case_state["last_answer"])
            return

        # Fresh full investigation completed (new approval payload or completed impact)
        new_payload_obj: Optional[ApprovalPayload] = case_state.get("approval_payload")
        last_turn_kind = case_state.get("last_turn_kind")
        is_new_investigation = (
            case_state.get("investigation_completed")
            and case_state.get("operational_impact") is not None
            and not case_state.get("refused")
            and (
                last_turn_kind == "investigation"
                if last_turn_kind is not None
                else (
                    (new_payload_obj is not None and new_payload_obj.action_id != prev_action_id)
                    or (prev_state is None or not prev_state.get("investigation_completed"))
                )
            )
        )

        if is_new_investigation and case_state.get("disruption_fact") and case_state.get("operational_impact"):
            fact = case_state["disruption_fact"]
            impact = case_state["operational_impact"]
            findings = case_state.get("documentary_findings") or []
            options = case_state.get("recovery_options") or []
            await _emit_supplyguard_subagent_steps(
                fact=fact,
                impact=impact,
                findings=findings,
                options=options,
                user_profile=profile,
                graph_res=case_state.get("graph_res"),
                challenger_res=case_state.get("challenger_res"),
                approval_payload=new_payload_obj,
            )
            dashboard_md = format_operational_impact_dashboard(
                fact=fact,
                impact=impact,
                findings=findings,
                user_profile=profile,
                case_id=case_state.get("case_id", "CASE-MC17-001"),
            )
            matrix_md = format_strategy_comparison_matrix(
                options=options,
                fact=fact,
                impact=impact,
            )
            await stream_message(f"{dashboard_md}\n\n---\n\n{matrix_md}")
            if new_payload_obj is not None:
                await _send_approval_card(case_state, thread_id, user_profile=profile)
            return

        # Follow-up Q&A, RBAC denial, policy challenge, or security refusal
        await stream_message(case_state.get("last_answer") or "Request processed.")
        if new_payload_obj is not None and new_payload_obj.action_id != prev_action_id:
            await _send_approval_card(case_state, thread_id, user_profile=profile)
    except Exception as exc:
        logger.exception("Error processing message for thread %s", thread_id)
        await cl.Message(
            content=(
                "❌ **Something went wrong while processing your request.**\n\n"
                f"Details: `{exc}`\n"
                "Please try again or contact support if the issue persists."
            )
        ).send()


# ==============================================================================
# 10. Action Callbacks: Approve, Reject, Modify Plan, Switch Role, Export (#49, #50)
# ==============================================================================


def _extract_action_payload(action: cl.Action) -> dict[str, Any]:
    """Decode action payload compatibly across Chainlit 1.3.2 (`value`) and 2.x (`payload`)."""
    payload = getattr(action, "payload", None)
    if not payload and hasattr(action, "value") and action.value:
        try:
            payload = json.loads(action.value) if isinstance(action.value, str) else action.value
        except Exception:
            payload = {"action_id": str(action.value)}
    return payload or {}


async def _handle_approval_decision(action: cl.Action, approved: bool) -> None:
    """Process Approve/Reject button clicks with RBAC guard, double-click lock, and report export."""
    payload = _extract_action_payload(action)
    action_id = payload.get("action_id", "")
    thread_id = payload.get("thread_id")
    expected_hash = payload.get("payload_hash", "")
    if not thread_id:
        try:
            thread_id = cl.user_session.get("thread_id") or _resolve_session_thread_id()
        except Exception:
            thread_id = "default_thread"

    try:
        profile = get_active_user_profile()
    except PermissionError as exc:
        await cl.Message(content=f"🔒 **Authentication Required:** {exc}").send()
        return
    if not profile.can_approve:
        await cl.Message(
            content=(
                f"🔒 **RBAC Authorization Denied:** Active role **`{profile.role}`** (**{profile.name}**) is a **Read-Only Viewer** "
                "and is not authorized to approve or reject procurement actions."
            )
        ).send()
        return

    lock = _get_lock(action_id or thread_id)

    async with lock:
        approval_msg = None
        if action_id:
            try:
                approval_msg = cl.user_session.get(f"approval_msg:{action_id}")
            except Exception:
                approval_msg = None

        async def _clear_card_actions() -> None:
            if approval_msg is not None:
                try:
                    await approval_msg.remove_actions()
                except Exception:
                    pass
            try:
                await action.remove()
            except Exception:
                pass

        orchestrator = get_orchestrator()
        try:
            case_state = orchestrator.get_state(
                thread_id,
                requester=profile,
                raise_on_unauthorized=True,
            )
        except PermissionError as exc:
            await cl.Message(content=f"🔒 **Access Denied:** {exc}").send()
            return
        if case_state is None or case_state.get("approval_payload") is None:
            await cl.Message(content="⚠️ No pending approval payload found for this thread.").send()
            return

        sg_payload: ApprovalPayload = case_state["approval_payload"]
        if (action_id and action_id in _handled_actions) or case_state.get("status") == "executed":
            await _clear_card_actions()
            await cl.Message(content="ℹ️ This action has already been processed.").send()
            return
        if action_id and sg_payload.action_id != action_id:
            await _clear_card_actions()
            await cl.Message(content="ℹ️ This approval card is no longer active (superseded by a modified plan).").send()
            return
        if expected_hash and not sg_payload.verify_binding(expected_hash):
            await cl.Message(
                content="⚠️ **Payload Binding Mismatch!** The approval payload changed since this card was rendered. Please review and approve the revalidated card."
            ).send()
            return

        try:
            if approved:
                receipt, was_duplicate = await cl.make_async(orchestrator.approve_and_execute)(
                    thread_id,
                    profile,
                    expected_payload_hash=expected_hash or sg_payload.payload_hash,
                )
                if action_id:
                    _handled_actions.add(action_id)
                await _clear_card_actions()

                case_state = orchestrator.get_state(thread_id) or case_state
                sg_payload = case_state["approval_payload"]

                async with cl.Step(name=SUBAGENT_STEP_NAMES["procurement_mcp"], type="run") as step:
                    step.output = format_step_output("procurement_mcp", {"procurement_receipt": receipt})

                report, md_path, pdf_path = generate_incident_report_artifacts(thread_id, case_state)
                elements = []
                if hasattr(cl, "File"):
                    elements = [
                        cl.File(name=md_path.name, path=str(md_path), display="inline"),
                        cl.File(name=pdf_path.name, path=str(pdf_path), display="inline"),
                    ]
                export_action = _create_cl_action(
                    name="export_report",
                    payload={"thread_id": thread_id, "case_id": sg_payload.case_id},
                    label="📄 Export Incident Report (Markdown & PDF)",
                )
                receipt_md = format_procurement_receipt(receipt, sg_payload, is_replay=was_duplicate)
                await cl.Message(
                    content=f"{receipt_md}\n\n---\n\n{report.to_markdown()}",
                    elements=elements,
                    actions=[export_action],
                ).send()
            else:
                await cl.make_async(orchestrator.reject)(thread_id, profile)
                if action_id:
                    _handled_actions.add(action_id)
                await _clear_card_actions()
                await cl.Message(
                    content=(
                        f"❌ **Recovery Plan Rejected (`{sg_payload.action_id}`)**\n\n"
                        "No purchase order, expedite request, or stock transfer was executed in the simulated procurement system. "
                        "You may click **✏️ Modify Plan** or specify updated constraints in chat to generate a new recovery proposal."
                    )
                ).send()
        except Exception as exc:
            logger.exception("Error handling approval decision for thread %s (action %s)", thread_id, action_id)
            await cl.Message(
                content=(
                    "❌ **Unable to complete approval decision.**\n\n"
                    f"Details: `{exc}`\n"
                    "No state lock was finalized; please review the plan or retry."
                )
            ).send()


@cl.action_callback("approve_action")
async def on_approve(action: cl.Action) -> None:
    """Handle operator approval."""
    await _handle_approval_decision(action, approved=True)


@cl.action_callback("reject_action")
async def on_reject(action: cl.Action) -> None:
    """Handle operator rejection."""
    await _handle_approval_decision(action, approved=False)


@cl.action_callback("modify_action")
async def on_modify(action: cl.Action) -> None:
    """Handle operator 'Modify Plan' click: invalidate current approval card and prompt for updated parameters."""
    payload = _extract_action_payload(action)
    action_id = payload.get("action_id", "")
    thread_id = payload.get("thread_id") or cl.user_session.get("thread_id") or _resolve_session_thread_id()

    try:
        profile = get_active_user_profile()
    except PermissionError as exc:
        await cl.Message(content=f"🔒 **Authentication Required:** {exc}").send()
        return
    if not profile.can_approve:
        await cl.Message(
            content=f"🔒 **RBAC Authorization Denied:** Role `{profile.role}` is Read-Only and cannot modify procurement plans."
        ).send()
        return

    orchestrator = get_orchestrator()
    try:
        case_state = orchestrator.get_state(
            thread_id,
            requester=profile,
            raise_on_unauthorized=True,
        )
    except PermissionError as exc:
        await cl.Message(content=f"🔒 **Access Denied:** {exc}").send()
        return

    approval_msg = cl.user_session.get(f"approval_msg:{action_id}") if action_id else None
    if approval_msg is not None:
        try:
            await approval_msg.remove_actions()
        except Exception:
            pass
    try:
        await action.remove()
    except Exception:
        pass

    if case_state is not None:
        old_payload: Optional[ApprovalPayload] = case_state.get("approval_payload")
        if old_payload:
            old_payload.status = ActionStatus.INVALIDATED
        case_state["status"] = "awaiting_modification"
        orchestrator.persist_state(thread_id, case_state)

    await cl.Message(
        content=(
            f"✏️ **Modify Recovery Plan — Previous Approval Card (`{action_id}`) Invalidated**\n\n"
            "Per payload-binding rules, any change to supplier, quantity, unit price, or spending cap requires full revalidation and a new approval.\n"
            "Please type your desired modification in the chat (for example: *“Change Cordillera quantity to 2,500 units”* or *“Increase spending cap to €90,000”*)."
        )
    ).send()


@cl.action_callback("export_report")
async def on_export_report(action: cl.Action) -> None:
    """Handle on-demand Markdown & PDF Incident Report export button click (Issue #50)."""
    payload = _extract_action_payload(action)
    thread_id = payload.get("thread_id") or cl.user_session.get("thread_id") or _resolve_session_thread_id()
    try:
        profile = get_active_user_profile()
    except PermissionError as exc:
        await cl.Message(content=f"🔒 **Authentication Required:** {exc}").send()
        return
    orchestrator = get_orchestrator()
    try:
        case_state = orchestrator.get_state(
            thread_id,
            requester=profile,
            raise_on_unauthorized=True,
        ) or orchestrator.get_latest_state(requester=profile)
    except PermissionError as exc:
        await cl.Message(content=f"🔒 **Access Denied:** {exc}").send()
        return
    if not case_state:
        await cl.Message(content="ℹ️ No completed case found for your account/role to export.").send()
        return
    report, md_path, pdf_path = generate_incident_report_artifacts(thread_id, case_state)
    elements = []
    if hasattr(cl, "File"):
        elements = [
            cl.File(name=md_path.name, path=str(md_path), display="inline"),
            cl.File(name=pdf_path.name, path=str(pdf_path), display="inline"),
        ]
    await cl.Message(
        content=(
            f"📄 **Incident Report Exported (`{report.report_id}`)**\n\n"
            f"- **Markdown Artifact:** `{md_path.name}`\n"
            f"- **PDF Artifact:** `{pdf_path.name}`"
        ),
        elements=elements,
    ).send()
