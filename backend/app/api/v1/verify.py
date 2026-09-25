from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings
from app.core.errors import ApiError
from app.core.logging import get_logger
from app.schemas.verify import VerifyOut
from app.services.chain.web3_client import get_contract

logger = get_logger(__name__)
router = APIRouter(tags=["verify"])


@router.get("/verify/{token_id}", response_model=VerifyOut)
async def verify_credential(token_id: int) -> VerifyOut:
    """Public: institution-facing check of a Nominee Credential. Reads only
    from Sepolia (no Supabase / PII) per Implementation_Plan.md section 8.2
    and section 14 ("On-chain holds only hashes and state, never personal data")."""
    credential = get_contract("credential")
    registry = get_contract("registry")
    ledger = get_contract("ledger")

    if credential is None or registry is None:
        raise ApiError(
            "chain_not_configured",
            "Service unavailable",
            "Chain contracts are not configured on this server yet.",
            503,
        )

    try:
        locked = credential.functions.locked(token_id).call()
    except Exception as exc:
        raise ApiError("credential_not_found", "Not found", f"No credential found for token {token_id}.", 404) from exc

    try:
        # NomineeCredential.credentialData(tokenId) -> (vaultId, shareBps, releasedAt); see
        # contracts/src/NomineeCredential.sol -- no personal data, just the commitment.
        vault_id, share_bps, released_at = credential.functions.credentialData(token_id).call()
    except Exception:
        logger.warning("verify_credential_data_read_failed", token_id=token_id)
        vault_id, share_bps, released_at = None, None, None

    claim_events = []
    if ledger is not None and vault_id is not None:
        try:
            from app.services.chain.web3_client import get_w3

            w3 = get_w3()
            logs = ledger.events.ClaimEvent().get_logs(argument_filters={"vaultId": vault_id})
            for log in logs[:50]:
                args = log["args"]
                claim_events.append(
                    {
                        "status": args.get("status"),
                        "doc_hash": "0x" + args["docHash"].hex() if args.get("docHash") else None,
                        "at": args.get("at"),
                        "tx_hash": log["transactionHash"].hex() if hasattr(log["transactionHash"], "hex") else log["transactionHash"],
                    }
                )
        except Exception:
            logger.warning("verify_claim_events_failed", token_id=token_id)

    explorer_base = "https://sepolia.etherscan.io"
    return VerifyOut.model_validate(
        {
            "token_id": token_id,
            "valid": True,
            "locked": bool(locked),
            "vault_id": vault_id or 0,
            "share_bps": share_bps or 0,
            "released_at": released_at,
            "claim_events": claim_events,
            "explorer_url": f"{explorer_base}/token/{settings.CREDENTIAL_ADDRESS}?a={token_id}" if settings.CREDENTIAL_ADDRESS else None,
        }
    )
